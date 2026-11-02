import json
from types import SimpleNamespace

import pytest

from src import config, llm


def test_resolve_key_from_env_and_aliases(monkeypatch):
    assert not config.resolve_key().available
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSyExampleKey1234567890")
    info = config.resolve_key()
    assert info.available and info.source == ".env / GOOGLE_API_KEY"
    monkeypatch.setenv("GEMINI_API_KEY", '"AIzaSyOther000000000000001"')  # quotes are stripped, earlier alias wins
    assert config.resolve_key().key == "AIzaSyOther000000000000001"


def test_placeholder_is_not_a_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_api_key_here")
    info = config.resolve_key()
    assert not info.available and info.placeholder_found


def test_session_override_wins_and_mask(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyFromEnv00000000000")
    info = config.resolve_key("AIzaSyOverride0000000000")
    assert info.source == "session override"
    assert "AIzaSyOverride0000000000" not in info.masked and info.masked.startswith("AIza")


def test_load_env_reads_dotenv_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("﻿GEMINI_API_KEY=AIzaSyFromFile0000000000\n", encoding="utf-8")
    monkeypatch.setattr(config, "ENV_PATH", env)
    monkeypatch.chdir(tmp_path)
    assert config.load_env()
    assert config.resolve_key().key == "AIzaSyFromFile0000000000"
    monkeypatch.delenv("GEMINI_API_KEY")


# ----------------------------------------------------------------- fake Gemini client
class FakeModels:
    def __init__(self, fail_models=(), error="boom", chunks=("Hello ", "world")):
        self.fail_models, self.error, self.chunks, self.calls = set(fail_models), error, chunks, []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        if model in self.fail_models:
            raise RuntimeError(self.error)
        return SimpleNamespace(text="".join(self.chunks))

    def generate_content_stream(self, model, contents, config):
        self.calls.append(model)
        if model in self.fail_models:
            raise RuntimeError(self.error)
        return iter(SimpleNamespace(text=c) for c in self.chunks)


def fake_client(models):
    return lambda api_key: SimpleNamespace(models=models)


MSG = [{"role": "user", "content": "hi"}]


def test_generate_falls_back_to_next_model(monkeypatch):
    models = FakeModels(fail_models={"gemini-3.5-flash"})
    monkeypatch.setattr(llm, "_client", fake_client(models))
    assert llm.generate("sys", MSG, "k") == "Hello world"
    assert models.calls == ["gemini-3.5-flash", "gemini-2.5-flash"] and llm.LAST_MODEL == "gemini-2.5-flash"


def test_auth_error_stops_without_trying_other_models(monkeypatch):
    models = FakeModels(fail_models={"gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"}, error="403 PERMISSION_DENIED api key")
    monkeypatch.setattr(llm, "_client", fake_client(models))
    with pytest.raises(llm.LLMError, match="API key was rejected"):
        llm.generate("sys", MSG, "k")
    assert len(models.calls) == 1


def test_stream_yields_chunks_and_falls_back(monkeypatch):
    models = FakeModels(fail_models={"gemini-3.5-flash"}, chunks=("a", "b", "c"))
    monkeypatch.setattr(llm, "_client", fake_client(models))
    assert "".join(llm.stream("sys", MSG, "k")) == "abc"
    assert models.calls[-1] == "gemini-2.5-flash"


def test_model_choice_is_respected(monkeypatch):
    models = FakeModels()
    monkeypatch.setattr(llm, "_client", fake_client(models))
    llm.generate("sys", MSG, "k", model="gemini-2.5-pro")
    assert models.calls == ["gemini-2.5-pro"]


def test_friendly_errors():
    assert "rate limit" in llm.friendly_error(RuntimeError("429 RESOURCE_EXHAUSTED")).lower()
    assert "not available" in llm.friendly_error(RuntimeError("404 model not found"))


def test_parse_json_handles_fences():
    assert llm.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
