"""Command-line interface."""
from __future__ import annotations

import typer

from . import __version__

app = typer.Typer(help="Quality gate for Arabic LLM applications.", no_args_is_help=True)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"qistas {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True, help="Show version."),
) -> None:
    """Qistas CLI."""
