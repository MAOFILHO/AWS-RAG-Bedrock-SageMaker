"""One command starts the Python service, the Node API and the page; the README says how."""

import os
import re
import signal
import stat
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
START = ROOT / "scripts" / "start.sh"
README = (ROOT / "README.md").read_text()


def test_start_script_is_executable_and_valid_bash():
    assert START.stat().st_mode & stat.S_IXUSR
    subprocess.run(["bash", "-n", str(START)], check=True)


def _run_with_fake_tools(tmp_path, env=None):
    """Run start.sh with `uv` and `npm` replaced by scripts that log their arguments and exit."""
    log = tmp_path / "calls.log"
    for tool in ("uv", "npm"):
        fake = tmp_path / tool
        fake.write_text(f'#!/usr/bin/env bash\necho "{tool} $* | PORT=${{PORT:-}} SERVICE_URL=${{SERVICE_URL:-}} RAG_API_PORT=${{RAG_API_PORT:-}}" >> "{log}"\n')
        fake.chmod(0o755)
    run_env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    for name in ("RAG_SERVICE_PORT", "RAG_API_PORT", "RAG_UI_PORT"):
        run_env.pop(name, None)
    run_env.update(env or {})
    result = subprocess.run(["bash", str(START)], env=run_env, capture_output=True, text=True, timeout=60)
    return result, log.read_text()


def test_start_runs_the_three_parts_on_the_default_ports(tmp_path):
    result, calls = _run_with_fake_tools(tmp_path)
    assert "uv run uvicorn rag_course.service:create_app --factory --port 8000" in calls
    assert "npm --prefix web run api | PORT=3001 SERVICE_URL=http://127.0.0.1:8000" in calls
    assert re.search(r"npm --prefix web run dev -- --port 5173 --strictPort \|.*RAG_API_PORT=3001", calls)
    assert "http://localhost:5173" in result.stdout


def test_start_ports_come_from_settings(tmp_path):
    env = {"RAG_SERVICE_PORT": "9000", "RAG_API_PORT": "9001", "RAG_UI_PORT": "9002"}
    _, calls = _run_with_fake_tools(tmp_path, env)
    assert "--port 9000" in calls
    assert "PORT=9001 SERVICE_URL=http://127.0.0.1:9000" in calls
    assert "--port 9002 --strictPort" in calls and "RAG_API_PORT=9001" in calls


def test_start_stops_the_other_parts_when_one_exits(tmp_path):
    """The service fails at once; start.sh must return and stop the API and the page."""
    pids = tmp_path / "pids"
    (tmp_path / "uv").write_text("#!/usr/bin/env bash\nexit 1\n")
    (tmp_path / "npm").write_text(f'#!/usr/bin/env bash\n[[ "$*" == *" run "* ]] || exit 0\necho $$ >> "{pids}"\nexec sleep 60\n')
    for tool in ("uv", "npm"):
        (tmp_path / tool).chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    subprocess.run(["bash", str(START)], env=env, capture_output=True, timeout=20)
    time.sleep(0.5)
    started = [int(pid) for pid in pids.read_text().split()]
    assert len(started) == 2
    for pid in started:
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def _fake_tools_one_part_dies(tmp_path, dying_exit):
    """`uv` (the service) exits with `dying_exit` after a moment; `npm` runs (the API and the page) stay up."""
    (tmp_path / "uv").write_text(f"#!/usr/bin/env bash\nsleep 1\nexit {dying_exit}\n")
    (tmp_path / "npm").write_text('#!/usr/bin/env bash\n[[ "$*" == *" run "* ]] || exit 0\nexec sleep 60\n')
    for tool in ("uv", "npm"):
        (tmp_path / tool).chmod(0o755)
    return {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}


def test_start_exits_with_the_code_of_the_part_that_died(tmp_path):
    env = _fake_tools_one_part_dies(tmp_path, 3)
    result = subprocess.run(["bash", str(START)], env=env, capture_output=True, timeout=20)
    assert result.returncode == 3


def test_start_exits_non_zero_when_a_part_exits_cleanly_on_its_own(tmp_path):
    env = _fake_tools_one_part_dies(tmp_path, 0)
    result = subprocess.run(["bash", str(START)], env=env, capture_output=True, timeout=20)
    assert result.returncode != 0


def test_start_exits_zero_on_ctrl_c_and_stops_every_part(tmp_path):
    pids = tmp_path / "pids"
    (tmp_path / "uv").write_text(f'#!/usr/bin/env bash\necho $$ >> "{pids}"\nexec sleep 60\n')
    (tmp_path / "npm").write_text(f'#!/usr/bin/env bash\n[[ "$*" == *" run "* ]] || exit 0\necho $$ >> "{pids}"\nexec sleep 60\n')
    for tool in ("uv", "npm"):
        (tmp_path / tool).chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    proc = subprocess.Popen(["bash", str(START)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 15
    while time.time() < deadline and (not pids.exists() or len(pids.read_text().split()) < 3):
        time.sleep(0.1)
    started = [int(pid) for pid in pids.read_text().split()]
    assert len(started) == 3
    proc.send_signal(signal.SIGINT)
    assert proc.wait(timeout=15) == 0
    time.sleep(0.5)
    for pid in started:
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def test_page_proxy_follows_the_api_port_setting():
    config = (ROOT / "web" / "vite.config.ts").read_text()
    assert "process.env.RAG_API_PORT" in config


def test_readme_names_the_start_command_ports_settings_and_upload_cost():
    running = re.search(r"^### Ask from the browser\n(.*?)(?=^### )", README, re.M | re.S).group(1)
    assert "scripts/start.sh" in running
    for port in ("8000", "3001", "5173"):
        assert port in running
    assert "upload" in running and "Titan" in running and "cost" in running
    for setting in ("RAG_SERVICE_PORT", "RAG_API_PORT", "RAG_UI_PORT"):
        assert f"`{setting}`" in README
