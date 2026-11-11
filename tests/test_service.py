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


def _sources_app():
    from fakes import saved_page

    fetched = []

    def fetch(url):
        fetched.append(url)
        return saved_page(url)

    return fetched, fetch


def test_service_lists_the_three_sources():
    with TestClient(create_app(fake_models())) as client:
        listed = client.get("/sources").json()
    assert [s["id"] for s in listed] == ["web", "pdf", "sql"]
    assert all(s["name"] and s["description"] for s in listed)


def test_service_answers_each_source_with_its_pipeline():
    from fakes import fake_sql_models

    fetched, fetch = _sources_app()
    models = fake_sql_models({"How many customers are there?": "SELECT COUNT(CustomerId) FROM Customer"})
    with TestClient(create_app(models, fetch=fetch)) as client:
        sql_reply = client.post("/ask", json={"question": "How many customers are there?", "source": "sql"})
    assert sql_reply.json() == {"answer": "Rows: [(59,)]"}
    with TestClient(create_app(fake_models(), fetch=fetch)) as client:
        web_reply = client.post("/ask", json={"question": "What is cloud computing?", "source": "web"})
        pdf_reply = client.post("/ask", json={"question": QUESTION, "source": "pdf"})
    assert web_reply.json() == {"answer": rag_course.ask("web", "What is cloud computing?", models=fake_models(), fetch=fetch)}
    assert pdf_reply.json() == {"answer": rag_course.ask("pdf", QUESTION, models=fake_models())}


def test_service_loads_the_web_pages_once():
    fetched, fetch = _sources_app()
    with TestClient(create_app(fake_models(), fetch=fetch)) as client:
        assert fetched == []
        client.post("/ask", json={"question": "What is cloud computing?", "source": "web"})
        loaded = len(fetched)
        client.post("/ask", json={"question": "What is data science?", "source": "web"})
    assert loaded > 0 and len(fetched) == loaded


def test_service_refuses_a_question_that_asks_to_change_data():
    from fakes import fake_sql_models
    from rag_course import sql

    question = "How many customers are there?; DROP TABLE Customer;"
    with TestClient(create_app(fake_sql_models({}))) as client:
        reply = client.post("/ask", json={"question": question, "source": "sql"})
    assert reply.json() == {"answer": sql.REFUSAL}


def test_service_rejects_an_unknown_source():
    with TestClient(create_app(fake_models())) as client:
        reply = client.post("/ask", json={"question": "Hi?", "source": "csv"})
    assert reply.status_code == 400


KIWIS = "Kiwis are flightless birds from New Zealand."


def _upload(client, name="kiwis.pdf", content=None):
    from fakes import text_pdf

    return client.put("/pdf", params={"name": name}, content=text_pdf([KIWIS]) if content is None else content)


def test_service_names_the_default_pdf_as_active():
    with TestClient(create_app(fake_models())) as client:
        assert client.get("/pdf").json() == {"name": "invoice.pdf", "uploaded": False}


def test_service_answers_from_an_uploaded_pdf_then_switches_back():
    with TestClient(create_app(fake_models())) as client:
        reply = _upload(client)
        assert reply.status_code == 200
        assert reply.json() == {"name": "kiwis.pdf", "uploaded": True}
        assert client.get("/pdf").json() == {"name": "kiwis.pdf", "uploaded": True}
        ask = {"question": "Which birds are flightless kiwis?", "source": "pdf"}
        assert client.post("/ask", json=ask).json() == {"answer": KIWIS}
        assert client.delete("/pdf").json() == {"name": "invoice.pdf", "uploaded": False}
        back = client.post("/ask", json={"question": QUESTION, "source": "pdf"}).json()
        assert back == {"answer": rag_course.ask("pdf", QUESTION, models=fake_models())}


def test_service_keeps_the_active_pdf_when_an_upload_is_not_a_pdf():
    with TestClient(create_app(fake_models())) as client:
        _upload(client)
        reply = _upload(client, "notes.pdf", b"this is not a pdf")
        assert reply.status_code == 400
        assert reply.json() == {"error": "That file is not a readable PDF."}
        assert client.get("/pdf").json() == {"name": "kiwis.pdf", "uploaded": True}
