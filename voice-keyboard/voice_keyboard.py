"""Voice Keyboard: talk, and it types into whatever app you're using.

Runs in the system tray. Press the hotkey (default Ctrl+Shift+Space) to
start listening, press it again to stop. Text is typed letter by letter into
the focused window and is never sent: no Enter key is ever pressed.
"""
import logging
import os
import subprocess
import sys
import threading

from pynput import keyboard
import pystray
from PIL import Image, ImageDraw

from vk import config
from vk.app import Controller

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


def beep(freq):
    if sys.platform == "win32":
        import winsound
        threading.Thread(target=winsound.Beep, args=(freq, 70), daemon=True).start()


def open_file(path):
    if sys.platform == "win32":
        subprocess.Popen(["notepad.exe", path])
    else:
        subprocess.Popen(["xdg-open", path])


def launch_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    return f'"{exe}" "{os.path.abspath(__file__)}"'


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


# ---- tray icon ------------------------------------------------------------

def make_icon(color):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((22, 6, 42, 40), radius=10, fill=color)          # mic head
    d.arc((14, 18, 50, 50), start=0, end=180, fill=color, width=4)       # holder
    d.line((32, 50, 32, 58), fill=color, width=4)                        # stand
    d.line((22, 58, 42, 58), fill=color, width=4)
    return img


ICON_IDLE = make_icon((150, 150, 150, 255))
ICON_LISTENING = make_icon((230, 40, 40, 255))


def pretty_hotkey(hk):
    return "+".join(p.strip("<>").capitalize() for p in hk.split("+"))


class TrayApp:
    def __init__(self):
        self.cfg = config.load()
        self.hotkeys = None
        self.controller = Controller(self.cfg, self.notify, self._on_state)
        self.icon = pystray.Icon(APP_NAME, ICON_IDLE, "Voice Keyboard", menu=self._menu())

    def _menu(self):
        Item = pystray.MenuItem
        return pystray.Menu(
            Item(lambda _: ("Stop listening" if self.controller.listening else "Start listening")
                 + f"  ({pretty_hotkey(self.cfg['hotkey_toggle'])})",
                 lambda: self._bg(self.controller.toggle), default=True),
            Item(lambda _: f"Undo last phrase  ({pretty_hotkey(self.cfg['hotkey_undo'])})",
                 lambda: self.controller.undo()),
            pystray.Menu.SEPARATOR,
            Item("Settings…", lambda: open_file(config.config_path())),
            Item("Reload settings", self.reload),
            Item("Open log", lambda: open_file(config.log_path())),
            Item("Start with Windows", self._toggle_startup,
                 checked=lambda _: startup_enabled(), visible=sys.platform == "win32"),
            pystray.Menu.SEPARATOR,
            Item("Quit", self.quit),
        )

    @staticmethod
    def _bg(fn):
        # Never block the keyboard hook / tray thread.
        threading.Thread(target=fn, daemon=True).start()

    def notify(self, title, message):
        log.info("notify: %s - %s", title, message)
        try:
            self.icon.notify(message, title)
        except Exception:
            pass

    def _on_state(self, listening):
        if self.cfg["beep"]:
            beep(880 if listening else 520)
        self.icon.icon = ICON_LISTENING if listening else ICON_IDLE
        self.icon.title = "Voice Keyboard - listening" if listening else "Voice Keyboard"
        self.icon.update_menu()

    def _toggle_startup(self, icon, item):
        set_startup(not startup_enabled())

    def register_hotkeys(self):
        if self.hotkeys:
            self.hotkeys.stop()
        self.hotkeys = keyboard.GlobalHotKeys({
            self.cfg["hotkey_toggle"]: lambda: self._bg(self.controller.toggle),
            self.cfg["hotkey_undo"]: self.controller.undo,
        })
        self.hotkeys.start()

    def reload(self):
        try:
            self.cfg = config.load()
        except Exception as e:
            self.notify("Settings error", f"Couldn't read config.json: {e}")
            return
        self.controller.apply_config(self.cfg)
        try:
            self.register_hotkeys()
        except Exception as e:
            self.notify("Hotkey error", str(e))
            return
        self.icon.update_menu()
        self.notify("Voice Keyboard", "Settings reloaded.")

    def quit(self):
        self.controller.shutdown()
        if self.hotkeys:
            self.hotkeys.stop()
        self.icon.stop()

    def run(self):
        self.register_hotkeys()

        def setup(icon):
            icon.visible = True
            if not config.api_key(self.cfg):
                open_file(config.config_path())
                self.notify("Welcome to Voice Keyboard",
                            "Paste your OpenAI API key into the settings file, save it, "
                            "then choose 'Reload settings' from the tray icon.")
            else:
                self.notify("Voice Keyboard is running",
                            f"Press {pretty_hotkey(self.cfg['hotkey_toggle'])} to start talking.")

        self.icon.run(setup)


def main():
    logging.basicConfig(
        filename=config.log_path(), level=logging.INFO, encoding="utf-8",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not single_instance():
        message_box("Voice Keyboard", "Voice Keyboard is already running (check the tray).")
        return
    try:
        app = TrayApp()
    except Exception as e:
        log.exception("startup failed")
        message_box("Voice Keyboard", f"Couldn't start: {e}\n\nSee {config.log_path()}")
        return
    app.run()


if __name__ == "__main__":
    main()
