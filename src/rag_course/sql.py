"""SQL Pipeline: the secure Text-to-SQL path from RAG_4 over Chinook, read-only and SELECT-only."""

import re
import sqlite3
from pathlib import Path

from rag_course.core import Models

DEFAULT_DB = Path("data/Chinook.db")

REFUSAL = "I can only answer read-only questions about the database."
FAILED = "I couldn't answer that from the database. Please rephrase your question."

SQL_PROMPT = """You are a SQLite expert who writes READ-ONLY queries.
Rules:
- Write exactly ONE SELECT statement. Never write INSERT, UPDATE, DELETE, DROP, ALTER or CREATE.
- If the request asks to change, add or delete data, output exactly: BLOCKED
- Return ONLY the raw SQL query with NO markdown, NO backticks, NO explanation.
- Do NOT write SELECT * — only select relevant columns.
- Use ONLY table and column names that appear in the table info, spelled exactly. Invoice has BillingCountry, not Country; Customer has Country.
- When the question asks "which" or "who", return names, not IDs.
- Use LIMIT 10 unless the question asks for a specific number or for "all".

Table info:
{table_info}

Question: {question}
SQLQuery:"""

ANSWER_PROMPT = """Question: {question}
SQL result rows: {rows}
Answer the question in one or two plain sentences using ONLY these rows. Do not show SQL."""

WRITE_SQL = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX)\b|\bREPLACE\b(?!\s*\()",
    re.I,
)
QUOTED = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"")


def clean_sql(text: str) -> str:
    text = re.sub(r"```(?:sql)?", "", text, flags=re.I).split("SQLResult")[0]
    return re.sub(r"^\s*SQLQuery:\s*", "", text, flags=re.I).strip()


def guard_sql(sql: str) -> str | None:
    """Return the statement if it is one read-only SELECT, else None. Model SQL is never trusted."""
    statement = sql.strip().rstrip(";").strip()
    if (
        ";" in statement
        or not statement.upper().startswith(("SELECT", "WITH"))
        or WRITE_SQL.search(QUOTED.sub("''", statement))
    ):
        return None
    return statement


def connect_read_only(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(db).resolve()}?mode=ro", uri=True)


def table_info(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND sql IS NOT NULL")
    return "\n\n".join(sql for (sql,) in rows)


def ask(question: str, models: Models, db: Path = DEFAULT_DB) -> str:
    if not Path(db).is_file():
        raise FileNotFoundError(f"database not found: {db}")
    conn = connect_read_only(db)
    try:
        prompt = SQL_PROMPT.format(table_info=table_info(conn), question=question)
        rows = None
        for _ in range(2):
            sql = guard_sql(clean_sql(models.answer.answer(prompt)))
            if sql is None:
                return REFUSAL
            try:
                rows = conn.execute(sql).fetchall()
                break
            except sqlite3.Error as error:
                prompt += f" {sql}\nSQLError: {error}\nFix the error and write the corrected query.\nSQLQuery:"
        if rows is None:
            return FAILED
    finally:
        conn.close()
    return models.answer.answer(ANSWER_PROMPT.format(question=question, rows=rows[:50])).strip()
