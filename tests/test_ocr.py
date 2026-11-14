"""OCR 端到端测试:程序生成样例图 → 真实识别。

依赖 rapidocr_onnxruntime,未安装时自动跳过(CI 中已安装,会真实执行)。
"""

import pytest

pytest.importorskip("rapidocr_onnxruntime", reason="OCR 引擎未安装,跳过端到端测试")

from snapocr.ocr import OcrEngine  # noqa: E402


def _render_text_image(text: str, size=(560, 140)):
    """用 PIL 渲染一张白底黑字的样例图。"""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    font = None
    for candidate in ("DejaVuSans.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(candidate, 52)
            break
        except OSError:
            continue
    if font is None:
        pytest.skip("测试环境没有可用的 TrueType 字体")
    draw.text((20, 40), text, fill="black", font=font)
    return img


@pytest.fixture(scope="module")
def engine():
    return OcrEngine(confidence=0.3)


def test_recognize_english_and_digits(engine):
    text = engine.recognize(_render_text_image("Hello 123"))
    lowered = text.lower().replace(" ", "")
    assert "hello" in lowered or "123" in lowered


def test_recognize_returns_str(engine):
    text = engine.recognize(_render_text_image("SnapOCR"))
    assert isinstance(text, str)
