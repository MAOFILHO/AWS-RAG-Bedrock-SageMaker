# RAG on AWS Bedrock

Ask questions about web pages, a PDF or a SQL database from the terminal. Answers come from Amazon Nova Lite on AWS Bedrock, grounded in text retrieved with Titan Text Embeddings v2. When the retrieved text holds no answer, the model says so.

This is a runnable Python port of the RAG course notebooks. The four notebooks stay in `notebooks/` as the course reference.

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
