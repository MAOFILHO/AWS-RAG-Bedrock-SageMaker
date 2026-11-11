"""One command starts the Python service, the Node API and the page; the README says how."""

import os
import re
import stat
import subprocess
from pathlib import Path

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
