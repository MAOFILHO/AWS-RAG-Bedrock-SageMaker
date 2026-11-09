"""The board's gh read helper: --slurp with --jq is rejected up front, never halts."""
import json
import os
import subprocess
import sys
from pathlib import Path

HELPER = Path(__file__).resolve().parents[1] / ".agents/bin/super-board-github-read.py"

FAKE_GH = """#!/bin/sh
echo x >> "$FAKE_GH_LOG"
if [ -n "$FAKE_GH_FAIL" ]; then echo "HTTP 500 server error" >&2; exit 1; fi
echo '[[]]'
"""


def run_helper(tmp_path, *gh_args, fail=False):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "SB_GITHUB_HALT_FILE": str(tmp_path / "github-halt.json"),
        "SB_GITHUB_RETRY_DELAY": "0",
        "FAKE_GH_LOG": str(tmp_path / "gh.log"),
    }
    if fail:
        env["FAKE_GH_FAIL"] = "1"
    result = subprocess.run(
        [sys.executable, str(HELPER), "--kind", "comments", "--", *gh_args],
        capture_output=True, text=True, env=env,
    )
    log = tmp_path / "gh.log"
    calls = len(log.read_text().splitlines()) if log.exists() else 0
    return result, calls, tmp_path / "github-halt.json"


def test_slurp_with_jq_is_rejected_up_front(tmp_path):
    result, calls, halt_file = run_helper(
        tmp_path, "api", "repos/o/r/issues/1/comments", "--paginate", "--slurp", "--jq", "."
    )
    assert result.returncode == 64
    assert calls == 0
    assert not halt_file.exists()
    hints = [line for line in result.stderr.splitlines() if line.strip()]
    assert len(hints) == 1
    assert "rate-limit-etiquette.md" in hints[0]


def test_slurp_with_jq_equals_form_is_rejected(tmp_path):
    result, calls, halt_file = run_helper(
        tmp_path, "api", "repos/o/r/issues/1/comments", "--paginate", "--slurp", "--jq=."
    )
    assert result.returncode == 64
    assert calls == 0
    assert not halt_file.exists()


def test_paginate_alone_proceeds(tmp_path):
    result, calls, halt_file = run_helper(
        tmp_path, "api", "repos/o/r/issues/1/comments", "--paginate", "--slurp"
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == [[]]
    assert calls == 1
    assert not halt_file.exists()


def test_real_github_failure_still_halts_after_three_attempts(tmp_path):
    result, calls, halt_file = run_helper(
        tmp_path, "api", "repos/o/r/issues/1/comments", "--paginate", "--slurp", fail=True
    )
    assert result.returncode == 79
    assert calls == 3
    assert halt_file.exists()
