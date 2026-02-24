"""PDF merge logic using pypdf."""

from pathlib import Path

from pypdf import PdfWriter

from pdf_burger.logger import logger


def merge_pdfs(files: list[Path], output: Path) -> None:
    """Merge multiple PDF files into a single output file."""
    writer = PdfWriter()

    for f in files:
        logger.debug("追加: %s", f)
        writer.append(str(f))

    writer.write(str(output))
    writer.close()

    logger.info("%d 個のPDFを結合しました -> %s", len(files), output)
