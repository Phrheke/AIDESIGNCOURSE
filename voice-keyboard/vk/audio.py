"""Microphone capture -> 16 kHz mono float chunks, plus a tiny voice detector."""
import collections

import numpy as np

TARGET_RATE = 16000  # what Whisper expects


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


class PhraseSplitter:
    """Feeds mic audio to a session, skipping silence and ending phrases at pauses."""

    def __init__(self, session, min_level=0.004, silence_s=0.7, max_phrase_s=12):
        self.session = session
        self.detector = VoiceDetector(min_level)
        self.preroll = PreRoll()
        self.silence_s = silence_s
        self.max_phrase_s = max_phrase_s
        self.speaking = False
        self.phrase_s = 0.0

    def feed(self, chunk):
        kind, silence = self.detector.feed(chunk)
        if not self.speaking:
            # Skip silence; keep a short pre-roll so word starts aren't cut.
            self.preroll.push(chunk)
            if kind == "speech":
                self.speaking = True
                self.phrase_s = 0.0
                for c in self.preroll.drain():
                    self.session.send_audio(c)
            return
        self.session.send_audio(chunk)
        self.phrase_s += len(chunk) / TARGET_RATE
        if silence >= self.silence_s:
            self.session.commit()
            self.speaking = False
        elif self.phrase_s >= self.max_phrase_s:
            self.session.commit()
            self.phrase_s = 0.0


def list_microphones():
    """Names of input devices, using the same driver type as the default mic
    (Windows lists every mic once per driver, which would show duplicates)."""
    import sounddevice as sd

    try:
        default_api = sd.query_devices(kind="input")["hostapi"]
    except Exception:
        default_api = None
    names = []
    for dev in sd.query_devices():
        if dev["max_input_channels"] > 0 and dev["hostapi"] in (default_api, None):
            if dev["name"] not in names:
                names.append(dev["name"])
    return names


def resolve_device(device):
    """Turn a saved mic name into a device index; None means the default mic."""
    if device is None or isinstance(device, int) or device == "":
        return device if device != "" else None
    import sounddevice as sd

    try:
        default_api = sd.query_devices(kind="input")["hostapi"]
    except Exception:
        default_api = None
    matches = [(i, d) for i, d in enumerate(sd.query_devices())
               if d["max_input_channels"] > 0 and str(device).lower() in d["name"].lower()]
    if not matches:
        return None  # mic unplugged: fall back to the default one
    matches.sort(key=lambda m: m[1]["hostapi"] != default_api)
    return matches[0][0]


class Microphone:
    def __init__(self, on_chunk, device=None, block_ms=40):
        self.on_chunk = on_chunk
        self.device = device
        self.block_ms = block_ms
        self._stream = None

    def start(self):
        import sounddevice as sd

        device = resolve_device(self.device)
        info = sd.query_devices(device, "input")
        rate = int(info["default_samplerate"])
        resampler = Resampler(rate)

        def callback(indata, frames, time_info, status):
            out = resampler.process(indata[:, 0].copy())
            if len(out):
                self.on_chunk(out)

        self._stream = sd.InputStream(
            device=device, samplerate=rate, channels=1, dtype="float32",
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
