"""PDF file collection from paths and directories."""

import re
from pathlib import Path

from pdf_burger.logger import logger


def natural_sort_key(path: Path) -> list:
    """Sort key for natural ordering (1, 2, 10 instead of 1, 10, 2)."""
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def collect_pdfs(inputs: list[str], recursive: bool = False) -> list[Path]:
    """Collect PDF files from file paths and directories.

    Files are returned in input order. PDFs within a directory are sorted
    in natural order.
    """
    result: list[Path] = []

    for raw in inputs:
        path = Path(raw).resolve()

        if not path.exists():
            raise FileNotFoundError(f"パスが見つかりません: {raw}")

        if path.is_file():
            if path.suffix.lower() != ".pdf":
                raise ValueError(f"PDFファイルではありません: {raw}")
            result.append(path)

        elif path.is_dir():
            glob_fn = path.rglob if recursive else path.glob
            pdfs = sorted(
                (p for p in glob_fn("*.[pP][dD][fF]") if p.is_file()),
                key=natural_sort_key,
            )
            if not pdfs:
                logger.warning("ディレクトリにPDFがありません: %s", raw)
            result.extend(pdfs)

    if len(result) < 1:
        raise ValueError("結合するPDFファイルが見つかりません")

    return result
