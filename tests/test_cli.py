from typer.testing import CliRunner

from rag_course.cli import app

runner = CliRunner()


def test_help_lists_ask_and_eval():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ask" in result.output
    assert "eval" in result.output


def test_eval_says_not_built_yet():
    result = runner.invoke(app, ["eval"])
    assert result.exit_code == 0
    assert "not built yet" in result.output


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
    absent = tmp_path / "invoice.pdf"
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
