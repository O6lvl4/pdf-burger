"""Terminal output for pdf-burger."""

from __future__ import annotations

from rich.console import Console

err = Console(stderr=True, highlight=False)

_verbose: bool = False


def set_verbose(v: bool) -> None:
    global _verbose
    _verbose = v


def info(msg: str) -> None:
    err.print(msg)


def verbose(msg: str) -> None:
    if _verbose:
        err.print(f"[dim]{msg}[/dim]")


def warning(msg: str) -> None:
    err.print(f"[yellow]warning:[/yellow] {msg}")


def error(msg: str) -> None:
    err.print(f"[red bold]error:[/red bold] {msg}")


def success(msg: str) -> None:
    err.print(f"[green]{msg}[/green]")
