# Voice Keyboard (Windows)

Talk, and it types into **whatever app you're using**: browser, Word, Slack, WhatsApp Desktop, VS Code, and so on.
It acts like a keyboard: text appears **letter by letter** while you speak, and it **never presses Enter**.
Your text stays in the box until you review it and send it yourself.

- Types exactly what you say. No rewriting, no autocorrect. It uses OpenAI's live transcription, the same kind of model as ChatGPT's dictation.
- It's light. No AI runs on your PC. It's a small tray app (about 50 MB of RAM) that streams your mic to OpenAI.
- If the final transcript differs from the live guess, it backspaces and fixes the text, the way you'd fix a typo.

## Download and run (easiest)

1. Download **VoiceKeyboard.exe** from
   <https://github.com/Phrheke/AIDESIGNCOURSE/releases/download/voice-keyboard-latest/VoiceKeyboard.exe>
2. Double-click it. If Windows says **"Windows protected your PC"**, click **More info → Run anyway**.
   The app isn't code-signed, which is normal for small personal apps.
3. The Voice Keyboard window opens on **Settings**. Paste your OpenAI API key and click **Save**.
   Get a key at <https://platform.openai.com/api-keys>. Billing must be enabled. It costs about $0.20–0.40 per hour of speech.

No Python or installing needed. Put the .exe anywhere, e.g. your Desktop.

## Use it

| Action | Shortcut |
|---|---|
| Start / stop listening | **Ctrl + Shift + Space**, or the big button in the window |
| Delete the last phrase it typed | **Ctrl + Shift + Backspace** |

1. Click into any text box in any app.
2. Press **Ctrl+Shift+Space**. You'll hear a high beep and the tray mic icon turns **red**.
3. Talk. Words appear as you speak.
4. Press **Ctrl+Shift+Space** again to stop (low beep).

Closing the window keeps it running in the tray (bottom-right, near the clock).
Right-click the tray mic icon → **Quit** to exit fully.
Every phrase it heard is listed on the Home page, so you can copy it again if needed.

## Run from source instead (optional)

Install Python 3.9+ from python.org (tick "Add python.exe to PATH") and double-click **`run.bat`**.
To build the .exe yourself, double-click **`build.bat`**.

## Settings

Everything common is on the **Settings** page of the window. Advanced options live in
`%APPDATA%\VoiceKeyboard\config.json`; restart the app after editing that file.

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

## Troubleshooting

- **Nothing types:** Settings → **Open log**. Usually it's a wrong API key or no billing on the OpenAI account.
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

- `voice_keyboard.py`: starts the app; tray icon, hotkeys, Start with Windows.
- `vk/ui.py`: the window (Home + Settings).
- `vk/app.py`: start/stop logic; decides where phrases end.
- `vk/audio.py`: mic capture, resampling to 24 kHz, voice detection.
- `vk/realtime.py`: OpenAI Realtime transcription connection.
- `vk/typer.py`: turns the text stream into keystrokes and corrections.
- `vk/keys.py`: Windows `SendInput` keystrokes.

Run the tests with `python -m unittest discover tests`.
