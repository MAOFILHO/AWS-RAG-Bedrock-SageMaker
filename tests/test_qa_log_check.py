import importlib.util
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / ".agents" / "bin" / "super-board-qa-log-check.py"
spec = importlib.util.spec_from_file_location("qa_log_check", SCRIPT)
qa_log_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa_log_check)


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def repo_with_added(tmp_path, files):
    git(tmp_path, "init", "-q", "-b", "base")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "README.md").write_text("x")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    git(tmp_path, "checkout", "-qb", "pr")
    for name in files:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "pr")
    return tmp_path


def run(repo):
    return qa_log_check.main(["--repo", str(repo), "--base", "base", "--head", "pr"])


def test_added_log_fails_and_names_file(tmp_path, capsys):
    repo = repo_with_added(tmp_path, ["pytest.log"])
    assert run(repo) == 1
    out = capsys.readouterr().out
    assert "pytest.log" in out
    assert "remove" in out.lower()


def test_log_under_runs_dir_passes(tmp_path, capsys):
    repo = repo_with_added(tmp_path, ["docs/super-board/runs/r1/evidence.md"])
    assert run(repo) == 0


def test_log_inside_runs_dir_passes(tmp_path):
    repo = repo_with_added(tmp_path, ["docs/super-board/runs/r1/pytest.log"])
    assert run(repo) == 0


def test_nested_log_outside_runs_dir_fails(tmp_path, capsys):
    repo = repo_with_added(tmp_path, ["src/deep/qa.log", "src/ok.py"])
    assert run(repo) == 1
    assert "src/deep/qa.log" in capsys.readouterr().out


def test_diff_without_logs_passes(tmp_path):
    repo = repo_with_added(tmp_path, ["src/ok.py"])
    assert run(repo) == 0
