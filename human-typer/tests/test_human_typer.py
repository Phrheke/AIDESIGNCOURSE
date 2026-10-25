"""Run: python -m unittest discover tests"""
import os
import re
import statistics
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from htyper import engine  # noqa: E402
from htyper.engine import TypingJob  # noqa: E402
from htyper.timing import (MIN_DELAY, NEIGHBOURS, describe_wpm, is_symbol,  # noqa: E402
                           plan, total_seconds)

SAMPLE = ("Hello Sarah, thanks for the update. I'll review the design files tonight!\n"
          "Can we move the call to 3pm tomorrow? Let me know what works for you.\n\n"
          "Best,\nDrey\t(sent from my laptop) #team @work 100% sure.") * 3


class FakeKeys:
    """A pretend text box: typing appends, backspace deletes."""

    def __init__(self):
        self.typed = []
        self.screen = ""
        self.backspaces = 0

    def type_char(self, ch):
        self.typed.append(ch)
        self.screen += ch

    def backspace(self):
        self.backspaces += 1
        self.screen = self.screen[:-1]

    def wait_for_modifiers_released(self):
        pass


def replay(steps):
    keys = FakeKeys()
    for _, kind, ch, _ in steps:
        keys.backspace() if kind == "back" else keys.type_char(ch)
    return keys


LONG = ("Typing is a skill that improves with practice and patience over many "
        "weeks of steady work at the keyboard ") * 25


def word_speeds(text, steps, wpm):
    """Speed of each word (as a fraction of wpm), ignoring the first word."""
    delays = [s[0] for s in steps]
    out = []
    for m in re.finditer(r"[A-Za-z]+ ", text):
        if m.start() == 0:
            continue
        seconds = sum(delays[m.start():m.end()])
        out.append((len(m.group()) * 12 / seconds) / wpm)
    return out


class TimingTest(unittest.TestCase):
    def test_speed_drifts_below_the_chosen_wpm_but_never_above(self):
        for wpm in (45, 75, 110):
            speeds = word_speeds(LONG, plan(LONG, wpm, natural=False, typos="off", seed=1), wpm)
            self.assertLessEqual(max(speeds), 1.0 + 1e-9, "went faster than the chosen speed")
            self.assertGreater(min(speeds), 0.6)
            self.assertTrue(0.82 < statistics.mean(speeds) < 0.97, statistics.mean(speeds))
            self.assertGreater(max(speeds), 0.95, "never came back up near the top speed")
            self.assertGreater(statistics.pstdev(speeds), 0.02, "speed doesn't vary")

    def test_pace_changes_gradually_not_randomly(self):
        speeds = word_speeds(LONG, plan(LONG, 75, natural=False, typos="off", seed=2), 75)
        jumps = [abs(a - b) for a, b in zip(speeds, speeds[1:])]
        self.assertLess(statistics.mean(jumps), 0.12)

    def test_no_pauses_between_plain_words(self):
        steps = plan(LONG, 75, natural=True, typos="off", seed=3)
        per_key = 12 / 75
        self.assertLess(max(s[0] for s in steps), per_key * 4)

    def test_pauses_around_numbers_and_symbols(self):
        text = "Pay me 4500 dollars, today. Call 555-0199 or email a@b.co now please " * 10
        steps = plan(text, 75, natural=True, typos="off", seed=4)
        d = [s[0] for s in steps]
        letters = [d[i] for i in range(1, len(text))
                   if text[i].isalpha() and text[i - 1].isalpha()]
        into_symbol = [d[i] for i in range(1, len(text))
                       if is_symbol(text[i]) and not is_symbol(text[i - 1])]
        after_sentence = [d[i] for i in range(1, len(text)) if text[i - 1] == "."
                          and text[i] == " "]
        typical = statistics.median(letters)
        self.assertGreater(statistics.mean(into_symbol), typical * 1.8)
        self.assertGreater(statistics.mean(after_sentence), typical * 3)

    def test_new_lines_get_a_pause(self):
        text = "first line here\nsecond line here\n" * 10
        d = [s[0] for s in plan(text, 75, typos="off", seed=5)]
        after_nl = [d[i] for i in range(1, len(text)) if text[i - 1] == "\n"]
        self.assertGreater(statistics.mean(after_nl), 12 / 75 * 3)

    def test_final_text_is_exact_even_with_typos(self):
        for seed in range(20):
            keys = replay(plan(SAMPLE, 75, typos="sometimes", seed=seed))
            self.assertEqual(keys.screen, SAMPLE)

    def test_typos_are_occasional_neighbour_keys_and_get_fixed(self):
        steps = plan(LONG, 75, typos="rare", seed=6)
        typos = 0
        # count wrong keys: typed characters that don't match the text at that spot
        keys = FakeKeys()
        for _, kind, ch, _ in steps:
            if kind == "back":
                keys.backspace()
                continue
            pos = len(keys.screen)
            if LONG[pos] != ch:
                typos += 1
                self.assertIn(ch.lower(), NEIGHBOURS[LONG[pos].lower()])
            keys.type_char(ch)
        words = len(LONG.split())
        self.assertEqual(keys.screen, LONG)
        self.assertTrue(2 <= typos <= words * 0.05, f"{typos} typos in {words} words")
        self.assertGreater(keys.backspaces, 0)

    def test_typos_off_means_no_backspaces(self):
        steps = plan(LONG, 75, typos="off", seed=7)
        self.assertNotIn("back", [s[1] for s in steps])
        self.assertEqual("".join(s[2] for s in steps), LONG)

    def test_numbers_and_symbols_never_get_typos(self):
        text = "Order 12345 costs $99.95 (tax 7%) ref #A-77 " * 40
        for seed in range(5):
            steps = plan(text, 75, typos="sometimes", seed=seed)
            keys = FakeKeys()
            for _, kind, ch, _ in steps:
                if kind == "back":
                    keys.backspace()
                    continue
                pos = len(keys.screen)
                if text[pos] != ch:
                    self.assertTrue(text[pos].isalpha())
                keys.type_char(ch)

    def test_different_every_run(self):
        self.assertNotEqual(plan(SAMPLE, 75), plan(SAMPLE, 75))

    def test_labels(self):
        self.assertEqual(describe_wpm(75), "professional typist")
        self.assertEqual(describe_wpm(30), "relaxed typist")


class EngineTest(unittest.TestCase):
    def run_job(self, text, wpm=4000, **kw):
        keys = FakeKeys()
        updates = []
        kw.setdefault("typos", "off")
        job = TypingJob(text, keys, wpm, on_update=lambda j: updates.append(j.state), **kw)
        job.start()
        return job, keys, updates

    def test_types_text_exactly(self):
        job, keys, updates = self.run_job(SAMPLE, typos="sometimes")
        job.join(len(SAMPLE) * MIN_DELAY * 3 + 5)
        self.assertEqual(keys.screen, SAMPLE)
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
        target = total_seconds(job.steps)
        self.assertLess(abs(took - target), target * 0.35 + engine.SLICE)


if __name__ == "__main__":
    unittest.main()
