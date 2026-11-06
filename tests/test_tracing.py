"""Offline checks of optional LangSmith tracing: off unless LANGSMITH_API_KEY is set."""

from unittest.mock import MagicMock

import langsmith
import langsmith.utils
from fakes import fake_models, saved_page
from langsmith import run_trees
from langsmith.utils import tracing_is_enabled

import rag_course
from rag_course.core import Settings, tracing

KEY = "ls-secret-value-123"


class FakeClient:
    created = []

    def __init__(self, api_key):
        self.api_key = api_key
        FakeClient.created.append(self)


def setup_function():
    FakeClient.created.clear()


def test_without_a_key_no_tracing_client_is_created():
    settings = Settings.from_env({})
    with tracing(settings, FakeClient):
        assert not tracing_is_enabled()
    assert FakeClient.created == []


def test_blank_key_counts_as_no_key():
    settings = Settings.from_env({"LANGSMITH_API_KEY": ""})
    with tracing(settings, FakeClient):
        assert not tracing_is_enabled()
    assert FakeClient.created == []


def test_with_a_key_tracing_is_enabled_through_a_client_built_from_it():
    settings = Settings.from_env({"LANGSMITH_API_KEY": KEY})
    with tracing(settings, FakeClient):
        assert tracing_is_enabled()
    assert [c.api_key for c in FakeClient.created] == [KEY]


def test_the_key_never_shows_in_the_settings_text():
    settings = Settings.from_env({"LANGSMITH_API_KEY": KEY})
    assert KEY not in repr(settings)
    assert KEY not in str(settings)


def mock_client_factory(keys):
    def make(api_key=None, **_):
        keys.append(api_key)
        return MagicMock()

    return make


def test_ask_traces_through_a_client_built_from_the_env_key(monkeypatch):
    keys = []
    monkeypatch.setenv("LANGSMITH_API_KEY", KEY)
    monkeypatch.setattr(langsmith, "Client", mock_client_factory(keys))
    answer = rag_course.ask("web", "What is cloud computing?", models=fake_models(), fetch=saved_page)
    assert "cloud computing" in answer.lower()
    assert keys == [KEY]


def test_ask_builds_no_tracing_client_without_a_key(monkeypatch):
    keys = []
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setattr(langsmith, "Client", mock_client_factory(keys))
    rag_course.ask("web", "What is cloud computing?", models=fake_models(), fetch=saved_page)
    assert keys == []


def test_ask_builds_no_client_when_the_env_flag_is_on_but_there_is_no_key(monkeypatch):
    keys = []
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    langsmith.utils.get_env_var.cache_clear()
    monkeypatch.setattr(run_trees, "_CLIENT", None)
    monkeypatch.setattr(run_trees, "Client", mock_client_factory(keys))
    try:
        rag_course.ask("web", "What is cloud computing?", models=fake_models(), fetch=saved_page)
    finally:
        monkeypatch.undo()
        langsmith.utils.get_env_var.cache_clear()
    assert keys == []
