<div align="center">

# SnapOCR

**Press a hotkey → drag a box → get text in your clipboard.**

A lightweight, offline screenshot-to-text (OCR) tool for Windows.
Powered by [RapidOCR](https://github.com/RapidAI/RapidOCR) — no API keys, no cloud, no telemetry.

[![CI](https://github.com/yund229/SnapOCR/actions/workflows/ci.yml/badge.svg)](https://github.com/yund229/SnapOCR/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/yund229/SnapOCR?include_prereleases)](https://github.com/yund229/SnapOCR/releases)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[中文说明](#中文说明) · [Features](#features) · [Install](#install) · [Usage](#usage) · [How it works](#how-it-works) · [FAQ](#faq)

</div>

---

## Features

- **Global hotkey** — `Ctrl+Alt+A` (configurable) triggers region capture from anywhere
- **Drag-to-select overlay** — crosshair cursor with a dimmed fullscreen mask, multi-monitor supported
- **Offline OCR** — ONNX Runtime models bundled locally, Chinese & English, zero network usage
- **Auto copy** — recognized text lands in your clipboard instantly
- **CJK-aware post-processing** — merges OCR line fragments into flowing paragraphs, strips stray spaces between Chinese characters
- **High-DPI correct** — per-monitor DPI awareness, coordinates match physical pixels
- **Tray resident** — lives in the system tray, near-zero footprint
- **Single-file portable exe** — download from Releases, no Python required

## Install

### Option 1: Portable exe (recommended)

Grab `SnapOCR.exe` from the [Releases](https://github.com/yund229/SnapOCR/releases) page and run it. Done.

### Option 2: From source

```bash
pip install git+https://github.com/yund229/SnapOCR.git
snapocr            # or: python -m snapocr
```

## Usage

1. Run SnapOCR — a tray icon appears.
2. Press `Ctrl+Alt+A`, drag a box around any text on screen.
3. Release the mouse: text is recognized, copied to clipboard, and shown in a result popup (`Esc` closes, auto-closes after 15 s).

### CLI flags

| Flag | Effect |
| --- | --- |
| `--hotkey` | Change the trigger hotkey, e.g. `--hotkey ctrl+shift+s` |
| `--confidence` | OCR confidence threshold (default `0.5`) |
| `--no-result` | Skip the popup — copy + tray balloon only |
| `--save-screenshot DIR` | Also save the raw screenshot as PNG |
| `--config PATH` | Use a custom config file |

Settings persist at `%APPDATA%\SnapOCR\config.json` (accessible from the tray menu).

## How it works

```
 global hotkey          drag-select overlay         RapidOCR (ONNX, local)
 ─────────────►  main  ─────────────────────►  grab bbox  ────────────────►  post-process
 keyboard hook      tkinter fullscreen               ImageGrab              merge CJK lines,
 (worker thread)    mask + rectangle                 (physical px)          strip spaces
                                                                            ────► clipboard + popup
```

- The keyboard hook only *signals* an event; tkinter always runs on the main thread (the most stable arrangement on Windows).
- The OCR model loads lazily on first use, so startup is instant.
- Text post-processing lives in [`snapocr/ocr.py`](snapocr/ocr.py) and is fully covered by unit tests.

## Development

```bash
git clone https://github.com/yund229/SnapOCR.git
cd SnapOCR
pip install -e .[dev]
pytest            # unit tests + end-to-end OCR test on rendered sample images
ruff check snapocr tests
```

Build the portable exe locally:

```bash
pyinstaller --onefile --name SnapOCR --collect-all rapidocr_onnxruntime snapocr/__main__.py
```

Pushing a `v*` tag triggers the release workflow, which builds and attaches `SnapOCR.exe` automatically.

## FAQ

**Is my screen content uploaded anywhere?**
No. Recognition runs entirely offline with bundled ONNX models.

**It fails on my laptop with mixed DPI monitors?**
Fixed by per-monitor DPI awareness; make sure you run a recent release.

**Linux / macOS?**
Core logic is cross-platform, but the hotkey + tray layer is currently Windows-oriented (`os.startfile`, balloon tips). PRs welcome.

## Roadmap

- [ ] Result window with inline re-edit
- [ ] Table / QR code mode
- [ ] History panel (`Ctrl+Alt+H`)
- [ ] Cross-platform hotkey layer via pynput

## Acknowledgments

- [RapidOCR](https://github.com/RapidAI/RapidOCR) — PaddleOCR models on ONNX Runtime
- [pystray](https://github.com/moses-palmer/pystray) · [keyboard](https://github.com/boppreh/keyboard) · [pyperclip](https://github.com/asweigart/pyperclip)

## License

[MIT](LICENSE) © 2026 yund229

---

<div align="center" id="中文说明">

## 中文说明

SnapOCR 是一款 Windows 下的轻量级**截图取字工具**:按下全局热键 → 拖框 → 文字自动进剪贴板。基于 RapidOCR 本地离线识别,**无需联网、无需 API Key、不上传任何数据**。

### 功能亮点

- 全局热键 `Ctrl+Alt+A` 触发框选,支持多显示器
- 离线 OCR,中英文混排识别效果好
- 中文后处理:自动合并行片段、去掉汉字间多余空格
- 高 DPI 屏幕坐标精确,截图不偏移
- 托盘常驻,提供便携版单文件 exe,无需安装 Python

### 快速开始

```bash
# 方式一:去 Releases 下载 SnapOCR.exe 直接运行
# 方式二:源码安装
pip install git+https://github.com/yund229/SnapOCR.git
snapocr
```

按 `Ctrl+Alt+A` → 拖框 → 松开鼠标即得文本(已复制 + 弹窗展示)。配置文件位于 `%APPDATA%\SnapOCR\config.json`,托盘菜单可直接打开。

</div>
