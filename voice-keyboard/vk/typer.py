"""Turns streaming transcript updates into keystrokes, one letter at a time.

Each spoken phrase is an "item" with an id from the API. Items are typed in
the order they first appear. While an item is being typed we keep what is on
screen (`typed`) and what it should become (`target`); each step either types
the next letter or, if the transcript changed its mind, backspaces the part
that no longer matches -- just like a person fixing a typo.
"""
import threading
import time

# Never put an automatic space before these.
NO_SPACE_BEFORE = set(".,!?;:)]}%…")


def clean(text):
    # Newlines would press Enter and could send your message. Never type them.
    return text.replace("\r", " ").replace("\n", " ").replace("\t", " ")


def common_prefix_len(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


class _Item:
    def __init__(self, session_start):
        self.text = ""
        self.done = False
        self.prefix = None  # decided when the first letter is typed
        self.typed = ""
        self.session_start = session_start
        self.last_change = time.monotonic()


class Typer:
    def __init__(self, keys, delay_s=0.012, space_between=True,
                 space_at_session_start=False, correct_on_final=True, stall_s=4.0):
        self.keys = keys
        self.delay_s = delay_s
        self.space_between = space_between
        self.space_at_session_start = space_at_session_start
        self.correct_on_final = correct_on_final
        self.stall_s = stall_s

        self._cond = threading.Condition()
        self._items = {}
        self._order = []       # ids still to be typed, oldest first
        self._finished = set()
        self._history = []     # text of each finished phrase, for undo
        self._last_char = None
        self._fresh = True     # next new item starts a listening session
        self._undo = 0
        self._running = False
        self._thread = None

    # ---- called from other threads -------------------------------------

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, name="typer", daemon=True)
        self._thread.start()

    def stop(self):
        with self._cond:
            self._running = False
            self._cond.notify_all()

    def configure(self, **kwargs):
        with self._cond:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def new_session(self):
        with self._cond:
            self._fresh = True

    def on_delta(self, item_id, delta):
        with self._cond:
            item = self._get(item_id)
            if item is None or item.done:
                return
            item.text += delta
            item.last_change = time.monotonic()
            self._cond.notify_all()

    def on_completed(self, item_id, transcript):
        with self._cond:
            item = self._get(item_id)
            if item is None:
                return
            if transcript is not None and (self.correct_on_final or not item.typed):
                item.text = transcript
            item.done = True
            item.last_change = time.monotonic()
            self._cond.notify_all()

    def undo(self):
        with self._cond:
            self._undo += 1
            self._cond.notify_all()

    def is_idle(self):
        with self._cond:
            return not self._order and not self._undo

    # ---- internals (lock held) ------------------------------------------

    def _get(self, item_id):
        if item_id in self._finished:
            return None
        item = self._items.get(item_id)
        if item is None:
            item = _Item(self._fresh)
            self._fresh = False
            self._items[item_id] = item
            self._order.append(item_id)
        return item

    def _target(self, item):
        body = clean(item.text).lstrip()
        if not body:
            return ""
        if item.prefix is None:
            if item.session_start:
                want_space = self.space_at_session_start
            else:
                last = self._last_char
                want_space = self.space_between and last is not None and not last.isspace()
            item.prefix = " " if want_space and body[0] not in NO_SPACE_BEFORE else ""
        return item.prefix + body

    def _finish_current(self):
        item_id = self._order.pop(0)
        item = self._items.pop(item_id)
        self._finished.add(item_id)
        if item.typed:
            self._history.append(item.typed)
            self._last_char = item.typed[-1]
        elif item.session_start:
            # Nothing was said in this item; hand "session start" to the next one.
            if self._order:
                self._items[self._order[0]].session_start = True
            else:
                self._fresh = True

    def _next_action(self):
        """Return ("type", ch), ("back", n) or None. Updates state optimistically."""
        if not self._order:
            if self._undo:
                self._undo = 0 if not self._history else self._undo - 1
                if self._history:
                    text = self._history.pop()
                    self._last_char = self._history[-1][-1] if self._history else None
                    return ("back", len(text))
            return None

        item = self._items[self._order[0]]
        target = self._target(item)
        typed = item.typed
        i = common_prefix_len(typed, target)
        if i < len(typed):
            item.typed = typed[:i]
            return ("back", len(typed) - i)
        if len(typed) < len(target):
            ch = target[len(typed)]
            item.typed += ch
            return ("type", ch)

        stalled = len(self._order) > 1 and time.monotonic() - item.last_change > self.stall_s
        if item.done or stalled:
            self._finish_current()
            return self._next_action()
        return None

    def _run(self):
        while True:
            with self._cond:
                if not self._running:
                    return
                action = self._next_action()
                if action is None:
                    self._cond.wait(0.25)
                    continue
            kind, arg = action
            self.keys.wait_for_modifiers_released()
            if kind == "type":
                self.keys.type_text(arg)
                if self.delay_s:
                    time.sleep(self.delay_s)
            else:
                self.keys.backspace(arg)
