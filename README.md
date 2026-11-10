# RAG on AWS Bedrock — Ask Your Documents

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Bedrock-FF9900?logo=amazon-aws&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-6C3FC5)
![Tests](https://img.shields.io/badge/Tests-offline-green)
[![CI](https://github.com/MAOFILHO/AWS-RAG-Bedrock-SageMaker/actions/workflows/ci.yml/badge.svg)](https://github.com/MAOFILHO/AWS-RAG-Bedrock-SageMaker/actions/workflows/ci.yml)

Ask questions about web pages, a PDF or a SQL database from the terminal. Answers come from Amazon Nova Lite on AWS Bedrock. For web pages and the PDF, the answer is grounded in text retrieved with Titan Text Embeddings v2. For the SQL database, the model writes a read-only query and answers from its rows. When the Source holds no answer, the model says so.

This is a runnable Python port of the RAG course notebooks. The four notebooks stay in `notebooks/` as the course reference.

## Why this is built this way

- **Pay per question, nothing idle.** Bedrock bills per token. No endpoint runs while you sleep.
- **Tests need no AWS.** A fake answer model and a fake embedding model replace Bedrock, so tests are free and fast.
- **No secrets in code.** The AWS CLI credential chain supplies access. `.env` is git-ignored; `.env.example` holds names only.
- **One lock file.** `uv.lock` pins every version, so the same install works on every machine.
- **Notebooks kept.** The 4 originals stay in `notebooks/` as the course reference.

## RAG architecture

```
Question
   │
   ▼
Embed the question  (Titan Text Embeddings v2)
   │
   ▼
Cosine search over an in-memory numpy store
   │   chunks: 500 characters, 50 overlap
   ▼
Top-3 chunks
   │
   ▼
Nova Lite answers using ONLY those chunks
   │
   ▼
Answer, or the fixed "I don't know" sentence
```

The model never answers from memory alone. This flow applies to the web and PDF Sources. The SQL Source uses a read-only, `SELECT`-only query instead of chunks.

| Parameter | Value |
|---|---|
| Answer model | `amazon.nova-lite-v1:0` |
| Embedding model | `amazon.titan-embed-text-v2:0` |
| Region | `us-east-1` |
| Chunk size / overlap | 500 / 50 characters |
| Chunks retrieved (top-k) | 3 |
| Vector store | numpy, cosine similarity, in memory |

## Problem and Solution

**The problem.** A language model alone answers from memory. It can state a wrong fact with confidence, and it knows nothing about your own pages, PDFs or tables. Teams that want answers from their own material also need to see where each answer came from, and to be sure the system will not write to their database.

**The solution.** `rag` answers from the material you point it at, one Source per question:

- **Web pages and PDF.** The text is split into chunks, embedded with Titan Text Embeddings v2 and searched by cosine similarity. Nova Lite answers from the top 3 chunks only.
- **SQL database.** The model writes one `SELECT` query. The database opens read-only, so a model-written `DROP` or `DELETE` cannot run. The model then answers from the rows.
- **No answer in the Source.** The model says so with one fixed sentence instead of guessing.
- **Proof it works.** `rag eval` scores retrieval, grounding and safety against golden question sets and fails the run when a threshold is missed.

## Results

Numbers from the last live `rag eval` run, on 2026-11-09 (34 golden cases against real Bedrock, mode `live`). Every threshold passed.

| Metric | Score | Threshold |
|---|---|---|
| hit@3 | 1.00 | at least 0.80 |
| MRR | 1.00 | at least 0.60 |
| Faithfulness | 1.00 | none (reported only) |
| Relevance | 1.00 | none (reported only) |
| Safety | 1.00 | 1.00 |
| Overall | 1.00 | at least 0.80 |
| p95 latency | 2.30 s | at most 15 s |

The judge also caught the planted wrong answer. The report does not store cost per query, so it is not listed here. See [Cost estimate](#cost-estimate) for the prices. Run `uv run rag eval` to reproduce these numbers.

## Architecture

One `rag ask` call goes through a Source pipeline, then the shared Core, then Bedrock.

```
rag ask --source web|pdf|sql "question"
        │
        ▼
   CLI (typer)  ── rag_course/cli.py
        │
        ▼
┌── Source pipelines ───────────────────────────┐
│  web.py   fetch 2 IBM pages → text → chunks   │
│  pdf.py   read data/invoice.pdf → chunks          │
│  sql.py   SELECT-only query, read-only SQLite │
└───────────────────┬───────────────────────────┘
                    ▼
┌── Core ── rag_course/core.py ─────────────────┐
│  Settings from env (models, region)           │
│  numpy VectorStore, cosine top-3              │
│  retry on throttling                          │
│  optional LangSmith tracing                   │
└───────────────────┬───────────────────────────┘
                    ▼
┌── Amazon Bedrock (us-east-1) ─────────────────┐
│  Titan Text Embeddings v2   embeds            │
│  Nova Lite                  answers           │
└───────────────────────────────────────────────┘
```

## The four notebooks

The four original notebooks in `notebooks/` are the course reference.

| Notebook | Source | In this project |
|---|---|---|
| `RAG_1_Project` | Two IBM web pages | `rag ask --source web` |
| `RAG_2_PDF_Project` | `data/invoice.pdf` | `rag ask --source pdf` |
| `RAG_3_SQL_Project` | `data/Chinook.db` | `rag ask --source sql` |
| `RAG_4_Testing_Project` | Testing and a judge model | `rag eval` |

## Tech Stack

| Layer | Technology |
|---|---|
| Language and packaging | Python 3.12, `uv` with a locked `uv.lock` |
| Answer model | Amazon Nova Lite (`amazon.nova-lite-v1:0`) |
| Embeddings | Amazon Titan Text Embeddings v2 (`amazon.titan-embed-text-v2:0`) |
| AWS client | `boto3` |
| Vector store | `numpy`, cosine similarity, in memory |
| Chunking | `langchain-text-splitters` (500 characters, 50 overlap) |
| Web and PDF input | `requests`, `beautifulsoup4`, `pypdf` |
| SQL input | SQLite (`data/Chinook.db`), opened read-only |
| CLI | `typer` |
| Tracing (optional) | LangSmith |
| Tests | `pytest`, offline with fakes |

## AWS tools and their role

| AWS tool | Role in this project | Used by the code |
|---|---|---|
| Amazon Bedrock | Runs the answer model (`amazon.nova-lite-v1:0`) and the embedding model (`amazon.titan-embed-text-v2:0`) | Yes |
| AWS IAM | Gives `boto3` permission to call Bedrock | Yes |
| Amazon SageMaker | The original course notebooks ran on a SageMaker notebook instance, which supplied Python and the IAM role | No |

Nothing else is created in your AWS account. No server, database or container is deployed.

## Prerequisites

- [uv](https://docs.astral.sh/uv/). It installs Python 3.12 if it is missing.
- The [AWS CLI](https://aws.amazon.com/cli/).
- An AWS account with Bedrock model access to Amazon Nova Lite and Titan Text Embeddings v2 in `us-east-1`.
- Internet access for the `web` Source, which fetches two IBM pages.

## Setup

Setup takes 6 steps.

1. Install [uv](https://docs.astral.sh/uv/) and the [AWS CLI](https://aws.amazon.com/cli/).

2. Clone the repo and install the dependencies. `uv` installs Python 3.12 if it is missing.

   ```bash
   git clone https://github.com/MAOFILHO/AWS-RAG-Bedrock-SageMaker.git
   cd AWS-RAG-Bedrock-SageMaker
   uv sync --frozen
   ```

3. Check the install. The tests need no AWS access.

   ```bash
   uv run pytest
   ```

4. Give `boto3` AWS credentials that can call Bedrock in `us-east-1`, then check them.

   ```bash
   aws configure
   aws sts get-caller-identity
   ```

5. In the Bedrock console, open Model access and enable Amazon Nova Lite and Titan Text Embeddings v2.

6. Ask a question.

   ```bash
   uv run rag ask --source web "What is cloud computing?"
   ```

## Running the project

### Ask a Source

A Source is the material you ask about. Each `rag ask` call takes one.

```bash
# Two IBM web pages
uv run rag ask --source web "What is data science?"

# The bundled PDF (data/invoice.pdf)
uv run rag ask --source pdf "What is this document about?"

# Your own PDF
uv run rag ask --source pdf --pdf path/to/file.pdf "Your question"

# The Chinook SQLite database (data/Chinook.db), read-only, SELECT only
uv run rag ask --source sql "How many customers are there?"
```

### Chat

`rag chat` loads one Source once and answers many questions. It reads one question per line from the terminal. Type `exit` or end the input to stop.

```bash
uv run rag chat --source pdf
```

### Evaluate

`rag eval` scores the golden question sets, writes reports and exits with code 1 when a threshold fails. It calls real Bedrock, including a judge model, so it costs a few cents per run.

```bash
uv run rag eval
```

Each run writes a CSV and an HTML report to `reports/`, named `eval_<mode>_<timestamp>`. The thresholds are hit@3 at least 0.80, MRR at least 0.60, p95 latency at most 15 s, safety 1.00 and overall at least 0.80. A run also fails when the judge does not catch a planted wrong answer.

The first run for a mode saves its scores as `reports/baseline_<mode>.json`. Later runs compare against it and print each regression and each score drop. To replace the baseline with the current run:

```bash
uv run rag eval --save-baseline
```

`--mode <label>` names the run, so a separate baseline is kept per label. `--out <folder>` changes the report folder.

### Settings

All optional. The defaults match the notebooks.

| Variable | Default | Purpose |
|---|---|---|
| `RAG_MODEL_ID` | `amazon.nova-lite-v1:0` | Answer model |
| `RAG_EMBED_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Embedding model |
| `AWS_REGION` | `us-east-1` | Bedrock region |
| `LANGSMITH_API_KEY` | unset | Turns on LangSmith tracing when set |

### Optional: LangSmith tracing

Tracing is off by default. Set a key and runs appear in the LangSmith project `rag-course`. Never commit a key; `.env.example` holds names only.

```bash
export LANGSMITH_API_KEY=your-key
uv run rag ask --source web "What is cloud computing?"
```

## Project layout

```
pyproject.toml          dependencies and the `rag` command
uv.lock                 pinned versions
data/                   Chinook.db, invoice.pdf
notebooks/              the four course notebooks
src/rag_course/         cli, core (settings, Bedrock, numpy store), web, pdf, sql, evaluate, report
tests/                  offline tests and fakes
```

## Run the tests

Tests need no AWS access. A fake answer model and a fake embedding model replace Bedrock, and saved copies of the web pages replace the network.

```bash
uv run pytest
```

Live tests need AWS access. They call real Bedrock and cost a few cents. Run them by hand:

```bash
uv run pytest -m live
```

| Test group | Files | What it checks |
|---|---|---|
| Bedrock wrappers | `test_bedrock.py` | Request shapes, checked with botocore's Stubber |
| CLI and README | `test_cli.py`, `test_readme.py` | Commands, exit codes, and that every README command parses |
| Sources | `test_web.py`, `test_pdf.py`, `test_sql.py` | Chunking, loading and the read-only SQL path |
| Safety and data quality | `test_safety.py`, `test_data_quality.py` | Refusals, destructive questions, empty and odd input |
| Evaluation | `test_eval.py`, `test_golden.py` | Scores, judge settings, cost sums and the golden sets |
| Tracing | `test_tracing.py` | LangSmith stays off without a key |
| Board tooling | `test_github_read.py`, `test_qa_log_check.py` | Helper scripts used by the build board |

## AWS Region

The code defaults to **`us-east-1`**. Both models are called there. To use another region, set `AWS_REGION` and enable the same two models in that region first:

```bash
export AWS_REGION=us-west-2
```

## Cost estimate

Target: stay under $20 in AWS spend. Nothing here bills by the hour, so cost follows the number of questions.

| Item | Price | Note |
|---|---|---|
| Nova Lite input | $0.06 per 1M tokens | On-demand, `us-east-1` |
| Nova Lite output | $0.24 per 1M tokens | On-demand, `us-east-1` |
| Titan Text Embeddings v2 | per input token, very low rate | Used to embed chunks and each question |
| Idle resources | none | No endpoint, instance or database |

Each prompt holds only 3 chunks of 500 characters, so a question stays well under a cent. `rag eval` adds judge-model calls and costs a few cents per run. Check the [Bedrock pricing page](https://aws.amazon.com/bedrock/pricing/) before a large run. Prices change.

**Guardrail (do this once):** create an AWS Budget of $20 with alerts at 50%, 80% and 100%.

1. Open AWS Billing, then Budgets, then Create budget.
2. Choose Cost budget, monthly, amount `20`.
3. Add email alerts at 50%, 80% and 100% of actual spend.

An AWS Budget alerts you. It does not stop spend. Check the Bedrock line in Cost Explorer after any `rag eval` run, since the judge model adds calls.

## Key engineering decisions

| Decision | Reason |
|---|---|
| numpy store, no vector database | No extra service to host or pay for |
| Same defaults as the notebooks | Results compare directly to the course |
| SQL opened read-only, `SELECT` only | A model-written `DROP` or `DELETE` cannot run |
| Fakes at the Bedrock boundary only | Tests check behavior, not call order |
| Tracing from env key only | No key ever sits in code |

## Author

**Marcos Oliveira** — [GitHub](https://github.com/MAOFILHO)
