"""Human Typer: paste text, and it types it into any app like a person would.

Esc stops, F8 pauses / resumes. Settings are kept in
%APPDATA%\\HumanTyper\\settings.json (your text is never saved).
"""
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from htyper import keys
from htyper.engine import TypingJob
from htyper.timing import describe_wpm, plan, total_seconds

DEFAULTS = {
    "wpm": 75,
    "natural_pauses": True,
    "remote_mode": False,
    "shift_enter": False,
    "guard_window": True,
    "countdown": 5,
    "typos": "rare",
}
TYPO_CHOICES = [("off", "Never"), ("rare", "Rarely (a few in a long text)"),
                ("sometimes", "Sometimes")]
GREY, RED, GREEN = "#6b7280", "#dc2626", "#16a34a"


def settings_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "HumanTyper")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "settings.json")


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(settings_path(), encoding="utf-8") as f:
            s.update({k: v for k, v in json.load(f).items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return s


def save_settings(s):
    try:
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except OSError:
        pass


def fmt_time(seconds):
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m} min {s:02d} s"
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min"


def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


class App:
    def __init__(self, root):
        self.root = root
        self.s = load_settings()
        self.job = None
        self.countdown_left = 0
        self._calls = queue.Queue()

        root.title("Human Typer")
        root.minsize(520, 560)
        try:
            root.iconbitmap(default=resource("icon.ico"))
        except tk.TclError:
            pass
        root.protocol("WM_DELETE_WINDOW", self.quit)

        style = ttk.Style(root)
        style.configure("Big.TButton", font=("Segoe UI", 12, "bold"), padding=(10, 10))
        style.configure("Status.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("Hint.TLabel", foreground=GREY)

        f = ttk.Frame(root, padding=14)
        f.pack(fill="both", expand=True)
        self._build(f)
        self._refresh_counts()
        self._set_idle()

        threading.Thread(target=self._watch_keys, name="keys", daemon=True).start()
        root.after(50, self._pump)

    # ---- layout ---------------------------------------------------------

    def _build(self, f):
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="Paste the text to type", font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(top, text="Clear", command=self._clear).pack(side="right")
        ttk.Button(top, text="Paste", command=self._paste).pack(side="right", padx=4)

        box = ttk.Frame(f)
        box.pack(fill="both", expand=True, pady=(6, 4))
        self.text = tk.Text(box, wrap="word", font=("Segoe UI", 10), undo=True,
                            relief="solid", borderwidth=1, padx=8, pady=6, height=10)
        sb = ttk.Scrollbar(box, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.bind("<<Modified>>", self._on_text_change)

        self.counts = ttk.Label(f, style="Hint.TLabel")
        self.counts.pack(fill="x")

        speed = ttk.LabelFrame(f, text=" Speed ", padding=10)
        speed.pack(fill="x", pady=(10, 0))
        self.wpm = tk.IntVar(value=int(self.s["wpm"]))
        row = ttk.Frame(speed)
        row.pack(fill="x")
        ttk.Label(row, text="Slower", style="Hint.TLabel").pack(side="left")
        ttk.Scale(row, from_=30, to=160, variable=self.wpm,
                  command=lambda _: self._on_speed()).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(row, text="Faster", style="Hint.TLabel").pack(side="left")
        self.wpm_label = ttk.Label(speed, font=("Segoe UI", 10, "bold"), wraplength=480,
                                   justify="left")
        self.wpm_label.pack(anchor="w", pady=(6, 0))

        opts = ttk.LabelFrame(f, text=" Options ", padding=10)
        opts.pack(fill="x", pady=(10, 0))
        self.v = {}
        for key, text in (
                ("natural_pauses", "Natural pauses around numbers, symbols and new lines"),
                ("remote_mode", "Remote desktop mode (AnyDesk, RustDesk, virtual machines)"),
                ("shift_enter", "Type line breaks as Shift+Enter (so chat apps don't send early)"),
                ("guard_window", "Pause if I switch to another window")):
            self.v[key] = tk.BooleanVar(value=bool(self.s[key]))
            ttk.Checkbutton(opts, text=text, variable=self.v[key],
                            command=lambda: (self._save(), self._refresh_counts())).pack(
                anchor="w", pady=1)
        trow = ttk.Frame(opts)
        trow.pack(anchor="w", pady=(6, 0))
        ttk.Label(trow, text="Make a typo and fix it:").pack(side="left")
        labels = dict(TYPO_CHOICES)
        self.typos = tk.StringVar(value=labels.get(self.s["typos"], labels["rare"]))
        tb = ttk.Combobox(trow, textvariable=self.typos, values=[l for _, l in TYPO_CHOICES],
                          width=28, state="readonly")
        tb.pack(side="left", padx=6)
        tb.bind("<<ComboboxSelected>>", lambda e: (self._save(), self._refresh_counts()))
        crow = ttk.Frame(opts)
        crow.pack(anchor="w", pady=(6, 0))
        ttk.Label(crow, text="Start typing after").pack(side="left")
        self.countdown = tk.StringVar(value=str(self.s["countdown"]))
        cb = ttk.Combobox(crow, textvariable=self.countdown, values=["3", "5", "10", "15"],
                          width=4, state="readonly")
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._save())
        ttk.Label(crow, text="seconds (time to click into your app)").pack(side="left")

        run = ttk.Frame(f)
        run.pack(fill="x", pady=(12, 0))
        self.status = ttk.Label(run, style="Status.TLabel")
        self.status.pack(anchor="w")
        self.bar = ttk.Progressbar(run, maximum=1000)
        self.bar.pack(fill="x", pady=6)
        btns = ttk.Frame(run)
        btns.pack(fill="x")
        self.start_btn = ttk.Button(btns, text="▶  Start typing", style="Big.TButton",
                                    command=self.start)
        self.start_btn.pack(side="left", fill="x", expand=True)
        self.pause_btn = ttk.Button(btns, text="Pause (F8)", command=self._toggle_pause)
        self.stop_btn = ttk.Button(btns, text="Stop (Esc)", command=self.stop)
        ttk.Label(run, style="Hint.TLabel",
                  text="While typing: Esc = stop, F8 = pause / resume.").pack(anchor="w", pady=(6, 0))

    # ---- text box -------------------------------------------------------

    def _get_text(self):
        return self.text.get("1.0", "end-1c")

    def _paste(self):
        try:
            clip = self.root.clipboard_get()
        except tk.TclError:
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", clip)

    def _clear(self):
        self.text.delete("1.0", "end")

    def _on_text_change(self, _):
        self.text.edit_modified(False)
        self._refresh_counts()

    def _on_speed(self):
        self.wpm.set(int(round(self.wpm.get())))
        self._refresh_counts()
        self._save()

    def _refresh_counts(self):
        text = self._get_text().replace("\r\n", "\n")
        wpm = self.wpm.get()
        self.wpm_label.configure(
            text=f"Top speed {wpm} WPM ({describe_wpm(wpm)}). "
                 f"It drifts between about {round(wpm * 0.8)} and {wpm}, never above.")
        if not text:
            self.counts.configure(text="Tip: click Paste to use what you copied.")
            return
        words = len(text.split())
        estimate = total_seconds(plan(text, wpm, self.v["natural_pauses"].get(),
                                      self._typo_setting(), seed=0))
        self.counts.configure(
            text=f"{len(text):,} characters · {words:,} words · takes about {fmt_time(estimate)}")

    def _typo_setting(self):
        for key, label in TYPO_CHOICES:
            if label == self.typos.get():
                return key
        return "rare"

    def _save(self):
        self.s.update({k: v.get() for k, v in self.v.items()})
        self.s["wpm"] = self.wpm.get()
        self.s["countdown"] = int(self.countdown.get())
        self.s["typos"] = self._typo_setting()
        save_settings(self.s)

    # ---- running --------------------------------------------------------

    def start(self):
        text = self._get_text()
        if not text.strip():
            self.status.configure(text="Paste some text first.", foreground=RED)
            return
        if not keys.IS_WINDOWS:
            self.status.configure(text="Typing only works on Windows.", foreground=RED)
            return
        self._save()
        self.countdown_left = int(self.countdown.get())
        self._show_running()
        # Get out of the way so you can click into the app to type in.
        self.root.iconify()
        self._tick_countdown()

    def _tick_countdown(self):
        if self.countdown_left is None:
            return  # cancelled
        if self.countdown_left > 0:
            msg = f"Starting in {self.countdown_left}… click into your app now"
            self.status.configure(text=msg, foreground=GREY)
            self.root.title(f"{self.countdown_left}… - Human Typer")
            self.countdown_left -= 1
            self.root.after(1000, self._tick_countdown)
            return
        self.countdown_left = None
        kb = keys.Keyboard(remote=self.s["remote_mode"], newline_shift_enter=self.s["shift_enter"])
        self.job = TypingJob(
            self._get_text(), kb, self.s["wpm"], self.s["natural_pauses"], self.s["typos"],
            on_update=lambda job: self._calls.put(lambda: self._show_job(job)),
            window={"current": keys.foreground_window, "is_ours": keys.window_is_ours},
            guard_window=self.s["guard_window"])
        self.job.start()

    def _toggle_pause(self):
        if self.job:
            self.job.toggle_pause()

    def stop(self):
        if self.countdown_left is not None and self.countdown_left >= 0 and not self.job:
            self.countdown_left = None
            self._set_idle("Cancelled.")
            return
        if self.job:
            self.job.stop()

    def _show_running(self):
        self.start_btn.pack_forget()
        self.pause_btn.pack(side="left", fill="x", expand=True)
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.bar["value"] = 0
        self.text.configure(state="disabled")

    def _set_idle(self, message="Ready", color=GREEN):
        self.job = None
        self.countdown_left = None
        self.pause_btn.pack_forget()
        self.stop_btn.pack_forget()
        self.start_btn.pack(side="left", fill="x", expand=True)
        self.text.configure(state="normal")
        self.status.configure(text=message, foreground=color)
        self.root.title("Human Typer")

    def _show_job(self, job):
        if job is not self.job:
            return
        pct = int(job.progress * 100)
        self.bar["value"] = job.progress * 1000
        if job.state == "typing":
            self.pause_btn.configure(text="Pause (F8)")
            self.status.configure(text=f"Typing… {pct}% · about {fmt_time(job.seconds_left)} left",
                                  foreground=GREY)
            self.root.title(f"Typing {pct}% - Human Typer")
        elif job.state == "paused":
            self.pause_btn.configure(text="Resume (F8)")
            self.status.configure(text=f"{job.pause_reason} ({pct}% done)", foreground=RED)
            self.root.title(f"Paused {pct}% - Human Typer")
        elif job.state == "done":
            self._beep()
            self._set_idle(f"Done ✓  Typed {len(job.text):,} characters.")
        elif job.state == "stopped":
            self._set_idle(f"Stopped at {pct}%.", RED)

    @staticmethod
    def _beep():
        if keys.IS_WINDOWS:
            import winsound
            winsound.MessageBeep()

    # ---- Esc / F8, from anywhere ----------------------------------------

    def _watch_keys(self):
        f8_was_down = False
        while True:
            time.sleep(0.03)
            busy = self.job is not None or self.countdown_left is not None
            if not busy:
                f8_was_down = False
                continue
            if keys.key_down(keys.VK_ESCAPE):
                self._calls.put(self.stop)
            f8 = keys.key_down(keys.VK_F8)
            if f8 and not f8_was_down:
                self._calls.put(self._toggle_pause)
            f8_was_down = f8

    def _pump(self):
        while True:
            try:
                fn = self._calls.get_nowait()
            except queue.Empty:
                break
            fn()
        self.root.after(50, self._pump)

    def quit(self):
        if self.job:
            self.job.stop()
        self.root.destroy()


def main():
    if keys.IS_WINDOWS:
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp on high-DPI screens
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
