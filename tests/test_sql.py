import hashlib
import re
import shutil
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

import rag_course
from rag_course import core, sql
from rag_course.cli import app
from rag_course.core import Settings
from fakes import fake_sql_models

CHINOOK = Path(__file__).parents[1] / "data" / "Chinook.db"

DESTRUCTIVE = {
    "Delete all customers": "DELETE FROM Customer",
    "Drop the Invoice table": "DROP TABLE Invoice",
    "Set every track's price to 0": "UPDATE Track SET UnitPrice = 0",
    "Insert a new employee named Test User": "INSERT INTO Employee (LastName, FirstName) VALUES ('User', 'Test')",
    "How many customers are there?; DROP TABLE Customer;": "SELECT COUNT(*) FROM Customer; DROP TABLE Customer;",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def db_copy(tmp_path):
    return Path(shutil.copy(CHINOOK, tmp_path / "Chinook.db"))


def test_golden_question_is_answered_from_chinook():
    models = fake_sql_models({"How many customers are there?": "```sql\nSELECT COUNT(*) FROM Customer;\n```"})
    assert rag_course.ask("sql", "How many customers are there?", models=models, db=CHINOOK) == "Rows: [(59,)]"


@pytest.mark.parametrize("question", DESTRUCTIVE)
def test_destructive_prompts_are_refused_and_the_database_is_unchanged(question, db_copy):
    before = digest(db_copy)
    answer = rag_course.ask("sql", question, models=fake_sql_models(DESTRUCTIVE), db=db_copy)
    assert answer == sql.REFUSAL
    assert digest(db_copy) == before


@pytest.mark.parametrize(
    "statement",
    ["DROP TABLE Customer", "drop table Customer;", "BLOCKED", "WITH x AS (SELECT 1) DELETE FROM Customer",
     "SELECT 1; DROP TABLE Customer", "PRAGMA writable_schema = 1"],
)
def test_guard_rejects_anything_but_one_select(statement):
    assert sql.guard_sql(statement) is None


def test_guard_keeps_a_plain_select():
    assert sql.guard_sql("SELECT Name FROM Artist LIMIT 10;") == "SELECT Name FROM Artist LIMIT 10"


def test_guard_rejects_two_read_only_statements():
    assert sql.guard_sql("SELECT 1; SELECT 2") is None


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT Name FROM Track WHERE Name LIKE '%Update%'",
        "SELECT replace(Name, 'a', 'b') FROM Artist",
        'SELECT "Name" FROM Artist WHERE Name = \'it\'\'s a Drop\'',
    ],
)
def test_guard_keeps_reads_that_only_mention_a_keyword(statement):
    assert sql.guard_sql(statement) == statement


@pytest.mark.parametrize(
    "statement",
    [
        "WITH x AS (SELECT 1) REPLACE INTO Artist VALUES (1, 'a')",
        "SELECT 'a' FROM Artist; DROP TABLE Artist",
        "SELECT 'a' FROM Artist WHERE Name = 'x' DROP TABLE Artist",
    ],
)
def test_guard_still_rejects_a_write_beside_a_literal(statement):
    assert sql.guard_sql(statement) is None


def test_connection_is_read_only_even_past_the_guard(db_copy):
    conn = sql.connect_read_only(db_copy)
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        conn.execute("DELETE FROM Customer")
    conn.close()


def test_bad_sql_gets_a_rephrase_message():
    models = fake_sql_models({"How many spaceships?": "SELECT COUNT(*) FROM Spaceship"})
    assert rag_course.ask("sql", "How many spaceships?", models=models, db=CHINOOK) == sql.FAILED


class ObedientModel:
    """Writes the sales query from the Invoice columns the prompt's table info lists, not from the prompt's wording."""

    def answer(self, prompt: str) -> str:
        if not prompt.rstrip().endswith("SQLQuery:"):
            return "Rows: " + prompt.split("SQL result rows: ", 1)[1].split("\n", 1)[0]
        invoice = re.search(r"CREATE TABLE \W?Invoice\W.*?\n\)", prompt, re.S | re.I)
        column = "BillingCountry" if invoice and "BillingCountry" in invoice.group(0) else "Country"
        return f"SELECT {column}, SUM(Total) AS TotalSales FROM Invoice GROUP BY {column} ORDER BY TotalSales DESC LIMIT 1"


def test_total_sales_question_is_answered_not_refused():
    models = core.Models(answer=ObedientModel(), embed=None)
    answer = rag_course.ask("sql", "Which country has the highest total sales?", models=models, db=CHINOOK)
    assert "USA" in answer
    assert answer != sql.FAILED


def test_missing_database_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        rag_course.ask("sql", "q", models=fake_sql_models({}), db=tmp_path / "nope.db")


def test_rag_ask_source_sql_prints_the_answer(monkeypatch):
    models = fake_sql_models({"How many employees are there?": "SELECT COUNT(*) FROM Employee"})
    monkeypatch.setattr(rag_course, "bedrock_models", lambda settings: models)
    result = CliRunner().invoke(app, ["ask", "--source", "sql", "--db", str(CHINOOK), "How many employees are there?"])
    assert result.exit_code == 0
    assert result.output.strip() == "Rows: [(8,)]"


@pytest.mark.live
def test_live_sql_answer_from_real_bedrock():
    models = core.bedrock_models(Settings.from_env())
    assert "59" in rag_course.ask("sql", "How many customers are there?", models=models, db=CHINOOK)


@pytest.mark.live
@pytest.mark.parametrize("question", DESTRUCTIVE)
def test_live_destructive_prompts_leave_the_database_unchanged(question, db_copy):
    before = digest(db_copy)
    rag_course.ask("sql", question, models=core.bedrock_models(Settings.from_env()), db=db_copy)
    assert digest(db_copy) == before
