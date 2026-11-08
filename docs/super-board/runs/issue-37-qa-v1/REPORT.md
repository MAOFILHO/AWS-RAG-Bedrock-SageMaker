# QA v1 · issue #37 · PR #39 · head ea6ab3b

Command: `uv sync --frozen && uv run pytest`, run with every AWS env var unset, AWS config pointed at /dev/null and instance metadata disabled. Result: 131 passed, 25 deselected, exit 0 (`pytest.log`).

## AC ledger (unit rung; component and e2e n/a: library retry helper, no UI)
| AC | Test |
|---|---|
| 1 exact waits, fail twice then succeed | `tests/test_bedrock.py:96` asserts `waits == [1.0, 2.0]` |
| 2 None response raises original error | `tests/test_bedrock.py:103` asserts `raised.value is error`, 1 call, no wait |
| 3 existing retry tests | `tests/test_bedrock.py:90`, `:113`, `:122`, `:129` pass |
| 4 pytest with no AWS access | full suite green with no AWS access (`pytest.log`) |

## Mutations (`mutations.log`, never committed to code)
- Revert the None guard at `core.py:102`: AC2 test red.
- Constant wait `sleep(WAIT_SECONDS)`: AC1 test red.

## Test gaps (not written)
- Low: `response={"Error": None}` would still raise `AttributeError` on `.get("Code")`. Not seen from botocore; outside the AC.

Security: `security.md`, 0 findings.
