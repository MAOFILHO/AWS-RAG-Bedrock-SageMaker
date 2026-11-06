"""Top-level entry point that `rag ask` uses."""

from pathlib import Path
from typing import Callable

from rag_course import sql, web
from rag_course.core import Models, Settings, bedrock_models


def ask(
    source: str,
    question: str,
    *,
    models: Models | None = None,
    fetch: Callable[[str], str] | None = None,
    db: Path | None = None,
) -> str:
    models = models or bedrock_models(Settings.from_env())
    if source == "web":
        return web.ask(question, models, fetch or web.fetch_page)
    if source == "sql":
        return sql.ask(question, models, db or sql.DEFAULT_DB)
    raise ValueError(f"unknown source: {source}")
