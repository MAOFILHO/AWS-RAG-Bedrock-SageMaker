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
