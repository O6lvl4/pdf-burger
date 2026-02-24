"""Terminal output for pdf-burger.

Functional approach: create_console() returns a frozen dataclass with
bound output functions — no mutable global state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from rich.console import Console as RichConsole


@dataclass(frozen=True)
class Console:
    info: Callable[[str], None]
    verbose: Callable[[str], None]
    warning: Callable[[str], None]
    error: Callable[[str], None]
    success: Callable[[str], None]
    rich: RichConsole


def create_console(verbose: bool = False) -> Console:
    """Create an immutable Console with bound output functions."""
    rich = RichConsole(stderr=True, highlight=False)

    return Console(
        info=lambda msg: rich.print(msg),
        verbose=(lambda msg: rich.print(f"[dim]{msg}[/dim]")) if verbose else lambda _: None,
        warning=lambda msg: rich.print(f"[yellow]warning:[/yellow] {msg}"),
        error=lambda msg: rich.print(f"[red bold]error:[/red bold] {msg}"),
        success=lambda msg: rich.print(f"[green]{msg}[/green]"),
        rich=rich,
    )
