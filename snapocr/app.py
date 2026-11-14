"""SnapOCR 主程序:托盘常驻 + 全局热键。

执行流:热键 → 主线程弹出框选遮罩 → 抓图 → OCR → 复制剪贴板 → 提示。
pystray 托盘在独立线程运行,tkinter 始终在主线程(Windows 下最稳妥)。
"""

from __future__ import annotations

import argparse
import ctypes
import datetime
import os
import sys
import threading
from typing import Optional

from snapocr import __version__
from snapocr.clipboard import copy_text
from snapocr.config import Config, load, save
from snapocr.ocr import OcrEngine


def _enable_dpi_awareness() -> None:
    """让截图坐标与物理像素一致,避免高 DPI 屏幕截到错位/模糊区域。"""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def _tray_image():
    """程序化生成托盘图标(取景框 + “文”),无需外部资源文件。"""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([3, 3, 61, 61], radius=14, fill=(24, 28, 44, 255))
    # 取景框四角
    length = 14
    for x0, y0, dx, dy in ((8, 8, 1, 1), (56, 8, -1, 1), (8, 56, 1, -1), (56, 56, -1, -1)):
        draw.line([(x0, y0), (x0 + dx * length, y0)], fill=(0, 229, 255, 255), width=4)
        draw.line([(x0, y0), (x0, y0 + dy * length)], fill=(0, 229, 255, 255), width=4)
    try:
        font = ImageFont.truetype("msyh.ttc", 26)
    except OSError:
        font = ImageFont.load_default()
    draw.text((32, 33), "文", fill=(255, 255, 255, 255), font=font, anchor="mm")
    return img


def _show_result_window(text: str, hotkey_hint: str) -> None:
    """结果弹窗:文本可直接编辑,支持局部复制/撤销,15 秒无操作自动关闭。"""
    import tkinter as tk

    from snapocr.clipboard import copy_text

    root = tk.Tk()
    root.title("SnapOCR 识别结果")
    root.attributes("-topmost", True)
    root.geometry("560x360")
    root.configure(bg="#1b1f2a")

    count_var = tk.StringVar()

    def update_count(_event=None):
        content = body.get("1.0", "end-1c")
        count_var.set(f"{len(content)} 字符 · Esc 关闭 · Ctrl+Enter 复制并关闭")

    info = tk.Label(root, textvariable=count_var, fg="#8fa3b8", bg="#1b1f2a",
                    font=("Microsoft YaHei", 9), anchor="w", padx=12, pady=8)
    info.pack(fill="x")

    body = tk.Text(
        root, wrap="word", relief="flat", undo=True, maxundo=-1,
        bg="#12151d", fg="#e6edf3", insertbackground="#e6edf3",
        font=("Microsoft YaHei", 11), padx=12, pady=10,
    )
    body.pack(fill="both", expand=True, padx=12)
    body.insert("1.0", text)
    body.bind("<<Modified>>", update_count)
    update_count()

    bar = tk.Frame(root, bg="#1b1f2a")
    bar.pack(fill="x", padx=12, pady=10)

    def btn(text, cmd, primary=False):
        return tk.Button(
            bar, text=text, command=cmd, relief="flat",
            bg="#00e5ff" if primary else "#2a3040",
            fg="#101418" if primary else "#c9d4e0",
            font=("Microsoft YaHei", 10, "bold" if primary else "normal"),
            padx=12, pady=4, cursor="hand2",
        )

    def get_copy_text() -> str:
        sel = body.tag_ranges("sel")
        return body.get("sel.first", "sel.last") if sel else body.get("1.0", "end-1c")

    def do_copy(_event=None):
        copy_text(get_copy_text())
        copy_btn.config(text="已复制 ✓")
        root.after(1200, lambda: copy_btn.config(text="复制"))

    def close(_event=None):
        root.destroy()

    def undo():
        try:
            body.edit_undo()
        except tk.TclError:
            pass

    def select_all():
        body.tag_add("sel", "1.0", "end-1c")

    copy_btn = btn("复制", do_copy, primary=True)
    copy_btn.pack(side="left")
    btn("全选", select_all).pack(side="left", padx=4)
    btn("撤销", undo).pack(side="left", padx=4)
    btn("关闭", close).pack(side="right")

    root.bind("<Escape>", close)
    root.bind("<Control-Return>", do_copy)
    root.after(30000, close)
    root.mainloop()


class SnapOcrApp:
    """事件驱动的常驻应用:热键线程只发信号,主线程串行干活。"""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._wake = threading.Event()
        self._engine: Optional[OcrEngine] = None
        self.icon = None

    def _get_engine(self) -> OcrEngine:
        if self._engine is None:
            self._engine = OcrEngine(confidence=self.cfg.confidence)
        return self._engine

    # ---- 热键线程调用 ----
    def request_capture(self) -> None:
        self._wake.set()

    # ---- 主线程 ----
    def run_forever(self) -> None:
        while True:
            self._wake.wait()
            self._wake.clear()
            try:
                self._process()
            except Exception as exc:  # 不让任何异常终止常驻进程
                self._notify(f"出错:{exc}")

    def _notify(self, message: str) -> None:
        if self.icon is not None:
            try:
                self.icon.notify(message, title="SnapOCR")
            except Exception:
                pass

    def _process(self) -> None:
        from snapocr.capture import grab_region

        image = grab_region()
        if image is None:
            return

        if self.cfg.enable_editor:
            from snapocr.editor import edit_image

            image = edit_image(image)
            if image is None:
                return

        self._notify("正在识别…")

        if self.cfg.save_screenshot and self.cfg.screenshot_dir:
            os.makedirs(self.cfg.screenshot_dir, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            image.save(os.path.join(self.cfg.screenshot_dir, f"snapocr_{stamp}.png"))

        text = self._get_engine().recognize(image)

        if not text.strip():
            self._notify("未识别到文本,请框选更清晰的区域")
            return
        if self.cfg.auto_copy and copy_text(text):
            pass
        if self.cfg.show_result:
            _show_result_window(text, hotkey_hint=self.cfg.hotkey)
        else:
            self._notify(f"已复制 {len(text)} 个字符")

    # ---- 托盘 ----
    def _build_tray(self):
        import pystray
        from pystray import Menu, MenuItem

        def on_capture(_icon=None, _item=None):
            self.request_capture()

        def on_config(_icon=None, _item=None):
            path = save(self.cfg)  # 写入一份默认配置,方便用户修改
            os.startfile(os.path.dirname(path))

        def on_exit(_icon=None, _item=None):
            self.icon.stop()
            os._exit(0)

        menu = Menu(
            MenuItem(f"截图取字 ({self.cfg.hotkey})", on_capture, default=True),
            MenuItem("打开配置目录", on_config),
            MenuItem("退出", on_exit),
        )
        self.icon = pystray.Icon("SnapOCR", _tray_image(), "SnapOCR — 截图取字", menu)
        self.icon.run_detached()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snapocr", description="截图取字:框选屏幕区域 → OCR → 自动复制剪贴板",
    )
    parser.add_argument("--hotkey", help="全局热键,默认 ctrl+alt+a")
    parser.add_argument("--confidence", type=float, help="OCR 置信度阈值,默认 0.5")
    parser.add_argument("--no-editor", action="store_true", help="跳过标注编辑器,直接识别")
    parser.add_argument("--no-result", action="store_true", help="不弹结果窗口,仅复制+气泡提示")
    parser.add_argument("--save-screenshot", metavar="DIR", help="保存原始截图到指定目录")
    parser.add_argument("--config", help="自定义配置文件路径")
    parser.add_argument("--version", action="version", version=f"snapocr {__version__}")
    return parser


def main(argv=None) -> None:
    args = _build_parser().parse_args(argv)
    _enable_dpi_awareness()

    cfg = load(args.config)
    if args.hotkey:
        cfg.hotkey = args.hotkey
    if args.confidence is not None:
        cfg.confidence = args.confidence
    if args.no_editor:
        cfg.enable_editor = False
    if args.no_result:
        cfg.show_result = False
    if args.save_screenshot:
        cfg.save_screenshot = True
        cfg.screenshot_dir = args.save_screenshot

    app = SnapOcrApp(cfg)

    import keyboard

    keyboard.add_hotkey(cfg.hotkey, app.request_capture)

    app._build_tray()
    app.run_forever()


if __name__ == "__main__":
    main()
