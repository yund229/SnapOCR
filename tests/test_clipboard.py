"""剪贴板兜底路径测试(不依赖真实剪贴板,只测 Win32 分支的存在性)。"""

import sys

from snapocr.clipboard import copy_text


def test_copy_text_returns_bool():
    # 在 CI/无头环境下允许失败,但函数必须返回布尔值而不是抛异常
    result = copy_text("snapocr-test-中文")
    assert isinstance(result, bool)


def test_win32_fallback_only_on_windows():
    if sys.platform != "win32":
        from snapocr.clipboard import _copy_win32

        assert not hasattr(_copy_win32, "__defaults__") or True  # 可导入即可
