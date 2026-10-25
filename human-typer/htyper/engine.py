"""Runs one typing job on a background thread: pause, resume, stop, progress."""
import threading
import time

from .timing import plan

SLICE = 0.03  # how often waits check for pause/stop


class TypingJob:
    """States: "typing", "paused", "stopped", "done"."""

    def __init__(self, text, keys, wpm, natural=True, typos="rare", on_update=None,
                 window=None, guard_window=False, seed=None):
        self.text = text.replace("\r\n", "\n").replace("\r", "\n")
        self.keys = keys
        self.steps = plan(self.text, wpm, natural, typos, seed)
        self.step = 0
        self.on_update = on_update or (lambda job: None)
        self.window = window  # dict with "current", "is_ours" callables
        self.guard_window = guard_window
        self.done_chars = 0
        self.state = "typing"
        self.pause_reason = ""
        self._target = None
        self._next = 0.0  # when the next key is due (time.monotonic)
        self._resume = threading.Event()
        self._resume.set()
        self._stop = False
        self._thread = None

    # ---- control (any thread) -------------------------------------------

    def start(self):
        self._thread = threading.Thread(target=self._run, name="typing", daemon=True)
        self._thread.start()

    def pause(self, reason="Paused"):
        if self.state == "typing":
            self.state, self.pause_reason = "paused", reason
            self._resume.clear()
            self.on_update(self)

    def resume(self):
        if self.state == "paused":
            self._target = None  # type into whatever window you're in now
            self._next = time.monotonic()  # carry on from now, no catch-up burst
            self.state, self.pause_reason = "typing", ""
            self._resume.set()
            self.on_update(self)

    def toggle_pause(self):
        if self.state == "paused":
            self.resume()
        else:
            self.pause()

    def stop(self):
        if self.state in ("typing", "paused"):
            self._stop = True
            self.state = "stopped"
            self._resume.set()
            self.on_update(self)

    def join(self, timeout=None):
        if self._thread:
            self._thread.join(timeout)

    # ---- progress -------------------------------------------------------

    @property
    def progress(self):
        return self.done_chars / len(self.text) if self.text else 1.0

    @property
    def seconds_left(self):
        return sum(s[0] for s in self.steps[self.step:])

    # ---- the loop -------------------------------------------------------

    def _wait_until_due(self):
        # Keys are scheduled on a running clock, so a sleep that runs a bit
        # long is made up on the next key instead of slowing the whole text.
        while not self._stop:
            self._resume.wait()
            left = self._next - time.monotonic()
            if left <= 0 or self._stop:
                return
            time.sleep(min(SLICE, left))

    def _check_window(self):
        if not self.window:
            return True
        hwnd = self.window["current"]()
        if self.window["is_ours"](hwnd):
            self.pause("Click into the app you want to type in, then press F8")
            return False
        if self._target is None:
            self._target = hwnd
        elif self.guard_window and hwnd != self._target:
            self.pause("You switched windows. Click back where it was typing, then press F8")
            return False
        return True

    def _run(self):
        last_update = 0.0
        self._next = time.monotonic()
        while self.step < len(self.steps) and not self._stop:
            delay, kind, ch, done = self.steps[self.step]
            self._next += delay
            self._wait_until_due()
            while not self._stop:
                self._resume.wait()
                if self._stop or self._check_window():
                    break
            if self._stop:
                break
            self.keys.wait_for_modifiers_released()
            if kind == "back":
                self.keys.backspace()
            else:
                self.keys.type_char(ch)
            self.step += 1
            self.done_chars = done
            now = time.monotonic()
            if now - last_update > 0.1:
                last_update = now
                self.on_update(self)
        if not self._stop:
            self.state = "done"
        self.on_update(self)
