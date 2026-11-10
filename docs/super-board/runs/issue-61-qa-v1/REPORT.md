# QA v1 — issue #61, PR #63 @ 61ca3a9

Env: macOS arm64, `uv sync --frozen`, AWS access stripped (no keys, no `AWS_PROFILE`,
`AWS_CONFIG_FILE` and `AWS_SHARED_CREDENTIALS_FILE` on missing paths,
`AWS_EC2_METADATA_DISABLED=true`). Real botocore, no fakes.

| Command | Exit | stderr lines | Traceback / NoCredentialsError |
|---|---|---|---|
| staging `033a071` `rag ask --source pdf` (before) | 1 | 259 | yes |
| `rag ask --source web` | 2 | 1 | none |
| `rag ask --source pdf` | 2 | 1 | none |
| `rag ask --source sql` | 2 | 1 | none |
| `rag chat --source web` | 2 | 1 | none |
| `rag chat --source pdf` | 2 | 1 | none |
| `rag chat --source sql` | 2 | 1 | none |
| `rag eval` | 2 | 1 | none |

Line: `Error: no AWS access found. Run `aws configure`, enable Bedrock model access, then try again.`

Offline tests: 3 in `tests/test_cli.py` pass. Mutation (drop `NoCredentialsError` from the
catch) turns all 3 red; restored, green. Full suite: 206 passed.

Edge, not in AC: `AWS_PROFILE=does-not-exist` still prints a 191-line traceback ending in
`ProfileNotFound` (exit 1). `edge-bogus-profile.stderr`.

Security: pr-security-review, 0 findings.
