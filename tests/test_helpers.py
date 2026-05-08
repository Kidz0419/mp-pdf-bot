"""Tests for pure helper functions in mybot."""
import importlib.machinery
import importlib.util
from pathlib import Path

# load mybot module dynamically (no .py extension)
_path = str(Path(__file__).resolve().parent.parent / "mybot")
_loader = importlib.machinery.SourceFileLoader("mybot", _path)
_spec = importlib.util.spec_from_loader("mybot", _loader, origin=_path)
mybot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mybot)


def test_sanitize_filename_strips_invalid_chars():
    assert mybot.sanitize_filename('a/b\\c:d*e?f"g<h>i|j') == "a_b_c_d_e_f_g_h_i_j"

def test_sanitize_filename_keeps_chinese():
    assert mybot.sanitize_filename("看见童话~") == "看见童话~"

def test_sanitize_filename_truncates():
    assert len(mybot.sanitize_filename("x" * 200, max_len=80)) == 80

def test_sanitize_filename_strips_control_chars():
    assert mybot.sanitize_filename("a\x00b\x1fc") == "a_b_c"

def test_find_chrome_returns_existing_path(tmp_path, monkeypatch):
    fake_chrome = tmp_path / "Chrome"
    fake_chrome.write_text("")
    monkeypatch.setattr(mybot, "CHROME_CANDIDATES", [str(fake_chrome)])
    assert mybot.find_chrome() == str(fake_chrome)

def test_find_chrome_raises_when_none(monkeypatch):
    monkeypatch.setattr(mybot, "CHROME_CANDIDATES", ["/nonexistent/path"])
    try:
        mybot.find_chrome()
    except SystemExit as e:
        assert "Chrome" in str(e) or e.code != 0
    else:
        raise AssertionError("expected SystemExit")

def test_load_config_parses_env_file(tmp_path):
    cfg = tmp_path / "config.env"
    cfg.write_text("WEWE_RSS_PORT=4001\nAUTH_CODE=secret\n# comment\nCRON_TIME=\"0 6 * * *\"\n")
    result = mybot.load_config(cfg)
    assert result["WEWE_RSS_PORT"] == "4001"
    assert result["AUTH_CODE"] == "secret"
    assert result["CRON_TIME"] == "0 6 * * *"
