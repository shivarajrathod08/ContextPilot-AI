"""Tests for the optional Alan AI voice embed.

No network calls are made: these cover key handling, HTML validity, and the
guarantee that the embed stays inert when the project is not configured.
"""

import pytest

from core import alan_voice


class TestAlanConfig:
    def test_unconfigured_returns_empty_html(self, monkeypatch):
        monkeypatch.delenv("ALAN_PROJECT_KEY", raising=False)
        assert not alan_voice.is_configured()
        assert alan_voice.build_embed_html() == ""

    def test_configured_key_is_detected(self, monkeypatch):
        monkeypatch.setenv("ALAN_PROJECT_KEY", "abcdef1234567890")
        assert alan_voice.is_configured()

    def test_explicit_key_overrides_environment(self, monkeypatch):
        monkeypatch.setenv("ALAN_PROJECT_KEY", "environmentkey123")
        assert alan_voice.get_project_key("explicitkey12345") == "explicitkey12345"


class TestEmbedHtml:
    def test_embed_loads_sdk_and_host(self, monkeypatch):
        monkeypatch.setenv("ALAN_PROJECT_KEY", "abcdef1234567890")
        html = alan_voice.build_embed_html()

        assert "alan_lib.min.js" in html
        assert "abcdef1234567890" in html
        assert "v1.alan.app" in html
        assert "prefillTask" in html

    def test_malformed_key_is_rejected(self, monkeypatch):
        monkeypatch.setenv("ALAN_PROJECT_KEY", 'bad"key</script>')
        with pytest.raises(ValueError):
            alan_voice.build_embed_html()

    def test_key_is_json_encoded(self):
        html = alan_voice.build_embed_html('key-with_underscores123')
        assert '"key-with_underscores123"' in html