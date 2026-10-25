"""Run: python -m unittest discover tests"""
import os
import statistics
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from htyper import engine  # noqa: E402
from htyper.engine import TypingJob  # noqa: E402
from htyper.timing import MIN_DELAY, describe_wpm, plan_delays, seconds_for  # noqa: E402

SAMPLE = ("Hello Sarah, thanks for the update. I'll review the design files tonight!\n"
          "Can we move the call to 3pm tomorrow? Let me know what works for you.\n\n"
          "Best,\nDrey\t(sent from my laptop) #team @work 100% sure.") * 3


class FakeKeys:
    def __init__(self):
        self.typed = []

    def type_char(self, ch):
        self.typed.append(ch)

    def wait_for_modifiers_released(self):
        pass


class TimingTest(unittest.TestCase):
    def test_total_time_matches_wpm(self):
        for wpm in (40, 75, 120):
            delays = plan_delays(SAMPLE, wpm, seed=1)
            target = seconds_for(SAMPLE, wpm)
            self.assertAlmostEqual(sum(delays), target, delta=target * 0.03)

    def test_delays_vary_and_are_never_robotic(self):
        delays = plan_delays(SAMPLE, 75, seed=2)[1:]
        self.assertTrue(all(d >= MIN_DELAY for d in delays))
        self.assertGreater(len(set(round(d, 4) for d in delays)), len(delays) * 0.8)
        self.assertGreater(statistics.pstdev(delays) / statistics.mean(delays), 0.3)

    def test_natural_pauses_after_sentences_and_lines(self):
        delays = plan_delays(SAMPLE, 75, seed=3)
        after = lambda chars: statistics.mean(  # noqa: E731
            delays[i] for i in range(1, len(SAMPLE)) if SAMPLE[i - 1] in chars)
        normal = statistics.median(delays[1:])
        self.assertGreater(after(".!?"), normal * 2.5)
        self.assertGreater(after("\n"), normal * 3)
        self.assertGreater(after(","), normal * 1.5)

    def test_without_natural_pauses_rhythm_is_even(self):
        delays = plan_delays(SAMPLE, 75, natural=False, seed=4)[1:]
        self.assertLess(max(delays), statistics.median(delays) * 4)

    def test_different_every_run(self):
        self.assertNotEqual(plan_delays(SAMPLE, 75), plan_delays(SAMPLE, 75))

    def test_labels(self):
        self.assertEqual(describe_wpm(75), "professional typist")
        self.assertEqual(describe_wpm(30), "relaxed typist")


class EngineTest(unittest.TestCase):
    def run_job(self, text, wpm=4000, **kw):
        keys = FakeKeys()
        updates = []
        job = TypingJob(text, keys, wpm, on_update=lambda j: updates.append(j.state), **kw)
        job.start()
        return job, keys, updates

    def test_types_text_exactly(self):
        job, keys, updates = self.run_job(SAMPLE)
        job.join(len(SAMPLE) * MIN_DELAY * 2 + 5)
        self.assertEqual("".join(keys.typed), SAMPLE)
        self.assertEqual(job.state, "done")
        self.assertEqual(updates[-1], "done")

    def test_windows_line_endings_become_single_enter(self):
        job, keys, _ = self.run_job("a\r\nb\rc")
        job.join(5)
        self.assertEqual("".join(keys.typed), "a\nb\nc")

    def test_pause_resume_and_stop(self):
        job, keys, _ = self.run_job("x" * 400, wpm=300)
        time.sleep(0.3)
        job.pause()
        time.sleep(0.1)
        n = len(keys.typed)
        time.sleep(0.3)
        self.assertEqual(len(keys.typed), n, "kept typing while paused")
        self.assertEqual(job.state, "paused")
        job.resume()
        time.sleep(0.3)
        self.assertGreater(len(keys.typed), n)
        job.stop()
        job.join(2)
        self.assertEqual(job.state, "stopped")
        self.assertLess(len(keys.typed), 400)

    def test_pauses_when_window_changes_then_continues_in_new_one(self):
        current = {"hwnd": 1}
        window = {"current": lambda: current["hwnd"], "is_ours": lambda h: h == 99}
        job, keys, _ = self.run_job("y" * 200, wpm=600, window=window, guard_window=True)
        time.sleep(0.2)
        current["hwnd"] = 2
        time.sleep(0.2)
        self.assertEqual(job.state, "paused")
        self.assertIn("switched windows", job.pause_reason)
        n = len(keys.typed)
        job.resume()
        job.join(10)
        self.assertEqual(job.state, "done")
        self.assertEqual(len(keys.typed), 200)
        self.assertGreater(len(keys.typed), n)

    def test_never_types_into_its_own_window(self):
        window = {"current": lambda: 99, "is_ours": lambda h: h == 99}
        job, keys, _ = self.run_job("hello", window=window)
        time.sleep(0.2)
        self.assertEqual(job.state, "paused")
        self.assertEqual(keys.typed, [])
        job.stop()

    def test_real_speed_is_close_to_target(self):
        text = "The quick brown fox jumps over the lazy dog. " * 2
        wpm = 600
        job, keys, _ = self.run_job(text, wpm=wpm)
        t = time.monotonic()
        job.join(20)
        took = time.monotonic() - t
        target = seconds_for(text, wpm)
        self.assertLess(abs(took - target), target * 0.35 + engine.SLICE)


if __name__ == "__main__":
    unittest.main()
