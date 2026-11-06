"""Top-level entry point that `rag ask` uses."""

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
