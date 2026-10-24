"""Fake keyboard: sends keystrokes to whatever window has focus.

On Windows this uses SendInput with KEYEVENTF_UNICODE, the same path an
on-screen keyboard uses, so any app (browser, Word, Slack, games' chat
boxes...) receives it as normal typing.
"""
import sys
import time

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    VK_BACK = 0x08
    # Shift, Ctrl, Alt, Left Win, Right Win
    MODIFIER_VKS = (0x10, 0x11, 0x12, 0x5B, 0x5C)

    ULONG_PTR = wintypes.WPARAM

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = (("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR))

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = (("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR))

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = (("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD))

    class _INPUTUNION(ctypes.Union):
        _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = (("type", wintypes.DWORD), ("u", _INPUTUNION))

    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
    user32.GetAsyncKeyState.restype = ctypes.c_short

    def _key(vk=0, scan=0, flags=0):
        inp = INPUT(type=INPUT_KEYBOARD)
        inp.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
        return inp

    def _send(inputs):
        arr = (INPUT * len(inputs))(*inputs)
        user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))

    class Keyboard:
        def type_text(self, text):
            inputs = []
            data = text.encode("utf-16-le")
            for i in range(0, len(data), 2):
                unit = int.from_bytes(data[i:i + 2], "little")
                inputs.append(_key(scan=unit, flags=KEYEVENTF_UNICODE))
                inputs.append(_key(scan=unit, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
            if inputs:
                _send(inputs)

        def backspace(self, count):
            for _ in range(count):
                _send([_key(vk=VK_BACK), _key(vk=VK_BACK, flags=KEYEVENTF_KEYUP)])
                time.sleep(0.004)

        def wait_for_modifiers_released(self):
            # If you're still holding Ctrl/Shift from the hotkey, our letters
            # would turn into shortcuts (Ctrl+A, ...). Wait until you let go.
            while any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in MODIFIER_VKS):
                time.sleep(0.01)

else:
    # Non-Windows fallback (handy for development).
    class Keyboard:
        def __init__(self):
            from pynput.keyboard import Controller, Key
            self._kb, self._key = Controller(), Key

        def type_text(self, text):
            self._kb.type(text)

        def backspace(self, count):
            for _ in range(count):
                self._kb.tap(self._key.backspace)

        def wait_for_modifiers_released(self):
            pass
