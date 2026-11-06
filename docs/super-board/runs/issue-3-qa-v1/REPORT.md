# QA v1 issue 3 @ cf5c061
$ uv sync --frozen && uv run pytest -q
Checked 12 packages in 1ms
..                                                                       [100%]
2 passed in 0.04s
$ uv run rag --help (commands)
│ ask   Ask a question (not built yet).                                        │
│ eval  Evaluate answers (not built yet).                                      │
$ ls notebooks data
data:
Chinook_Sqlite.sql .txt
Chinook.db
invoice.pdf

notebooks:
RAG_1_Project.ipynb
RAG_2_PDF_Project.ipynb
RAG_3_SQL_Project.ipynb
RAG_4_Testing_Project.ipynb
$ notebooks renamed 100%, unchanged
 rename {data => notebooks}/RAG_1_Project.ipynb (100%)
 rename {data => notebooks}/RAG_2_PDF_Project.ipynb (100%)
 rename {data => notebooks}/RAG_3_SQL_Project.ipynb (100%)
 rename {data => notebooks}/RAG_4_Testing_Project.ipynb (100%)
pr-security-review: 0 findings
