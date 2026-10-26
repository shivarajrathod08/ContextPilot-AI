"""Tests for the optional open-weight (Ollama) generation engine.

Verifies configuration resolution, availability probing, error mapping, and that
selecting the local engine leaves the deterministic default untouched.
"""

import urllib.error

import pytest

from core import openweight_engine as oe
from core.ai_common import brief_from_markdown
from core.generator import generate_brief
from core.models import BriefRequest, GenerationMode, ProjectType, TaskScope


class TestLocalConfig:
    def test_defaults_to_local_ollama(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        assert oe.get_local_config() == ("http://localhost:11434", "")

    def test_explicit_values_beat_environment(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://gpu-box:11434/")
        monkeypatch.setenv("OLLAMA_MODEL", "env-model")
        assert oe.get_local_config("http://override:11434", "cli-model") == (
            "http://override:11434",
            "cli-model",
        )

    def test_rejects_non_http_base_url(self):
        with pytest.raises(ValueError):
            oe.get_local_config("localhost:11434", "model")

    def test_empty_base_url_falls_back_to_default(self):
        assert oe.get_local_config("", "model")[0] == "http://localhost:11434"


class TestAvailability:
    def test_missing_model_is_reported(self):
        is_ready, message = oe.is_local_llm_available("http://localhost:11434", "")
        assert not is_ready
        assert "model" in message.lower()

    def test_unreachable_server_explains_how_to_start(self, monkeypatch):
        def boom(*args, **kwargs):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(oe, "_http_json", boom)
        is_ready, message = oe.is_local_llm_available("http://localhost:11434", "qwen2.5:7b-instruct")
        assert not is_ready
        assert "ollama serve" in message

    def test_installed_model_is_detected(self, monkeypatch):
        monkeypatch.setattr(
            oe,
            "_http_json",
            lambda *args, **kwargs: {"models": [{"name": "qwen2.5:7b-instruct"}]},
        )
        is_ready, message = oe.is_local_llm_available("http://localhost:11434", "qwen2.5:7b-instruct")
        assert is_ready
        assert "qwen2.5:7b-instruct" in message

    def test_untagged_alias_matches_installed_tag(self, monkeypatch):
        monkeypatch.setattr(
            oe,
            "_http_json",
            lambda *args, **kwargs: {"models": [{"name": "qwen2.5:7b-instruct"}]},
        )
        is_ready, _ = oe.is_local_llm_available("http://localhost:11434", "qwen2.5")
        assert is_ready

    def test_missing_model_suggests_pull(self, monkeypatch):
        monkeypatch.setattr(
            oe,
            "_http_json",
            lambda *args, **kwargs: {"models": [{"name": "mistral:7b"}]},
        )
        is_ready, message = oe.is_local_llm_available("http://localhost:11434", "qwen2.5:7b-instruct")
        assert not is_ready
        assert "ollama pull" in message


class TestLocalGeneration:
    def test_requires_a_model(self):
        with pytest.raises(ValueError):
            oe.generate_local_brief(BriefRequest(task_description="Implement a meaningful feature"))

    def test_builds_brief_from_chat_response(self, monkeypatch):
        captured = {}

        def fake_http(url, payload=None, timeout=10.0):
            captured["url"] = url
            captured["payload"] = payload
            return {"message": {"role": "assistant", "content": "# Brief: Local\n\n## 1. Summary\nBody"}}

        monkeypatch.setattr(oe, "_http_json", fake_http)
        request = BriefRequest(
            task_description="Add pagination to the products API",
            project_type=ProjectType.PYTHON,
            local_model="qwen2.5:7b-instruct",
        )
        brief = oe.generate_local_brief(request)

        assert captured["url"] == "http://localhost:11434/api/chat"
        assert captured["payload"]["model"] == "qwen2.5:7b-instruct"
        assert captured["payload"]["stream"] is False
        assert captured["payload"]["messages"][0]["role"] == "system"
        assert brief.mode_used == GenerationMode.LOCAL_OPEN_WEIGHT
        assert brief.title == "Brief: Local"
        assert brief.raw_markdown_override.startswith("# Brief: Local")
        assert not brief.is_repo_scanned

    def test_missing_model_maps_http_404(self, monkeypatch):
        def fake_http(url, payload=None, timeout=10.0):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

        monkeypatch.setattr(oe, "_http_json", fake_http)
        with pytest.raises(RuntimeError) as excinfo:
            oe.generate_local_brief(BriefRequest(task_description="Implement something useful", local_model="missing:1b"))
        assert "ollama pull" in str(excinfo.value)

    def test_empty_response_is_rejected(self, monkeypatch):
        monkeypatch.setattr(oe, "_http_json", lambda *args, **kwargs: {"message": {"content": "  "}})
        with pytest.raises(RuntimeError):
            oe.generate_local_brief(BriefRequest(task_description="Implement something useful", local_model="tiny:1b"))


class TestGeneratorRouting:
    def test_local_engine_is_selected_explicitly(self, monkeypatch):
        monkeypatch.setattr("core.generator.is_local_llm_available", lambda *args: (True, "ready"))
        seen = {}

        def fake_generate(request):
            seen["request"] = request
            return brief_from_markdown(
                request,
                "# Local Brief\n\n## 1. Summary\nBody",
                GenerationMode.LOCAL_OPEN_WEIGHT,
                "summary",
            )

        monkeypatch.setattr("core.generator.generate_local_brief", fake_generate)
        request = BriefRequest(
            task_description="Add pagination to the products API",
            engine=GenerationMode.LOCAL_OPEN_WEIGHT,
            local_model="qwen2.5:7b-instruct",
        )
        brief, warnings = generate_brief(request)

        assert brief.mode_used == GenerationMode.LOCAL_OPEN_WEIGHT
        assert warnings == []
        assert seen["request"].local_model == "qwen2.5:7b-instruct"

    def test_unready_local_engine_raises_runtime_error(self, monkeypatch):
        monkeypatch.setattr("core.generator.is_local_llm_available", lambda *args: (False, "server down"))
        with pytest.raises(RuntimeError) as excinfo:
            generate_brief(
                BriefRequest(
                    task_description="Add pagination to the products API",
                    engine=GenerationMode.LOCAL_OPEN_WEIGHT,
                    local_model="qwen2.5:7b-instruct",
                )
            )
        assert "server down" in str(excinfo.value)

    def test_default_request_still_uses_rule_based_engine(self):
        request = BriefRequest(
            task_description="Add pagination to the Spring Boot products API",
            project_type=ProjectType.JAVA_SPRING,
            task_scope=TaskScope.FEATURE,
        )
        assert request.resolve_engine() == GenerationMode.RULE_BASED
        brief, _ = generate_brief(request)
        assert brief.mode_used == GenerationMode.RULE_BASED