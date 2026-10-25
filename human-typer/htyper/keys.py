"""Sends keystrokes to whatever window has focus (Windows SendInput).

Two ways to type a character:
- normal: sends the character itself (KEYEVENTF_UNICODE). Works with any
  character, including emoji and accents, in every normal app.
- remote: presses the real keys (Shift + the key, ...) using your keyboard
  layout. Remote-desktop tools like AnyDesk and RustDesk forward real keys,
  not characters. Characters your layout can't type fall back to normal.
Enter and Tab are always pressed as real keys.
"""
import ctypes
import os
import sys
import time

IS_WINDOWS = sys.platform == "win32"

VK_BACK, VK_TAB, VK_RETURN = 0x08, 0x09, 0x0D
VK_SHIFT, VK_CONTROL, VK_MENU = 0x10, 0x11, 0x12
VK_ESCAPE, VK_F8 = 0x1B, 0x77
MODIFIER_VKS = (VK_SHIFT, VK_CONTROL, VK_MENU, 0x5B, 0x5C)

if IS_WINDOWS:
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    # Windows normally sleeps in ~16 ms steps; ask for 1 ms so timing is precise.
    try:
        ctypes.WinDLL("winmm").timeBeginPeriod(1)
    except OSError:
        pass

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
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
    user32.VkKeyScanW.argtypes = (wintypes.WCHAR,)
    user32.VkKeyScanW.restype = ctypes.c_short
    user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
    user32.MapVirtualKeyW.restype = wintypes.UINT
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))

    def _key(vk=0, scan=0, flags=0):
        inp = INPUT(type=INPUT_KEYBOARD)
        inp.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
        return inp

    def _send(*inputs):
        arr = (INPUT * len(inputs))(*inputs)
        user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))

    def _tap_vk(vk, mods=()):
        for m in mods:
            _send(_key(vk=m, scan=user32.MapVirtualKeyW(m, 0)))
        scan = user32.MapVirtualKeyW(vk, 0)
        _send(_key(vk=vk, scan=scan))
        time.sleep(0.008)  # a key is held for a moment, not zero time
        _send(_key(vk=vk, scan=scan, flags=KEYEVENTF_KEYUP))
        for m in reversed(mods):
            _send(_key(vk=m, scan=user32.MapVirtualKeyW(m, 0), flags=KEYEVENTF_KEYUP))

    def _type_unicode(ch):
        data = ch.encode("utf-16-le")
        for i in range(0, len(data), 2):
            unit = int.from_bytes(data[i:i + 2], "little")
            _send(_key(scan=unit, flags=KEYEVENTF_UNICODE),
                  _key(scan=unit, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))

    def _type_real_keys(ch):
        if len(ch.encode("utf-16-le")) != 2:
            return False
        r = user32.VkKeyScanW(ch)
        if r == -1:
            return False
        vk, state = r & 0xFF, (r >> 8) & 0xFF
        mods = [m for bit, m in ((1, VK_SHIFT), (2, VK_CONTROL), (4, VK_MENU)) if state & bit]
        _tap_vk(vk, mods)
        return True

    def key_down(vk):
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)

    def foreground_window():
        return user32.GetForegroundWindow()

    def window_is_ours(hwnd):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == os.getpid()

else:  # lets the UI and tests run on other systems; nothing is typed
    def key_down(vk):
        return False

    def foreground_window():
        return 1

    def window_is_ours(hwnd):
        return False


class Keyboard:
    def __init__(self, remote=False, newline_shift_enter=False):
        self.remote = remote
        self.newline_shift_enter = newline_shift_enter

    def type_char(self, ch):
        if not IS_WINDOWS:
            raise RuntimeError("Typing only works on Windows")
        if ch == "\n":
            _tap_vk(VK_RETURN, [VK_SHIFT] if self.newline_shift_enter else [])
        elif ch == "\t":
            _tap_vk(VK_TAB)
        elif not (self.remote and _type_real_keys(ch)):
            _type_unicode(ch)

    def wait_for_modifiers_released(self):
        # If you're holding Ctrl/Alt/Shift, letters would turn into shortcuts.
        while any(key_down(vk) for vk in MODIFIER_VKS):
            time.sleep(0.01)
