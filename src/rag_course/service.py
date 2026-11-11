"""Web service: lists the Sources and answers a question with the chosen Source's Pipeline.

The PDF opens at start-up; the web and SQL Sources open on first use and stay open.
The PDF Source answers from the active PDF: the default one, or the last one uploaded.

Run it with `uv run uvicorn rag_course.service:create_app --factory --port 8000`.
"""

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Callable

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from rag_course import pdf, sql, web
from rag_course.core import Models, Settings, SourceError, bedrock_models


DEFAULT_UPLOADS = Path(__file__).resolve().parents[2] / "uploads"

SOURCES = [
    {"id": "web", "name": "Web", "description": "Two IBM pages on cloud computing and data science."},
    {"id": "pdf", "name": "PDF", "description": "The K21 course PDF."},
    {"id": "sql", "name": "SQL", "description": "The Chinook music store database, read-only."},
]


class Question(BaseModel):
    question: str
    source: str = "pdf"


def create_app(
    models: Models | None = None,
    fetch: Callable[[str], str] = web.fetch_page,
    db: Path = sql.DEFAULT_DB,
    uploads: Path = DEFAULT_UPLOADS,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.models = models or bedrock_models(Settings.from_env())
        m = app.state.models
        pdf_store = pdf.store(m)
        app.state.default_pdf = lambda question: pdf.answer(question, pdf_store, m)
        app.state.answerers = {"pdf": app.state.default_pdf}
        app.state.pdf_name = pdf.DEFAULT_PDF.name
        app.state.pdf_file = None
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

    def active_pdf():
        return {"name": app.state.pdf_name, "uploaded": app.state.answerers["pdf"] is not app.state.default_pdf}

    @app.get("/pdf")
    def get_pdf():
        return active_pdf()

    def forget_upload():
        if app.state.pdf_file:
            app.state.pdf_file.unlink(missing_ok=True)
        app.state.pdf_file = None

    @app.put("/pdf")
    def put_pdf(name: str, content: Annotated[bytes, Body(media_type="application/pdf")]):
        m = app.state.models
        # The file is saved under a name we make up. The name the user sent is only shown back.
        uploads.mkdir(parents=True, exist_ok=True)
        path = uploads / f"{uuid.uuid4().hex}.pdf"
        path.write_bytes(content)
        try:
            store = pdf.store(m, path)
        except pdf.NoTextError:
            path.unlink()
            return JSONResponse({"error": "That PDF has no text to read. A scan will not work."}, status_code=400)
        except SourceError:
            path.unlink()
            return JSONResponse({"error": "That file is not a readable PDF."}, status_code=400)
        forget_upload()
        app.state.pdf_file = path
        app.state.answerers["pdf"] = lambda question: pdf.answer(question, store, m)
        app.state.pdf_name = name.replace("\\", "/").rsplit("/", 1)[-1] or "upload.pdf"
        return active_pdf()

    @app.delete("/pdf")
    def reset_pdf():
        forget_upload()
        app.state.answerers["pdf"] = app.state.default_pdf
        app.state.pdf_name = pdf.DEFAULT_PDF.name
        return active_pdf()

    @app.post("/ask")
    def ask(body: Question):
        if not body.question.strip():
            return JSONResponse({"error": "question must not be empty"}, status_code=400)
        if body.source not in {item["id"] for item in SOURCES}:
            return JSONResponse({"error": f"unknown source: {body.source}"}, status_code=400)
        return {"answer": answerer(body.source)(body.question)}

    return app

