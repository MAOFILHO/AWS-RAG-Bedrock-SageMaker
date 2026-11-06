"""Top-level entry point that `rag ask` uses."""

from typing import Callable

from rag_course import web
from rag_course.core import Models, Settings, bedrock_models


def ask(
    source: str,
    question: str,
    *,
    models: Models | None = None,
    fetch: Callable[[str], str] | None = None,
) -> str:
    models = models or bedrock_models(Settings.from_env())
    if source == "web":
        return web.ask(question, models, fetch or web.fetch_page)
    raise ValueError(f"unknown source: {source}")
