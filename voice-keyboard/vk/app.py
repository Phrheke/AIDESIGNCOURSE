"""Ties microphone, speech recognition and typing together; owns the state."""
import itertools
import logging
import threading

from . import config
from .audio import Microphone, PhraseSplitter
from .keys import Keyboard
from .local import MODEL_SIZES, LocalSession, SpeechModel
from .typer import Typer

log = logging.getLogger("app")


class Controller:
    def __init__(self, cfg, notify, on_state, on_heard=None, on_model=None):
        self.cfg = cfg
        self.notify = notify          # notify(title, message)
        self.on_state = on_state      # on_state(listening: bool)
        self.on_heard = on_heard      # on_heard(final phrase text)
        self.on_model = on_model      # on_model(status text, ready: bool)
        self.listening = False
        self.model = None
        self.model_ready = False
        self.model_status = "Loading speech model…"
        self._lock = threading.Lock()
        self._model_gen = 0
        self._mic = None
        self._session = None
        self._ids = itertools.count(1)
        self.typer = Typer(Keyboard())
        self.apply_config(cfg, reload_model=False)
        self.typer.start()

    def apply_config(self, cfg, reload_model=True):
        old = self.cfg
        self.cfg = cfg
        self.typer.configure(
            delay_s=max(0, cfg["typing_delay_ms"]) / 1000.0,
            space_between=cfg["space_between_phrases"],
            space_at_session_start=cfg["space_at_session_start"],
            correct_on_final=cfg["correct_on_final"],
        )
        if self.model is not None:
            self.model.prompt = cfg["prompt"] or None
            self.model.language = cfg["language"] or None
        if reload_model and self.model is not None and (
                SpeechModel(cfg["model_size"], cfg["language"], "").name != self.model.name
                or cfg["cpu_threads"] != old["cpu_threads"]):
            self.load_model()

    # ---- speech model ---------------------------------------------------

    def load_model(self):
        """Download (first time only) and load the speech model in the background."""
        cfg = self.cfg
        model = SpeechModel(cfg["model_size"], cfg["language"], config.models_dir(),
                            prompt=cfg["prompt"], threads=cfg["cpu_threads"])
        with self._lock:
            self._model_gen += 1
            gen = self._model_gen
            self.model_ready = False
        if model.is_downloaded():
            self._set_model_status("Loading speech model…", False)
        else:
            size = MODEL_SIZES.get(cfg["model_size"], ("", "?"))[1]
            self._set_model_status(
                f"Downloading speech model ({size}, one time only)…", False)

        def work():
            try:
                model.load()
            except Exception as e:
                log.exception("speech model failed to load")
                if gen == self._model_gen:
                    self._set_model_status(
                        "Couldn't load the speech model. Check your internet for the "
                        f"first-time download, then restart. ({e})", False)
                return
            with self._lock:
                if gen != self._model_gen:
                    return  # settings changed again meanwhile
                self.model = model
                self.model_ready = True
            self._set_model_status("Ready", True)

        threading.Thread(target=work, name="model-load", daemon=True).start()

    def _set_model_status(self, text, ready):
        self.model_status = text
        if self.on_model:
            self.on_model(text, ready)

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
        if not self.model_ready:
            self.notify("Voice Keyboard", self.model_status)
            return
        cfg = self.cfg
        session = LocalSession(self.model, self.typer.on_partial, self._on_completed,
                               tag=f"s{next(self._ids)}:", live=cfg["live_typing"])
        splitter = PhraseSplitter(session, cfg["vad_min_level"],
                                  cfg["silence_commit_ms"] / 1000.0, cfg["max_phrase_seconds"])
        mic = Microphone(splitter.feed, device=cfg["mic_device"])
        self.typer.new_session()
        session.start()
        try:
            name = mic.start()
        except Exception as e:
            session.abort()
            log.exception("microphone failed")
            self.notify("Microphone error", str(e))
            return
        log.info("listening on %s with %s", name, self.model.name)
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

    def shutdown(self):
        self.stop()
        self.typer.stop()
