"""Optional AI-powered implementation brief generation using Google Gemini API.

Transparently integrates with Gemini using the official google-genai SDK when
a GEMINI_API_KEY is configured, while strictly redacting all keys from logs, UI,
and error messages.
"""

import os
from typing import Optional, Tuple

from core.ai_common import (
    SYSTEM_INSTRUCTION,
    brief_from_markdown,
    build_repo_notice,
    build_user_prompt,
    extract_title,
    sanitize_string,
)
from core.models import (
    BriefRequest,
    GenerationMode,
    ImplementationBrief,
)


def _sanitize_string(text: str, key_to_redact: Optional[str] = None) -> str:
    """Removes any API key patterns or provided key from strings."""
    return sanitize_string(text, key_to_redact)


def is_ai_available(custom_key: Optional[str] = None) -> Tuple[bool, str]:
    """Checks whether an API key is configured either via parameter or environment."""
    if custom_key is not None:
        key = custom_key.strip()
    else:
        key = os.getenv("GEMINI_API_KEY", "").strip()

    if not key:
        return False, "No Gemini API key found. Provide one in the sidebar or set the GEMINI_API_KEY environment variable."
    return True, "API Key detected (in-memory / environment)."


def generate_ai_brief(request: BriefRequest) -> ImplementationBrief:
    """Invokes Google Gemini to generate a tailored, professional implementation brief.

    Raises:
        ValueError: If API key is missing.
        RuntimeError: If the Gemini API invocation fails.
    """
    if request.gemini_api_key is not None:
        key = request.gemini_api_key.strip()
    else:
        key = os.getenv("GEMINI_API_KEY", "").strip()

    if not key:
        raise ValueError("Missing Gemini API Key. Please provide a key in the settings or set GEMINI_API_KEY.")

    try:
        from google import genai
        from google.genai import types
        from google.genai.errors import APIError, ClientError
    except ImportError as e:
        raise RuntimeError(f"The 'google-genai' package is not installed: {e}")

    repo_notice = build_repo_notice(request)
    user_prompt = build_user_prompt(request, "AI-Powered Engine (Gemini API)")

    client = genai.Client(api_key=key)

    # Try primary model gemini-2.5-flash with fallback to gemini-2.0-flash
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]
    last_error: Optional[Exception] = None
    raw_text: str = ""

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.3,
                ),
            )
            raw_text = response.text or ""
            if raw_text.strip():
                break
        except Exception as exc:
            last_error = exc
            # If it's an auth error (bad key), don't retry with another model
            err_str = str(exc)
            if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                break
            continue

    if not raw_text.strip():
        if last_error:
            sanitized_err = _sanitize_string(str(last_error), key)
            if "API_KEY_INVALID" in sanitized_err or "API key not valid" in sanitized_err:
                raise RuntimeError("Gemini API invocation failed: The provided Gemini API key is invalid. Please check your key at https://aistudio.google.com/.")
            if "RESOURCE_EXHAUSTED" in sanitized_err or "429" in sanitized_err:
                raise RuntimeError("Gemini API invocation failed: Rate limit or quota exceeded. Please wait a moment before trying again or switch to the Rule-Based engine.")
            raise RuntimeError(f"Gemini API invocation failed: {sanitized_err}")
        raise RuntimeError("Gemini returned an empty response. Please adjust your prompt and try again.")

    return brief_from_markdown(
        request=request,
        raw_text=raw_text,
        mode=GenerationMode.AI_POWERED,
        summary="AI-generated comprehensive brief generated via Gemini API.",
        repository_status=repo_notice,
    )


def re_title(markdown: str) -> Optional[str]:
    """Helper to extract the H1 title from markdown."""
    return extract_title(markdown)