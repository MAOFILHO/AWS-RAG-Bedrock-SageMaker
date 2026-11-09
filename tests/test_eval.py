"""rag eval with fake Bedrock: the scores it prints, the judge's temperature and the cost sums."""

import json
import re

import pytest
from typer.testing import CliRunner

from fakes import FakeEmbeddings, saved_page
from rag_course import evaluate
from rag_course.cli import app
from rag_course.core import BedrockAnswerModel, Models

runner = CliRunner()


class ScriptedModel:
    """Answers with the retrieved context, and judges every answer faithful but one question irrelevant."""

    def __init__(self):
        self.input_tokens = self.output_tokens = 0

    def answer(self, prompt: str) -> str:
        if "strict evaluator" in prompt:
            question = prompt.split("QUESTION: ", 1)[1].split("\n\nANSWER:", 1)[0]
            reply = json.dumps({"faithful": True, "relevant": "benefits" not in question, "reason": "x"})
        else:
            reply = prompt.split("Context:\n", 1)[1].split("\n\nQuestion: ", 1)[0]
        self.input_tokens += 1000
        self.output_tokens += 100
        return reply


def fake_models() -> Models:
    return Models(answer=ScriptedModel(), embed=FakeEmbeddings())


def test_run_eval_scores_the_golden_sets_offline():
    ticks = iter(range(100))
    scores = evaluate.run_eval(fake_models(), fetch=saved_page, clock=lambda: next(ticks) * 2.0)
    assert scores.faithfulness == 1.0
    assert scores.relevance == pytest.approx(0.8)
    assert scores.p95_latency == 2.0
    assert scores.hit_at_3 == 1.0
    assert scores.mrr == pytest.approx(0.96, abs=0.005)


def test_cost_counts_only_the_answer_call_tokens():
    scores = evaluate.run_eval(fake_models(), fetch=saved_page)
    assert scores.cost_per_query == pytest.approx(0.00006 + 0.1 * 0.00024)


def test_hit_at_3_and_mrr_follow_the_rank_of_the_golden_source(monkeypatch):
    class Stub:
        def __init__(self, embed, chunks):
            self.chunks = chunks

        def search(self, query, k=3):
            return [(c, 1.0) for c in self.chunks[:k]]

    monkeypatch.setattr(evaluate, "VectorStore", Stub)
    scores = evaluate.run_eval(fake_models(), fetch=saved_page)
    assert scores.hit_at_3 == pytest.approx(5 / 12)  # first 3 chunks: 3 cloud web cases, 2 pdf page-1 cases
    assert scores.mrr == pytest.approx(5 / 12)


def test_judge_asks_bedrock_with_temperature_zero():
    calls = []

    class Client:
        def converse(self, **kwargs):
            calls.append(kwargs)
            return {
                "output": {"message": {"content": [{"text": '{"faithful": true, "relevant": true}'}]}},
                "usage": {"inputTokens": 10, "outputTokens": 2},
            }

    model = BedrockAnswerModel(Client(), "amazon.nova-lite-v1:0")
    assert evaluate.judge(model, "q", "c", "a") == {"faithful": True, "relevant": True}
    assert [c["inferenceConfig"] for c in calls] == [{"temperature": 0}]
    assert (model.input_tokens, model.output_tokens) == (10, 2)


def test_unparseable_judge_reply_counts_as_unfaithful_and_irrelevant():
    model = type("M", (), {"answer": lambda self, prompt: "no json here"})()
    assert evaluate.judge(model, "q", "c", "a") == {"faithful": False, "relevant": False}


def test_rag_eval_prints_all_six_scores(monkeypatch):
    monkeypatch.setattr(evaluate, "bedrock_models", lambda settings: fake_models())
    monkeypatch.setattr("rag_course.web.fetch_page", saved_page)
    result = runner.invoke(app, ["eval"])
    assert result.exit_code == 0, result.output
    lines = dict(line.split(": ", 1) for line in result.output.strip().splitlines())
    assert list(lines) == ["hit@3", "MRR", "faithfulness", "relevance", "p95 latency", "cost per query"]
    assert lines["faithfulness"] == "1.00"
    assert lines["relevance"] == "0.80"
    assert lines["cost per query"] == "$0.000084"
    assert re.fullmatch(r"\d+\.\d\d s", lines["p95 latency"])
