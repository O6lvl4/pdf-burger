"""Tests for pdf_burger.collector."""

from pathlib import Path

from pdf_burger.collector import CollectResult, collect_pdfs, natural_sort_key
from pdf_burger.monads import Err, Ok


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
        assert result.is_ok()
        assert result.unwrap().files == (pdf.resolve(),)

    def test_multiple_files_preserve_order(self, make_pdf, tmp_path):
        b = make_pdf("b.pdf")
        a = make_pdf("a.pdf")
        result = collect_pdfs([str(b), str(a)])
        assert result.is_ok()
        assert result.unwrap().files == (b.resolve(), a.resolve())

    def test_directory_sorted(self, make_pdf, tmp_path):
        d = tmp_path / "docs"
        d.mkdir()
        make_pdf("10.pdf", directory=d)
        make_pdf("2.pdf", directory=d)
        make_pdf("1.pdf", directory=d)
        result = collect_pdfs([str(d)])
        names = [p.name for p in result.unwrap().files]
        assert names == ["1.pdf", "2.pdf", "10.pdf"]

    def test_mixed_file_and_dir(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        d = tmp_path / "sub"
        d.mkdir()
        make_pdf("x.pdf", directory=d)
        b = make_pdf("b.pdf")
        result = collect_pdfs([str(a), str(d), str(b)])
        names = [p.name for p in result.unwrap().files]
        assert names == ["a.pdf", "x.pdf", "b.pdf"]

    def test_recursive(self, make_pdf, tmp_path):
        d = tmp_path / "top"
        d.mkdir()
        make_pdf("a.pdf", directory=d)
        sub = d / "nested"
        sub.mkdir()
        make_pdf("b.pdf", directory=sub)
        flat = collect_pdfs([str(d)], recursive=False)
        assert len(flat.unwrap().files) == 1
        rec = collect_pdfs([str(d)], recursive=True)
        assert len(rec.unwrap().files) == 2

    def test_nonexistent_path_returns_err(self):
        result = collect_pdfs(["/nonexistent/path.pdf"])
        assert result.is_err()
        assert "path not found" in result.error

    def test_non_pdf_file_returns_err(self, tmp_path):
        txt = tmp_path / "note.txt"
        txt.write_text("hello")
        result = collect_pdfs([str(txt)])
        assert result.is_err()
        assert "not a PDF file" in result.error

    def test_empty_directory_returns_err(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        result = collect_pdfs([str(d)])
        assert result.is_err()
        assert "no PDF files to merge" in result.error

    def test_no_pdfs_at_all_returns_err(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        result = collect_pdfs([str(d)])
        assert result.is_err()

    def test_corrupt_explicit_file_returns_err(self, tmp_path):
        bad = tmp_path / "bad.pdf"
        bad.write_text("not a pdf")
        result = collect_pdfs([str(bad)])
        assert result.is_err()
        assert "cannot read PDF" in result.error

    def test_corrupt_file_in_dir_becomes_warning(self, make_pdf, tmp_path):
        d = tmp_path / "docs"
        d.mkdir()
        make_pdf("good.pdf", directory=d)
        bad = d / "bad.pdf"
        bad.write_text("not a pdf")
        result = collect_pdfs([str(d)])
        assert result.is_ok()
        cr = result.unwrap()
        assert len(cr.files) == 1
        assert cr.files[0].name == "good.pdf"
        assert len(cr.warnings) == 1


class TestResultMonad:
    """Verify monadic properties of collect_pdfs results."""

    def test_ok_bind_chains(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        result = collect_pdfs([str(a)]).bind(
            lambda cr: Ok(len(cr.files))
        )
        assert result == Ok(1)

    def test_err_bind_short_circuits(self):
        result = collect_pdfs(["/nope.pdf"]).bind(
            lambda cr: Ok("should not reach")
        )
        assert result.is_err()

    def test_ok_map_transforms(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        result = collect_pdfs([str(a)]).map(lambda cr: cr.files)
        assert result.is_ok()
        assert len(result.unwrap()) == 1
