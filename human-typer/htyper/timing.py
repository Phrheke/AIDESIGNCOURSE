"""How long to wait before each key, so typing has a human rhythm.

We first give every character a *relative* weight (common letter pairs are
quick, capitals and symbols are slower, sentences and new lines get a
breather), then scale all the waits so the whole text comes out at exactly
the chosen words-per-minute. "Words" use the typing-test standard of five
characters each.
"""
import random

# Letter pairs that trained fingers type in a quick roll.
FAST_PAIRS = set(
    "th he in er an re on at en nd ti es or te of ed is it al ar st to nt ng se "
    "ha as ou io le ve co me de hi ri ro ic ne ea ra ce li ch ll be ma si om ur".split())

SHIFTED = set('~!@#$%^&*()_+{}|:"<>?')
MIN_DELAY = 0.018  # nobody presses keys faster than ~55 per second


def describe_wpm(wpm):
    if wpm < 40:
        return "relaxed typist"
    if wpm < 60:
        return "average typist"
    if wpm < 90:
        return "professional typist"
    if wpm < 120:
        return "very fast typist"
    return "speed-typing champion"


def seconds_for(text, wpm):
    return len(text) * 12.0 / wpm


def _weight(prev, ch, rng, natural):
    w = rng.lognormvariate(0, 0.32)  # everyday unevenness
    if prev and (prev + ch).lower() in FAST_PAIRS:
        w *= 0.72
    if ch.isupper() or ch in SHIFTED:
        w *= 1.35  # reaching for Shift
    elif ch.isdigit() or not (ch.isalpha() or ch.isspace()):
        w *= 1.25
    if prev == " " and ch != " ":
        w *= 1.12  # starting a new word
    if natural and prev:
        if prev in ",;:":
            w += rng.uniform(1.2, 2.8)
        elif prev in ".!?":
            w += rng.uniform(2.5, 6.0)
        elif prev == "\n":
            w += rng.uniform(4.0, 10.0)
        elif prev == " " and rng.random() < 0.025:
            w += rng.uniform(4.0, 12.0)  # the odd moment to think
    return w


def plan_delays(text, wpm, natural=True, seed=None):
    """Seconds to wait before each character of text."""
    if not text:
        return []
    rng = random.Random(seed)
    weights = [_weight(text[i - 1] if i else "", ch, rng, natural) for i, ch in enumerate(text)]
    scale = seconds_for(text, wpm) / sum(weights)
    delays = [max(MIN_DELAY, w * scale) for w in weights]
    delays[0] = 0.0  # start right away
    return delays
