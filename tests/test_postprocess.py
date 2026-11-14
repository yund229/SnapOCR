"""文本后处理单元测试:不依赖 OCR 引擎,纯逻辑验证。"""

from snapocr.ocr import merge_lines, postprocess, squeeze_spaces


class TestSqueezeSpaces:
    def test_removes_spaces_between_cjk(self):
        assert squeeze_spaces("你好 世界") == "你好世界"
        assert squeeze_spaces("你 好 ， 世 界") == "你好，世界"

    def test_keeps_latin_word_spaces(self):
        assert squeeze_spaces("hello world") == "hello world"

    def test_mixed_content(self):
        assert squeeze_spaces("使用 Python 写代码") == "使用 Python 写代码"

    def test_empty_string(self):
        assert squeeze_spaces("") == ""


class TestMergeLines:
    def test_merges_cjk_lines(self):
        assert merge_lines(["今天天气", "不错"]) == "今天天气不错"

    def test_breaks_on_sentence_punctuation(self):
        assert merge_lines(["第一行。", "第二行"]) == "第一行。\n第二行"

    def test_keeps_latin_lines_separate(self):
        assert merge_lines(["hello", "world"]) == "hello\nworld"

    def test_empty_list(self):
        assert merge_lines([]) == ""


class TestPostprocess:
    def test_filters_low_confidence(self):
        lines = [
            ([[0, 0], [10, 10]], "高置信", 0.9),
            ([[0, 0], [10, 10]], "低置信", 0.2),
        ]
        assert postprocess(lines, confidence=0.5) == "高置信"

    def test_malformed_items_are_skipped(self):
        lines = [
            [0, 0],                      # 缺字段
            ("box", "缺分数"),           # 缺置信度
            ("box", "坏分数", "abc"),    # 分数无法解析
            ([[0, 0], [1, 1]], "正常", 0.9),
        ]
        assert postprocess(lines, confidence=0.5) == "正常"

    def test_empty_result(self):
        assert postprocess([]) == ""
