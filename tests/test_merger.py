"""Tests for pdf_burger.merger."""

from pathlib import Path

from pypdf import PdfReader

from pdf_burger.merger import merge_pdfs


class TestMergePdfs:
    def test_merge_two_files(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        b = make_pdf("b.pdf")
        output = tmp_path / "out.pdf"
        merge_pdfs([a, b], output)
        assert output.exists()
        reader = PdfReader(str(output))
        assert len(reader.pages) == 2

    def test_merge_single_file(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        output = tmp_path / "out.pdf"
        merge_pdfs([a], output)
        reader = PdfReader(str(output))
        assert len(reader.pages) == 1

    def test_merge_preserves_page_count(self, make_pdf, tmp_path):
        files = [make_pdf(f"{i}.pdf") for i in range(5)]
        output = tmp_path / "out.pdf"
        merge_pdfs(files, output)
        reader = PdfReader(str(output))
        assert len(reader.pages) == 5

    def test_merge_creates_output_directory(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        output = tmp_path / "subdir" / "deep" / "out.pdf"
        merge_pdfs([a], output)
        assert output.exists()
