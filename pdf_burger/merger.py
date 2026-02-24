"""PDF merge logic using pypdf."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)

from pdf_burger import console

_PROGRESS_THRESHOLD = 5


def merge_pdfs(files: list[Path], output: Path) -> None:
    """Merge multiple PDF files into a single output file."""
    if not output.parent.exists():
        console.verbose(f"  ディレクトリを作成: {output.parent}")
        output.parent.mkdir(parents=True, exist_ok=True)

    writer = PdfWriter()

    if len(files) > _PROGRESS_THRESHOLD:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console.err,
            transient=True,
        ) as progress:
            task = progress.add_task("結合中...", total=len(files))
            for f in files:
                writer.append(str(f))
                progress.update(task, advance=1)
    else:
        for f in files:
            console.verbose(f"  追加: {f.name}")
            writer.append(str(f))

    writer.write(str(output))
    page_count = len(writer.pages)
    writer.close()

    console.success(
        f"{len(files)} 個のPDF ({page_count} ページ) を結合しました -> {output.name}"
    )
    console.verbose(f"  出力先: {output}")
