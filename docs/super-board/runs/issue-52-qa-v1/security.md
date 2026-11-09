# pr-security-review · PR #56 vs origin/staging · head 96c989b

Diff: `src/rag_course/core.py` (+6, a `SourceError` class and an empty-chunks check),
`src/rag_course/pdf.py` (+10/-3, wraps `PdfReader` in a `PyPdfError` catch and checks for no text),
`src/rag_course/cli.py` (+7/-1, prints `Error: <reason>` to stderr and exits 2) and
`tests/test_data_quality.py` (+100, test-only, excluded by rule 11).
No new input source, subprocess call, file write, deserialization or secret handling.
The error line names only the PDF path the caller passed on the CLI (precedent 3).

Result: 0 findings.
Note: the lane had no sub-agent tool in this session, so the find and false-positive passes ran
inline in the QA worker.
