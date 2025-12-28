from unittest.mock import patch

from poehub.core.i18n import LANG_EN, LANG_ZH_CN, LANG_ZH_TW, STRINGS, tr


class TestI18n:
    def test_tr_en(self):
        # Test a known key
        key = "CLOSE_MENU"
        result = tr(LANG_EN, key)
        assert result == "Close"

    def test_tr_fallback(self):
        # Test fallback to En if key missing in target lang
        # Let's artificially creating a missing key scenario by mocking STRINGS
        with patch.dict(STRINGS, {LANG_EN: {"test": "English"}, "es": {}}):
            result = tr("es", "test")
            assert result == "English"

    def test_tr_missing_key(self):
        # Key missing in both
        key = "NON_EXISTENT_KEY_123"
        result = tr(LANG_EN, key)
        assert result == key

    def test_tr_formatting(self):
        # Test formatting
        with patch.dict(STRINGS, {LANG_EN: {"hello": "Hello {name}"}}):
            result = tr(LANG_EN, "hello", name="World")
            assert result == "Hello World"

    def test_tr_formatting_error(self):
        # Test formatting error handling
        with patch.dict(STRINGS, {LANG_EN: {"hello": "Hello {name}"}}):
            # Missing format argument
            result = tr(LANG_EN, "hello")
            # Should return template
            assert result == "Hello {name}"

    def test_tr_zh_tw(self):
        # Test another language
        key = "CLOSE_MENU"
        # Assuming ZH_TW has this key
        result = tr(LANG_ZH_TW, key)
        assert result == "關閉"

    def test_tr_zh_cn(self):
        # Test Simplified Chinese
        key = "CLOSE_MENU"
        result = tr(LANG_ZH_CN, key)
        assert result == "关闭"
