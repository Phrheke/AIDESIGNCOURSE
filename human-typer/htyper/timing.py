"""Plans every keystroke: what to press and how long to wait before it.

- Speed: the chosen WPM is a ceiling. The pace drifts from word to word,
  mostly a little below it and now and then back up to it, never above.
  ("Words" use the typing-test standard of five characters.)
- Pauses: only around numbers and symbols (and after line breaks).
- Mistakes: now and then a word gets a neighbouring QWERTY key, the typist
  types on a key or two, notices, backspaces and fixes it.
"""
import random

# Letter pairs that trained fingers type in a quick roll.
FAST_PAIRS = set(
    "th he in er an re on at en nd ti es or te of ed is it al ar st to nt ng se "
    "ha as ou io le ve co me de hi ri ro ic ne ea ra ce li ch ll be ma si om ur".split())

# Keys next to each other on a QWERTY keyboard; same-row neighbours first,
# since those are the slips people make most.
NEIGHBOURS = {
    "q": "wa", "w": "qeas", "e": "wrds", "r": "etdf", "t": "ryfg", "y": "tugh",
    "u": "yihj", "i": "uojk", "o": "ipkl", "p": "ol", "a": "sqwz", "s": "adwexz",
    "d": "sferxc", "f": "dgrtcv", "g": "fhtyvb", "h": "gjyubn", "j": "hkuinm",
    "k": "jliom", "l": "kop", "z": "xas", "x": "zcsd", "c": "xvdf", "v": "cbfg",
    "b": "vngh", "n": "bmhj", "m": "njk",
}

# chance that a word gets a typo, by setting
TYPO_RATES = {"off": 0.0, "rare": 0.02, "sometimes": 0.045}
MIN_WORDS_BETWEEN_TYPOS = 8

PACE_LOW, PACE_HIGH, PACE_USUAL = 0.78, 1.0, 0.91
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


def is_symbol(ch):
    """Numbers and special characters: anything that isn't a letter or space."""
    return not ch.isalpha() and not ch.isspace()


def _segments(text):
    """Split into runs of non-space characters and single whitespace chars."""
    out, start = [], 0
    for i, ch in enumerate(text):
        if ch.isspace():
            if start < i:
                out.append((start, i))
            out.append((i, i + 1))
            start = i + 1
    if start < len(text):
        out.append((start, len(text)))
    return out


def _base_delays(text, wpm, natural, rng):
    """Wait before each character, before mistakes are added."""
    delays = [0.0] * len(text)
    pace = PACE_USUAL
    for start, end in _segments(text):
        if text[start].isspace() and text[start] != "\n":
            # Pace drifts between words: pulled back toward its usual level,
            # nudged at random, and never past the chosen speed.
            pace += 0.3 * (PACE_USUAL - pace) + rng.gauss(0, 0.035)
            pace = min(PACE_HIGH, max(PACE_LOW, pace))
        per_key = 12.0 / (wpm * pace)
        n = end - start
        if n == 1:
            weights = [rng.uniform(1.0, 1.25)]
        else:
            weights = []
            for i in range(start, end):
                w = rng.lognormvariate(0, 0.28)
                if i > start and (text[i - 1] + text[i]).lower() in FAST_PAIRS:
                    w *= 0.75
                weights.append(w)
            # Within a word keys speed up and slow down, but the word as a
            # whole is typed at exactly the current pace.
            total = sum(weights)
            weights = [w * n / total for w in weights]
        for k, i in enumerate(range(start, end)):
            delays[i] = per_key * weights[k]

    if natural:
        for i in range(1, len(text)):
            ch, prev = text[i], text[i - 1]
            per_key = 12.0 / (wpm * PACE_USUAL)
            extra = 0.0
            if is_symbol(ch) and not is_symbol(prev):
                extra += rng.uniform(0.8, 2.0)    # reaching for a number/symbol
            elif is_symbol(ch) and ch.isdigit():
                extra += rng.uniform(0.2, 0.6)    # numbers are slower to type
            if is_symbol(prev) and not is_symbol(ch):
                if prev in ".!?":
                    extra += rng.uniform(3.0, 6.0)  # end of a sentence
                elif prev in ",;:":
                    extra += rng.uniform(1.5, 3.0)
                else:
                    extra += rng.uniform(0.6, 1.8)  # back to letters
            if prev == "\n":
                extra += rng.uniform(4.0, 9.0)
            delays[i] += extra * per_key

    delays = [max(MIN_DELAY, d) for d in delays]
    if delays:
        delays[0] = 0.0  # start right away
    return delays


def _wrong_key(ch, rng):
    near = NEIGHBOURS.get(ch.lower())
    if not near:
        return None
    # the first two neighbours are on the same row: the most common slips
    wrong = rng.choice(near[:2]) if rng.random() < 0.8 else rng.choice(near)
    return wrong.upper() if ch.isupper() else wrong


def plan(text, wpm, natural=True, typos="rare", seed=None):
    """Steps to perform: (delay seconds, "type" or "back", character, done).

    `done` is how many characters of the real text are correctly typed after
    the step, for the progress bar.
    """
    rng = random.Random(seed)
    delays = _base_delays(text, wpm, natural, rng)
    rate = TYPO_RATES.get(typos, 0.0)
    per_key = 12.0 / (wpm * PACE_USUAL)
    steps = []
    since_typo = MIN_WORDS_BETWEEN_TYPOS
    i = 0
    for start, end in _segments(text):
        word = text[start:end]
        typo_at = None
        if (rate and sum(c.isalpha() for c in word) >= 3
                and since_typo >= MIN_WORDS_BETWEEN_TYPOS and rng.random() < rate):
            candidates = [k for k in range(start + 1, end) if text[k].lower() in NEIGHBOURS]
            if candidates:
                typo_at = rng.choice(candidates)
        if not word.isspace():
            since_typo += 1
        for i in range(start, end):
            if i == typo_at:
                wrong = _wrong_key(text[i], rng)
                # type the wrong key, maybe a key or two more, then notice
                run_on = min(rng.choice((0, 0, 1, 1, 2)), end - i - 1)
                steps.append((delays[i], "type", wrong, i))
                for k in range(1, run_on + 1):
                    steps.append((delays[i + k], "type", text[i + k], i))
                notice = per_key * rng.uniform(2.0, 4.5)
                for b in range(run_on + 1):
                    gap = notice if b == 0 else per_key * rng.uniform(0.5, 0.9)
                    steps.append((gap, "back", "", i))
                steps.append((per_key * rng.uniform(0.8, 1.4), "type", text[i], i + 1))
                since_typo = 0
            else:
                steps.append((delays[i], "type", text[i], i + 1))
    return steps


def total_seconds(steps):
    return sum(s[0] for s in steps)
