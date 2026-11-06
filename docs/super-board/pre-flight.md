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
- [ ] `verify_commands` is notebook-JSON only. Change it to `uv sync --frozen && uv run pytest` when #3 merges. Orchestrator action.
