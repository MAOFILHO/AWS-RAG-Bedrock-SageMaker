from enum import Enum
from pathlib import Path

import typer

import rag_course
from rag_course import sql

app = typer.Typer(help="Ask questions over web pages, a PDF or a SQL database.")


class Source(str, Enum):
    web = "web"
    sql = "sql"


@app.command()
def ask(
    question: str,
    source: Source = typer.Option(..., "--source", help="Which Source to ask."),
    db: Path = typer.Option(sql.DEFAULT_DB, "--db", help="SQLite database for --source sql."),
) -> None:
    """Ask a question about one Source."""
    typer.echo(rag_course.ask(source.value, question, db=db))


@app.command("eval")
def eval_() -> None:
    """Evaluate answers (not built yet)."""
    typer.echo("rag eval: not built yet")
