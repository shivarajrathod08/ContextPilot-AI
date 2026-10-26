"""Optional open-weight language model engine backed by a local Ollama runtime.

Calls Ollama's HTTP API directly, so the application gains a working open-weight
model with no API key and no additional Python package. Every failure is mapped
to an actionable message, letting the UI fall back to the deterministic engine
instead of crashing.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Optional, Tuple

from core.ai_common import (
    SYSTEM_INSTRUCTION,
    brief_from_markdown,
    build_repo_notice,
    build_user_prompt,
    sanitize_string,
)
from core.models import BriefRequest, GenerationMode, ImplementationBrief

DEFAULT_BASE_URL = "http://localhost:11434"

_PROBE_TIMEOUT_SECONDS = 2.0
_GENERATION_TIMEOUT_SECONDS = 180.0


def _normalize_base_url(url: str) -> str:
    """Validates and trims a user-supplied Ollama base URL."""
    cleaned = (url or "").strip().rstrip("/")
    if not cleaned:
        return DEFAULT_BASE_URL
    if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
        raise ValueError("The Ollama base URL must start with http:// or https:// (for example http://localhost:11434).")
    return cleaned


def get_local_config(
    custom_base_url: Optional[str] = None,
    custom_model: Optional[str] = None,
) -> Tuple[str, str]:
    """Resolves the Ollama base URL and model from arguments, then environment.

    No endpoint or model is assumed beyond the standard local Ollama default.
    """
    base_url = custom_base_url if custom_base_url is not None else os.getenv("OLLAMA_BASE_URL", "")
    model = custom_model if custom_model is not None else os.getenv("OLLAMA_MODEL", "")

    normalized_base = _normalize_base_url(base_url)
    normalized_model = (model or "").strip()
    return normalized_base, normalized_model


def _http_json(url: str, payload: Optional[dict] = None, timeout: float = 10.0) -> dict:
    """Minimal JSON GET/POST helper built on the standard library."""
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _known_model_names(base_url: str) -> list:
    """Returns the model tags currently installed in the local Ollama runtime."""
    data = _http_json(f"{base_url}/api/tags", timeout=_PROBE_TIMEOUT_SECONDS)
    models = data.get("models", []) if isinstance(data, dict) else []
    names = []
    for entry in models:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("model")
        if name:
            names.append(name)
    return names


def _model_matches(requested: str, installed: list) -> bool:
    """Accepts an exact tag or an untagged alias such as ``qwen2.5``."""
    if requested in installed:
        return True
    return any(name.split(":")[0] == requested for name in installed)


def is_local_llm_available(
    custom_base_url: Optional[str] = None,
    custom_model: Optional[str] = None,
) -> Tuple[bool, str]:
    """Checks that Ollama is reachable and that the requested model is pulled."""
    try:
        base_url, model = get_local_config(custom_base_url, custom_model)
    except ValueError as exc:
        return False, str(exc)

    if not model:
        return False, "No open-weight model configured. Set OLLAMA_MODEL or enter a model name in the sidebar."

    try:
        installed = _known_model_names(base_url)
    except urllib.error.HTTPError as exc:
        return False, f"Ollama at {base_url} returned HTTP {exc.code}. Check that the server is healthy."
    except (urllib.error.URLError, TimeoutError, OSError):
        return False, (
            f"Could not reach Ollama at {base_url}. Start it with `ollama serve` "
            "or set OLLAMA_BASE_URL to the correct address."
        )
    except ValueError:
        return False, f"Ollama at {base_url} returned an unreadable response."

    if not _model_matches(model, installed):
        return False, f"Model '{model}' is not available in Ollama. Run `ollama pull {model}` and try again."

    return True, f"Ollama reachable at {base_url} with model '{model}'."


def generate_local_brief(request: BriefRequest) -> ImplementationBrief:
    """Generates an implementation brief with a local open-weight model.

    Raises:
        ValueError: If no model is configured or the base URL is invalid.
        RuntimeError: If Ollama is unreachable, the model is missing, or the
            response is empty/unreadable.
    """
    base_url, model = get_local_config(request.local_base_url, request.local_model)
    if not model:
        raise ValueError("No open-weight model configured. Set OLLAMA_MODEL or enter a model name in the sidebar.")

    repo_notice = build_repo_notice(request)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": build_user_prompt(request, GenerationMode.LOCAL_OPEN_WEIGHT.value)},
        ],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_ctx": 8192,
            "num_predict": 2048,
        },
    }

    try:
        response = _http_json(
            f"{base_url}/api/chat",
            payload=payload,
            timeout=_GENERATION_TIMEOUT_SECONDS,
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(
                f"Model '{model}' is not available in Ollama. Run `ollama pull {model}` and try again."
            )
        detail = sanitize_string(str(exc.reason or exc))
        raise RuntimeError(f"Ollama request failed with HTTP {exc.code}: {detail}")
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError(
            f"Could not reach Ollama at {base_url}. Start it with `ollama serve` "
            "or set OLLAMA_BASE_URL to the correct address."
        )
    except ValueError:
        raise RuntimeError("Ollama returned a response that could not be parsed as JSON.")

    message = response.get("message", {}) if isinstance(response, dict) else {}
    raw_text = (message.get("content") or "").strip()
    if not raw_text:
        raise RuntimeError("The open-weight model returned an empty response. Try another model or a more specific task.")

    return brief_from_markdown(
        request=request,
        raw_text=raw_text,
        mode=GenerationMode.LOCAL_OPEN_WEIGHT,
        summary="AI-generated comprehensive brief generated via a local open-weight model (Ollama).",
        repository_status=repo_notice,
    )