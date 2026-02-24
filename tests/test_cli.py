"""Tests for pdf_burger.cli."""

from pathlib import Path

from pypdf import PdfReader

from pdf_burger.cli import main


class TestCli:
    def test_basic_merge(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        b = make_pdf("b.pdf")
        output = tmp_path / "out.pdf"
        rc = main([str(a), str(b), "-o", str(output)])
        assert rc == 0
        assert output.exists()
        reader = PdfReader(str(output))
        assert len(reader.pages) == 2

    def test_output_already_exists_without_overwrite(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        output = tmp_path / "out.pdf"
        output.write_text("dummy")
        rc = main([str(a), "-o", str(output)])
        assert rc == 1

    def test_output_already_exists_with_overwrite(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        output = tmp_path / "out.pdf"
        output.write_text("dummy")
        rc = main([str(a), "-o", str(output), "--overwrite"])
        assert rc == 0
        assert output.exists()

    def test_dry_run(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        output = tmp_path / "out.pdf"
        rc = main([str(a), "-o", str(output), "--dry-run"])
        assert rc == 0
        assert not output.exists()

    def test_nonexistent_input(self, tmp_path):
        output = tmp_path / "out.pdf"
        rc = main(["/nonexistent.pdf", "-o", str(output)])
        assert rc == 1

    def test_directory_input(self, make_pdf, tmp_path):
        d = tmp_path / "docs"
        d.mkdir()
        make_pdf("1.pdf", directory=d)
        make_pdf("2.pdf", directory=d)
        output = tmp_path / "out.pdf"
        rc = main([str(d), "-o", str(output)])
        assert rc == 0
        reader = PdfReader(str(output))
        assert len(reader.pages) == 2

    def test_recursive_flag(self, make_pdf, tmp_path):
        d = tmp_path / "top"
        d.mkdir()
        make_pdf("a.pdf", directory=d)
        sub = d / "nested"
        sub.mkdir()
        make_pdf("b.pdf", directory=sub)
        output = tmp_path / "out.pdf"
        rc = main([str(d), "-o", str(output), "--recursive"])
        assert rc == 0
        reader = PdfReader(str(output))
        assert len(reader.pages) == 2

    def test_verbose_flag(self, make_pdf, tmp_path):
        a = make_pdf("a.pdf")
        output = tmp_path / "out.pdf"
        rc = main([str(a), "-o", str(output), "--verbose"])
        assert rc == 0
