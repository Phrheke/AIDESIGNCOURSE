"""OpenAI Realtime transcription session over a WebSocket.

One RealtimeSession = one press of the hotkey. Audio is queued until the
socket is ready, so nothing you say while it connects is lost.
"""
import base64
import json
import logging
import queue
import threading
import time

import websocket

log = logging.getLogger("realtime")

# Models that stream text continuously and do not accept server turn detection.
LIVE_MODEL_PREFIXES = ("gpt-live", "gpt-realtime-whisper")
MIN_COMMIT_BYTES = 4800  # 100 ms of 24 kHz 16-bit audio


def is_live_model(model):
    return model.startswith(LIVE_MODEL_PREFIXES)


def _merge(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def build_session_update(cfg):
    transcription = {"model": cfg["model"]}
    if cfg.get("language"):
        transcription["language"] = cfg["language"]
    if cfg.get("prompt"):
        transcription["prompt"] = cfg["prompt"]
    audio_in = {
        "format": {"type": "audio/pcm", "rate": 24000},
        "transcription": transcription,
    }
    if cfg.get("noise_reduction"):
        audio_in["noise_reduction"] = {"type": cfg["noise_reduction"]}
    if is_live_model(cfg["model"]):
        audio_in["turn_detection"] = None  # we decide where phrases end
    else:
        audio_in["turn_detection"] = {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": int(cfg.get("silence_commit_ms", 700)),
        }
    session = {"type": "transcription", "audio": {"input": audio_in}}
    _merge(session, cfg.get("session_override") or {})
    return {"type": "session.update", "session": session}


class RealtimeSession:
    def __init__(self, cfg, api_key, on_delta, on_completed, on_error, tag=""):
        self.cfg = cfg
        self.on_delta = on_delta
        self.on_completed = on_completed
        self.on_error = on_error
        self.tag = tag  # makes item ids unique across sessions

        headers = [f"Authorization: Bearer {api_key}"]
        headers += [f"{k}: {v}" for k, v in (cfg.get("extra_headers") or {}).items()]
        self._ws = websocket.WebSocketApp(
            cfg["realtime_url"], header=headers,
            on_open=self._on_open, on_message=self._on_message,
            on_error=self._on_ws_error, on_close=self._on_close)

        self._out = queue.Queue()
        self._ready = threading.Event()
        self._closed = threading.Event()
        self._lock = threading.Lock()
        self._pending = set()      # items seen but not completed
        self._awaiting_commits = 0
        self._bytes_since_commit = 0
        self._error_reported = False

    # ---- public ---------------------------------------------------------

    def start(self):
        threading.Thread(target=self._ws.run_forever, name="ws",
                         kwargs={"ping_interval": 20, "ping_timeout": 10}, daemon=True).start()
        threading.Thread(target=self._sender, name="ws-send", daemon=True).start()

    def send_audio(self, pcm16):
        self._out.put(("audio", pcm16))

    def commit(self):
        self._out.put(("commit", None))

    def finish(self, timeout=8.0):
        """Flush remaining audio, wait for the last words, then disconnect."""
        self._out.put(("finish", timeout))

    def abort(self):
        self._closed.set()
        try:
            self._ws.close()
        except Exception:
            pass

    # ---- sending --------------------------------------------------------

    def _send(self, event):
        self._ws.send(json.dumps(event))

    def _do_commit(self):
        with self._lock:
            if self._bytes_since_commit < MIN_COMMIT_BYTES:
                return
            self._bytes_since_commit = 0
            self._awaiting_commits += 1
        self._send({"type": "input_audio_buffer.commit"})

    def _sender(self):
        while not self._ready.wait(0.1):
            if self._closed.is_set():
                return
        try:
            while not self._closed.is_set():
                try:
                    kind, arg = self._out.get(timeout=0.2)
                except queue.Empty:
                    continue
                if kind == "audio":
                    self._send({"type": "input_audio_buffer.append",
                                "audio": base64.b64encode(arg).decode("ascii")})
                    with self._lock:
                        self._bytes_since_commit += len(arg)
                elif kind == "commit":
                    self._do_commit()
                elif kind == "finish":
                    self._do_commit()
                    self._wait_for_results(arg)
                    break
        except Exception as e:
            if not self._closed.is_set():
                self._report(f"Connection lost: {e}")
        finally:
            self.abort()

    def _wait_for_results(self, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not self._closed.is_set():
            with self._lock:
                if self._awaiting_commits <= 0 and not self._pending:
                    return
            time.sleep(0.05)
        log.info("%s gave up waiting for final transcript", self.tag)

    # ---- receiving ------------------------------------------------------

    def _on_open(self, ws):
        log.info("%s connected", self.tag)
        self._send(build_session_update(self.cfg))
        # Fallback in case the server never confirms the session.
        threading.Timer(3.0, self._ready.set).start()

    def _on_message(self, ws, message):
        try:
            self.handle_event(json.loads(message))
        except Exception:
            log.exception("bad event: %.300s", message)

    def handle_event(self, evt):
        t = evt.get("type", "")
        if t in ("session.updated", "transcription_session.updated"):
            log.info("%s session ready", self.tag)
            self._ready.set()
        elif t == "conversation.item.input_audio_transcription.delta":
            item = self.tag + evt["item_id"]
            with self._lock:
                self._pending.add(item)
            self.on_delta(item, evt.get("delta", ""))
        elif t == "conversation.item.input_audio_transcription.completed":
            item = self.tag + evt["item_id"]
            with self._lock:
                self._pending.discard(item)
            log.info("%s heard: %s", self.tag, evt.get("transcript", ""))
            self.on_completed(item, evt.get("transcript"))
        elif t == "conversation.item.input_audio_transcription.failed":
            item = self.tag + evt["item_id"]
            with self._lock:
                self._pending.discard(item)
            self.on_completed(item, None)
            self._report("Transcription failed: " + json.dumps(evt.get("error", {})))
        elif t == "input_audio_buffer.committed":
            with self._lock:
                self._pending.add(self.tag + evt["item_id"])
                if self._awaiting_commits > 0:
                    self._awaiting_commits -= 1
                else:
                    self._bytes_since_commit = 0  # server-side VAD committed
        elif t == "error":
            err = evt.get("error", {})
            text = f"{err.get('code') or err.get('type')}: {err.get('message')}"
            if "commit" in text.lower() or "buffer too small" in text.lower():
                log.info("%s %s", self.tag, text)
                with self._lock:
                    self._awaiting_commits = max(0, self._awaiting_commits - 1)
            else:
                self._report(text)

    def _on_ws_error(self, ws, error):
        if not self._closed.is_set():
            self._report(f"Connection error: {error}")

    def _on_close(self, ws, code, reason):
        log.info("%s closed (%s %s)", self.tag, code, reason)
        if code and code != 1000 and not self._closed.is_set():
            self._report(f"Disconnected ({code}): {reason}")
        self._closed.set()

    def _report(self, text):
        log.error("%s %s", self.tag, text)
        if not self._error_reported:
            self._error_reported = True
            self.on_error(text)
