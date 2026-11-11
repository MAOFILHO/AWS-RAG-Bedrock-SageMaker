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


def _app(tmp_path):
    return create_app(fake_models(), uploads=tmp_path / "uploads")


def _upload(client, name="kiwis.pdf", content=None):
    from fakes import text_pdf

    return client.put("/pdf", params={"name": name}, content=text_pdf([KIWIS]) if content is None else content)


def test_service_names_the_default_pdf_as_active():
    with TestClient(create_app(fake_models())) as client:
        assert client.get("/pdf").json() == {"name": "k21.pdf", "uploaded": False}


def test_service_answers_from_an_uploaded_pdf_then_switches_back(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        reply = _upload(client)
        assert reply.status_code == 200
        assert reply.json() == {"name": "kiwis.pdf", "uploaded": True}
        assert client.get("/pdf").json() == {"name": "kiwis.pdf", "uploaded": True}
        ask = {"question": "Which birds are flightless kiwis?", "source": "pdf"}
        assert client.post("/ask", json=ask).json() == {"answer": KIWIS}
        assert client.delete("/pdf").json() == {"name": "k21.pdf", "uploaded": False}
        back = client.post("/ask", json={"question": QUESTION, "source": "pdf"}).json()
        assert back == {"answer": rag_course.ask("pdf", QUESTION, models=fake_models())}


def test_service_keeps_the_active_pdf_when_an_upload_is_not_a_pdf(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        _upload(client)
        reply = _upload(client, "notes.pdf", b"this is not a pdf")
        assert reply.status_code == 400
        assert reply.json() == {"error": "That file is not a readable PDF."}
        assert client.get("/pdf").json() == {"name": "kiwis.pdf", "uploaded": True}


def test_service_refuses_a_pdf_with_no_text(tmp_path):
    from fakes import text_pdf

    with TestClient(_app(tmp_path)) as client:
        _upload(client)
        reply = _upload(client, "scan.pdf", text_pdf([]))
        assert reply.status_code == 400
        assert reply.json() == {"error": "That PDF has no text to read. A scan will not work."}
        assert client.get("/pdf").json() == {"name": "kiwis.pdf", "uploaded": True}
    assert len(list((tmp_path / "uploads").iterdir())) == 1


def test_service_never_uses_the_file_name_as_a_path(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        reply = _upload(client, "../x.pdf")
        assert reply.json() == {"name": "x.pdf", "uploaded": True}
        _upload(client, "..\\..\\y.pdf")
        assert client.get("/pdf").json()["name"] == "y.pdf"
    assert not (tmp_path / "x.pdf").exists()
    assert [p.parent for p in tmp_path.rglob("*.pdf")] == [tmp_path / "uploads"]


def test_service_keeps_only_the_newest_uploaded_file(tmp_path):
    from fakes import text_pdf

    with TestClient(_app(tmp_path)) as client:
        _upload(client, "one.pdf")
        first = list((tmp_path / "uploads").iterdir())
        _upload(client, "two.pdf", text_pdf(["Owls hunt at night."]))
        second = list((tmp_path / "uploads").iterdir())
        assert len(first) == 1 and len(second) == 1 and first != second
        client.delete("/pdf")
    assert list((tmp_path / "uploads").iterdir()) == []


def test_service_deletes_an_upload_left_by_an_earlier_run(tmp_path):
    from fakes import text_pdf

    with TestClient(_app(tmp_path)) as client:
        _upload(client, "a.pdf")
    with TestClient(_app(tmp_path)) as client:
        _upload(client, "b.pdf", text_pdf(["Owls hunt at night."]))
        assert len(list((tmp_path / "uploads").iterdir())) == 1


def test_service_deletes_the_saved_file_when_the_embed_call_fails(tmp_path):
    from rag_course.core import Models
    from fakes import FakeAnswerModel, FakeEmbeddings

    class FlakyEmbeddings(FakeEmbeddings):
        broken = False

        def embed(self, texts):
            if self.broken:
                raise RuntimeError("bedrock is down")
            return super().embed(texts)

    embed = FlakyEmbeddings()
    app = create_app(Models(answer=FakeAnswerModel(), embed=embed), uploads=tmp_path / "uploads")
    with TestClient(app, raise_server_exceptions=False) as client:
        embed.broken = True
        assert _upload(client).status_code == 500
    assert list((tmp_path / "uploads").iterdir()) == []


def test_upload_folder_is_ignored_by_git():
    import subprocess
    from rag_course import service

    root = service.DEFAULT_UPLOADS.parent
    check = subprocess.run(["git", "check-ignore", "-q", f"{service.DEFAULT_UPLOADS.name}/x.pdf"], cwd=root)
    assert check.returncode == 0
