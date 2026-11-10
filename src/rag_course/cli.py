import re
import sys
from contextlib import contextmanager
from enum import Enum
from importlib.metadata import version as package_version
from pathlib import Path

import typer
from botocore.exceptions import NoCredentialsError, NoRegionError, PartialCredentialsError

import rag_course
from rag_course import pdf as pdf_pipeline
from rag_course import evaluate as evaluation
from rag_course import report
from rag_course import sql
from rag_course.core import SourceError

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


@contextmanager
def _aws_access():
    """Turn a missing AWS login or region into one plain line and exit 2."""
    try:
        yield
    except (NoCredentialsError, PartialCredentialsError, NoRegionError):
        typer.echo("Error: no AWS access found. Run `aws configure`, enable Bedrock model access, then try again.", err=True)
        raise typer.Exit(code=2)


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
    _check_pdf(source, pdf)
    try:
        with _aws_access():
            answer = rag_course.ask(source.value, question, pdf=pdf, db=db)
    except SourceError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2)
    typer.echo(answer)


def _check_pdf(source: Source, pdf: Path | None) -> None:
    if source is Source.pdf:
        path = pdf or pdf_pipeline.DEFAULT_PDF
        if not path.is_file():
            typer.echo(f"Error: PDF not found: {path}", err=True)
            raise typer.Exit(code=2)


@app.command()
def chat(
    source: Source = typer.Option(..., "--source", help="Which Source to chat with."),
    pdf: Path | None = typer.Option(None, "--pdf", help="PDF to ask (default: data/invoice.pdf)."),
    db: Path = typer.Option(sql.DEFAULT_DB, "--db", help="SQLite database for --source sql."),
) -> None:
    """Ask many questions about one Source, loaded once. Type exit or end the input to stop."""
    _check_pdf(source, pdf)
    answer = None
    for line in sys.stdin:
        question = line.strip()
        if question == "exit":
            break
        if not question:
            typer.echo("Type a question, or exit to stop.")
            continue
        try:
            with _aws_access():
                answer = answer or rag_course.open_source(source.value, pdf=pdf, db=db)
                reply = answer(question)
        except SourceError as error:
            typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(code=2)
        typer.echo(reply)


@app.command("eval")
def eval_(
    mode: str = typer.Option("live", "--mode", help="Run label used in the report and baseline file names."),
    out: Path = typer.Option(Path("reports"), "--out", help="Folder for the reports and the baseline."),
    update_baseline: bool = typer.Option(
        False, "--save-baseline", "--update-baseline", help="Save this run's scores as the baseline, replacing any."
    ),
) -> None:
    """Score the golden sets (calls real Bedrock), write CSV and HTML reports, and exit 1 when a threshold fails."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", mode):
        typer.echo("Error: --mode may only hold letters, digits, - and _", err=True)
        raise typer.Exit(code=2)
    with _aws_access():
        scores = evaluation.run_eval()
    typer.echo(evaluation.format_scores(scores))
    reports = report.write_reports(scores, mode, out, update_baseline)
    typer.echo(f"reports: {reports.csv} {reports.html}")
    typer.echo(f"baseline: {'written' if reports.baseline_written else 'compared'} {reports.baseline}")
    for drop in reports.score_drops:
        flag = " REGRESSION" if drop.regressed else ""
        typer.echo(f"score {drop.name}: baseline {drop.before:.2f}, now {drop.now:.2f} ({drop.change:+.2f}){flag}")
    for key in reports.regressions:
        typer.echo(f"regression: {key}")
    failed = evaluation.failures(scores)
    for line in failed:
        typer.echo(f"FAIL: {line}")
    if failed:
        raise typer.Exit(code=1)
    typer.echo("PASS: all thresholds met")
