import pytest
from typer.testing import CliRunner

import rag_course
from rag_course import core, web
from rag_course.cli import app
from rag_course.core import DONT_KNOW, Settings
from fakes import fake_models, saved_page


def ask_web(question: str) -> str:
    return rag_course.ask("web", question, models=fake_models(), fetch=saved_page)


@pytest.mark.parametrize(
    ("question", "page", "topic"),
    [
        ("What is cloud computing?", web.URLS[0], "cloud computing"),
        ("What is data science?", web.URLS[1], "data science"),
    ],
)
def test_golden_question_is_answered_from_the_saved_pages(question, page, topic):
    answer = ask_web(question)
    assert topic in answer.lower()
    assert answer in saved_page(page)


def test_out_of_scope_question_gets_the_fixed_sentence():
    assert ask_web("Who won the FIFA World Cup in 1998?") == DONT_KNOW


def test_rag_ask_source_web_prints_the_answer(monkeypatch):
    monkeypatch.setattr(rag_course, "bedrock_models", lambda settings: fake_models())
    monkeypatch.setattr(web, "fetch_page", saved_page)
    result = CliRunner().invoke(app, ["ask", "--source", "web", "What is cloud computing?"])
    assert result.exit_code == 0
    assert "cloud computing" in result.output
    assert result.output.strip() in saved_page(web.URLS[0])


def test_settings_defaults():
    assert Settings.from_env({}) == Settings(
        "amazon.nova-lite-v1:0", "amazon.titan-embed-text-v2:0", "us-east-1"
    )


def test_settings_overrides():
    env = {"RAG_MODEL_ID": "m", "RAG_EMBED_MODEL_ID": "e", "AWS_REGION": "eu-west-1"}
    assert Settings.from_env(env) == Settings("m", "e", "eu-west-1")


@pytest.mark.live
def test_live_web_answer_from_real_bedrock():
    models = core.bedrock_models(Settings.from_env())
    assert rag_course.ask("web", "What is cloud computing?", models=models) != DONT_KNOW
