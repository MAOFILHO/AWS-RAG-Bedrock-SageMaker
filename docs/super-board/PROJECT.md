# Project: AWS-RAG-Bedrock-SageMaker

Course material (K21) on retrieval-augmented generation (RAG) with AWS Bedrock and SageMaker.

## Layout

| Path | What it holds |
|---|---|
| `data/RAG_1_Project.ipynb` | RAG project 1 notebook |
| `data/RAG_2_PDF_Project.ipynb` | RAG over PDF documents |
| `data/RAG_3_SQL_Project.ipynb` | RAG over SQL data |
| `data/RAG_4_Testing_Project.ipynb` | RAG testing project |
| `data/Chinook.db`, `data/Chinook_Sqlite.sql .txt` | Chinook sample SQLite database used by the SQL notebook |
| `data/k21.pdf` | Source PDF used by the PDF notebook |
| `docs/User_Guide.pdf` | User guide |

## Build and checks

No package manifest, no tests, no lint config. The one merge check in `verify_commands`
confirms every `.ipynb` parses as valid JSON.

## Notes

- Base branch: `staging` (merges land here; `main` stays clean).
- Notebooks are JSON; large diffs are normal. Keep one card to one notebook where possible.
- Never commit AWS credentials. Key names only.
