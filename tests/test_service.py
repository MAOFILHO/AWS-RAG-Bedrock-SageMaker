import pytest
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
        assert client.get("/pdf").json() == {"name": "invoice.pdf", "uploaded": False}


def test_service_answers_from_an_uploaded_pdf_then_switches_back(tmp_path):
    with TestClient(_app(tmp_path)) as client:
        reply = _upload(client)
        assert reply.status_code == 200
        assert reply.json() == {"name": "kiwis.pdf", "uploaded": True}
        assert client.get("/pdf").json() == {"name": "kiwis.pdf", "uploaded": True}
        ask = {"question": "Which birds are flightless kiwis?", "source": "pdf"}
        assert client.post("/ask", json=ask).json() == {"answer": KIWIS}
        assert client.delete("/pdf").json() == {"name": "invoice.pdf", "uploaded": False}
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


def test_service_keeps_both_uploads_working_when_two_arrive_at_once(tmp_path, monkeypatch):
    import threading
    import time

    from rag_course import pdf
    from fakes import text_pdf

    uploads = tmp_path / "uploads"
    real_store, calls, counter = pdf.store, [], threading.Lock()

    def wait_for(count):
        end = time.monotonic() + 0.5
        while len(list(uploads.glob("*.pdf"))) != count and time.monotonic() < end:
            time.sleep(0.01)

    def store(models, path=pdf.DEFAULT_PDF):
        # Forces the bad order: the first upload waits for the second file to land, the second waits for the first sweep.
        if path.parent != uploads:
            return real_store(models, path)
        with counter:
            calls.append(path)
            first = len(calls) == 1
        wait_for(2) if first else wait_for(1)
        return real_store(models, path)

    monkeypatch.setattr(pdf, "store", store)
    with TestClient(_app(tmp_path), raise_server_exceptions=False) as client:
        codes = []
        threads = [
            threading.Thread(target=lambda n=n: codes.append(_upload(client, n, text_pdf([n])).status_code))
            for n in ("one.pdf", "two.pdf")
        ]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert codes == [200, 200]
        assert len(list(uploads.iterdir())) == 1


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


def test_service_ask_without_aws_access_names_aws_configure():
    from botocore.exceptions import NoCredentialsError

    class NoAccess:
        def embed(self, texts):
            raise NoCredentialsError()

        def answer(self, prompt):
            raise NoCredentialsError()

    from rag_course.core import Models

    with TestClient(create_app(Models(answer=NoAccess(), embed=NoAccess()))) as client:
        reply = client.post("/ask", json={"question": QUESTION, "source": "pdf"})
    assert reply.status_code == 503
    assert "aws configure" in reply.json()["error"]
    assert "NoCredentialsError" not in reply.text


def test_service_ask_with_a_missing_profile_names_it(monkeypatch):
    from botocore.exceptions import ProfileNotFound
    from rag_course.core import Models

    class Missing:
        def embed(self, texts):
            raise ProfileNotFound(profile="demo")

        answer = embed

    with TestClient(create_app(Models(answer=Missing(), embed=Missing()))) as client:
        reply = client.post("/ask", json={"question": QUESTION, "source": "pdf"})
    assert reply.status_code == 503
    assert "'demo'" in reply.json()["error"]


def _no_profile(monkeypatch):
    # The real boto3 path: a profile that does not exist fails in `boto3.client`, before any model call.
    monkeypatch.setenv("AWS_PROFILE", "nope-demo")
    monkeypatch.setenv("AWS_CONFIG_FILE", "/dev/null")
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", "/dev/null")


def test_service_starts_and_names_a_missing_profile_when_boto3_cannot_find_it(monkeypatch):
    _no_profile(monkeypatch)
    for source in ("pdf", "web", "sql"):
        with TestClient(create_app()) as client:
            reply = client.post("/ask", json={"question": QUESTION, "source": source})
        assert reply.status_code == 503
        assert "'nope-demo'" in reply.json()["error"]


def test_service_opens_the_pdf_on_the_next_question_once_access_works():
    from botocore.exceptions import NoCredentialsError
    from rag_course.core import Models

    good = fake_models()
    state = {"down": True}

    def flaky(call):
        def run(*args):
            if state["down"]:
                raise NoCredentialsError()
            return call(*args)

        return run

    models = Models(answer=good.answer, embed=type("E", (), {"embed": staticmethod(flaky(good.embed.embed))})())
    with TestClient(create_app(models)) as client:
        assert client.post("/ask", json={"question": QUESTION}).status_code == 503
        state["down"] = False
        reply = client.post("/ask", json={"question": QUESTION})
    assert reply.status_code == 200


def test_service_still_fails_on_an_error_that_is_not_aws_access():
    from rag_course.core import Models

    class Broken:
        def embed(self, texts):
            raise RuntimeError("boom")

        def answer(self, prompt):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        with TestClient(create_app(Models(answer=Broken(), embed=Broken()))):
            pass

    good = fake_models()
    models = Models(answer=Broken(), embed=good.embed)
    with TestClient(create_app(models), raise_server_exceptions=False) as client:
        reply = client.post("/ask", json={"question": QUESTION})
    assert reply.status_code == 500


def test_service_refuses_a_pdf_over_10_mb_and_takes_one_just_under(tmp_path):
    from fakes import text_pdf

    limit = 10 * 1024 * 1024
    with TestClient(_app(tmp_path)) as client:
        reply = _upload(client, "big.pdf", b"%PDF" + b" " * (limit + 1 - 4))
        assert reply.status_code == 413
        assert reply.json() == {"error": "That PDF is over the 10 MB limit."}
        assert client.get("/pdf").json() == {"name": "invoice.pdf", "uploaded": False}
        assert not list((tmp_path / "uploads").glob("*.pdf"))
        ok = _upload(client, "ok.pdf", text_pdf([KIWIS]) + b" " * (limit - len(text_pdf([KIWIS]))))
        assert ok.status_code == 200
