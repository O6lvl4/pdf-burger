"""Tests for pdf_burger.collector."""

import pytest
from pathlib import Path

from pdf_burger.collector import collect_pdfs, natural_sort_key


class TestNaturalSortKey:
    def test_numeric_parts(self):
        paths = [Path("10.pdf"), Path("2.pdf"), Path("1.pdf")]
        result = sorted(paths, key=natural_sort_key)
        assert [p.name for p in result] == ["1.pdf", "2.pdf", "10.pdf"]

    def test_alpha_parts(self):
        paths = [Path("c.pdf"), Path("a.pdf"), Path("b.pdf")]
        result = sorted(paths, key=natural_sort_key)
        assert [p.name for p in result] == ["a.pdf", "b.pdf", "c.pdf"]


class TestCollectPdfs:
    def test_single_file(self, make_pdf, tmp_path):
        pdf = make_pdf("test.pdf")
        result = collect_pdfs([str(pdf)])
        assert result == [pdf.resolve()]

    def test_multiple_files_preserve_order(self, make_pdf, tmp_path):
        b = make_pdf("b.pdf")
        a = make_pdf("a.pdf")
        result = collect_pdfs([str(b), str(a)])
        assert result == [b.resolve(), a.resolve()]

    def test_directory_sorted(self, make_pdf, tmp_path):
        d = tmp_path / "docs"
        d.mkdir()
        make_pdf("10.pdf", directory=d)
        make_pdf("2.pdf", directory=d)
        make_pdf("1.pdf", directory=d)
        result = collect_pdfs([str(d)])
        names = [p.name for p in result]
        assert names == ["1.pdf", "2.pdf", "10.pdf"]

    def test_mixed_file_and_dir(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        d = tmp_path / "sub"
        d.mkdir()
        make_pdf("x.pdf", directory=d)
        b = make_pdf("b.pdf")
        result = collect_pdfs([str(a), str(d), str(b)])
        names = [p.name for p in result]
        assert names == ["a.pdf", "x.pdf", "b.pdf"]

    def test_recursive(self, make_pdf, tmp_path):
        d = tmp_path / "top"
        d.mkdir()
        make_pdf("a.pdf", directory=d)
        sub = d / "nested"
        sub.mkdir()
        make_pdf("b.pdf", directory=sub)
        result_flat = collect_pdfs([str(d)], recursive=False)
        assert len(result_flat) == 1
        result_rec = collect_pdfs([str(d)], recursive=True)
        assert len(result_rec) == 2

    def test_nonexistent_path_raises(self):
        with pytest.raises(FileNotFoundError):
            collect_pdfs(["/nonexistent/path.pdf"])

    def test_non_pdf_file_raises(self, tmp_path):
        txt = tmp_path / "note.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match="PDFファイルではありません"):
            collect_pdfs([str(txt)])

    def test_empty_directory_warns(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        with pytest.raises(ValueError, match="結合するPDFファイルが見つかりません"):
            collect_pdfs([str(d)])

    def test_no_pdfs_at_all_raises(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        with pytest.raises(ValueError):
            collect_pdfs([str(d)])

    def test_corrupt_explicit_file_raises(self, tmp_path):
        bad = tmp_path / "bad.pdf"
        bad.write_text("not a pdf")
        with pytest.raises(ValueError, match="PDFファイルを読み込めません"):
            collect_pdfs([str(bad)])

    def test_corrupt_file_in_dir_skipped(self, make_pdf, tmp_path):
        d = tmp_path / "docs"
        d.mkdir()
        make_pdf("good.pdf", directory=d)
        bad = d / "bad.pdf"
        bad.write_text("not a pdf")
        result = collect_pdfs([str(d)])
        assert len(result) == 1
        assert result[0].name == "good.pdf"
