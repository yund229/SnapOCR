"""屏幕框选模块:全屏遮罩 + 拖拽画框,返回屏幕绝对坐标。

支持多显示器(Windows 下按虚拟屏幕整体覆盖);按 Esc 取消。
"""

from __future__ import annotations

import sys
from typing import Optional, Tuple

Box = Tuple[int, int, int, int]  # (left, top, right, bottom)


def _virtual_screen() -> Tuple[int, int, int, int]:
    """返回虚拟屏幕 (x, y, width, height);非 Windows 或获取失败时回退主屏。"""
    if sys.platform == "win32":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            x = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
            y = user32.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
            w = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
            h = user32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
            if w > 0 and h > 0:
                return x, y, w, h
        except Exception:
            pass
    try:
        import tkinter as tk

        probe = tk.Tk()
        w, h = probe.winfo_screenwidth(), probe.winfo_screenheight()
        probe.destroy()
        return 0, 0, w, h
    except Exception:
        return 0, 0, 1920, 1080


def select_region() -> Optional[Box]:
    """弹出全屏半透明遮罩,拖拽选框;返回屏幕绝对坐标,取消或空选返回 None。"""
    import tkinter as tk

    vx, vy, vw, vh = _virtual_screen()

    root = tk.Tk()
    root.overrideredirect(True)          # 无边框
    root.geometry(f"{vw}x{vh}+{vx}+{vy}")
    root.attributes("-topmost", True)
    root.config(bg="black")

    canvas = tk.Canvas(root, bg="black", highlightthickness=0, cursor="crosshair")
    canvas.pack(fill="both", expand=True)
    canvas.create_rectangle(
        0, 0, vw, vh, fill="#101418", stipple="gray50", outline=""
    )
    hint = canvas.create_text(
        vw // 2, 40, text="拖拽框选要识别的区域,Esc 取消",
        fill="#9fb3c8", font=("Microsoft YaHei", 12),
    )

    state = {"start": None, "rect": None, "result": None}

    def _hide_hint():
        canvas.itemconfigure(hint, state="hidden")

    def on_press(event):
        _hide_hint()
        state["start"] = (event.x, event.y)
        state["rect"] = canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="#00e5ff", width=2, dash=(5, 3),
        )

    def on_drag(event):
        if not state["start"]:
            return
        x0, y0 = state["start"]
        canvas.coords(state["rect"], x0, y0, event.x, event.y)

    def on_release(event):
        if not state["start"]:
            return
        x0, y0 = state["start"]
        state["result"] = (
            vx + min(x0, event.x), vy + min(y0, event.y),
            vx + max(x0, event.x), vy + max(y0, event.y),
        )
        root.quit()

    def on_escape(_event):
        root.quit()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", on_escape)
    root.focus_force()

    root.mainloop()
    root.destroy()

    result = state["result"]
    if result and result[2] - result[0] >= 4 and result[3] - result[1] >= 4:
        return result
    return None
