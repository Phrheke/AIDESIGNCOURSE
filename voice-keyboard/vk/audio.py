"""Microphone capture -> 24 kHz mono float chunks, plus a tiny voice detector."""
import collections

import numpy as np

TARGET_RATE = 24000


class Resampler:
    """Streaming linear resampler (keeps continuity between chunks)."""

    def __init__(self, src_rate, dst_rate=TARGET_RATE):
        self.step = src_rate / dst_rate
        self.pos = 0.0
        self.tail = np.zeros(0, dtype=np.float32)
        self.passthrough = src_rate == dst_rate

    def process(self, x):
        if self.passthrough:
            return x
        buf = np.concatenate([self.tail, x])
        last = len(buf) - 1
        if last < self.pos:
            self.tail = buf
            return np.zeros(0, dtype=np.float32)
        n = int((last - self.pos) / self.step) + 1
        idx = self.pos + np.arange(n) * self.step
        out = np.interp(idx, np.arange(len(buf)), buf).astype(np.float32)
        nxt = self.pos + n * self.step
        keep = int(nxt)
        self.tail = buf[keep:]
        self.pos = nxt - keep
        return out


def to_pcm16(x):
    return (np.clip(x, -1.0, 1.0) * 32767).astype("<i2").tobytes()


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0


class VoiceDetector:
    """Energy-based speech detection with an adaptive noise floor.

    feed() returns ("speech" | "silence", seconds_of_silence_so_far).
    """

    def __init__(self, min_level=0.004):
        self.min_level = min_level
        self.noise = 0.003
        self.silence_s = 0.0

    def feed(self, chunk):
        level = rms(chunk)
        threshold = max(self.min_level, self.noise * 3.0)
        dur = len(chunk) / TARGET_RATE
        if level > threshold:
            self.silence_s = 0.0
            return "speech", 0.0
        # Slowly follow the background noise level.
        self.noise = 0.95 * self.noise + 0.05 * level
        self.silence_s += dur
        return "silence", self.silence_s


class PreRoll:
    """Keeps the last few hundred ms of audio so word starts aren't clipped."""

    def __init__(self, seconds=0.35):
        self.max_samples = int(seconds * TARGET_RATE)
        self.chunks = collections.deque()
        self.samples = 0

    def push(self, chunk):
        self.chunks.append(chunk)
        self.samples += len(chunk)
        while self.chunks and self.samples - len(self.chunks[0]) >= self.max_samples:
            self.samples -= len(self.chunks.popleft())

    def drain(self):
        out = list(self.chunks)
        self.chunks.clear()
        self.samples = 0
        return out


class Microphone:
    def __init__(self, on_chunk, device=None, block_ms=40):
        self.on_chunk = on_chunk
        self.device = device
        self.block_ms = block_ms
        self._stream = None

    def start(self):
        import sounddevice as sd

        info = sd.query_devices(self.device, "input")
        rate = int(info["default_samplerate"])
        resampler = Resampler(rate)

        def callback(indata, frames, time_info, status):
            out = resampler.process(indata[:, 0].copy())
            if len(out):
                self.on_chunk(out)

        self._stream = sd.InputStream(
            device=self.device, samplerate=rate, channels=1, dtype="float32",
            blocksize=int(rate * self.block_ms / 1000), callback=callback)
        self._stream.start()
        return info["name"]

    def stop(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
