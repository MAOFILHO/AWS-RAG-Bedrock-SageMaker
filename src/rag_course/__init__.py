"""Top-level entry point that `rag ask` uses."""

from typing import Callable

from rag_course import web
from langsmith import traceable

from rag_course.core import Models, Settings, bedrock_models, tracing


def ask(
    source: str,
    question: str,
    *,
    models: Models | None = None,
    fetch: Callable[[str], str] | None = None,
) -> str:
    settings = Settings.from_env()
    with tracing(settings):
        return _ask(source, question, models or bedrock_models(settings), fetch)


@traceable(
    name="rag ask",
    run_type="chain",
    process_inputs=lambda inputs: {"source": inputs["source"], "question": inputs["question"]},
)
def _ask(source: str, question: str, models: Models, fetch: Callable[[str], str] | None) -> str:
    if source == "web":
        return web.ask(question, models, fetch or web.fetch_page)
    raise ValueError(f"unknown source: {source}")
