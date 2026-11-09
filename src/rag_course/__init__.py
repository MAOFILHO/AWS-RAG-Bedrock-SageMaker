"""Top-level entry points that `rag ask` and `rag chat` use."""

from pathlib import Path
from typing import Callable

from langsmith import traceable

from rag_course import pdf as pdf_pipeline
from rag_course import sql, web
from rag_course.core import Models, Settings, bedrock_models, tracing


def ask(
    source: str,
    question: str,
    *,
    models: Models | None = None,
    fetch: Callable[[str], str] | None = None,
    pdf: Path | None = None,
    db: Path | None = None,
) -> str:
    settings = Settings.from_env()
    with tracing(settings):
        return _ask(source, question, models or bedrock_models(settings), fetch, pdf, db)


@traceable(
    name="rag ask",
    run_type="chain",
    process_inputs=lambda inputs: {"source": inputs["source"], "question": inputs["question"]},
)
def _ask(
    source: str,
    question: str,
    models: Models,
    fetch: Callable[[str], str] | None,
    pdf: Path | None,
    db: Path | None,
) -> str:
    if source == "web":
        return web.ask(question, models, fetch or web.fetch_page)
    if source == "pdf":
        return pdf_pipeline.ask(question, models, pdf or pdf_pipeline.DEFAULT_PDF)
    if source == "sql":
        return sql.ask(question, models, db or sql.DEFAULT_DB)
    raise ValueError(f"unknown source: {source}")


def open_source(source: str, *, pdf: Path | None = None, db: Path | None = None) -> Callable[[str], str]:
    """Load a Source once and return a function that answers questions with the same Pipeline as `ask`."""
    settings = Settings.from_env()
    models = bedrock_models(settings)
    if source == "web":
        store = web.store(models, web.fetch_page)
        answer = lambda question: web.answer(question, store, models)  # noqa: E731
    elif source == "pdf":
        store = pdf_pipeline.store(models, pdf or pdf_pipeline.DEFAULT_PDF)
        answer = lambda question: pdf_pipeline.answer(question, store, models)  # noqa: E731
    elif source == "sql":
        answer = lambda question: sql.ask(question, models, db or sql.DEFAULT_DB)  # noqa: E731
    else:
        raise ValueError(f"unknown source: {source}")
    return lambda question: _chat(settings, source, question, answer)


def _chat(settings: Settings, source: str, question: str, answer: Callable[[str], str]) -> str:
    with tracing(settings):
        return _chat_run(source, question, answer)


@traceable(
    name="rag chat",
    run_type="chain",
    process_inputs=lambda inputs: {"source": inputs["source"], "question": inputs["question"]},
)
def _chat_run(source: str, question: str, answer: Callable[[str], str]) -> str:
    return answer(question)
