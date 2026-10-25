# Human Typer (Windows)

Paste some text, press **Start**, click into any app, and it types the text **exactly**, the way a person at a keyboard would.

- **Human rhythm.** Every keystroke has a slightly different gap. Common letter pairs ("th", "in", "er") come quicker, capitals and symbols take a little longer, and there are short breaths after commas, sentences and new lines.
- **Your speed.** Choose 30–160 words per minute. Around 60–90 WPM is a professional typist. The time estimate is accurate because the overall speed matches what you pick.
- **Exact.** Line breaks, tabs, symbols, accents and emoji are all typed as written.
- **Safe.** **Esc** stops, **F8** pauses and resumes. If you switch to another window it pauses by itself, so it never types into the wrong place.
- **Works over remote desktop.** Tick *Remote desktop mode* for AnyDesk, RustDesk or virtual machines. It then presses the real keys, which those tools forward.
- **Free and private.** Nothing to install, no internet, and your text is never saved.

## Download

**[HumanTyper.exe](https://github.com/Phrheke/AIDESIGNCOURSE/releases/download/human-typer-latest/HumanTyper.exe)**. Double-click to run.
If Windows says "Windows protected your PC", click **More info → Run anyway**. The app isn't code-signed, which is normal for small personal apps.

## How to use

1. Copy your text, then click **Paste** (or type or paste straight into the box).
2. Pick a speed, e.g. 75 WPM.
3. Click **Start typing**. The window minimizes and counts down 5 seconds.
4. **Click into the place you want it typed** (an email, a document, a chat box, AnyDesk…).
5. Leave it. Hover over the taskbar icon to see progress. It beeps when done.

| Key | What it does |
|---|---|
| **Esc** | Stop |
| **F8** | Pause / resume. After switching windows, click back into the right spot, then press F8. |

## Options

| Option | When to use it |
|---|---|
| Natural pauses | On by default. Turn it off for a perfectly steady rhythm. |
| Remote desktop mode | Typing into AnyDesk, RustDesk, TeamViewer or a virtual machine. Both computers should use the same keyboard layout. |
| Type line breaks as Shift+Enter | Chat apps (WhatsApp, Slack, Claude, ChatGPT) where Enter would send the message early. |
| Pause if I switch windows | On by default. It's the safety net that stops it typing into the wrong app. |
| Start typing after | How many seconds you get to click into your app. |

## Good to know

- **Code editors** (VS Code, etc.) often auto-indent and auto-close brackets as you type, so the result can differ from your text.
  Paste code into a plain editor such as Notepad, or turn those features off.
- Apps running **as administrator** ignore keystrokes from normal apps. Run Human Typer as administrator too.
- Don't hold Ctrl, Shift or Alt while it types. It waits for you to let go.

## Run from source

Install Python 3.9+ from python.org and double-click `run.bat`. `build.bat` makes the .exe. There are no extra packages to install.
Tests: `python -m unittest discover tests`.
