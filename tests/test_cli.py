from typer.testing import CliRunner

from rag_course.cli import app

runner = CliRunner()


def test_help_lists_ask_and_eval():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ask" in result.output
    assert "eval" in result.output


def _stub_ask(monkeypatch, calls):
    def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return "answer"

    monkeypatch.setattr("rag_course.ask", fake)


def test_ask_rejects_empty_question(monkeypatch):
    calls = []
    _stub_ask(monkeypatch, calls)
    result = runner.invoke(app, ["ask", "", "--source", "web"])
    assert result.exit_code == 2
    assert "Error: question must not be empty" in result.stderr
    assert calls == []


def test_ask_rejects_whitespace_question(monkeypatch):
    calls = []
    _stub_ask(monkeypatch, calls)
    result = runner.invoke(app, ["ask", " \t ", "--source", "web"])
    assert result.exit_code == 2
    assert "Error: question must not be empty" in result.stderr
    assert calls == []


def test_ask_passes_normal_question_unchanged(monkeypatch):
    calls = []
    _stub_ask(monkeypatch, calls)
    result = runner.invoke(app, ["ask", " hi ", "--source", "web"])
    assert result.exit_code == 0
    assert calls[0][0] == ("web", " hi ")


def test_version_prints_package_version():
    from importlib.metadata import version

    result = runner.invoke(app, ["--version"], prog_name="rag")
    assert result.exit_code == 0
    assert result.output.strip() == f"rag {version('rag-course')}"


def test_version_reads_installed_metadata_not_a_copied_string(monkeypatch):
    import rag_course.cli as cli

    monkeypatch.setattr(cli, "package_version", lambda dist: f"9.9.9-{dist}")
    result = runner.invoke(app, ["--version"], prog_name="rag")
    assert result.exit_code == 0
    assert result.output.strip() == "rag 9.9.9-rag-course"


def test_help_lists_version():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--version" in result.output


def test_ask_pdf_missing_path_errors_before_any_model_call(monkeypatch, tmp_path):
    calls = []
    _stub_ask(monkeypatch, calls)
    missing = tmp_path / "nope.pdf"
    result = runner.invoke(app, ["ask", "hi", "--source", "pdf", "--pdf", str(missing)])
    assert result.exit_code == 2
    assert f"Error: PDF not found: {missing}" in result.stderr
    assert calls == []


def test_ask_pdf_directory_path_gets_same_error(monkeypatch, tmp_path):
    calls = []
    _stub_ask(monkeypatch, calls)
    result = runner.invoke(app, ["ask", "hi", "--source", "pdf", "--pdf", str(tmp_path)])
    assert result.exit_code == 2
    assert f"Error: PDF not found: {tmp_path}" in result.stderr
    assert calls == []


def test_ask_pdf_default_path_checked_when_absent(monkeypatch, tmp_path):
    calls = []
    _stub_ask(monkeypatch, calls)
    absent = tmp_path / "k21.pdf"
    monkeypatch.setattr("rag_course.pdf.DEFAULT_PDF", absent)
    result = runner.invoke(app, ["ask", "hi", "--source", "pdf"])
    assert result.exit_code == 2
    assert f"Error: PDF not found: {absent}" in result.stderr
    assert calls == []


def test_ask_pdf_existing_file_reaches_ask(monkeypatch, tmp_path):
    calls = []
    _stub_ask(monkeypatch, calls)
    present = tmp_path / "ok.pdf"
    present.write_bytes(b"%PDF-1.4")
    result = runner.invoke(app, ["ask", "hi", "--source", "pdf", "--pdf", str(present)])
    assert result.exit_code == 0
    assert len(calls) == 1


def test_ask_web_and_sql_ignore_missing_pdf(monkeypatch, tmp_path):
    calls = []
    _stub_ask(monkeypatch, calls)
    missing = tmp_path / "nope.pdf"
    for source in ("web", "sql"):
        result = runner.invoke(app, ["ask", "hi", "--source", source, "--pdf", str(missing)])
        assert result.exit_code == 0
    assert len(calls) == 2


def _chat_web(monkeypatch, text):
    import rag_course
    from rag_course import web
    from fakes import fake_models, saved_page

    monkeypatch.setattr(rag_course, "bedrock_models", lambda settings: fake_models())
    monkeypatch.setattr(web, "fetch_page", saved_page)
    return runner.invoke(app, ["chat", "--source", "web"], input=text)


def test_chat_answers_three_questions_in_order_then_exits(monkeypatch):
    result = _chat_web(
        monkeypatch,
        "What is cloud computing?\nWhat is data science?\nWho won the FIFA World Cup in 1998?\nexit\nWhat is cloud computing?\n",
    )
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert len(lines) == 3
    assert "cloud computing" in lines[0].lower()
    assert "data science" in lines[1].lower()
    assert "don't know" in lines[2].lower()


def test_chat_empty_line_gets_hint_and_no_bedrock_call(monkeypatch):
    import rag_course
    from rag_course import web
    from fakes import saved_page

    def no_bedrock(settings):
        raise AssertionError("Bedrock must not be touched")

    monkeypatch.setattr(rag_course, "bedrock_models", no_bedrock)
    monkeypatch.setattr(web, "fetch_page", saved_page)
    result = runner.invoke(app, ["chat", "--source", "web"], input="\n  \nexit\n")
    assert result.exit_code == 0
    assert result.output.count("Type a question") == 2


def test_chat_end_of_input_exits_zero(monkeypatch):
    result = _chat_web(monkeypatch, "")
    assert result.exit_code == 0


def test_chat_loads_the_source_once_per_session(monkeypatch):
    from rag_course import web

    loads = []
    real = web.chunks
    monkeypatch.setattr(web, "chunks", lambda fetch=web.fetch_page: loads.append(1) or real(fetch))
    result = _chat_web(monkeypatch, "What is cloud computing?\nWhat is data science?\nWhat is cloud computing?\n")
    assert result.exit_code == 0
    assert len(result.output.strip().splitlines()) == 3
    assert len(loads) == 1


def test_chat_pdf_missing_path_errors_before_loading(monkeypatch, tmp_path):
    result = runner.invoke(app, ["chat", "--source", "pdf", "--pdf", str(tmp_path / "nope.pdf")])
    assert result.exit_code == 2
    assert "Error: PDF not found" in result.stderr
