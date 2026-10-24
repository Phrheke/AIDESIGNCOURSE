"""Tests for the platform-independent parts. Run: python -m unittest discover tests"""
import os
import sys
import threading
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vk.audio import PreRoll, Resampler, VoiceDetector, to_pcm16  # noqa: E402
from vk.realtime import RealtimeSession, build_session_update  # noqa: E402
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
        self.assertLessEqual(abs(len(out) - 24000), 2)
        expected = np.sin(2 * np.pi * 440 * np.arange(len(out)) / 24000)
        self.assertLess(np.max(np.abs(out - expected)), 0.02)

    def test_resampler_odd_rate(self):
        r = Resampler(44100)
        out = np.concatenate([r.process(np.zeros(441, np.float32)) for _ in range(100)])
        self.assertLessEqual(abs(len(out) - 24000), 2)

    def test_pcm16(self):
        self.assertEqual(len(to_pcm16(np.zeros(10, np.float32))), 20)

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
        self.assertAlmostEqual(silence, 0.04, places=3)

    def test_preroll_keeps_recent_audio(self):
        p = PreRoll(seconds=0.1)
        for _ in range(20):
            p.push(np.zeros(960, np.float32))
        total = sum(len(c) for c in p.drain())
        self.assertGreaterEqual(total, 2400)
        self.assertLess(total, 2400 + 960)


class RealtimeTest(unittest.TestCase):
    def cfg(self, **kw):
        cfg = {"model": "gpt-live-transcribe", "language": "en", "prompt": "",
               "noise_reduction": None, "silence_commit_ms": 700,
               "realtime_url": "wss://example.invalid", "session_override": {},
               "extra_headers": {}}
        cfg.update(kw)
        return cfg

    def test_live_model_session(self):
        s = build_session_update(self.cfg())["session"]
        self.assertEqual(s["type"], "transcription")
        self.assertIsNone(s["audio"]["input"]["turn_detection"])
        self.assertEqual(s["audio"]["input"]["transcription"],
                         {"model": "gpt-live-transcribe", "language": "en"})

    def test_other_model_uses_server_vad(self):
        s = build_session_update(self.cfg(model="gpt-4o-transcribe"))["session"]
        self.assertEqual(s["audio"]["input"]["turn_detection"]["type"], "server_vad")

    def test_override_merges(self):
        s = build_session_update(self.cfg(session_override={
            "audio": {"input": {"format": {"rate": 16000}}}}))["session"]
        self.assertEqual(s["audio"]["input"]["format"], {"type": "audio/pcm", "rate": 16000})

    def test_events_reach_typer_callbacks(self):
        got, errors = [], []
        s = RealtimeSession(self.cfg(), "key", lambda i, d: got.append(("d", i, d)),
                            lambda i, t: got.append(("c", i, t)), errors.append, tag="s1:")
        s.handle_event({"type": "conversation.item.input_audio_transcription.delta",
                        "item_id": "x", "delta": "Hi"})
        s.handle_event({"type": "conversation.item.input_audio_transcription.completed",
                        "item_id": "x", "transcript": "Hi."})
        s.handle_event({"type": "error", "error": {"code": "input_audio_buffer_commit_empty",
                                                   "message": "buffer too small"}})
        self.assertEqual(got, [("d", "s1:x", "Hi"), ("c", "s1:x", "Hi.")])
        self.assertEqual(errors, [])
        s.handle_event({"type": "error", "error": {"code": "invalid_api_key", "message": "bad"}})
        self.assertEqual(errors, ["invalid_api_key: bad"])


if __name__ == "__main__":
    unittest.main()
