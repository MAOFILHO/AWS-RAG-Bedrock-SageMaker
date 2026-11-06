from enum import Enum

import typer

import rag_course

app = typer.Typer(help="Ask questions over web pages, a PDF or a SQL database.")


class Source(str, Enum):
    web = "web"


@app.command()
def ask(
    question: str,
    source: Source = typer.Option(..., "--source", help="Which Source to ask."),
) -> None:
    """Ask a question about one Source."""
    typer.echo(rag_course.ask(source.value, question))


@app.command("eval")
def eval_() -> None:
    """Evaluate answers (not built yet)."""
    typer.echo("rag eval: not built yet")
