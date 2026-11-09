# QA v1 · issue #59 · PR #60 · head fdc59f4

| AC | Proof |
|---|---|
| 1 stub writes only SELECT, stacked question gets REFUSAL | `tests/test_sql.py:65` passes; red when the check is removed (`mutants.txt`) |
| 2 model never called | `tests/test_sql.py:70` asserts `model.calls == 0`; red when the check moves after the model call |
| 3 `Which tracks have Drop in the name?` answered | `tests/test_sql.py:76` passes; red when the `;` split is dropped |
| 4 4 other destructive cases refused | `tests/test_sql.py:42` 4 cases pass, DB digest unchanged; live eval rows PASS (`rag-eval-safety-rows.csv`) |
| 5 live `uv run rag eval` prints `safety: 1.00` | `rag-eval-live.txt`: safety 1.00, overall 1.00, exit 0 |
| 6 `uv run pytest` passes with no AWS | `pytest-no-aws.txt`: 203 passed, AWS env and config cleared |

## Test gaps (not written)
- Medium: surviving mutant `return ";" in question` (refuse any `;`). Witness: `How many customers?; and how many invoices?` should be answered. No test pins it.
- Low: lowercase stacked write `...?; drop table Customer` not pinned (`WRITE_SQL` is `re.I`, so it works today).
- Low: a `;` then a write word in a read question (`Tracks; named Drop`) is refused. Accepted by the issue's Fix.

Security: `security.md`, 0 findings.
