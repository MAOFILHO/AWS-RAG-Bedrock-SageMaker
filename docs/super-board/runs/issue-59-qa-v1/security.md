# pr-security-review · PR #60 vs staging · head fdc59f4

Result: 0 findings.

- Diff: `src/rag_course/sql.py` (+8 −1), `tests/test_sql.py` (+33).
- `question_asks_for_write` only adds an early `REFUSAL` before the database opens. It narrows what runs; it opens no new path to the database.
- `guard_sql`, the read-only `mode=ro` connection and the SELECT-only rule are unchanged.
- The prompt line change puts no new user content in the prompt (exclusion 14 anyway).
- Finding and false-positive passes ran inline in the QA lane: this host has no sub-task tool.
