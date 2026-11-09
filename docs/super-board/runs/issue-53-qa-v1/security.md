# pr-security-review · PR #57 vs origin/staging · head 81102ab

Diff: `src/rag_course/report.py` (+47/-5, saves the six scores in the baseline JSON and compares
them on the next run), `src/rag_course/cli.py` (+6/-1, a `--save-baseline` alias and one
`score <name>: ...` line per score) and `tests/test_eval.py` (+41, test-only, excluded by rule 11).
The baseline is read with `json.loads` (no pickle or YAML). Its path is `<--out>/baseline_<mode>.json`;
`--mode` is still limited to `[A-Za-z0-9_-]+` and `--out` is a CLI flag (precedent 3).
Score drops go to stdout only; the HTML report does not render them, so no new markup path.
No new subprocess call, network call, secret or user-data handling.

Result: 0 findings.
Note: the lane had no sub-agent tool in this session, so the find and false-positive passes ran
inline in the QA worker.
