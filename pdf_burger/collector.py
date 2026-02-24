"""PDF file collection from paths and directories."""

from __future__ import annotations

import re
from pathlib import Path

from pdf_burger import console


def natural_sort_key(path: Path) -> list:
    """Sort key for natural ordering (1, 2, 10 instead of 1, 10, 2)."""
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _validate_pdf(path: Path) -> None:
    """Quick validation that a file is a readable PDF."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        if len(reader.pages) == 0:
            raise ValueError(f"PDF has no pages: {path}")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"cannot read PDF: {path} ({e})")


def collect_pdfs(inputs: list[str], recursive: bool = False) -> list[Path]:
    """Collect PDF files from file paths and directories.

    Files are returned in input order. PDFs within a directory are sorted
    in natural order. Corrupt PDFs in directories are skipped with a warning;
    explicitly specified corrupt PDFs cause an error.
    """
    result: list[Path] = []

    for raw in inputs:
        path = Path(raw).resolve()

        if not path.exists():
            raise FileNotFoundError(f"path not found: {raw}")

        if path.is_file():
            if path.suffix.lower() != ".pdf":
                raise ValueError(f"not a PDF file: {raw}")
            _validate_pdf(path)
            result.append(path)

        elif path.is_dir():
            glob_fn = path.rglob if recursive else path.glob
            pdfs = sorted(
                (p for p in glob_fn("*.[pP][dD][fF]") if p.is_file()),
                key=natural_sort_key,
            )
            if not pdfs:
                console.warning(f"no PDFs found in directory: {raw}")
            for pdf in pdfs:
                try:
                    _validate_pdf(pdf)
                    result.append(pdf)
                except ValueError as e:
                    console.warning(str(e))

    if len(result) < 1:
        raise ValueError("no PDF files to merge")

    return result
