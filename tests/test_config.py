"""配置模块测试:读写回环、损坏文件回退。"""

import json

from snapocr.config import Config, load, save


def test_default_config():
    cfg = Config()
    assert cfg.hotkey == "ctrl+alt+a"
    assert cfg.auto_copy is True
    assert cfg.show_result is True
    assert 0.0 <= cfg.confidence <= 1.0


def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    cfg = Config(hotkey="ctrl+shift+x", confidence=0.7, show_result=False)
    save(cfg, str(path))
    loaded = load(str(path))
    assert loaded == cfg


def test_load_missing_file_returns_defaults(tmp_path):
    cfg = load(str(tmp_path / "not_exist.json"))
    assert cfg == Config()


def test_load_corrupt_file_returns_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{broken json!!", encoding="utf-8")
    cfg = load(str(path))
    assert cfg == Config()


def test_load_ignores_unknown_keys(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"hotkey": "f9", "future_field": 1}), encoding="utf-8")
    cfg = load(str(path))
    assert cfg.hotkey == "f9"
