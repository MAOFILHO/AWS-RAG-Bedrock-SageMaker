"""Web service: lists the Sources and answers a question with the chosen Source's Pipeline.

The PDF opens at start-up; the web and SQL Sources open on first use and stay open.

Run it with `uv run uvicorn rag_course.service:create_app --factory --port 8000`.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from rag_course import pdf, sql, web
from rag_course.core import Models, Settings, bedrock_models


SOURCES = [
    {"id": "web", "name": "Web", "description": "Two IBM pages on cloud computing and data science."},
    {"id": "pdf", "name": "PDF", "description": "The course PDF."},
    {"id": "sql", "name": "SQL", "description": "The Chinook music store database, read-only."},
]


class Question(BaseModel):
    question: str
    source: str = "pdf"


def create_app(
    models: Models | None = None,
    fetch: Callable[[str], str] = web.fetch_page,
    db: Path = sql.DEFAULT_DB,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.models = models or bedrock_models(Settings.from_env())
        m = app.state.models
        pdf_store = pdf.store(m)
        app.state.answerers = {"pdf": lambda question: pdf.answer(question, pdf_store, m)}
        yield

    app = FastAPI(lifespan=lifespan)

    def answerer(source: str) -> Callable[[str], str]:
        if source not in app.state.answerers:
            m = app.state.models
            if source == "web":
                web_store = web.store(m, fetch)
                app.state.answerers[source] = lambda question: web.answer(question, web_store, m)
            else:
                app.state.answerers[source] = lambda question: sql.ask(question, m, db)
        return app.state.answerers[source]

    @app.get("/sources")
    def sources():
        return SOURCES

    @app.post("/ask")
    def ask(body: Question):
        if not body.question.strip():
            return JSONResponse({"error": "question must not be empty"}, status_code=400)
        if body.source not in {item["id"] for item in SOURCES}:
            return JSONResponse({"error": f"unknown source: {body.source}"}, status_code=400)
        return {"answer": answerer(body.source)(body.question)}

    return app

