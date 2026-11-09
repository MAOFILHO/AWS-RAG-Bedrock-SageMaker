# RAG on AWS Bedrock — Ask Your Documents

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Bedrock-FF9900?logo=amazon-aws&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-6C3FC5)
![Tests](https://img.shields.io/badge/Tests-offline-green)

Ask questions about web pages, a PDF or a SQL database from the terminal. Answers come from Amazon Nova Lite on AWS Bedrock. For web pages and the PDF, the answer is grounded in text retrieved with Titan Text Embeddings v2. For the SQL database, the model writes a read-only query and answers from its rows. When the Source holds no answer, the model says so.

This is a runnable Python port of the RAG course notebooks. The four notebooks stay in `notebooks/` as the course reference.

## Why this is built this way

- **Pay per question, nothing idle.** Bedrock bills per token. No endpoint runs while you sleep.
- **Tests need no AWS.** A fake answer model and a fake embedding model replace Bedrock, so tests are free and fast.
- **No secrets in code.** The AWS CLI credential chain supplies access. `.env` is git-ignored; `.env.example` holds names only.
- **One lock file.** `uv.lock` pins every version, so the same install works on every machine.
- **Notebooks kept.** The 4 originals stay in `notebooks/` as the course reference.

## How answers stay grounded

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

## AWS tools and their role

| AWS tool | Role in this project | Used by the code |
|---|---|---|
| Amazon Bedrock | Runs the answer model (`amazon.nova-lite-v1:0`) and the embedding model (`amazon.titan-embed-text-v2:0`) | Yes |
| AWS IAM | Gives `boto3` permission to call Bedrock | Yes |
| Amazon SageMaker | The original course notebooks ran on a SageMaker notebook instance, which supplied Python and the IAM role | No |

Nothing else is created in your AWS account. No server, database or container is deployed.

## Ask a Source

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

## Chat

`rag chat` loads one Source once and answers many questions. It reads one question per line from the terminal. Type `exit` or end the input to stop.

```bash
uv run rag chat --source pdf
```

## Evaluate

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

## Settings

All optional. The defaults match the notebooks.

| Variable | Default | Purpose |
|---|---|---|
| `RAG_MODEL_ID` | `amazon.nova-lite-v1:0` | Answer model |
| `RAG_EMBED_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Embedding model |
| `AWS_REGION` | `us-east-1` | Bedrock region |
| `LANGSMITH_API_KEY` | unset | Turns on LangSmith tracing when set |

## Optional: LangSmith tracing

Tracing is off by default. Set a key and runs appear in the LangSmith project `rag-course`. Never commit a key; `.env.example` holds names only.

```bash
export LANGSMITH_API_KEY=your-key
uv run rag ask --source web "What is cloud computing?"
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

## Budget: $20 maximum

Target: stay under $20 in AWS spend. The design keeps cost low:

- **Low-cost models.** Nova Lite is among the cheapest Bedrock text models. Titan Embed v2 is priced per token at a very low rate.
- **No always-on resources.** There is no endpoint, instance or database to bill by the hour.
- **Small inputs.** Top-3 chunks of 500 characters keep each prompt short.

Check current prices on the [Bedrock pricing page](https://aws.amazon.com/bedrock/pricing/) before a large run. Prices change.

**Guardrail (do this once):** create an AWS Budget of $20 with alerts at 50%, 80% and 100%.

1. Open AWS Billing, then Budgets, then Create budget.
2. Choose Cost budget, monthly, amount `20`.
3. Add email alerts at 50%, 80% and 100% of actual spend.

An AWS Budget alerts you. It does not stop spend. Check the Bedrock line in Cost Explorer after any `rag eval` run, since the judge model adds calls.

## The notebooks

The four original notebooks in `notebooks/` are the course reference.

| Notebook | Source | In this project |
|---|---|---|
| `RAG_1_Project` | Two IBM web pages | `rag ask --source web` |
| `RAG_2_PDF_Project` | `data/invoice.pdf` | `rag ask --source pdf` |
| `RAG_3_SQL_Project` | `data/Chinook.db` | `rag ask --source sql` |
| `RAG_4_Testing_Project` | Testing and a judge model | `rag eval` |

## Project layout

```
pyproject.toml          dependencies and the `rag` command
uv.lock                 pinned versions
data/                   Chinook.db, invoice.pdf
notebooks/              the four course notebooks
src/rag_course/         cli, core (settings, Bedrock, numpy store), web, pdf, sql, evaluate, report
tests/                  offline tests and fakes
```

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
