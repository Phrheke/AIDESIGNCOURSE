"""End-to-end check with real speech and the real model.

Feeds a WAV file through the same path as the microphone (in real time, so
live typing kicks in) and checks what gets "typed".

    python tests/speech_check.py speech.wav "expected words" [model_size]
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np  # noqa: E402
from faster_whisper import decode_audio  # noqa: E402

from test_core import FakeKeys, wait_idle  # noqa: E402
from vk.audio import PhraseSplitter, TARGET_RATE  # noqa: E402
from vk.local import LocalSession, SpeechModel  # noqa: E402
from vk.typer import Typer  # noqa: E402


def words(text):
    return "".join(c.lower() if c.isalnum() else " " for c in text).split()


def main():
    wav, expected = sys.argv[1], sys.argv[2]
    size = sys.argv[3] if len(sys.argv) > 3 else "base"

    model = SpeechModel(size, "en", os.path.join(tempfile.gettempdir(), "vk-models"))
    t = time.monotonic()
    model.load()
    print(f"model {model.name} loaded in {time.monotonic() - t:.1f}s")

    audio = decode_audio(wav, sampling_rate=TARGET_RATE)
    # half a second of silence before, a second after
    audio = np.concatenate([np.zeros(TARGET_RATE // 2), audio, np.zeros(TARGET_RATE)])
    audio = audio.astype(np.float32)

    keys = FakeKeys()
    typer = Typer(keys, delay_s=0.005)
    typer.start()
    typer.new_session()
    partials = []

    def on_partial(item, text):
        partials.append(text)
        typer.on_partial(item, text)

    session = LocalSession(model, on_partial, typer.on_completed, tag="t:")
    session.start()
    splitter = PhraseSplitter(session)
    block = int(0.04 * TARGET_RATE)
    t = time.monotonic()
    for i in range(0, len(audio), block):
        splitter.feed(audio[i:i + block])
        time.sleep(0.04)  # real time, like a microphone
    session.finish()
    session.done.wait(60)
    wait_idle(typer, timeout=30)
    lag = time.monotonic() - t - len(audio) / TARGET_RATE

    print(f"live updates: {len(partials)}  -> {partials[:4]}")
    print(f"typed: {keys.screen!r}")
    print(f"finished {lag:.1f}s after the audio ended; backspaces used: {keys.backspaces}")
    missing = [w for w in words(expected) if w not in words(keys.screen)]
    if missing:
        print(f"FAIL: missing words {missing}")
        sys.exit(1)
    if not partials:
        print("FAIL: no live typing happened")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
