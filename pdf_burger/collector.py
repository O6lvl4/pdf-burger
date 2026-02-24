"""PDF file collection from paths and directories.

All functions return Result — no exceptions raised.
Warnings are accumulated as data (Writer-like pattern), not as side effects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import partial, reduce
from pathlib import Path

from pypdf import PdfReader

from pdf_burger.monads import Err, Ok, Result, partition_results, safe


@dataclass(frozen=True)
class CollectResult:
    """Immutable collection result carrying both files and warnings."""
    files: tuple[Path, ...]
    warnings: tuple[str, ...]


def natural_sort_key(path: Path) -> list:
    """Sort key for natural ordering (1, 2, 10 instead of 1, 10, 2)."""
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


@safe
def _read_pdf(path: Path) -> Path:
    """Try to read a PDF. Returns Ok(path) or Err(exception)."""
    reader = PdfReader(str(path))
    if len(reader.pages) == 0:
        raise ValueError(f"PDF has no pages: {path}")
    return path


def validate_pdf(path: Path) -> Result[Path, str]:
    """Validate a PDF is readable. Returns Ok(path) or Err(message)."""
    return _read_pdf(path).map_err(lambda e: str(e))


def _resolve_file(raw: str, path: Path) -> Result[CollectResult, str]:
    """Resolve an explicit file path. Errors are fatal (Err)."""
    if path.suffix.lower() != ".pdf":
        return Err(f"not a PDF file: {raw}")
    return validate_pdf(path).map(
        lambda p: CollectResult(files=(p,), warnings=())
    ).map_err(lambda e: f"cannot read PDF: {raw} ({e})")


def _resolve_dir(raw: str, path: Path, recursive: bool) -> Result[CollectResult, str]:
    """Resolve a directory. Corrupt PDFs become warnings, not errors."""
    glob_fn = path.rglob if recursive else path.glob
    pdfs = sorted(
        (p for p in glob_fn("*.[pP][dD][fF]") if p.is_file()),
        key=natural_sort_key,
    )

    if not pdfs:
        return Ok(CollectResult(
            files=(),
            warnings=(f"no PDFs found in directory: {raw}",),
        ))

    validated = list(map(validate_pdf, pdfs))
    valid_paths, errors = partition_results(validated)

    return Ok(CollectResult(
        files=tuple(valid_paths),
        warnings=tuple(errors),
    ))


def _resolve_input(recursive: bool, raw: str) -> Result[CollectResult, str]:
    """Resolve a single CLI input (file or directory) into a CollectResult."""
    path = Path(raw).resolve()
    if not path.exists():
        return Err(f"path not found: {raw}")
    if path.is_file():
        return _resolve_file(raw, path)
    if path.is_dir():
        return _resolve_dir(raw, path, recursive)
    return Err(f"unsupported path type: {raw}")


def _merge_collect_results(a: CollectResult, b: CollectResult) -> CollectResult:
    """Monoid-like merge of two CollectResults."""
    return CollectResult(
        files=(*a.files, *b.files),
        warnings=(*a.warnings, *b.warnings),
    )


_EMPTY = CollectResult(files=(), warnings=())


def collect_pdfs(inputs: list[str], recursive: bool = False) -> Result[CollectResult, str]:
    """Collect PDFs from inputs. Returns Ok(CollectResult) or Err(message).

    Uses fold (reduce) to accumulate results monadically.
    Short-circuits on the first fatal error (explicit file that fails).
    """
    resolve = partial(_resolve_input, recursive)

    def accumulate(
        acc: Result[CollectResult, str],
        raw: str,
    ) -> Result[CollectResult, str]:
        return acc.bind(
            lambda prev: resolve(raw).map(
                lambda curr: _merge_collect_results(prev, curr)
            )
        )

    return reduce(accumulate, inputs, Ok(_EMPTY)).bind(
        lambda cr: Err("no PDF files to merge") if not cr.files else Ok(cr)
    )
