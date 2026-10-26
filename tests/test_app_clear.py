"""Regression tests for the Clear button and workspace session state.

These drive the real Streamlit script through `AppTest`, so they cover widget
state, callbacks, preset re-application, and generated-result cleanup together.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")
TASK = "Add pagination to the Spring Boot products API"


def _boot() -> AppTest:
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    assert not app.exception, app.exception
    return app


def _button(app: AppTest, label: str):
    return next(button for button in app.button if label in button.label)


def _generate(app: AppTest, task: str = TASK) -> AppTest:
    app.text_area[0].set_value(task).run()
    _button(app, "Generate").click().run()
    assert not app.exception, app.exception
    return app


def _clear(app: AppTest) -> AppTest:
    _button(app, "Clear").click().run()
    assert not app.exception, app.exception
    return app


class TestClearAfterGeneration:
    def test_clear_resets_input_and_generated_results(self):
        app = _generate(_boot())
        assert app.metric[0].value == "Deterministic"
        assert "last_brief" in app.session_state

        app = _clear(app)

        assert app.text_area[0].value == ""
        assert "last_brief" not in app.session_state
        assert "last_warnings" not in app.session_state
        assert "generation_success" not in app.session_state
        assert len(app.metric) == 0
        assert len(app.checkbox) == 0
        assert len(app.error) == 0

    def test_clear_resets_acceptance_and_qa_checklist_state(self):
        app = _generate(_boot())
        assert any(key.startswith("ac_check_") for key in app.session_state)
        assert any(key.startswith("test_") for key in app.session_state)

        next(cb for cb in app.checkbox if cb.key.startswith("ac_check_")).set_value(True).run()
        next(cb for cb in app.checkbox if cb.key.startswith("test_")).set_value(True).run()
        assert any(cb.value for cb in app.checkbox)

        app = _clear(app)

        assert not any(
            key.startswith(("ac_check_", "test_", "step_")) for key in app.session_state
        )
        assert not any(cb.value for cb in app.checkbox)
        assert len(app.checkbox) == 0

    def test_generation_still_works_after_clear(self):
        app = _clear(_generate(_boot(), TASK))

        app = _generate(app, "Add Redis rate limiting to the FastAPI login endpoint")

        assert not app.error
        assert app.metric[0].value == "Deterministic"
        assert "last_brief" in app.session_state
        assert len(app.checkbox) > 0


class TestClearAndInputState:
    def test_clear_is_not_overwritten_by_selected_preset(self):
        app = _boot()
        preset = next(select for select in app.sidebar.selectbox if select.label == "Load Example Task")
        preset.select("Spring Boot: REST API Pagination for Products").run()
        assert "pagination" in app.text_area[0].value.lower()

        app = _clear(app)

        assert app.text_area[0].value == ""
        # A later rerun must not resurrect the preset text.
        app.run()
        assert app.text_area[0].value == ""

    def test_typed_task_persists_across_reruns(self):
        app = _boot()
        app.text_area[0].set_value("Implement an idempotent payment webhook consumer").run()
        app.run()

        assert app.text_area[0].value == "Implement an idempotent payment webhook consumer"

    def test_clear_after_local_engine_failure_clears_error_state(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        app = _boot()
        app.sidebar.radio[0].set_value("Open-Weight Local Model (Ollama)").run()

        app = _generate(app, "Add Redis rate limiting to the FastAPI login endpoint")
        assert app.error
        assert "generation_success" in app.session_state

        app = _clear(app)

        assert app.text_area[0].value == ""
        assert len(app.error) == 0
        assert "generation_success" not in app.session_state


class TestEngineSelectionIntact:
    def test_all_engines_remain_selectable(self):
        app = _boot()
        options = app.sidebar.radio[0].options
        assert any("Rule-Based" in option for option in options)
        assert any("Open-Weight" in option for option in options)
        assert any("Gemini" in option for option in options)

    def test_gemini_mode_still_prompts_for_key(self):
        app = _boot()
        app.sidebar.radio[0].set_value("AI-Powered Engine (Gemini API)").run()

        assert any(field.label == "Gemini API Key" for field in app.sidebar.text_input)

    def test_ollama_mode_still_prompts_for_model_and_url(self):
        app = _boot()
        app.sidebar.radio[0].set_value("Open-Weight Local Model (Ollama)").run()

        labels = [field.label for field in app.sidebar.text_input]
        assert "Open-Weight Model" in labels
        assert "Ollama Base URL" in labels