"""Settings: stored as JSON in %APPDATA%\\VoiceKeyboard\\config.json."""
import json
import os
import sys

DEFAULTS = {
    # Your OpenAI API key. Leave empty to use the OPENAI_API_KEY environment variable.
    "api_key": "",
    # gpt-live-transcribe streams words while you talk. Any other model
    # (e.g. gpt-4o-transcribe) types each phrase after you pause.
    "model": "gpt-live-transcribe",
    # Language code like "en", "es", "fr". Empty = auto-detect.
    "language": "en",
    # Optional hint: names, jargon or spellings the model should know about.
    "prompt": "",
    "hotkey_toggle": "<ctrl>+<shift>+<space>",
    "hotkey_undo": "<ctrl>+<shift>+<backspace>",
    # Pause between typed letters. 0 = as fast as possible.
    "typing_delay_ms": 12,
    # Put a space between phrases automatically.
    "space_between_phrases": True,
    # Put a space before the very first phrase after you start listening.
    "space_at_session_start": False,
    # When the final transcript differs from the live one, backspace and fix it.
    "correct_on_final": True,
    "beep": True,
    # Microphone name or index. null = Windows default microphone.
    "mic_device": None,
    # How long a pause ends a phrase (milliseconds).
    "silence_commit_ms": 700,
    # Force a phrase break after this many seconds of continuous speech.
    "max_phrase_seconds": 20,
    # Minimum mic level counted as speech (0..1). Raise it in noisy rooms.
    "vad_min_level": 0.004,
    # "near_field" (headset/laptop mic), "far_field", or null to disable.
    "noise_reduction": None,
    "realtime_url": "wss://api.openai.com/v1/realtime?intent=transcription",
    # Escape hatches in case the API changes: merged into the session config / headers.
    "session_override": {},
    "extra_headers": {},
}


def app_dir():
    base = os.environ.get("APPDATA") if sys.platform == "win32" else None
    path = os.path.join(base, "VoiceKeyboard") if base else os.path.expanduser("~/.voicekeyboard")
    os.makedirs(path, exist_ok=True)
    return path


def config_path():
    return os.path.join(app_dir(), "config.json")


def log_path():
    return os.path.join(app_dir(), "voicekeyboard.log")


def load():
    """Load settings, creating the file with defaults on first run."""
    path = config_path()
    cfg = dict(DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig") as f:
            cfg.update(json.load(f))
    # Write back so newly added settings show up in the file.
    save(cfg)
    return cfg


def save(cfg):
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def api_key(cfg):
    return (cfg.get("api_key") or os.environ.get("OPENAI_API_KEY") or "").strip()
