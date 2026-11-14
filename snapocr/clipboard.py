"""剪贴板模块:优先 pyperclip,失败时回退 Windows API。"""

from __future__ import annotations

import sys


def copy_text(text: str) -> bool:
    """把文本写入系统剪贴板,成功返回 True。"""
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        pass
    if sys.platform == "win32":
        return _copy_win32(text)
    return False


def _copy_win32(text: str) -> bool:
    """pyperclip 失效时的兜底:直接调用 Win32 剪贴板 API。"""
    import ctypes

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    data = text.encode("utf-16-le") + b"\x00\x00"

    if not user32.OpenClipboard(0):
        return False
    try:
        user32.EmptyClipboard()
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            return False
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return False
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()
