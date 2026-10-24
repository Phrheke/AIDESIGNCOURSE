"""Tests for the platform-independent parts. Run: python -m unittest discover tests"""
import os
import sys
import threading
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vk.audio import PreRoll, Resampler, VoiceDetector  # noqa: E402
from vk.local import LocalSession, drop_last_word, model_name  # noqa: E402
from vk.typer import Typer  # noqa: E402


class FakeKeys:
    """Simulates a text box receiving keystrokes."""

    def __init__(self):
        self.screen = ""
        self.backspaces = 0
        self.lock = threading.Lock()

    def type_text(self, text):
        with self.lock:
            self.screen += text

    def backspace(self, n):
        with self.lock:
            self.screen = self.screen[:-n] if n else self.screen
            self.backspaces += n

    def wait_for_modifiers_released(self):
        pass


def wait_idle(typer, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if typer.is_idle():
            time.sleep(0.05)
            return
        time.sleep(0.01)
    raise AssertionError("typer never went idle")


class TyperTest(unittest.TestCase):
    def setUp(self):
        self.keys = FakeKeys()
        self.typer = Typer(self.keys, delay_s=0)
        self.typer.start()

    def tearDown(self):
        self.typer.stop()

    def test_streams_deltas_and_spaces_phrases(self):
        t = self.typer
        t.new_session()
        for d in ["Hello", " there", " friend."]:
            t.on_delta("a", d)
        t.on_completed("a", "Hello there friend.")
        t.on_delta("b", "How are")
        t.on_delta("b", " you?")
        t.on_completed("b", "How are you?")
        wait_idle(t)
        self.assertEqual(self.keys.screen, "Hello there friend. How are you?")

    def test_final_transcript_corrects_with_backspace(self):
        t = self.typer
        t.new_session()
        t.on_delta("a", "I scream")
        wait_idle_partial = time.monotonic() + 1
        while self.keys.screen != "I scream" and time.monotonic() < wait_idle_partial:
            time.sleep(0.01)
        t.on_completed("a", "Ice cream")
        wait_idle(t)
        self.assertEqual(self.keys.screen, "Ice cream")
        self.assertGreater(self.keys.backspaces, 0)

    def test_partial_updates_replace_text(self):
        t = self.typer
        t.new_session()
        t.on_partial("a", "I scream")
        t.on_partial("a", "Ice cream is")
        t.on_completed("a", "Ice cream is great.")
        wait_idle(t)
        self.assertEqual(self.keys.screen, "Ice cream is great.")

    def test_newlines_never_typed(self):
        t = self.typer
        t.new_session()
        t.on_completed("a", "line one\nline two")
        wait_idle(t)
        self.assertNotIn("\n", self.keys.screen)

    def test_no_space_before_punctuation_and_no_leading_space(self):
        t = self.typer
        t.new_session()
        t.on_completed("a", "  Wait")
        t.on_completed("b", ", what?")
        wait_idle(t)
        self.assertEqual(self.keys.screen, "Wait, what?")

    def test_undo_removes_last_phrase(self):
        t = self.typer
        t.new_session()
        t.on_completed("a", "Keep this.")
        t.on_completed("b", "Delete this.")
        wait_idle(t)
        t.undo()
        wait_idle(t)
        self.assertEqual(self.keys.screen, "Keep this.")

    def test_new_session_has_no_leading_space(self):
        t = self.typer
        t.new_session()
        t.on_completed("a", "One.")
        wait_idle(t)
        t.new_session()
        t.on_completed("b", "Two.")
        wait_idle(t)
        self.assertEqual(self.keys.screen, "One.Two.")

    def test_empty_item_passes_session_start_on(self):
        t = self.typer
        t.new_session()
        t.on_completed("a", "")
        t.on_completed("b", "Hi")
        wait_idle(t)
        self.assertEqual(self.keys.screen, "Hi")

    def test_late_events_for_finished_items_ignored(self):
        t = self.typer
        t.new_session()
        t.on_completed("a", "Done.")
        wait_idle(t)
        t.on_delta("a", " extra")
        wait_idle(t)
        self.assertEqual(self.keys.screen, "Done.")

    def test_stalled_item_is_skipped_when_next_arrives(self):
        self.typer.stall_s = 0.1
        t = self.typer
        t.new_session()
        t.on_delta("a", "Stuck")   # never completes
        time.sleep(0.2)
        t.on_completed("b", "Next")
        wait_idle(t)
        self.assertEqual(self.keys.screen, "Stuck Next")


class AudioTest(unittest.TestCase):
    def test_resampler_rate_and_continuity(self):
        src = 48000
        r = Resampler(src)
        t = np.arange(src) / src
        sine = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        out = np.concatenate([r.process(sine[i:i + 1920]) for i in range(0, src, 1920)])
        self.assertLessEqual(abs(len(out) - 16000), 2)
        expected = np.sin(2 * np.pi * 440 * np.arange(len(out)) / 16000)
        self.assertLess(np.max(np.abs(out - expected)), 0.02)

    def test_resampler_odd_rate(self):
        r = Resampler(44100)
        out = np.concatenate([r.process(np.zeros(441, np.float32)) for _ in range(100)])
        self.assertLessEqual(abs(len(out) - 16000), 2)

    def test_voice_detector(self):
        vd = VoiceDetector()
        quiet = np.random.default_rng(0).normal(0, 0.001, 960).astype(np.float32)
        loud = np.sin(np.arange(960) / 5).astype(np.float32) * 0.2
        for _ in range(10):
            kind, _ = vd.feed(quiet)
        self.assertEqual(kind, "silence")
        self.assertEqual(vd.feed(loud)[0], "speech")
        kind, silence = vd.feed(quiet)
        self.assertEqual(kind, "silence")
        self.assertAlmostEqual(silence, 0.06, places=3)

    def test_preroll_keeps_recent_audio(self):
        p = PreRoll(seconds=0.1)
        for _ in range(20):
            p.push(np.zeros(960, np.float32))
        total = sum(len(c) for c in p.drain())
        self.assertGreaterEqual(total, 1600)
        self.assertLess(total, 1600 + 960)


class FakeModel:
    """Pretends to transcribe: one word per 0.5 s of audio."""
    WORDS = "the quick brown fox jumps over the lazy dog".split()
    name = "fake"

    def __init__(self):
        self.calls = []

    def transcribe(self, audio, final):
        self.calls.append(("final" if final else "partial", len(audio)))
        n = max(1, int(len(audio) / 16000 / 0.5))
        text = " ".join(self.WORDS[:n])
        return text.capitalize() + ("." if final else "")


class LocalSessionTest(unittest.TestCase):
    def run_session(self, live):
        keys = FakeKeys()
        typer = Typer(keys, delay_s=0)
        typer.start()
        typer.new_session()
        model = FakeModel()
        partial_screens = []

        def on_partial(item, text):
            typer.on_partial(item, text)
            partial_screens.append(text)

        s = LocalSession(model, on_partial, typer.on_completed, tag="s1:", live=live)
        s.start()
        chunk = np.zeros(1600, np.float32)  # 0.1 s
        for _ in range(25):                  # 2.5 s phrase
            s.send_audio(chunk)
            time.sleep(0.02)
        s.commit()
        for _ in range(10):                  # second phrase, 1 s
            s.send_audio(chunk)
        s.finish()
        self.assertTrue(s.done.wait(3))
        wait_idle(typer)
        typer.stop()
        return keys.screen, model.calls, partial_screens

    def test_live_session_types_partials_then_finals(self):
        screen, calls, partials = self.run_session(live=True)
        self.assertEqual(screen, "The quick brown fox jumps. The quick.")
        self.assertIn("partial", [c[0] for c in calls])
        self.assertEqual([c[0] for c in calls].count("final"), 2)
        # partials hide the last (possibly half-heard) word
        self.assertTrue(all(not p.endswith(".") for p in partials))

    def test_non_live_session_only_types_finals(self):
        screen, calls, _ = self.run_session(live=False)
        self.assertEqual(screen, "The quick brown fox jumps. The quick.")
        self.assertEqual([c[0] for c in calls], ["final", "final"])

    def test_tiny_blips_are_ignored(self):
        model = FakeModel()
        done = []
        s = LocalSession(model, lambda *a: None, lambda i, t: done.append(t), live=False)
        s.start()
        s.send_audio(np.zeros(1600, np.float32))  # 0.1 s click
        s.finish()
        self.assertTrue(s.done.wait(2))
        self.assertEqual(done, [])

    def test_helpers(self):
        self.assertEqual(drop_last_word("hello there frie"), "hello there")
        self.assertEqual(drop_last_word("hello"), "")
        self.assertEqual(model_name("base", "en"), "base.en")
        self.assertEqual(model_name("base", "es"), "base")
        self.assertEqual(model_name("small", ""), "small")


if __name__ == "__main__":
    unittest.main()
