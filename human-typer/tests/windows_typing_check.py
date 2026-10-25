"""Real keystrokes on Windows: types into a text box and checks it's exact.

    python tests/windows_typing_check.py
"""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from htyper import keys  # noqa: E402
from htyper.engine import TypingJob  # noqa: E402

SAMPLE = ("Hello Sarah, it's 3pm! Price: $42.50 (approx) & 100% sure?\n"
          "Email me@example.com; path C:\\Users\\drey\tTabbed \"quotes\" [ok] {done} ~#^*_+=|<>/")


def check(remote):
    root = tk.Tk()
    root.title("typing check")
    root.geometry("900x200+100+100")
    box = tk.Text(root)
    box.pack(fill="both", expand=True)
    result = {}

    def begin():
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()
        box.focus_set()
        job = TypingJob(SAMPLE, keys.Keyboard(remote=remote), wpm=500, natural=False)
        result["job"] = job
        job.start()
        root.after(100, wait)

    def wait():
        if result["job"].state in ("typing", "paused"):
            root.after(100, wait)
        else:
            result["text"] = box.get("1.0", "end-1c")
            root.destroy()

    root.after(800, begin)
    root.after(60000, root.destroy)
    root.mainloop()
    got = result.get("text", "")
    ok = got == SAMPLE
    print(f"{'remote' if remote else 'normal'} mode: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("expected:", repr(SAMPLE))
        print("got:     ", repr(got))
    return ok


if __name__ == "__main__":
    results = [check(remote=False), check(remote=True)]
    sys.exit(0 if all(results) else 1)
