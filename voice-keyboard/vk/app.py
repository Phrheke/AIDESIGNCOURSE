"""Ties microphone, transcription and typing together; owns the state."""
import itertools
import logging
import threading

from . import config
from .audio import Microphone, PreRoll, VoiceDetector, to_pcm16, TARGET_RATE
from .keys import Keyboard
from .realtime import RealtimeSession, is_live_model
from .typer import Typer

log = logging.getLogger("app")


class Controller:
    def __init__(self, cfg, notify, on_state, on_heard=None):
        self.cfg = cfg
        self.notify = notify          # notify(title, message)
        self.on_state = on_state      # on_state(listening: bool)
        self.on_heard = on_heard      # on_heard(final phrase text)
        self.listening = False
        self._lock = threading.Lock()
        self._mic = None
        self._session = None
        self._ids = itertools.count(1)
        self.typer = Typer(Keyboard())
        self.apply_config(cfg)
        self.typer.start()

    def apply_config(self, cfg):
        self.cfg = cfg
        self.typer.configure(
            delay_s=max(0, cfg["typing_delay_ms"]) / 1000.0,
            space_between=cfg["space_between_phrases"],
            space_at_session_start=cfg["space_at_session_start"],
            correct_on_final=cfg["correct_on_final"],
        )

    # ---- start / stop ---------------------------------------------------

    def toggle(self):
        with self._lock:
            if self.listening:
                self._stop()
            else:
                self._start()

    def stop(self):
        with self._lock:
            if self.listening:
                self._stop()

    def undo(self):
        self.typer.undo()

    def _start(self):
        key = config.api_key(self.cfg)
        if not key:
            self.notify("API key needed",
                        "Open Settings from the tray icon and paste your OpenAI API key.")
            return
        cfg = self.cfg
        live = is_live_model(cfg["model"])
        session = RealtimeSession(
            cfg, key, self.typer.on_delta, self._on_completed,
            lambda text: self._on_session_error(session, text),
            tag=f"s{next(self._ids)}:")
        detector = VoiceDetector(cfg["vad_min_level"])
        preroll = PreRoll()
        state = {"speaking": False, "phrase_s": 0.0}
        silence_limit = cfg["silence_commit_ms"] / 1000.0
        max_phrase = cfg["max_phrase_seconds"]

        def on_chunk(chunk):
            # Runs on the audio thread: keep it quick.
            kind, silence = detector.feed(chunk)
            if not live:
                # Server decides where phrases end; just stream everything.
                session.send_audio(to_pcm16(chunk))
                return
            if not state["speaking"]:
                # Don't upload silence; keep a short pre-roll instead.
                preroll.push(chunk)
                if kind == "speech":
                    state["speaking"] = True
                    state["phrase_s"] = 0.0
                    for c in preroll.drain():
                        session.send_audio(to_pcm16(c))
                return
            session.send_audio(to_pcm16(chunk))
            state["phrase_s"] += len(chunk) / TARGET_RATE
            if silence >= silence_limit:
                session.commit()
                state["speaking"] = False
            elif state["phrase_s"] >= max_phrase:
                session.commit()
                state["phrase_s"] = 0.0

        mic = Microphone(on_chunk, device=cfg["mic_device"])
        self.typer.new_session()
        session.start()
        try:
            name = mic.start()
        except Exception as e:
            session.abort()
            log.exception("microphone failed")
            self.notify("Microphone error", str(e))
            return
        log.info("listening on %s with %s", name, cfg["model"])
        self._mic, self._session = mic, session
        self.listening = True
        self.on_state(True)

    def _stop(self):
        self._mic.stop()
        self._session.finish()
        self._mic = self._session = None
        self.listening = False
        self.on_state(False)
        log.info("stopped listening")

    def _on_completed(self, item_id, transcript):
        self.typer.on_completed(item_id, transcript)
        if transcript and transcript.strip() and self.on_heard:
            self.on_heard(transcript.strip())

    def _on_session_error(self, session, text):
        self.notify("Voice Keyboard", text)
        if text.startswith("Transcription failed"):
            return  # one phrase was lost; the session still works
        # Auth/connection/config errors: stop the mic so the icon is honest.
        threading.Thread(target=self._stop_session, args=(session,), daemon=True).start()

    def _stop_session(self, session):
        with self._lock:
            if self.listening and self._session is session:
                self._stop()

    def shutdown(self):
        self.stop()
        self.typer.stop()
