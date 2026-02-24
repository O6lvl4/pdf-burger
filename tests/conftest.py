"""Shared test fixtures."""

import pytest
from pathlib import Path
from pypdf import PdfWriter


@pytest.fixture
def make_pdf(tmp_path: Path):
    """Factory fixture that creates a minimal PDF with a given label."""
    def _make(name: str, directory: Path | None = None, text: str | None = None) -> Path:
        dest = (directory or tmp_path) / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        if text:
            # Add metadata so we can identify the source
            writer.add_metadata({"/Title": text})
        writer.write(str(dest))
        writer.close()
        return dest
    return _make
