"""The 8 RAG_4 data-quality cases, plus bad input (empty, oversized, odd encoding): offline, no AWS."""

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner

import rag_course
from rag_course import web
from rag_course.cli import app
from fakes import fake_models, text_pdf

RAG_4_CASES = (
    "test_data_web_pages_load_with_content",
    "test_data_web_junk_chunks_are_under_ten_percent",
    "test_data_web_has_no_duplicate_chunks",
    "test_data_every_web_chunk_carries_its_source",
    "test_data_pdf_has_three_pages_all_with_text",
    "test_data_pdf_chunks_name_their_page",
    "test_data_chinook_has_eleven_tables",
    "test_data_chinook_row_counts_match_the_original",
)

runner = CliRunner()


def test_all_8_rag_4_data_quality_cases_have_a_test():
    source = (Path(__file__).parent / "test_safety.py").read_text()
    defined = {n.name for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
    assert len(RAG_4_CASES) == 8 and set(RAG_4_CASES) <= defined


def ask_pdf_cli(path: Path):
    return runner.invoke(app, ["ask", "--source", "pdf", "--pdf", str(path), "What is a word?"])


def ask_web_cli(monkeypatch, page: str):
    monkeypatch.setattr(web, "fetch_page", lambda url: page)
    return runner.invoke(app, ["ask", "--source", "web", "What is cloud computing?"])


@pytest.fixture(autouse=True)
def offline_models(monkeypatch):
    monkeypatch.setattr(rag_course, "bedrock_models", lambda settings: fake_models())


def assert_clear_error(result, *words):
    assert result.exit_code == 2, result.output
    assert isinstance(result.exception, SystemExit), "a clear error exits, it does not raise"
    lines = result.stderr.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("Error: ")
    assert all(word in lines[0] for word in words)


def test_empty_pdf_file_gets_a_clear_error(tmp_path):
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    assert_clear_error(ask_pdf_cli(empty), "PDF", "empty.pdf")


def test_pdf_with_no_text_gets_a_clear_error(tmp_path):
    blank = tmp_path / "blank.pdf"
    blank.write_bytes(text_pdf([""]))
    assert_clear_error(ask_pdf_cli(blank), "no text", "blank.pdf")


def test_not_a_pdf_gets_a_clear_error(tmp_path):
    junk = tmp_path / "junk.pdf"
    junk.write_bytes(b"this is not a pdf at all")
    assert_clear_error(ask_pdf_cli(junk), "PDF", "junk.pdf")


@pytest.mark.parametrize("page", ["", "   \n\t\n  "], ids=["empty", "blank"])
def test_empty_text_input_gets_a_clear_error(monkeypatch, page):
    assert_clear_error(ask_web_cli(monkeypatch, page), "no text")


def test_oversized_document_gets_a_clean_answer(monkeypatch):
    page = "Cloud computing delivers servers over the internet.\n" * 20_000
    assert len(page) > 1_000_000
    result = ask_web_cli(monkeypatch, page)
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "Cloud computing delivers servers over the internet."


def test_odd_encoding_text_gets_a_clean_answer(monkeypatch):
    page = "Cloud computing café naïve �� \x00 delivers servers over the internet."
    result = ask_web_cli(monkeypatch, page)
    assert result.exit_code == 0, result.output
    assert "Cloud computing" in result.output


def test_pdf_with_accented_text_gets_a_clean_answer(tmp_path):
    accented = tmp_path / "accented.pdf"
    accented.write_bytes(text_pdf(["A caf\xe9 is a word from French."]))
    result = ask_pdf_cli(accented)
    assert result.exit_code == 0, result.output
    assert "word from French" in result.output

