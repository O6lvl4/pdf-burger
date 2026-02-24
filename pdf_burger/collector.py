"""PDF file collection from paths and directories.

Pure functions for resolving inputs into a flat list of validated PDF paths.
"""

from __future__ import annotations

import re
from functools import reduce
from pathlib import Path
from typing import Callable

from pypdf import PdfReader


def natural_sort_key(path: Path) -> list:
    """Sort key for natural ordering (1, 2, 10 instead of 1, 10, 2)."""
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def validate_pdf(path: Path) -> Path | ValueError:
    """Validate a PDF is readable. Returns the path or a ValueError."""
    try:
        reader = PdfReader(str(path))
        return ValueError(f"PDF has no pages: {path}") if len(reader.pages) == 0 else path
    except ValueError as e:
        return e
    except Exception as e:
        return ValueError(f"cannot read PDF: {path} ({e})")


def _resolve_file(raw: str, path: Path) -> list[Path]:
    """Resolve a single file input — raises on invalid."""
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"not a PDF file: {raw}")
    result = validate_pdf(path)
    if isinstance(result, ValueError):
        raise result
    return [result]


def _resolve_dir(
    raw: str,
    path: Path,
    recursive: bool,
    on_warning: Callable[[str], None],
) -> list[Path]:
    """Resolve a directory input — skips corrupt files with warning."""
    glob_fn = path.rglob if recursive else path.glob
    pdfs = sorted(
        (p for p in glob_fn("*.[pP][dD][fF]") if p.is_file()),
        key=natural_sort_key,
    )
    if not pdfs:
        on_warning(f"no PDFs found in directory: {raw}")
        return []
    validated = map(lambda p: (p, validate_pdf(p)), pdfs)
    return list(reduce(
        lambda acc, pair: (
            acc if isinstance(pair[1], ValueError) and not on_warning(str(pair[1])) else
            [*acc, pair[0]] if not isinstance(pair[1], ValueError) else acc
        ),
        validated,
        [],
    ))


def _resolve_input(
    raw: str,
    recursive: bool,
    on_warning: Callable[[str], None],
) -> list[Path]:
    """Resolve a single input (file or directory) into PDF paths."""
    path = Path(raw).resolve()
    if not path.exists():
        raise FileNotFoundError(f"path not found: {raw}")
    if path.is_file():
        return _resolve_file(raw, path)
    if path.is_dir():
        return _resolve_dir(raw, path, recursive, on_warning)
    return []


def collect_pdfs(
    inputs: list[str],
    recursive: bool = False,
    on_warning: Callable[[str], None] = lambda _: None,
) -> list[Path]:
    """Collect PDF files from file paths and directories.

    Pure in structure: side effects (warnings) are delegated to the
    on_warning callback injected by the caller.
    """
    files = reduce(
        lambda acc, raw: [*acc, *_resolve_input(raw, recursive, on_warning)],
        inputs,
        [],
    )
    if not files:
        raise ValueError("no PDF files to merge")
    return files
