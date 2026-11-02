"""Thin wrapper around the Google Gemini API (google-genai SDK).

Features: model fallback, streaming, JSON mode and friendly error messages.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterator, List, Optional

from .config import KeyInfo, MODEL_CHOICES, default_model, resolve_key

# Model that answered the most recent successful call (shown in the UI)
LAST_MODEL: Optional[str] = None

_AUTH_HINTS = ("api key", "api_key", "401", "403", "permission_denied", "unauthenticated")


class LLMError(RuntimeError):
    """Raised when Gemini cannot produce an answer."""


def get_api_key(explicit: Optional[str] = None) -> Optional[str]:
    return resolve_key(explicit).key


def key_info(explicit: Optional[str] = None) -> KeyInfo:
    return resolve_key(explicit)


def friendly_error(exc: BaseException) -> str:
    """Translate SDK exceptions into a short message a user can act on."""
    text = str(exc)
    low = text.lower()
    if any(h in low for h in _AUTH_HINTS):
        return "The API key was rejected. Check GEMINI_API_KEY in your .env file."
    if "429" in text or "resource_exhausted" in low or "quota" in low:
        return "Gemini rate limit or quota reached. Please try again in a moment."
    if "404" in text or "not found" in low:
        return "The selected model is not available for this key. Pick another model in AI settings."
    if any(w in low for w in ("connect", "timeout", "timed out", "network", "resolve", "unreachable")):
        return "Network problem while reaching Gemini. Check your internet connection."
    return (text[:160] + "…") if len(text) > 160 else (text or "Unknown Gemini error.")


def model_chain(primary: Optional[str] = None) -> List[str]:
    """Primary model first, then the remaining known models as fallbacks."""
    first = primary or default_model()
    return [first] + [m for m in MODEL_CHOICES if m != first][:2]


def _client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def _build(system: str, messages: List[Dict[str, str]], max_tokens: int, temperature: float, json_mode: bool):
    try:
        from google.genai import types
    except ImportError as exc:  # pragma: no cover
        raise LLMError("The google-genai package is not installed (pip install google-genai).") from exc

    contents = [
        types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part(text=m["content"])])
        for m in messages
    ]
    kwargs: Dict[str, Any] = dict(system_instruction=system, max_output_tokens=max_tokens, temperature=temperature)
    if json_mode:
        kwargs["response_mime_type"] = "application/json"
    return contents, types.GenerateContentConfig(**kwargs)


def generate(
    system: str,
    messages: List[Dict[str, str]],
    api_key: str,
    *,
    model: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.4,
    json_mode: bool = False,
) -> str:
    """One-shot completion. Tries the chosen model first, then fallbacks."""
    global LAST_MODEL
    contents, config = _build(system, messages, max_tokens, temperature, json_mode)
    client = _client(api_key)
    last_error: Optional[BaseException] = None
    for name in model_chain(model):
        try:
            response = client.models.generate_content(model=name, contents=contents, config=config)
            text = (response.text or "").strip()
            if text:
                LAST_MODEL = name
                return text
            last_error = LLMError(f"{name}: empty response")
        except Exception as exc:  # network, quota, bad model name, bad key ...
            last_error = exc
            if any(h in str(exc).lower() for h in _AUTH_HINTS):
                break  # another model will not fix a bad key
    raise LLMError(friendly_error(last_error) if last_error else "Gemini request failed") from last_error


def stream(
    system: str,
    messages: List[Dict[str, str]],
    api_key: str,
    *,
    model: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.4,
) -> Iterator[str]:
    """Yield the reply in small text chunks. Falls back to another model if none started."""
    global LAST_MODEL
    contents, config = _build(system, messages, max_tokens, temperature, False)
    client = _client(api_key)
    last_error: Optional[BaseException] = None
    for name in model_chain(model):
        started = False
        try:
            for chunk in client.models.generate_content_stream(model=name, contents=contents, config=config):
                piece = getattr(chunk, "text", None)
                if piece:
                    started = True
                    LAST_MODEL = name
                    yield piece
            if started:
                return
            last_error = LLMError(f"{name}: empty response")
        except Exception as exc:
            if started:  # cannot switch models half-way through an answer
                raise LLMError(friendly_error(exc)) from exc
            last_error = exc
            if any(h in str(exc).lower() for h in _AUTH_HINTS):
                break
    raise LLMError(friendly_error(last_error) if last_error else "Gemini request failed") from last_error


def parse_json(text: str):
    """Parse JSON from a model reply, tolerating ```json fences."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    return json.loads(cleaned)
