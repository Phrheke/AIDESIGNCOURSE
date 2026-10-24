"""Voice Keyboard: talk, and it types into whatever app you're using.

Opens a small window (Home + Settings) and lives in the system tray.
Press the hotkey (default Ctrl+Shift+Space) to start listening, press it
again to stop. Text is typed letter by letter into the focused window and
is never sent: no Enter key is ever pressed.
"""
import logging
import os
import queue
import subprocess
import sys
import threading

APP_NAME = "VoiceKeyboard"
log = logging.getLogger("main")


# ---- Windows helpers ------------------------------------------------------

def single_instance():
    """Return False if Voice Keyboard is already running."""
    if sys.platform != "win32":
        return True
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    single_instance.handle = kernel32.CreateMutexW(None, False, "Local\\VoiceKeyboardSingleton")
    return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS


def message_box(title, text):
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)  # MB_ICONINFORMATION
    else:
        print(f"{title}: {text}")


def dpi_aware():
    # Without this the window looks blurry on high-resolution screens.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


def beep(freq):
    if sys.platform == "win32":
        import winsound
        threading.Thread(target=winsound.Beep, args=(freq, 70), daemon=True).start()


def open_file(path):
    if not os.path.exists(path):
        open(path, "a").close()
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])


def launch_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    return f'"{exe}" "{os.path.abspath(__file__)}" --minimized'


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def startup_enabled():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_startup(enabled):
    if sys.platform != "win32":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enabled:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except OSError:
                pass


# ---- the app --------------------------------------------------------------

class VoiceKeyboardApp:
    def __init__(self, start_hidden=False):
        import tkinter as tk
        import pystray
        from vk import config
        from vk.app import Controller
        from vk.icon import GREY, RED, make_icon
        from vk.ui import MainWindow, pretty_hotkey

        self.config = config
        self.pretty_hotkey = pretty_hotkey
        self.cfg = config.load()
        self.hotkeys = None
        self._first_ready = True
        self._calls = queue.Queue()  # work for the UI thread (tkinter isn't thread-safe)
        self._icons = {False: make_icon(GREY), True: make_icon(RED)}

        self.controller = Controller(
            self.cfg,
            notify=self.notify,
            on_state=lambda listening: self.ui(self._on_state, listening),
            on_heard=lambda text: self.ui(self.window.add_heard, text),
            on_model=lambda text, ready: self.ui(self._on_model, text, ready))

        self.root = tk.Tk()
        self.window = MainWindow(self.root, self)
        if start_hidden:
            self.root.withdraw()

        Item = pystray.MenuItem
        self.icon = pystray.Icon(APP_NAME, self._icons[False], "Voice Keyboard", menu=pystray.Menu(
            Item("Open Voice Keyboard", lambda: self.ui(self.window.show), default=True),
            Item(lambda _: "Stop listening" if self.controller.listening else "Start listening",
                 lambda: self._bg(self.controller.toggle)),
            Item("Undo last phrase", lambda: self.controller.undo()),
            pystray.Menu.SEPARATOR,
            Item("Quit", lambda: self.ui(self.quit)),
        ))

    # ---- plumbing -------------------------------------------------------

    def ui(self, fn, *args):
        """Run fn on the UI thread."""
        self._calls.put((fn, args))

    def _pump(self):
        while True:
            try:
                fn, args = self._calls.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args)
            except Exception:
                log.exception("UI call failed")
        self.root.after(50, self._pump)

    @staticmethod
    def _bg(fn):
        # Never block the keyboard hook, tray or window.
        threading.Thread(target=fn, daemon=True).start()

    def notify(self, title, message):
        log.info("notify: %s - %s", title, message)
        try:
            self.icon.notify(message, title)
        except Exception:
            pass

    # ---- used by the window ---------------------------------------------

    def toggle_from_window(self):
        if self.controller.listening:
            self._bg(self.controller.toggle)
            return
        # Minimize first so the typing goes to the app you were using, not here.
        self.root.iconify()
        self.root.after(500, lambda: self._bg(self.controller.toggle))

    def open_log(self):
        open_file(self.config.log_path())

    def list_microphones(self):
        from vk.audio import list_microphones
        return list_microphones()

    def startup_enabled(self):
        return startup_enabled()

    def save_settings(self, new_cfg, start_with_windows):
        """Returns an error message, or None on success."""
        old = self.cfg
        self.cfg = new_cfg
        try:
            self.register_hotkeys()
        except Exception as e:
            self.cfg = old
            self.register_hotkeys()
            return f"That shortcut doesn't work: {e}"
        self.config.save(new_cfg)
        self.controller.apply_config(new_cfg)
        try:
            set_startup(start_with_windows)
        except OSError as e:
            return f"Saved, but couldn't change startup: {e}"
        return None

    # ---- state ----------------------------------------------------------

    def _on_state(self, listening):
        if self.cfg["beep"]:
            beep(880 if listening else 520)
        self.icon.icon = self._icons[listening]
        self.icon.title = "Voice Keyboard - listening" if listening else "Voice Keyboard"
        self.icon.update_menu()
        self.window.set_state(listening)

    def _on_model(self, text, ready):
        self.window.set_model_status(text, ready)
        self.icon.title = "Voice Keyboard" if ready else f"Voice Keyboard - {text}"
        if ready and self._first_ready:
            self._first_ready = False
            self.notify("Voice Keyboard is ready",
                        f"Press {self.pretty_hotkey(self.cfg['hotkey_toggle'])} in any app and talk.")

    def register_hotkeys(self):
        from pynput import keyboard
        if self.hotkeys:
            self.hotkeys.stop()
        self.hotkeys = keyboard.GlobalHotKeys({
            self.cfg["hotkey_toggle"]: lambda: self._bg(self.controller.toggle),
            self.cfg["hotkey_undo"]: self.controller.undo,
        })
        self.hotkeys.start()

    def quit(self):
        self.controller.shutdown()
        if self.hotkeys:
            self.hotkeys.stop()
        self.icon.stop()
        self.root.destroy()

    def run(self):
        self.register_hotkeys()
        self.icon.run_detached()
        self.controller.load_model()
        self.root.after(50, self._pump)
        self.root.mainloop()


def main():
    from vk import config
    logging.basicConfig(
        filename=config.log_path(), level=logging.INFO, encoding="utf-8",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not single_instance():
        message_box("Voice Keyboard", "Voice Keyboard is already running.\n\n"
                    "Look for the microphone icon in the tray (bottom-right, near the clock).")
        return
    dpi_aware()
    try:
        app = VoiceKeyboardApp(start_hidden="--minimized" in sys.argv)
    except Exception as e:
        log.exception("startup failed")
        message_box("Voice Keyboard", f"Couldn't start: {e}\n\nDetails: {config.log_path()}")
        return
    app.run()


if __name__ == "__main__":
    main()
