"""Speech recognition that runs on your own PC (free, offline).

Uses Whisper through faster-whisper. Whisper isn't a streaming model, so we
make it feel live: while you talk, the phrase so far is re-transcribed every
fraction of a second and the typer updates the text (backspacing words that
changed). When you pause, the phrase gets one last, more careful pass.
"""
import logging
import os
import threading
import time

import numpy as np

log = logging.getLogger("local")

RATE = 16000

# size -> (label shown in Settings, approximate download)
MODEL_SIZES = {
    "tiny": ("Fast (for older PCs)", "75 MB"),
    "base": ("Balanced (recommended)", "145 MB"),
    "small": ("Best accuracy (needs a good PC)", "480 MB"),
}


def model_name(size, language):
    # English-only models are more accurate for English.
    return f"{size}.en" if language == "en" and size in ("tiny", "base", "small") else size


class SpeechModel:
    """Loads Whisper once and transcribes audio. Safe to call from any thread."""

    def __init__(self, size, language, models_dir, prompt="", threads=0):
        self.size = size
        self.language = language or None
        self.models_dir = models_dir
        self.prompt = prompt or None
        self.threads = threads or min(4, os.cpu_count() or 2)
        self._model = None
        self._lock = threading.Lock()

    @property
    def name(self):
        return model_name(self.size, self.language)

    def is_downloaded(self):
        # huggingface_hub stores models as models--Systran--faster-whisper-<name>
        folder = os.path.join(self.models_dir, f"models--Systran--faster-whisper-{self.name}")
        return os.path.isdir(os.path.join(folder, "snapshots"))

    def load(self):
        from faster_whisper import WhisperModel

        t = time.monotonic()
        self._model = WhisperModel(self.name, device="cpu", compute_type="int8",
                                   cpu_threads=self.threads, download_root=self.models_dir)
        log.info("speech model %s ready in %.1fs", self.name, time.monotonic() - t)

    def transcribe(self, audio, final):
        with self._lock:
            segments, _ = self._model.transcribe(
                audio,
                language=self.language,
                beam_size=5 if final else 1,
                temperature=0.0,
                condition_on_previous_text=False,
                without_timestamps=True,
                initial_prompt=self.prompt,
                vad_filter=False,  # we only send audio where we heard speech
            )
            return " ".join(s.text.strip() for s in segments).strip()


def drop_last_word(text):
    # The last word of a phrase still being spoken is usually half-heard.
    cut = text.rstrip().rfind(" ")
    return text[:cut] if cut > 0 else ""


class LocalSession:
    """One press of the hotkey. Same shape as before: send_audio / commit / finish."""

    def __init__(self, model, on_partial, on_completed, tag="", live=True,
                 partial_every_s=0.6, min_partial_s=0.8):
        self.model = model
        self.on_partial = on_partial
        self.on_completed = on_completed
        self.tag = tag
        self.live = live
        self.partial_every_s = partial_every_s
        self.min_partial_s = min_partial_s

        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._chunks = []          # audio of the phrase being spoken
        self._samples = 0
        self._decoded_at = 0       # sample count at the last live update
        self._finals = []          # finished phrases waiting for their final pass
        self._count = 0
        self._phrase_id = self._new_id()
        self._finishing = False
        self._stopped = False
        self.done = threading.Event()

    def _new_id(self):
        self._count += 1
        return f"{self.tag}{self._count}"

    def start(self):
        threading.Thread(target=self._run, name="speech", daemon=True).start()

    def send_audio(self, chunk):
        with self._lock:
            self._chunks.append(chunk)
            self._samples += len(chunk)
        self._wake.set()

    def commit(self):
        with self._lock:
            self._commit_locked()
        self._wake.set()

    def _commit_locked(self):
        if self._samples >= int(0.25 * RATE):
            self._finals.append((self._phrase_id, np.concatenate(self._chunks)))
            self._phrase_id = self._new_id()
        self._chunks, self._samples, self._decoded_at = [], 0, 0

    def finish(self):
        with self._lock:
            self._commit_locked()
            self._finishing = True
        self._wake.set()

    def abort(self):
        self._stopped = True
        self._wake.set()

    def _run(self):
        try:
            while not self._stopped:
                job = None
                with self._lock:
                    if self._finals:
                        job = ("final",) + self._finals.pop(0)
                    elif (self.live and self._samples >= self.min_partial_s * RATE
                          and self._samples - self._decoded_at >= self.partial_every_s * RATE):
                        self._decoded_at = self._samples
                        job = ("partial", self._phrase_id, np.concatenate(self._chunks))
                    elif self._finishing:
                        return
                if job is None:
                    self._wake.wait(0.1)
                    self._wake.clear()
                    continue
                kind, item_id, audio = job
                try:
                    text = self.model.transcribe(audio, final=(kind == "final"))
                except Exception:
                    log.exception("transcription failed")
                    text = None
                if kind == "final":
                    log.info("%s heard: %s", self.tag, text)
                    self.on_completed(item_id, text or "")
                elif text:
                    with self._lock:
                        still_current = item_id == self._phrase_id
                    if still_current:
                        self.on_partial(item_id, drop_last_word(text))
        finally:
            self.done.set()
