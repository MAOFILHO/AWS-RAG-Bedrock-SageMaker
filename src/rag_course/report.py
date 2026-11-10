"""rag eval reports: a CSV and an HTML file per run, and a baseline per mode that the next run is compared to."""

import csv
import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from rag_course.evaluate import Scores, threshold_results


@dataclass(frozen=True)
class Reports:
    csv: Path
    html: Path
    baseline: Path
    baseline_written: bool
    regressions: list[str]
    score_drops: list["ScoreDrop"]


# Scores where lower is worse, and how far one may fall below the baseline before it is flagged.
COMPARED_SCORES = (
    ("hit@3", "hit_at_3"),
    ("MRR", "mrr"),
    ("faithfulness", "faithfulness"),
    ("relevance", "relevance"),
    ("safety", "safety"),
    ("overall", "overall"),
)
MAX_DROP = 0.05


@dataclass(frozen=True)
class ScoreDrop:
    name: str
    before: float
    now: float

    @property
    def change(self) -> float:
        return round(self.now - self.before, 4)

    @property
    def regressed(self) -> bool:
        return -self.change > MAX_DROP


def _key(case) -> str:
    return f"{case.category}: {case.question}"


def write_reports(
    scores: Scores,
    mode: str,
    out: Path,
    update_baseline: bool = False,
    now: Callable[[], datetime] = datetime.now,
) -> Reports:
    out.mkdir(parents=True, exist_ok=True)
    stamp = now().strftime("%Y%m%d_%H%M%S")
    baseline = out / f"baseline_{mode}.json"

    regressions, score_drops = [], []
    if baseline.is_file():
        saved = json.loads(baseline.read_text())
        regressions = [_key(c) for c in scores.cases if saved["cases"].get(_key(c)) and not c.passed]
        score_drops = [
            ScoreDrop(name, saved["scores"][field], getattr(scores, field))
            for name, field in COMPARED_SCORES
            if field in saved.get("scores", {})
        ]

    csv_path, html_path = out / f"eval_{mode}_{stamp}.csv", out / f"eval_{mode}_{stamp}.html"
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["mode", "timestamp", "category", "question", "safety", "status"])
        for case in scores.cases:
            writer.writerow([mode, stamp, case.category, case.question, case.safety, "PASS" if case.passed else "FAIL"])
    html_path.write_text(_html(scores, mode, stamp, regressions))

    write_baseline = update_baseline or not baseline.is_file()
    if write_baseline:
        baseline.write_text(json.dumps(
                {
                    "mode": mode,
                    "timestamp": stamp,
                    "scores": {field: getattr(scores, field) for _, field in COMPARED_SCORES},
                    "cases": {_key(c): c.passed for c in scores.cases},
                },
                indent=2,
            )
        )
    return Reports(csv_path, html_path, baseline, write_baseline, regressions, score_drops)


def _html(scores: Scores, mode: str, stamp: str, regressions: list[str]) -> str:
    def row(*cells) -> str:
        return "<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in cells) + "</tr>"

    thresholds = "".join(
        row(name, f"{value:.2f}", f"{limit:.2f}", "PASS" if ok else "FAIL") for name, value, limit, ok in threshold_results(scores)
    )
    cases = "".join(row(c.category, c.question, c.safety, "PASS" if c.passed else "FAIL") for c in scores.cases)
    regressed = "".join(f"<li>{html.escape(key)}</li>" for key in regressions) or "<li>none</li>"
    judge = "PASS" if scores.judge_catches_planted else "FAIL"
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>rag eval {html.escape(mode)} {stamp}</title></head><body>"
        f"<h1>rag eval: {html.escape(mode)} · {stamp}</h1>"
        "<h2>Thresholds</h2><table border='1'><tr><th>score</th><th>value</th><th>limit</th><th>status</th></tr>"
        f"{thresholds}</table>"
        f"<p>Judge catches the planted wrong answer: {judge}</p>"
        f"<h2>Regressions against the baseline</h2><ul>{regressed}</ul>"
        "<h2>Cases</h2><table border='1'><tr><th>category</th><th>question</th><th>safety</th><th>status</th></tr>"
        f"{cases}</table></body></html>"
    )
