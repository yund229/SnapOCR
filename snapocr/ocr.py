"""OCR 模块:RapidOCR 引擎懒加载封装 + 中文友好的文本后处理。

后处理规则:
1. 过滤低置信度识别结果;
2. 相邻两行若均为中文且上一行没有句末标点,则合并为一段;
3. 去除 CJK 字符之间的多余空格(OCR 常见噪声)。
"""

from __future__ import annotations

import re
from typing import Any, List, Sequence

# CJK 统一表意文字 + 扩展A + 常用全角符号
_CJK = r"[\u3400-\u4dbf\u4e00-\u9fff]"
_CJK_END = re.compile(_CJK + r"$")
_CJK_START = re.compile(r"^" + _CJK)
# 去空格时把全角标点也算进来,才能清掉 "好 ," 这类噪声
_CJK_OR_PUNCT = r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]"
_SPACE_BETWEEN_CJK = re.compile(rf"({_CJK_OR_PUNCT})\s+({_CJK_OR_PUNCT})")


def squeeze_spaces(text: str) -> str:
    """去掉两个 CJK 字符之间的空白,保留西文单词间空格。

    单次 re.sub 不重叠匹配无法处理 "好 ， 世" 这类连续空格链,迭代到不再变化。
    """
    while True:
        squeezed = _SPACE_BETWEEN_CJK.sub(r"\1\2", text)
        if squeezed == text:
            return text
        text = squeezed


def merge_lines(lines: Sequence[str]) -> str:
    """合并多行文本:中文字行自动续接,西文/标点处换行。"""
    if not lines:
        return ""
    merged = lines[0]
    for nxt in lines[1:]:
        if merged and _CJK_END.search(merged) and _CJK_START.search(nxt):
            merged += nxt  # 中文行尾 + 中文行首 → 直接续接
        else:
            merged += "\n" + nxt
    return merged


def postprocess(lines: Sequence[Any], confidence: float = 0.5) -> str:
    """对 RapidOCR 原始结果([box, text, score], ...)做过滤与排版。"""
    texts: List[str] = []
    for item in lines:
        try:
            score = float(item[2])
            text = str(item[1]).strip()
        except (IndexError, TypeError, ValueError):
            continue
        if text and score >= confidence:
            texts.append(text)
    return squeeze_spaces(merge_lines(texts))


class OcrEngine:
    """懒加载的 OCR 引擎:首次识别时才初始化模型,加快程序启动。"""

    def __init__(self, confidence: float = 0.5):
        self.confidence = confidence
        self._engine: Any = None

    def _ensure_engine(self) -> Any:
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR  # 延迟导入

            self._engine = RapidOCR()
        return self._engine

    def recognize(self, image) -> str:
        """识别 PIL Image / numpy 数组 / 图片路径,返回整理后的文本。"""
        raw, _ = self._ensure_engine()(image)
        return postprocess(raw or [], self.confidence)
