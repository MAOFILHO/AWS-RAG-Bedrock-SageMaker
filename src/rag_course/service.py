"""Web service: opens the default PDF once and answers questions with the PDF Pipeline.

Run it with `uv run uvicorn rag_course.service:create_app --factory --port 8000`.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from rag_course import pdf
from rag_course.core import Models, Settings, bedrock_models


class Question(BaseModel):
    question: str


def create_app(models: Models | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.models = models or bedrock_models(Settings.from_env())
        app.state.source = pdf.store(app.state.models)
        yield

    app = FastAPI(lifespan=lifespan)

    @app.post("/ask")
    def ask(body: Question):
        if not body.question.strip():
            return JSONResponse({"error": "question must not be empty"}, status_code=400)
        return {"answer": pdf.answer(body.question, app.state.source, app.state.models)}

    return app
