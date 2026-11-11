"""Live parity check: the page's path and `rag ask` give the same answer. Run by hand: `uv run pytest -m live`."""

import json
import os
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
QUESTION = "How many customers are there?"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url: str):
    with urllib.request.urlopen(url, timeout=5) as reply:
        return json.load(reply)


@pytest.mark.live
def test_ui_path_and_cli_give_the_same_answer():
    ports = {"RAG_SERVICE_PORT": _free_port(), "RAG_API_PORT": _free_port(), "RAG_UI_PORT": _free_port()}
    env = {**os.environ, **{name: str(port) for name, port in ports.items()}}
    start = subprocess.Popen(["bash", str(ROOT / "scripts" / "start.sh")], cwd=ROOT, env=env, start_new_session=True)
    ui = f"http://localhost:{ports['RAG_UI_PORT']}"
    try:
        deadline = time.time() + 180
        while True:
            try:
                _get(f"{ui}/api/sources")
                break
            except OSError:
                assert time.time() < deadline and start.poll() is None, "the app did not start"
                time.sleep(1)
        request = urllib.request.Request(
            f"{ui}/api/ask",
            data=json.dumps({"question": QUESTION, "source": "sql"}).encode(),
            headers={"content-type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=120) as reply:
            via_ui = json.load(reply)["answer"]
    finally:
        os.killpg(start.pid, signal.SIGTERM)
        start.wait(timeout=30)
    via_cli = subprocess.run(
        ["uv", "run", "rag", "ask", "--source", "sql", QUESTION], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    print(f"UI:  {via_ui}\nCLI: {via_cli}")
    assert via_ui.strip() == via_cli
