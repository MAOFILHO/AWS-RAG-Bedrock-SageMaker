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
