"""配置模块:默认存放于 %APPDATA%/SnapOCR/config.json,可被命令行参数覆盖。"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Optional

DEFAULT_HOTKEY = "ctrl+alt+a"


@dataclass
class Config:
    """SnapOCR 运行配置。"""

    hotkey: str = DEFAULT_HOTKEY          # 全局截图热键(keyboard 库语法)
    confidence: float = 0.5               # OCR 结果置信度阈值
    enable_editor: bool = True            # 截图后先打开标注编辑器(矩形/画笔/马赛克)
    auto_copy: bool = True                # 识别完成后自动复制到剪贴板
    show_result: bool = True              # 是否弹出结果窗口(否则仅托盘气泡提示)
    save_screenshot: bool = False         # 是否保存原始截图
    screenshot_dir: str = ""              # 截图保存目录(save_screenshot 开启时生效)


def config_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "SnapOCR")


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


def load(path: Optional[str] = None) -> Config:
    """读取配置;文件缺失或损坏时静默回退到默认值。"""
    path = path or config_path()
    cfg = Config()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, value in data.items():
                if hasattr(cfg, key) and value is not None:
                    setattr(cfg, key, value)
        except (OSError, ValueError, AttributeError):
            pass
    return cfg


def save(cfg: Config, path: Optional[str] = None) -> str:
    path = path or config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
    return path
