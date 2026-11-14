"""图片标注编辑器:矩形框 / 画笔 / 马赛克 / 撤销,可复制图片或继续识别。

渲染逻辑(render_ops / make_mosaic)是纯函数,与 GUI 分离,可独立单测;
编辑器每一步只往 ops 列表追加操作,撤销即弹出并重渲染,无需图像快照栈。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PIL.Image import Image

TOOLS = ("rect", "pen", "mosaic")
TOOL_NAMES = {"rect": "矩形框", "pen": "画笔", "mosaic": "马赛克"}
COLORS = {"红": "#ff3b30", "黄": "#ffd60a", "蓝": "#0a84ff", "白": "#ffffff"}
WIDTHS = {"细": 3, "中": 6, "粗": 12}
MOSAIC_BLOCK = 14


def make_mosaic(image: Image, block: int = MOSAIC_BLOCK) -> Image:
    """生成马赛克版本:缩小再放大,像素化。"""
    w, h = image.size
    small = image.resize((max(1, w // block), max(1, h // block)))
    return small.resize((w, h))


def _stamp_mosaic(img: Image, mosaic: Image, points: List, radius: int) -> None:
    """把马赛克图上的圆形区域戳到目标图上。"""
    w, h = img.size
    for x, y in points:
        box = (
            max(0, int(x) - radius), max(0, int(y) - radius),
            min(w, int(x) + radius), min(h, int(y) + radius),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        patch = mosaic.crop(box)
        img.paste(patch, (box[0], box[1]))


def render_ops(base: Image, ops: List[Dict[str, Any]]) -> Image:
    """把操作序列渲染到 base 的副本上,返回新图(纯函数)。"""
    from PIL import ImageDraw

    img = base.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    mosaic = None
    for op in ops:
        kind = op["type"]
        if kind == "rect":
            draw.rectangle(op["box"], outline=op["color"], width=op["width"])
        elif kind == "pen":
            pts = op["points"]
            if len(pts) == 1:
                x, y = pts[0]
                r = op["width"] / 2
                draw.ellipse((x - r, y - r, x + r, y + r), fill=op["color"])
            else:
                draw.line(pts, fill=op["color"], width=op["width"], joint="curve")
        elif kind == "mosaic":
            if mosaic is None:
                mosaic = make_mosaic(base)
            _stamp_mosaic(img, mosaic, op["points"], radius=op["width"] * 2)
    return img


class ImageEditor:
    """tkinter 标注编辑器,edit() 返回编辑后的图,取消返回 None。"""

    def __init__(self, image: Image):
        self.original = image.convert("RGB")
        self.ops: List[Dict[str, Any]] = []
        self.result: Optional[Image] = None
        self.tool = "rect"
        self.color = COLORS["红"]
        self.width = WIDTHS["中"]
        self._stroke: List = []
        self._preview: List[int] = []  # canvas 预览项 id
        self._photo = None
        self._scale = 1.0

    # ---- 对外入口 ----
    def edit(self) -> Optional[Image]:
        import tkinter as tk

        from PIL import ImageTk

        vw = self.original.width
        vh = self.original.height
        self._scale = min(1.0, 1100 / vw, 640 / vh)
        cw, ch = int(vw * self._scale), int(vh * self._scale)

        root = tk.Tk()
        root.title("SnapOCR 编辑 (标注后可复制图片或识别文字)")
        root.attributes("-topmost", True)
        root.configure(bg="#1b1f2a")

        bar = tk.Frame(root, bg="#1b1f2a")
        bar.pack(fill="x", padx=8, pady=6)

        def flat_btn(text, cmd, **kw):
            return tk.Button(
                bar, text=text, command=cmd, relief="flat",
                bg="#2a3040", fg="#e6edf3", font=("Microsoft YaHei", 9),
                padx=8, pady=3, cursor="hand2", **kw,
            )

        self._tool_var = tk.StringVar(value=TOOL_NAMES[self.tool])
        for t in TOOLS:
            flat_btn(
                TOOL_NAMES[t],
                lambda t=t: self._set_tool(t, self._tool_var),
            ).pack(side="left", padx=(8 if t == "rect" else 2, 2))
        tk.Label(bar, text="颜色:", bg="#1b1f2a", fg="#8fa3b8",
                 font=("Microsoft YaHei", 9)).pack(side="left", padx=(14, 2))
        for name, hexval in COLORS.items():
            tk.Button(
                bar, text=" ", bg=hexval, width=2, relief="flat", cursor="hand2",
                command=lambda h=hexval: setattr(self, "color", h),
            ).pack(side="left", padx=2)
        tk.Label(bar, text="粗细:", bg="#1b1f2a", fg="#8fa3b8",
                 font=("Microsoft YaHei", 9)).pack(side="left", padx=(14, 2))
        for name, w in WIDTHS.items():
            flat_btn(name, lambda w=w: setattr(self, "width", w)).pack(side="left", padx=2)
        flat_btn("撤销", self._undo).pack(side="left", padx=(14, 2))
        flat_btn("清空", self._clear).pack(side="left", padx=2)

        canvas = tk.Canvas(root, width=cw, height=ch, bg="#12151d",
                           highlightthickness=0, cursor="crosshair")
        canvas.pack(padx=8)
        self._canvas = canvas

        self._photo = ImageTk.PhotoImage(render_ops(self.original, self.ops).resize(
            (cw, ch)))
        self._base_photo = self._photo
        canvas.create_image(0, 0, image=self._photo, anchor="nw")

        foot = tk.Frame(root, bg="#1b1f2a")
        foot.pack(fill="x", padx=8, pady=8)
        self._status = tk.Label(foot, text=f"{vw}x{vh}", bg="#1b1f2a", fg="#8fa3b8",
                                font=("Microsoft YaHei", 9))
        self._status.pack(side="left")

        def flat_btn2(text, cmd, primary=False):
            return tk.Button(
                foot, text=text, command=cmd, relief="flat",
                bg="#00e5ff" if primary else "#2a3040",
                fg="#101418" if primary else "#e6edf3",
                font=("Microsoft YaHei", 10, "bold" if primary else "normal"),
                padx=16, pady=4, cursor="hand2",
            )

        flat_btn2("复制图片", self._copy_image).pack(side="right", padx=4)
        flat_btn2("识别文字", self._finish, primary=True).pack(side="right", padx=4)
        flat_btn2("取消", root.destroy).pack(side="right", padx=4)

        canvas.bind("<ButtonPress-1>", self._on_press)
        canvas.bind("<B1-Motion>", self._on_drag)
        canvas.bind("<ButtonRelease-1>", self._on_release)
        root.bind("<Escape>", lambda e: root.destroy())

        root.focus_force()
        root.mainloop()
        return self.result

    # ---- 内部 ----
    def _set_tool(self, tool, var):
        self.tool = tool
        var.set(TOOL_NAMES[tool])

    def _to_image_coords(self, x, y):
        return (int(x / self._scale), int(y / self._scale))

    def _clear_preview(self):
        for item in self._preview:
            self._canvas.delete(item)
        self._preview = []

    def _refresh(self):
        from PIL import ImageTk

        cw = int(self.original.width * self._scale)
        ch = int(self.original.height * self._scale)
        shown = render_ops(self.original, self.ops).resize((cw, ch))
        self._photo = ImageTk.PhotoImage(shown)
        self._canvas.create_image(0, 0, image=self._photo, anchor="nw")

    def _undo(self):
        if self.ops:
            self.ops.pop()
            self._refresh()

    def _clear(self):
        self.ops = []
        self._refresh()

    def _on_press(self, event):
        self._stroke = [self._to_image_coords(event.x, event.y)]
        if self.tool == "rect":
            self._preview = [self._canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline=self.color, width=self.width)]

    def _on_drag(self, event):
        if not self._stroke:
            return
        self._stroke.append(self._to_image_coords(event.x, event.y))
        if self.tool == "pen":
            x0, y0 = self._stroke[-2]
            x1, y1 = self._stroke[-1]
            self._preview.append(self._canvas.create_line(
                x0, y0, x1, y1,
                fill=self.color, width=self.width,
                capstyle="round"))
        elif self.tool == "rect":
            x0, y0 = self._stroke[0]
            self._canvas.coords(self._preview[0], x0, y0, event.x, event.y)
        elif self.tool == "mosaic":
            r = self.width * 2 * self._scale
            self._canvas.delete("mosaic_hint")
            self._canvas.create_oval(
                event.x - r, event.y - r, event.x + r, event.y + r,
                outline="#ffffff", width=1, tags="mosaic_hint")

    def _on_release(self, event):
        self._clear_preview()
        self._canvas.delete("mosaic_hint")
        if not self._stroke:
            return
        self._stroke.append(self._to_image_coords(event.x, event.y))
        if self.tool == "rect":
            x0, y0 = self._stroke[0]
            x1, y1 = self._stroke[-1]
            box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            if box[2] - box[0] > 3 and box[3] - box[1] > 3:
                self.ops.append({"type": "rect", "box": box,
                                 "color": self.color, "width": self.width})
        elif self.tool == "pen":
            self.ops.append({"type": "pen", "points": self._stroke,
                             "color": self.color, "width": self.width})
        elif self.tool == "mosaic":
            self.ops.append({"type": "mosaic", "points": self._stroke,
                             "width": self.width})
        self._stroke = []
        self._refresh()

    def _finish(self):
        self.result = render_ops(self.original, self.ops)
        self._canvas.master.destroy()

    def _copy_image(self):
        from snapocr.clipboard import copy_image

        ok = copy_image(render_ops(self.original, self.ops))
        self._status.config(text="已复制图片到剪贴板 ✓" if ok else "复制失败")


def edit_image(image: Image) -> Optional[Image]:
    """打开标注编辑器;关闭/取消返回 None。"""
    return ImageEditor(image).edit()
