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


def test_workflow_uses_no_secrets_or_stored_aws_keys():
    assert "secrets." not in WORKFLOW
    assert "AWS_" not in WORKFLOW


def test_only_the_eval_job_gets_aws_access_and_only_on_push():
    offline = WORKFLOW.replace(_job("eval"), "")
    assert "configure-aws-credentials" not in offline
    assert "id-token" not in offline
    eval_job = _job("eval")
    assert "if: github.event_name == 'push'" in eval_job
    assert "role-to-assume: arn:aws:iam::759316130780:role/rag-eval-ci" in eval_job


def test_workflow_sets_read_only_contents_permission():
    assert re.search(r"permissions:\s*\n\s+contents: read\b", WORKFLOW)


def test_readme_shows_the_ci_badge():
    assert "actions/workflows/ci.yml/badge.svg" in README.split("\n## ")[0]


def _job(name):
    """The text of one top-level job, up to the next job."""
    match = re.search(rf"\n  {name}:\n(.*?)(?=\n  \S|\Z)", WORKFLOW, re.S)
    assert match, f"no {name} job"
    return match.group(1)


def test_python_job_keeps_its_check_name_and_steps():
    tests = _job("tests")
    assert "uv sync --frozen" in tests
    assert "uv run pytest" in tests
    assert "npm" not in tests


def test_web_job_runs_npm_ci_test_and_build_in_web():
    web = _job("web")
    assert re.search(r"working-directory: web\n", web)
    steps = re.findall(r"- run: (.+)", web)
    assert steps == ["npm ci", "npm test", "npm run build"]


def test_web_job_installs_node_from_the_web_lock_file():
    web = _job("web")
    assert "actions/setup-node@" in web
    assert "cache-dependency-path: web/package-lock.json" in web
