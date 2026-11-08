# pr-security-review · PR #39 · head ea6ab3b · base staging

Diff: `src/rag_course/core.py` (1 line, retry error-code read) and `tests/test_bedrock.py` (tests only, hard exclusion 11).

The core change reads `error.response` with `or {}`. No user input reaches it, it opens no new I/O, and the original exception is re-raised unchanged.

Findings: 0
