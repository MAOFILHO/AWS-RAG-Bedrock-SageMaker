# pr-security-review · PR #55 vs origin/staging · head 0fb20e9

Diff: `src/rag_course/__init__.py` (+30, `open_source` builds one VectorStore and reuses it),
`src/rag_course/cli.py` (+26, `rag chat` reads questions from stdin) and `tests/test_cli.py`
(test-only, excluded by rule 11).
New input: the learner's own stdin lines, the same trust level as the `rag ask` argument.
The sql path still calls `sql.ask`, so `guard_sql` and the read-only connection apply to every
chat question. No new subprocess, file write, deserialization or secret handling.
Putting user text in a model prompt is excluded by rule 14.

Result: 0 findings.
Note: the lane had no sub-agent tool in this session, so the find and false-positive passes ran
inline in the QA worker.
