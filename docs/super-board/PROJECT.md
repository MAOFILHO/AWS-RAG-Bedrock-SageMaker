# Project: AWS-Bedrock-RAG-Eval

Course material on retrieval-augmented generation (RAG) with AWS Bedrock and SageMaker.

## Layout

| Path | What it holds |
|---|---|
| `notebooks/RAG_1_Project.ipynb` | RAG project 1 notebook |
| `notebooks/RAG_2_PDF_Project.ipynb` | RAG over PDF documents |
| `notebooks/RAG_3_SQL_Project.ipynb` | RAG over SQL data |
| `notebooks/RAG_4_Testing_Project.ipynb` | RAG testing project |
| `data/Chinook.db`, `data/Chinook_Sqlite.sql .txt` | Chinook sample SQLite database used by the SQL notebook |
| `data/invoice.pdf` | Source PDF used by the PDF notebook |
| `docs/User_Guide.pdf` | User guide |

## Build and checks

Python 3.12 project managed by `uv`: `uv sync --frozen && uv run pytest`; CLI `uv run rag --help`. The one merge check in `verify_commands`
confirms every `.ipynb` parses as valid JSON.

## Notes

- Base branch: `staging` (merges land here; `main` stays clean).
- Notebooks are JSON; large diffs are normal. Keep one card to one notebook where possible.
- Never commit AWS credentials. Key names only.
