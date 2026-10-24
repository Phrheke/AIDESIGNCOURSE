# Voice Keyboard (Windows) - free and offline

Talk, and it types into **whatever app you're using**: browser, Word, WhatsApp Desktop, Slack, VS Code, and so on.
It acts like a keyboard: text appears **letter by letter** while you speak, and it **never presses Enter**.
Your text stays in the box until you send it yourself.

- **Free.** No account, no API key, no subscription.
- **Private and offline.** Speech is recognised on your own PC by Whisper, a free open-source speech model. Nothing is sent anywhere.
- **Types what you say.** No rewriting, no autocorrect.
- It fixes words as it hears more, by backspacing and retyping them like a person correcting a typo.

## Download and run

1. Download **VoiceKeyboard.exe**:
   <https://github.com/Phrheke/AIDESIGNCOURSE/releases/download/voice-keyboard-latest/VoiceKeyboard.exe>
2. Double-click it. If Windows says **"Windows protected your PC"**, click **More info → Run anyway**.
   The app isn't code-signed, which is normal for small personal apps.
3. The first time, it downloads the speech model once (about 145 MB), so you need internet for that.
   The window shows **Getting ready…** until it's done. After that it works with no internet.

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
Everything it heard is listed on the Home page, so you can copy it again.

## Settings

| Setting | What it does |
|---|---|
| Accuracy | **Fast** (tiny model, for older PCs), **Balanced** (default) or **Best** (small model, needs a good PC). Each is downloaded once when you pick it. |
| Language | English, Spanish, French, Yoruba, … or auto-detect. |
| Microphone | Which mic to use. |
| Shortcuts | Pick a preset or type your own, e.g. `Ctrl+Alt+V` or `F9`. |
| Words to spell right | Names or jargon, e.g. `Figma, Webflow, Phrheke`. |
| Typing speed | Fast, or slower and more human-like. |
| Show words while I talk | Off means each phrase is typed after you pause. That's lighter on slow PCs. |
| Start with Windows | Launches it in the tray when you log in. |

Advanced options, like the pause length that ends a phrase or the mic sensitivity, are in
`%APPDATA%\VoiceKeyboard\config.json`. Restart the app after editing that file.

## Troubleshooting

- **Stuck on "Getting ready…"**: the one-time download needs internet. Check your connection and restart the app.
- **Typing lags behind your voice**: choose **Accuracy → Fast**, or turn off **Show words while I talk**.
- **Doesn't type into one specific app**: apps running *as administrator* ignore normal apps. Run Voice Keyboard as administrator too.
- **It "hears" background noise**: raise `vad_min_level` in config.json (e.g. `0.01`).
- **Words cut off at the start**: lower `vad_min_level` (e.g. `0.002`).
- For anything else, check the log: Settings → **Open log**.

## Run from source instead (optional)

Install Python 3.9+ from python.org (tick "Add python.exe to PATH") and double-click **`run.bat`**.
To build the .exe yourself, double-click **`build.bat`**.

## How it works

```
hotkey → microphone → voice detector → Whisper on your PC (re-reads the phrase every ~0.6 s)
                                             ↓ text so far
                 your app ← SendInput (Windows fake keyboard) ← typer (letter by letter, fixes)
```

- `voice_keyboard.py`: starts the app; tray icon, hotkeys, Start with Windows.
- `vk/ui.py`: the window (Home + Settings).
- `vk/app.py`: start/stop logic and speech model loading.
- `vk/local.py`: Whisper speech recognition, made to feel live.
- `vk/audio.py`: mic capture, voice detection, phrase splitting.
- `vk/typer.py`: turns text into keystrokes and corrections.
- `vk/keys.py`: Windows `SendInput` keystrokes.

Run the tests with `python -m unittest discover tests`.
