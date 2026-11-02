"""App configuration: .env loading and Gemini API-key discovery.

The key is read from the project's `.env` file (or the operating-system environment).
It is never written to disk, logged or shown in full anywhere in the UI.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

APP_NAME = "FinPilot AI"
APP_TAGLINE = "AI-powered personal finance copilot"

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"

# Any of these variable names is accepted for the Gemini key.
KEY_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY", "GEMINI_KEY")

DEFAULT_MODEL = "gemini-3.5-flash"
MODEL_CHOICES = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"]


def load_env() -> bool:
    """Load `.env` from the project folder (and the current folder). Safe to call repeatedly."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv not installed: fall back to real environment variables
        return False
    loaded = False
    for path in dict.fromkeys([ENV_PATH, Path.cwd() / ".env"]):
        if path.is_file():
            # utf-8-sig tolerates the BOM that some Windows editors add
            loaded = bool(load_dotenv(path, override=True, encoding="utf-8-sig")) or loaded
    return loaded


def is_placeholder(value: str) -> bool:
    v = value.strip().lower()
    return (
        not v
        or v.startswith(("your", "paste", "<", "changeme", "xxx"))
        or "api_key_here" in v
        or "your_gemini" in v
    )


def _clean(value: Optional[str]) -> str:
    return (value or "").strip().strip('"').strip("'").strip()


def mask(key: str) -> str:
    key = key.strip()
    return f"{key[:4]}…{key[-4:]}" if len(key) > 10 else "••••"


@dataclass(frozen=True)
class KeyInfo:
    key: Optional[str]
    source: Optional[str]  # ".env / GEMINI_API_KEY", "session override" or None
    placeholder_found: bool = False

    @property
    def available(self) -> bool:
        return bool(self.key)

    @property
    def masked(self) -> str:
        return mask(self.key) if self.key else ""


def resolve_key(session_override: Optional[str] = None) -> KeyInfo:
    """Find the Gemini key: optional UI override first, then .env / environment variables."""
    override = _clean(session_override)
    if override and not is_placeholder(override):
        return KeyInfo(override, "session override")
    placeholder = False
    for name in KEY_VARS:
        value = _clean(os.getenv(name))
        if not value:
            continue
        if is_placeholder(value):
            placeholder = True
            continue
        return KeyInfo(value, f".env / {name}")
    return KeyInfo(None, None, placeholder_found=placeholder)


def default_model() -> str:
    return _clean(os.getenv("GEMINI_MODEL")) or DEFAULT_MODEL
