"""Tests for pdf_burger.merger."""

from pathlib import Path

from pypdf import PdfReader

from pdf_burger.merger import MergeResult, merge_pdfs


class TestMergePdfs:
    def test_merge_two_files(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        b = make_pdf("b.pdf")
        output = tmp_path / "out.pdf"
        result = merge_pdfs((a, b), output).run()
        assert result.is_ok()
        mr = result.unwrap()
        assert isinstance(mr, MergeResult)
        assert mr.file_count == 2
        assert mr.page_count == 2

    def test_merge_single_file(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        output = tmp_path / "out.pdf"
        result = merge_pdfs((a,), output).run()
        assert result.unwrap().page_count == 1

    def test_merge_preserves_page_count(self, make_pdf, tmp_path):
        files = tuple(make_pdf(f"{i}.pdf") for i in range(5))
        output = tmp_path / "out.pdf"
        result = merge_pdfs(files, output).run()
        assert result.unwrap().page_count == 5
        reader = PdfReader(str(output))
        assert len(reader.pages) == 5

    def test_merge_creates_output_directory(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        output = tmp_path / "subdir" / "deep" / "out.pdf"
        result = merge_pdfs((a,), output).run()
        assert output.exists()
        assert result.unwrap().output == output

    def test_io_is_lazy(self, make_pdf, tmp_path):
        """IO action should not execute until .run() is called."""
        a = make_pdf("a.pdf")
        output = tmp_path / "lazy.pdf"
        io_action = merge_pdfs((a,), output)
        assert not output.exists()  # not yet executed
        io_action.run()
        assert output.exists()  # now executed
