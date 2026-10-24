# Voice Keyboard (Windows)

Talk, and it types into **whatever app you're using**: browser, Word, Slack, WhatsApp Desktop, VS Code, and so on.
It acts like a keyboard: text appears **letter by letter** while you speak, and it **never presses Enter**.
Your text stays in the box until you review it and send it yourself.

- Types exactly what you say. No rewriting, no autocorrect. It uses OpenAI's live transcription, the same kind of model as ChatGPT's dictation.
- It's light. No AI runs on your PC. It's a small tray app (about 50 MB of RAM) that streams your mic to OpenAI.
- If the final transcript differs from the live guess, it backspaces and fixes the text, the way you'd fix a typo.

## Setup (once)

1. Install **Python 3.9 or newer** from <https://www.python.org/downloads/>.
   During install, tick **"Add python.exe to PATH"**.
2. Get an OpenAI API key at <https://platform.openai.com/api-keys>. Billing must be enabled. Transcription costs about $0.20–0.40 per hour of speech.
3. Download this `voice-keyboard` folder and double-click **`run.bat`**.
   The first run installs everything into a private `.venv` folder.
4. A settings file opens in Notepad. Paste your key between the quotes on the `"api_key"` line, then save.
5. Right-click the **microphone icon** in the tray (bottom-right, maybe under the `^` arrow) and choose **Reload settings**.

## Use it

| Action | Shortcut |
|---|---|
| Start / stop listening | **Ctrl + Shift + Space** (or click the tray icon) |
| Delete the last phrase it typed | **Ctrl + Shift + Backspace** |

1. Click into any text box.
2. Press **Ctrl+Shift+Space**. You'll hear a high beep and the icon turns **red**.
3. Talk. Words appear as you speak.
4. Press **Ctrl+Shift+Space** again to stop (low beep). Any last words still finish typing.

Tip: don't click into another window while it's typing. Like a real keyboard, it types into whatever window has focus.

**Start with Windows:** right-click the tray icon and tick **Start with Windows**.

## Settings

Tray icon → **Settings…** opens `%APPDATA%\VoiceKeyboard\config.json`. After editing, choose **Reload settings**.

| Setting | What it does |
|---|---|
| `model` | `gpt-live-transcribe` (default) streams words while you talk. `gpt-4o-transcribe` types each phrase after you pause and can be slightly more accurate. |
| `language` | `"en"`, `"es"`, `"fr"`, … or `""` to auto-detect. |
| `prompt` | Names and jargon to spell correctly, e.g. `"Figma, Webflow, Phrheke"`. |
| `hotkey_toggle`, `hotkey_undo` | For example `"<ctrl>+<alt>+d"` or `"<f9>"`. |
| `typing_delay_ms` | Pause between letters. `0` is fastest; `30` looks more like human typing. |
| `space_between_phrases` | Adds a space between phrases automatically. |
| `space_at_session_start` | Adds a space before the first words each time you start, useful when continuing a sentence. |
| `correct_on_final` | Lets it backspace to fix text when the final transcript differs. |
| `silence_commit_ms` | How long a pause ends a phrase. |
| `vad_min_level` | Raise it (e.g. `0.01`) if background noise keeps it "hearing" things. |
| `mic_device` | `null` uses the Windows default mic, or set part of the mic's name, e.g. `"Headset"`. |
| `noise_reduction` | `"near_field"` for headsets and laptop mics, `"far_field"` for room mics. |
| `beep` | Turns the start/stop beeps on or off. |

## Make a standalone .exe (optional)

Double-click **`build.bat`**. You get `dist\VoiceKeyboard.exe`, which runs without Python.
Copy it anywhere and pin it, or use **Start with Windows**.

## Troubleshooting

- **Nothing types:** open the tray menu → **Open log**. Usually it's a wrong API key or no billing on the OpenAI account.
- **Doesn't type into one specific app:** apps running *as administrator* ignore normal apps. Run Voice Keyboard as administrator too.
- **Wrong microphone:** set `mic_device`, or change the default mic in Windows Sound settings.
- **Words get cut off at the start:** lower `vad_min_level` (e.g. `0.002`).
- **The hotkey clashes with another app:** change `hotkey_toggle`.

## How it works

```
hotkey → microphone → voice detector → OpenAI live transcription (WebSocket)
                                              ↓ word-by-word text
                 your app ← SendInput (Windows fake keyboard) ← typer (letter by letter, fixes)
```

- `voice_keyboard.py`: tray icon, hotkeys, Start with Windows.
- `vk/app.py`: start/stop logic; decides where phrases end.
- `vk/audio.py`: mic capture, resampling to 24 kHz, voice detection.
- `vk/realtime.py`: OpenAI Realtime transcription connection.
- `vk/typer.py`: turns the text stream into keystrokes and corrections.
- `vk/keys.py`: Windows `SendInput` keystrokes.

Run the tests with `python -m unittest discover tests`.
