import pytest


@pytest.fixture(autouse=True)
def no_real_keys(monkeypatch):
    """Tests must never pick up a developer's real key from the environment."""
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY", "GEMINI_KEY", "GEMINI_MODEL"):
        monkeypatch.delenv(name, raising=False)
