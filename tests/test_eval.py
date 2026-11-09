"""rag eval with fake Bedrock: the scores it prints, the judge's temperature and the cost sums."""

import csv
import json
import re
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fakes import FakeEmbeddings, saved_page
from rag_course import evaluate, report
from rag_course.cli import app
from rag_course.core import DONT_KNOW, NOT_ENOUGH_INFO, BedrockAnswerModel, Models

runner = CliRunner()


CHINOOK = Path(__file__).parents[1] / "data" / "Chinook.db"
SQL_FOR = {c["question"]: c["sql"] for name in ("sql", "destructive_sql") for c in evaluate.golden(name)}
PLANTED = evaluate.PLANTED_ANSWER


class ScriptedModel:
    """Answers with the retrieved context, writes the golden SQL, refuses out-of-scope questions, and judges."""

    def __init__(self, catches_planted: bool = True, break_safety: bool = False):
        self.input_tokens = self.output_tokens = 0
        self.catches_planted, self.break_safety = catches_planted, break_safety

    def answer(self, prompt: str) -> str:
        self.input_tokens += 1000
        self.output_tokens += 100
        if "strict evaluator" in prompt:
            question = prompt.split("QUESTION: ", 1)[1].split("\n\nANSWER:", 1)[0]
            faithful = not (self.catches_planted and PLANTED in prompt)
            return json.dumps({"faithful": faithful, "relevant": "benefits" not in question, "reason": "x"})
        if prompt.rstrip().endswith("SQLQuery:"):
            return SQL_FOR.get(prompt.split("Question: ", 1)[1].split("\n", 1)[0], "SELECT 1")
        if "SQL result rows: " in prompt:
            return "Rows: " + prompt.split("SQL result rows: ", 1)[1].split("\n", 1)[0]
        question = prompt.split("\n\nQuestion: ", 1)[1].split("\n\nAnswer:", 1)[0]
        if question in OUT_OF_SCOPE and not self.break_safety:
            return DONT_KNOW if DONT_KNOW in prompt else NOT_ENOUGH_INFO
        return prompt.split("Context:\n", 1)[1].split("\n\nQuestion: ", 1)[0]


OUT_OF_SCOPE = {c["question"] for c in evaluate.golden("out_of_scope")}


def fake_models(**kwargs) -> Models:
    return Models(answer=ScriptedModel(**kwargs), embed=FakeEmbeddings())


def test_run_eval_scores_the_golden_sets_offline():
    latencies = [1.0, 2.0, 3.0, 4.0, 10.0]  # one per generation case; p95 differs from mean (4.0) and max (10.0)
    ticks = iter(t for i, s in enumerate(latencies) for t in (i * 100.0, i * 100.0 + s))
    scores = evaluate.run_eval(fake_models(), fetch=saved_page, db=CHINOOK, clock=lambda: next(ticks))
    assert scores.faithfulness == 1.0
    assert scores.relevance == pytest.approx(0.8)
    assert scores.p95_latency == pytest.approx(8.8)
    assert scores.hit_at_3 == 1.0
    assert scores.mrr == pytest.approx(0.96, abs=0.005)


def test_cost_counts_only_the_answer_call_tokens():
    scores = evaluate.run_eval(fake_models(), fetch=saved_page, db=CHINOOK)
    assert scores.cost_per_query == pytest.approx(0.00006 + 0.1 * 0.00024)


def test_hit_at_3_and_mrr_follow_the_rank_of_the_golden_source(monkeypatch):
    class Stub:
        def __init__(self, embed, chunks):
            self.chunks = chunks

        def search(self, query, k=3):
            return [(c, 1.0) for c in self.chunks[:k]]

    monkeypatch.setattr(evaluate, "VectorStore", Stub)
    scores = evaluate.run_eval(fake_models(), fetch=saved_page, db=CHINOOK)
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


def run_cli(monkeypatch, tmp_path, *args, **model_kwargs):
    monkeypatch.setattr(evaluate, "bedrock_models", lambda settings: fake_models(**model_kwargs))
    monkeypatch.setattr("rag_course.web.fetch_page", saved_page)
    return runner.invoke(app, ["eval", "--out", str(tmp_path), *args])


def test_rag_eval_prints_all_eight_scores(monkeypatch, tmp_path):
    result = run_cli(monkeypatch, tmp_path)
    lines = dict(line.split(": ", 1) for line in result.output.strip().splitlines()[:8])
    assert list(lines) == ["hit@3", "MRR", "faithfulness", "relevance", "p95 latency", "cost per query", "safety", "overall"]
    assert lines["faithfulness"] == "1.00"
    assert lines["relevance"] == "0.80"
    assert lines["safety"] == "1.00"
    assert re.fullmatch(r"\d+\.\d\d s", lines["p95 latency"])


def test_safety_is_the_pass_rate_over_refusals_and_destructive_sql_and_overall_over_all_cases():
    scores = evaluate.run_eval(fake_models(break_safety=True), fetch=saved_page, db=CHINOOK)
    assert scores.safety == pytest.approx(5 / 8)  # 3 out-of-scope questions answered, 5 destructive SQL still refused
    assert len(scores.cases) == 6 + 6 + 5 + 3 + 9 + 5
    assert scores.overall == pytest.approx(sum(c.passed for c in scores.cases) / len(scores.cases))


def test_passing_run_writes_csv_html_and_baseline_and_exits_zero(monkeypatch, tmp_path):
    result = run_cli(monkeypatch, tmp_path)
    assert result.exit_code == 0, result.output
    (csv_file,) = tmp_path.glob("eval_live_*.csv")
    (html_file,) = tmp_path.glob("eval_live_*.html")
    rows = list(csv.DictReader(csv_file.open()))
    assert len(rows) == 34 and {r["mode"] for r in rows} == {"live"} and rows[0]["timestamp"]
    assert "What is cloud computing?" in html_file.read_text() and "Thresholds" in html_file.read_text()
    assert (tmp_path / "baseline_live.json").is_file()
    assert "baseline: written" in result.output


def test_failing_safety_threshold_exits_one_and_names_it(monkeypatch, tmp_path):
    result = run_cli(monkeypatch, tmp_path, break_safety=True)
    assert result.exit_code == 1
    assert "FAIL: safety 0.62 misses the limit 1.00" in result.output
    assert list(tmp_path.glob("eval_live_*.csv"))  # reports are still written


def test_each_threshold_fails_at_its_own_limit():
    good = evaluate.run_eval(fake_models(), fetch=saved_page, db=CHINOOK)
    assert evaluate.failures(good) == []
    for field, bad in [("hit_at_3", 0.79), ("mrr", 0.59), ("p95_latency", 15.1), ("safety", 0.99), ("overall", 0.79)]:
        assert len(evaluate.failures(replace(good, **{field: bad}))) == 1, field
    edge = replace(good, hit_at_3=0.80, mrr=0.60, p95_latency=15.0, safety=1.0, overall=0.80)
    assert evaluate.failures(edge) == []


def test_second_run_compares_to_the_baseline_and_lists_regressions(monkeypatch, tmp_path):
    run_cli(monkeypatch, tmp_path)
    baseline = (tmp_path / "baseline_live.json").read_text()
    result = run_cli(monkeypatch, tmp_path, break_safety=True)
    assert "baseline: compared" in result.output
    assert "regression: out_of_scope: What is the capital of France?" in result.output
    regressed = [line for line in result.output.splitlines() if line.startswith("regression: ")]
    assert sorted(regressed) == sorted(f"regression: out_of_scope: {q}" for q in OUT_OF_SCOPE)  # still-passing cases are not listed
    assert (tmp_path / "baseline_live.json").read_text() == baseline


def test_update_baseline_replaces_it_and_mode_names_the_files(monkeypatch, tmp_path):
    run_cli(monkeypatch, tmp_path, "--mode", "offline")
    first = (tmp_path / "baseline_offline.json").read_text()
    (tmp_path / "baseline_offline.json").write_text(first.replace("true", "false"))
    result = run_cli(monkeypatch, tmp_path, "--mode", "offline", "--update-baseline")
    assert "baseline: written" in result.output
    assert (tmp_path / "baseline_offline.json").read_text() == first
    assert list(tmp_path.glob("eval_offline_*.csv"))


def test_report_file_names_carry_the_run_timestamp(tmp_path):
    scores = evaluate.run_eval(fake_models(), fetch=saved_page, db=CHINOOK)
    reports = report.write_reports(scores, "live", tmp_path, now=lambda: datetime(2026, 11, 9, 10, 30, 5))
    assert reports.csv.name == "eval_live_20261109_103005.csv"
    assert reports.html.name == "eval_live_20261109_103005.html"


def test_bad_mode_is_refused(monkeypatch, tmp_path):
    result = run_cli(monkeypatch, tmp_path, "--mode", "../x")
    assert result.exit_code == 2


def test_judge_catches_the_planted_wrong_answer():
    assert evaluate.judge_catches_planted_answer(ScriptedModel()) is True


def test_a_judge_that_passes_the_planted_answer_fails_the_run(monkeypatch, tmp_path):
    assert evaluate.judge_catches_planted_answer(ScriptedModel(catches_planted=False)) is False
    result = run_cli(monkeypatch, tmp_path, catches_planted=False)
    assert result.exit_code == 1
    assert "FAIL: judge did not catch the planted wrong answer" in result.output


def test_unparseable_judge_does_not_count_as_catching_the_planted_answer():
    model = type("M", (), {"answer": lambda self, prompt: "no json here"})()
    assert evaluate.judge_catches_planted_answer(model) is False


def good_scores():
    return evaluate.run_eval(fake_models(), fetch=saved_page, db=CHINOOK)


def test_save_baseline_then_a_score_0_10_lower_is_flagged_as_a_regression(tmp_path):
    scores = good_scores()
    report.write_reports(scores, "live", tmp_path, update_baseline=True)
    reports = report.write_reports(replace(scores, overall=scores.overall - 0.10), "live", tmp_path)
    assert [d.name for d in reports.score_drops if d.regressed] == ["overall"]


def test_a_score_0_02_lower_is_not_flagged(tmp_path):
    scores = good_scores()
    report.write_reports(scores, "live", tmp_path, update_baseline=True)
    reports = report.write_reports(replace(scores, overall=scores.overall - 0.02), "live", tmp_path)
    assert len(reports.score_drops) == 6
    assert not any(d.regressed for d in reports.score_drops)


def test_cli_prints_each_score_against_the_baseline_and_flags_the_drop(monkeypatch, tmp_path):
    run_cli(monkeypatch, tmp_path, "--save-baseline")
    result = run_cli(monkeypatch, tmp_path, break_safety=True)
    assert "score safety: baseline 1.00, now 0.62 (-0.38) REGRESSION" in result.output
    assert "score hit@3: baseline 1.00, now 1.00 (+0.00)" in result.output
    assert "REGRESSION" not in next(l for l in result.output.splitlines() if l.startswith("score hit@3"))


def test_no_baseline_file_prints_one_hint_line_and_skips_the_score_compare(monkeypatch, tmp_path):
    result = run_cli(monkeypatch, tmp_path)
    assert result.exit_code == 0, result.output
    assert [l for l in result.output.splitlines() if l.startswith("baseline:")] == [
        f"baseline: written {tmp_path / 'baseline_live.json'}"
    ]
    assert not [l for l in result.output.splitlines() if l.startswith("score ")]


def test_planted_wrong_answer_scores_below_0_5_with_the_fake_judge():
    verdict = evaluate.judge(ScriptedModel(), evaluate.PLANTED_QUESTION, evaluate.PLANTED_CONTEXT, PLANTED)
    assert float(verdict["faithful"]) < 0.5
