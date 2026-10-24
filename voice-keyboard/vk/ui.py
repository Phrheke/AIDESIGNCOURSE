"""The app window: a Home page (start button, status, what it heard) and Settings.

Built with tkinter, which ships with Python, so it adds nothing to install.
"""
import time
import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from .icon import BLUE, make_icon
from .local import MODEL_SIZES

MODELS = [(size, f"{label} - {dl}") for size, (label, dl) in MODEL_SIZES.items()]
LANGUAGES = [
    ("", "Auto-detect"), ("en", "English"), ("es", "Spanish"), ("fr", "French"),
    ("de", "German"), ("pt", "Portuguese"), ("it", "Italian"), ("nl", "Dutch"),
    ("ar", "Arabic"), ("hi", "Hindi"), ("zh", "Chinese"), ("ja", "Japanese"),
    ("ko", "Korean"), ("ru", "Russian"), ("tr", "Turkish"), ("pl", "Polish"),
    ("sw", "Swahili"), ("yo", "Yoruba"), ("ig", "Igbo"), ("ha", "Hausa"),
]
HOTKEY_PRESETS = ["Ctrl+Shift+Space", "Ctrl+Alt+Space", "Ctrl+Alt+D", "F8", "F9", "F10"]
UNDO_PRESETS = ["Ctrl+Shift+Backspace", "Ctrl+Alt+Backspace", "Ctrl+Alt+Z", "F7"]
DEFAULT_MIC = "Windows default microphone"

GREEN, RED, GREY, AMBER = "#16a34a", "#dc2626", "#6b7280", "#d97706"


def pretty_hotkey(hk):
    """'<ctrl>+<shift>+<space>' -> 'Ctrl+Shift+Space'"""
    parts = []
    for p in hk.split("+"):
        p = p.strip().strip("<>")
        parts.append(p.upper() if len(p) <= 3 and p[:1] in "fF" and p[1:].isdigit()
                     else p.capitalize())
    return "+".join(parts)


def to_pynput(text):
    """'Ctrl+Shift+Space' -> '<ctrl>+<shift>+<space>'; single letters stay bare."""
    parts = []
    for p in text.replace(" ", "").split("+"):
        if not p:
            continue
        p = p.lower()
        if p == "win":
            p = "cmd"
        parts.append(p if len(p) == 1 else f"<{p}>")
    return "+".join(parts)


def _label_for(options, value):
    for v, label in options:
        if v == value:
            return label
    return value


def _value_for(options, label):
    for v, l in options:
        if l == label:
            return v
    return label


class MainWindow:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        self._told_about_tray = False

        root.title("Voice Keyboard")
        root.minsize(460, 520)
        self._icon = ImageTk.PhotoImage(make_icon(BLUE))
        root.iconphoto(True, self._icon)
        root.protocol("WM_DELETE_WINDOW", self.hide)

        style = ttk.Style(root)
        style.configure("Big.TButton", font=("Segoe UI", 12, "bold"), padding=(10, 10))
        style.configure("Status.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Hint.TLabel", foreground=GREY)
        style.configure("Warn.TLabel", foreground=RED)

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=10, pady=10)
        self.notebook = nb
        self.home = ttk.Frame(nb, padding=14)
        self.settings = ttk.Frame(nb, padding=14)
        nb.add(self.home, text="  Home  ")
        nb.add(self.settings, text="  Settings  ")
        self._build_home()
        self._build_settings()
        self.load_settings_into_form()
        self._model_ready = False
        self.set_model_status(app.controller.model_status, app.controller.model_ready)

    # ---- Home -----------------------------------------------------------

    def _build_home(self):
        f = self.home
        top = ttk.Frame(f)
        top.pack(fill="x")
        self.dot = tk.Canvas(top, width=22, height=22, highlightthickness=0, bg=self._bg())
        self.dot.pack(side="left", padx=(0, 10))
        self.dot_id = self.dot.create_oval(3, 3, 19, 19, fill=GREEN, outline="")
        self.status = ttk.Label(top, text="Ready", style="Status.TLabel")
        self.status.pack(side="left")

        self.hint = ttk.Label(f, style="Hint.TLabel", wraplength=420, justify="left")
        self.hint.pack(fill="x", pady=(8, 12))

        self.button = ttk.Button(f, style="Big.TButton", command=self.app.toggle_from_window)
        self.button.pack(fill="x")

        ttk.Label(f, style="Hint.TLabel", wraplength=420,
                  text="Free and private: speech is recognised on this PC, "
                       "nothing is sent to the internet.").pack(fill="x", pady=(8, 0))

        hdr = ttk.Frame(f)
        hdr.pack(fill="x", pady=(18, 4))
        ttk.Label(hdr, text="What it heard", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(hdr, text="Clear", command=self._clear_heard).pack(side="right")
        ttk.Button(hdr, text="Copy all", command=self._copy_heard).pack(side="right", padx=4)

        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        self.heard = tk.Text(box, height=10, wrap="word", font=("Segoe UI", 10),
                             relief="flat", padx=8, pady=6, state="disabled")
        sb = ttk.Scrollbar(box, command=self.heard.yview)
        self.heard.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.heard.pack(side="left", fill="both", expand=True)
        self.heard.tag_configure("time", foreground=GREY)

    def _bg(self):
        return ttk.Style(self.root).lookup("TFrame", "background") or "#f0f0f0"

    def set_model_status(self, text, ready):
        self._model_ready = ready
        if ready:
            self.set_state(self.app.controller.listening)
            return
        self.dot.itemconfigure(self.dot_id, fill=AMBER)
        self.status.configure(text="Getting ready…")
        self.hint.configure(text=text)
        self.button.configure(text="Please wait…", state="disabled")

    def set_state(self, listening):
        if not self._model_ready:
            return
        self.button.configure(state="normal")
        hk = pretty_hotkey(self.app.cfg["hotkey_toggle"])
        undo = pretty_hotkey(self.app.cfg["hotkey_undo"])
        if listening:
            self.dot.itemconfigure(self.dot_id, fill=RED)
            self.status.configure(text="Listening… talk now")
            self.button.configure(text="■  Stop listening")
            self.hint.configure(text=f"Typing into the app you're in. Press {hk} again to stop.")
        else:
            self.dot.itemconfigure(self.dot_id, fill=GREEN)
            self.status.configure(text="Ready")
            self.button.configure(text="🎤  Start listening")
            self.hint.configure(text=(
                f"Click into any app (browser, Word, WhatsApp…), press {hk} and talk. "
                f"Press it again to stop. {undo} deletes the last phrase. "
                "Nothing is ever sent: it never presses Enter."))

    def add_heard(self, text):
        self.heard.configure(state="normal")
        self.heard.insert("end", time.strftime("%H:%M  "), "time")
        self.heard.insert("end", text + "\n")
        self.heard.see("end")
        self.heard.configure(state="disabled")

    def _clear_heard(self):
        self.heard.configure(state="normal")
        self.heard.delete("1.0", "end")
        self.heard.configure(state="disabled")

    def _copy_heard(self):
        lines = self.heard.get("1.0", "end").splitlines()
        text = " ".join(line[7:] for line in lines if line.strip())
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    # ---- Settings -------------------------------------------------------

    def _build_settings(self):
        f = self.settings
        f.columnconfigure(1, weight=1)
        self.v = {
            "model_size": tk.StringVar(), "live_typing": tk.BooleanVar(), "language": tk.StringVar(),
            "mic_device": tk.StringVar(), "hotkey_toggle": tk.StringVar(),
            "hotkey_undo": tk.StringVar(), "prompt": tk.StringVar(),
            "typing_delay_ms": tk.IntVar(), "space_between_phrases": tk.BooleanVar(),
            "correct_on_final": tk.BooleanVar(), "beep": tk.BooleanVar(),
            "startup": tk.BooleanVar(),
        }
        row = 0

        def label(text, hint=None):
            nonlocal row
            ttk.Label(f, text=text).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
            if hint:
                ttk.Label(f, text=hint, style="Hint.TLabel", wraplength=280).grid(
                    row=row + 1, column=1, sticky="w")

        label("Accuracy", "Bigger = more accurate but slower. Downloads once.")
        ttk.Combobox(f, textvariable=self.v["model_size"], state="readonly",
                     values=[m[1] for m in MODELS]).grid(row=row, column=1, sticky="ew")
        row += 2

        label("Language")
        ttk.Combobox(f, textvariable=self.v["language"], state="readonly",
                     values=[l[1] for l in LANGUAGES]).grid(row=row, column=1, sticky="ew")
        row += 1

        label("Microphone")
        self.mic_box = ttk.Combobox(f, textvariable=self.v["mic_device"], state="readonly")
        self.mic_box.grid(row=row, column=1, sticky="ew")
        self.mic_box.bind("<Button-1>", lambda e: self._refresh_mics())
        row += 1

        label("Start / stop shortcut", "Pick one or type your own, e.g. Ctrl+Alt+V")
        ttk.Combobox(f, textvariable=self.v["hotkey_toggle"], values=HOTKEY_PRESETS).grid(
            row=row, column=1, sticky="ew")
        row += 2

        label("Undo shortcut")
        ttk.Combobox(f, textvariable=self.v["hotkey_undo"], values=UNDO_PRESETS).grid(
            row=row, column=1, sticky="ew")
        row += 1

        label("Words to spell right", "Names or jargon, comma separated (optional)")
        ttk.Entry(f, textvariable=self.v["prompt"]).grid(row=row, column=1, sticky="ew")
        row += 2

        label("Typing speed")
        speed = ttk.Frame(f)
        speed.grid(row=row, column=1, sticky="ew")
        ttk.Label(speed, text="Fast", style="Hint.TLabel").pack(side="left")
        ttk.Scale(speed, from_=0, to=50, variable=self.v["typing_delay_ms"],
                  command=lambda _: self.v["typing_delay_ms"].set(
                      round(self.v["typing_delay_ms"].get()))).pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Label(speed, text="Human-like", style="Hint.TLabel").pack(side="left")
        row += 1

        for key, text in (("live_typing", "Show words while I talk (off = type after each pause)"),
                          ("space_between_phrases", "Add a space between phrases"),
                          ("correct_on_final", "Fix words when the final transcript is clearer"),
                          ("beep", "Beep when starting / stopping"),
                          ("startup", "Start Voice Keyboard when Windows starts")):
            ttk.Checkbutton(f, text=text, variable=self.v[key]).grid(
                row=row, column=0, columnspan=2, sticky="w", pady=2)
            row += 1

        buttons = ttk.Frame(f)
        buttons.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        ttk.Button(buttons, text="Save", style="Big.TButton", command=self.save).pack(
            side="right")
        ttk.Button(buttons, text="Open log", command=self.app.open_log).pack(side="left")
        self.saved_label = ttk.Label(buttons, style="Hint.TLabel")
        self.saved_label.pack(side="right", padx=10)

    def _refresh_mics(self):
        try:
            mics = self.app.list_microphones()
        except Exception:
            mics = []
        self.mic_box.configure(values=[DEFAULT_MIC] + mics)

    def load_settings_into_form(self):
        cfg = self.app.cfg
        self.v["model_size"].set(_label_for(MODELS, cfg["model_size"]))
        self.v["language"].set(_label_for(LANGUAGES, cfg["language"]))
        self.v["mic_device"].set(cfg["mic_device"] or DEFAULT_MIC)
        self.v["hotkey_toggle"].set(pretty_hotkey(cfg["hotkey_toggle"]))
        self.v["hotkey_undo"].set(pretty_hotkey(cfg["hotkey_undo"]))
        self.v["prompt"].set(cfg.get("prompt", ""))
        self.v["typing_delay_ms"].set(int(cfg["typing_delay_ms"]))
        for key in ("live_typing", "space_between_phrases", "correct_on_final", "beep"):
            self.v[key].set(bool(cfg[key]))
        self.v["startup"].set(self.app.startup_enabled())
        self._refresh_mics()

    def save(self):
        mic = self.v["mic_device"].get()
        new = dict(self.app.cfg)
        new.update({
            "model_size": _value_for(MODELS, self.v["model_size"].get()),
            "live_typing": self.v["live_typing"].get(),
            "language": _value_for(LANGUAGES, self.v["language"].get()),
            "mic_device": None if mic in ("", DEFAULT_MIC) else mic,
            "hotkey_toggle": to_pynput(self.v["hotkey_toggle"].get()) or new["hotkey_toggle"],
            "hotkey_undo": to_pynput(self.v["hotkey_undo"].get()) or new["hotkey_undo"],
            "prompt": self.v["prompt"].get().strip(),
            "typing_delay_ms": int(self.v["typing_delay_ms"].get()),
            "space_between_phrases": self.v["space_between_phrases"].get(),
            "correct_on_final": self.v["correct_on_final"].get(),
            "beep": self.v["beep"].get(),
        })
        error = self.app.save_settings(new, self.v["startup"].get())
        if error:
            self.saved_label.configure(text=error, style="Warn.TLabel")
        else:
            self.saved_label.configure(text="Saved ✓", style="Hint.TLabel")
            self.root.after(3000, lambda: self.saved_label.configure(text=""))
            self.set_state(self.app.controller.listening)

    # ---- window visibility ---------------------------------------------

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self.root.withdraw()
        if not self._told_about_tray:
            self._told_about_tray = True
            self.app.notify("Still running",
                            "Voice Keyboard keeps working in the tray (bottom-right). "
                            "Right-click the mic icon to quit.")
