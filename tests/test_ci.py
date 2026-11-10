"""CI runs the Offline tests only, with no secrets and read-only repo access."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/ci.yml").read_text()
README = (ROOT / "README.md").read_text()


def test_workflow_runs_on_prs_and_staging_pushes():
    assert re.search(r"pull_request:\s*\n\s+branches: \[staging, main\]", WORKFLOW)
    assert re.search(r"push:\s*\n\s+branches: \[staging\]", WORKFLOW)


def test_workflow_installs_with_the_lock_file_and_runs_the_offline_tests():
    assert "uv sync --frozen" in WORKFLOW
    assert "uv run pytest\n" in WORKFLOW


def test_workflow_never_runs_the_live_tests():
    assert "-m live" not in WORKFLOW
    assert "live" not in re.sub(r"#.*", "", WORKFLOW).lower()


def test_workflow_uses_no_secrets_or_aws_credentials():
    assert "secrets." not in WORKFLOW
    assert "AWS_" not in WORKFLOW
    assert "configure-aws-credentials" not in WORKFLOW


def test_workflow_sets_read_only_contents_permission():
    assert re.search(r"permissions:\s*\n\s+contents: read\b", WORKFLOW)


def test_readme_shows_the_ci_badge():
    assert "actions/workflows/ci.yml/badge.svg" in README.split("\n## ")[0]
