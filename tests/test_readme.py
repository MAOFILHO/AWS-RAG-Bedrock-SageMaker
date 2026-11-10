"""The README stays true: short setup, AWS tools table, test notes, and every `rag` command parses."""

import re
import shlex
from pathlib import Path

import pytest
import typer

from rag_course.cli import app

README = (Path(__file__).resolve().parents[1] / "README.md").read_text()


def _section(title: str) -> str:
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", README, re.M | re.S)
    assert match, f"README has no '## {title}' section"
    return match.group(1)


def _rag_commands() -> list[list[str]]:
    lines = [line.strip() for line in README.splitlines() if line.strip().startswith("uv run rag ")]
    return [shlex.split(line)[3:] for line in lines]


SECTION_ORDER = [
    "Why this is built this way",
    "RAG architecture",
    "Problem and Solution",
    "Results",
    "Architecture",
    "The four notebooks",
    "Tech Stack",
    "AWS tools and their role",
    "Prerequisites",
    "Setup",
    "Running the project",
    "Project layout",
    "Run the tests",
    "AWS Region",
    "Cost estimate",
    "Key engineering decisions",
    "Author",
]


def test_readme_sections_follow_the_template_order():
    """Title and intro come first as the `#` heading; the other 17 sections are `##` headings in this order."""
    prose = re.sub(r"^```.*?^```", "", README, flags=re.M | re.S)
    assert README.startswith("# ")
    assert len(re.findall(r"^# ", prose, re.M)) == 1
    assert re.findall(r"^## (.+)$", prose, re.M) == SECTION_ORDER


def test_setup_stays_at_6_steps():
    setup = _section("Setup")
    assert "Setup takes 6 steps." in setup
    assert re.findall(r"^(\d+)\. ", setup, re.M) == ["1", "2", "3", "4", "5", "6"]


def test_aws_tools_table_lists_each_tool_and_marks_sagemaker_not_used():
    rows = {
        cells[0]: cells[2]
        for line in _section("AWS tools and their role").splitlines()
        if line.startswith("| ") and len(cells := [c.strip() for c in line.strip("|").split("|")]) == 3
    }
    assert rows["Amazon Bedrock"] == "Yes"
    assert rows["AWS IAM"] == "Yes"
    assert rows["Amazon SageMaker"] == "No"


def test_readme_says_tests_need_no_aws_and_live_tests_do():
    tests = _section("Run the tests")
    assert "Tests need no AWS access." in tests
    assert "Live tests need AWS access." in tests
    assert "uv run pytest -m live" in tests


def test_readme_documents_ask_chat_and_eval():
    names = {args[0] for args in _rag_commands()}
    assert names == {"ask", "chat", "eval"}


@pytest.mark.parametrize("args", _rag_commands(), ids=lambda args: " ".join(args))
def test_each_rag_command_in_readme_parses(args):
    """Parse each command with the real CLI, without running it, so no Bedrock call is made."""
    group = typer.main.get_command(app)
    args = ["data/k21.pdf" if arg == "path/to/file.pdf" else arg for arg in args]
    parent = typer.Context(group, info_name="rag")
    command = group.get_command(parent, args[0])
    assert command is not None, f"no rag command {args[0]!r}"
    command.make_context(args[0], args[1:], parent=parent)
