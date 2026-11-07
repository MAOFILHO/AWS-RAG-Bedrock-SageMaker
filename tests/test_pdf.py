import pytest
from typer.testing import CliRunner

import rag_course
from rag_course import core, pdf
from rag_course.cli import app
from rag_course.core import NOT_ENOUGH_INFO, Settings
from fakes import fake_models, text_pdf


def ask_pdf(question: str, path=pdf.DEFAULT_PDF) -> str:
    return rag_course.ask("pdf", question, models=fake_models(), pdf=path)


def test_golden_question_is_answered_from_the_course_pdf():
    answer = ask_pdf("What are case studies and success stories?")
    assert "case studies" in answer.lower()
    assert answer in "\n".join(pdf.load_pdf(pdf.DEFAULT_PDF))


def test_out_of_scope_question_gets_the_fixed_sentence():
    assert ask_pdf("Who won the FIFA World Cup in 1998?") == NOT_ENOUGH_INFO


def test_rag_ask_source_pdf_works_from_any_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(rag_course, "bedrock_models", lambda settings: fake_models())
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["ask", "--source", "pdf", "What are SDKs and APIs?"])
    assert result.exit_code == 0, result.output
    assert "SDKs and APIs" in result.output


def test_pdf_option_uses_another_file(monkeypatch, tmp_path):
    monkeypatch.setattr(rag_course, "bedrock_models", lambda settings: fake_models())
    other = tmp_path / "other.pdf"
    other.write_bytes(text_pdf(["Kiwis are flightless birds from New Zealand."]))
    args = ["ask", "--source", "pdf", "--pdf", str(other), "Which birds are flightless kiwis?"]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "Kiwis are flightless birds from New Zealand."


@pytest.mark.live
def test_live_pdf_answer_from_real_bedrock():
    models = core.bedrock_models(Settings.from_env())
    answer = rag_course.ask("pdf", "What are the business applications of Amazon Q?", models=models)
    assert answer != NOT_ENOUGH_INFO
