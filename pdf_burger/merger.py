"""PDF merge logic using pypdf.

Side effects (file I/O, progress display) are isolated via callbacks.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from pathlib import Path
from typing import Callable

from pypdf import PdfWriter
from rich.console import Console as RichConsole
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)

PROGRESS_THRESHOLD = 5


@dataclass(frozen=True)
class MergeResult:
    output: Path
    file_count: int
    page_count: int


def _append_pdf(writer: PdfWriter, path: Path) -> PdfWriter:
    """Append a single PDF to the writer. Returns the same writer for chaining."""
    writer.append(str(path))
    return writer


def _build_writer(files: list[Path]) -> PdfWriter:
    """Build a PdfWriter by folding over all input files."""
    return reduce(_append_pdf, files, PdfWriter())


def _build_writer_with_progress(
    files: list[Path],
    rich_console: RichConsole,
) -> PdfWriter:
    """Build a PdfWriter with a progress bar for large merges."""
    writer = PdfWriter()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=rich_console,
        transient=True,
    ) as progress:
        task = progress.add_task("merging...", total=len(files))
        for f in files:
            _append_pdf(writer, f)
            progress.update(task, advance=1)
    return writer


def merge_pdfs(
    files: list[Path],
    output: Path,
    on_verbose: Callable[[str], None] = lambda _: None,
    rich_console: RichConsole | None = None,
) -> MergeResult:
    """Merge PDF files and write to output. Returns an immutable MergeResult."""
    if not output.parent.exists():
        on_verbose(f"  creating directory: {output.parent}")
        output.parent.mkdir(parents=True, exist_ok=True)

    if len(files) > PROGRESS_THRESHOLD and rich_console is not None:
        writer = _build_writer_with_progress(files, rich_console)
    else:
        for f in files:
            on_verbose(f"  adding: {f.name}")
        writer = _build_writer(files)

    writer.write(str(output))
    page_count = len(writer.pages)
    writer.close()

    return MergeResult(output=output, file_count=len(files), page_count=page_count)
