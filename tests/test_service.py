from fastapi.testclient import TestClient

import rag_course
from rag_course.service import create_app
from fakes import fake_models

QUESTION = "What are SDKs and APIs?"


def test_service_answers_like_rag_ask():
    with TestClient(create_app(fake_models())) as client:
        reply = client.post("/ask", json={"question": QUESTION})
    assert reply.status_code == 200
    assert reply.json() == {"answer": rag_course.ask("pdf", QUESTION, models=fake_models())}


def test_service_opens_the_pdf_once(monkeypatch):
    from rag_course import pdf

    opened = []
    real = pdf.store
    monkeypatch.setattr(pdf, "store", lambda *args: opened.append(1) or real(*args))
    with TestClient(create_app(fake_models())) as client:
        client.post("/ask", json={"question": QUESTION})
        client.post("/ask", json={"question": "What is a vector database?"})
    assert opened == [1]


def test_service_rejects_an_empty_question():
    with TestClient(create_app(fake_models())) as client:
        reply = client.post("/ask", json={"question": "  "})
    assert reply.status_code == 400
    assert reply.json() == {"error": "question must not be empty"}
