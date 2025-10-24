import typer
from rich import print

from data_store import init_db
from gmail_client import get_labels

app = typer.Typer(help="Gmail ML Client - trainable spam filter and auto sorter")


@app.command()
def init():
    """Initialize local DB and verify Gmail auth."""
    init_db()
    get_labels()
    print("[green]DB ready and Gmail auth OK.[/green]")


if __name__ == "__main__":
    app()
