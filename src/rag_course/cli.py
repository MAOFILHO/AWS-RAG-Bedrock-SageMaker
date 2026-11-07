from enum import Enum
from importlib.metadata import version as package_version
from pathlib import Path

import typer

import rag_course
from rag_course import pdf as pdf_pipeline
from rag_course import sql

app = typer.Typer(help="Ask questions over web pages, a PDF or a SQL database.")


def _show_version(show: bool) -> None:
    if show:
        typer.echo(f"rag {package_version('rag-course')}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_show_version, is_eager=True, help="Show the version and exit."
    ),
) -> None:
    """Ask questions over web pages, a PDF or a SQL database."""


class Source(str, Enum):
    web = "web"
    pdf = "pdf"
    sql = "sql"


@app.command()
def ask(
    question: str,
    source: Source = typer.Option(..., "--source", help="Which Source to ask."),
    pdf: Path | None = typer.Option(None, "--pdf", help="PDF to ask (default: data/invoice.pdf)."),
    db: Path = typer.Option(sql.DEFAULT_DB, "--db", help="SQLite database for --source sql."),
) -> None:
    """Ask a question about one Source."""
    if not question.strip():
        typer.echo("Error: question must not be empty", err=True)
        raise typer.Exit(code=2)
    if source is Source.pdf:
        path = pdf or pdf_pipeline.DEFAULT_PDF
        if not path.is_file():
            typer.echo(f"Error: PDF not found: {path}", err=True)
            raise typer.Exit(code=2)
    typer.echo(rag_course.ask(source.value, question, pdf=pdf, db=db))


@app.command("eval")
def eval_() -> None:
    """Evaluate answers (not built yet)."""
    typer.echo("rag eval: not built yet")
