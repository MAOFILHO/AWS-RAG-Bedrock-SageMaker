# Pre-flight

Checked 2026-11-05 for issues #2 to #10 on board #5.

## Credentials the loop will need

- [✓] Old LangSmith key revoked (owner confirmed 2026-11-05).
- [✓] AWS credentials work (`aws sts get-caller-identity` returned an account).
- [✓] Bedrock lists `amazon.nova-lite-v1:0` and `amazon.titan-embed-text-v2:0` in `us-east-1` (issues #4, #5, #6, #8).

## Tools the loop will need

- [✓] `gh` CLI authenticated as MAOFILHO.
- [✓] `uv` installed (issues #3 and later).
- [✓] `verify_commands` passes the readiness gate (exit 0).

## Environment

- [✓] Base branch `staging` exists.
- [✓] `verify_commands` is `uv sync --frozen && uv run pytest` (changed 2026-11-06 after #3 merged).

## UI cards #82, #76 to #81 (checked 2026-11-10)

- [✓] Node 26.7.0 and npm 12.0.2 installed.
- [✓] GitHub Actions CI runs `uv run pytest` on every PR (card #83).
- [ ] `verify_commands` runs only `uv sync --frozen && uv run pytest`. It does not run the Node and React tests. Owner decision needed before #82 runs.
- [ ] The Python web dependency (likely FastAPI) is new in `pyproject.toml` and `uv.lock`. Owner looks at the dependency list when #82 lands.
