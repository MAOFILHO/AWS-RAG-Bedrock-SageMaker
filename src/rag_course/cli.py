import typer

app = typer.Typer(help="Ask questions over web pages, a PDF or a SQL database.")


@app.command()
def ask() -> None:
    """Ask a question (not built yet)."""
    typer.echo("rag ask: not built yet")


@app.command("eval")
def eval_() -> None:
    """Evaluate answers (not built yet)."""
    typer.echo("rag eval: not built yet")
