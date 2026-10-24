"""Settings: stored as JSON in %APPDATA%\\VoiceKeyboard\\config.json."""
import json
import os
import sys

DEFAULTS = {
    # Speech model size: "tiny" (fast), "base" (balanced), "small" (most accurate).
    "model_size": "base",
    # Language code like "en", "es", "fr". Empty = auto-detect.
    "language": "en",
    # Optional hint: names, jargon or spellings the model should know about.
    "prompt": "",
    # Show words while you talk (True), or type each phrase after you pause (False).
    "live_typing": True,
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
    # Microphone name. null = Windows default microphone.
    "mic_device": None,
    # How long a pause ends a phrase (milliseconds).
    "silence_commit_ms": 700,
    # Force a phrase break after this many seconds of continuous speech.
    "max_phrase_seconds": 12,
    # Minimum mic level counted as speech (0..1). Raise it in noisy rooms.
    "vad_min_level": 0.004,
    # CPU threads for speech recognition. 0 = automatic.
    "cpu_threads": 0,
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
            saved = json.load(f)
        # Only keep settings this version knows about.
        cfg.update({k: v for k, v in saved.items() if k in DEFAULTS})
    # Write back so newly added settings show up in the file.
    save(cfg)
    return cfg


def save(cfg):
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def models_dir():
    path = os.path.join(app_dir(), "models")
    os.makedirs(path, exist_ok=True)
    return path
