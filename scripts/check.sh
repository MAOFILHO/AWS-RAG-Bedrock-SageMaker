#!/usr/bin/env bash
# One command for all Offline tests (Python, Node API, React) with no AWS access.
set -euo pipefail
cd "$(dirname "$0")/.."
for name in $(env | grep -o '^AWS_[A-Z_]*'); do unset "$name"; done
export AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_EC2_METADATA_DISABLED=true
uv run pytest
npm --prefix web ci --silent
npm --prefix web test
