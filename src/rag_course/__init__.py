"""Top-level entry points that `rag ask` and `rag chat` use."""

from pathlib import Path
from typing import Callable

from langsmith import traceable

from rag_course import pdf as pdf_pipeline
from rag_course import sql, web
from rag_course.core import PDF_PROMPT, WEB_PROMPT, Models, Settings, VectorStore, answer_with_context, bedrock_models, tracing


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


def open_source(
    source: str,
    *,
    models: Models | None = None,
    fetch: Callable[[str], str] | None = None,
    pdf: Path | None = None,
    db: Path | None = None,
) -> Callable[[str], str]:
    """Load a Source once and return a function that answers questions with the same Pipeline as `ask`."""
    settings = Settings.from_env()
    models = models or bedrock_models(settings)
    if source == "web":
        chunks, prompt = web.chunks(fetch or web.fetch_page), WEB_PROMPT
    elif source == "pdf":
        chunks, prompt = pdf_pipeline.chunks(pdf or pdf_pipeline.DEFAULT_PDF), PDF_PROMPT
    elif source == "sql":
        return lambda question: _chat_answer(settings, lambda: sql.ask(question, models, db or sql.DEFAULT_DB))
    else:
        raise ValueError(f"unknown source: {source}")
    store = VectorStore(models.embed, chunks)
    return lambda question: _chat_answer(settings, lambda: answer_with_context(question, store, models, prompt)[0])


def _chat_answer(settings: Settings, answer: Callable[[], str]) -> str:
    with tracing(settings):
        return answer()
