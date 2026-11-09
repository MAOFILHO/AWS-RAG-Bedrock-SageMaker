"""rag eval: retrieval hit@3 and MRR, judged faithfulness and relevance, p95 latency and cost per query."""

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from rag_course import pdf, web
from rag_course.core import (
    PDF_PROMPT,
    WEB_PROMPT,
    Models,
    Settings,
    VectorStore,
    answer_with_context,
    bedrock_models,
)

GOLDEN = Path(__file__).resolve().parents[2] / "tests" / "golden"

# Nova Lite on-demand, US East (N. Virginia), USD per 1,000 tokens ($0.06 / $0.24 per 1M).
# Re-checked 2026-11-08 against the AWS Price List API (AmazonBedrock offer, USE1-NovaLite-input-tokens
# and -output-tokens) and https://aws.amazon.com/bedrock/pricing/. Same as the RAG_4 notebook.
PRICE_PER_1K_INPUT = 0.00006
PRICE_PER_1K_OUTPUT = 0.00024

JUDGE_PROMPT = """You are a strict evaluator of a RAG system. Reply ONLY with JSON:
{{"faithful": true or false, "relevant": true or false, "reason": "<one sentence>"}}
- faithful = true only if EVERY claim in ANSWER is supported by CONTEXT.
- relevant = true if ANSWER addresses QUESTION.

CONTEXT:
{context}

QUESTION: {question}

ANSWER: {answer}"""


@dataclass(frozen=True)
class Scores:
    hit_at_3: float
    mrr: float
    faithfulness: float
    relevance: float
    p95_latency: float
    cost_per_query: float


def golden(name: str, golden_dir: Path = GOLDEN) -> list[dict]:
    return json.loads((golden_dir / f"{name}.json").read_text())


def judge(model, question: str, context: str, answer: str) -> dict:
    raw = model.answer(JUDGE_PROMPT.format(context=context, question=question, answer=answer))
    try:
        verdict = json.loads(re.search(r"\{.*\}", raw, re.S).group())
        return {"faithful": verdict["faithful"] is True, "relevant": verdict["relevant"] is True}
    except (AttributeError, KeyError, ValueError):
        return {"faithful": False, "relevant": False}


def run_eval(
    models: Models | None = None,
    fetch: Callable[[str], str] | None = None,
    pdf_path: Path = pdf.DEFAULT_PDF,
    golden_dir: Path = GOLDEN,
    clock: Callable[[], float] = time.perf_counter,
) -> Scores:
    models = models or bedrock_models(Settings.from_env())
    stores = {
        "web": VectorStore(models.embed, web.chunks(fetch or web.fetch_page)),
        "pdf": VectorStore(models.embed, pdf.chunks(pdf_path)),
    }
    prompts = {"web": WEB_PROMPT, "pdf": PDF_PROMPT}

    ranks = []
    for case in golden("web", golden_dir):
        sources = [chunk.source for chunk, _ in stores["web"].search(case["question"], 3)]
        ranks.append(sources.index(case["source"]) + 1 if case["source"] in sources else None)
    for case in golden("pdf", golden_dir):
        sources = [chunk.source for chunk, _ in stores["pdf"].search(case["question"], 3)]
        wanted = [i for i, source in enumerate(sources) if source.endswith(f"#page={case['page']}")]
        ranks.append(wanted[0] + 1 if wanted else None)

    verdicts, seconds, costs = [], [], []
    for case in golden("generation", golden_dir):
        pipeline, question = case["pipeline"], case["question"]
        tokens_before = _tokens(models)
        start = clock()
        answer, context = answer_with_context(question, stores[pipeline], models, prompts[pipeline])
        seconds.append(clock() - start)
        used = np.subtract(_tokens(models), tokens_before)
        costs.append(used[0] / 1000 * PRICE_PER_1K_INPUT + used[1] / 1000 * PRICE_PER_1K_OUTPUT)
        verdicts.append(judge(models.answer, question, context, answer))

    return Scores(
        hit_at_3=float(np.mean([r is not None for r in ranks])),
        mrr=float(np.mean([1 / r if r else 0 for r in ranks])),
        faithfulness=float(np.mean([v["faithful"] for v in verdicts])),
        relevance=float(np.mean([v["relevant"] for v in verdicts])),
        p95_latency=float(np.percentile(seconds, 95)),
        cost_per_query=float(np.mean(costs)),
    )


def _tokens(models: Models) -> tuple[int, int]:
    return getattr(models.answer, "input_tokens", 0), getattr(models.answer, "output_tokens", 0)


def format_scores(scores: Scores) -> str:
    return "\n".join(
        [
            f"hit@3: {scores.hit_at_3:.2f}",
            f"MRR: {scores.mrr:.2f}",
            f"faithfulness: {scores.faithfulness:.2f}",
            f"relevance: {scores.relevance:.2f}",
            f"p95 latency: {scores.p95_latency:.2f} s",
            f"cost per query: ${scores.cost_per_query:.6f}",
        ]
    )
