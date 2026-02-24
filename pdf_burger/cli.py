"""CLI entry point for pdf-burger.

Thin boundary layer: parses args, wires pure functions together,
and handles all side effects (I/O, exit codes).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pdf_burger import __version__
from pdf_burger.collector import collect_pdfs
from pdf_burger.console import Console, create_console
from pdf_burger.merger import MergeResult, merge_pdfs


# --- Pure functions ---


def resolve_output(output_arg: str | None, inputs: tuple[str, ...]) -> Path:
    """Determine output path. Auto-generates a unique name when -o is omitted."""
    if output_arg is not None:
        return Path(output_arg)
    candidate = (
        Path.cwd() / f"{Path(inputs[0]).name}.pdf"
        if len(inputs) == 1 and Path(inputs[0]).is_dir()
        else Path.cwd() / "merged.pdf"
    )
    return unique_path(candidate)


def unique_path(path: Path) -> Path:
    """If path exists, append _001, _002, etc."""
    if not path.exists():
        return path
    return next(
        (
            candidate
            for i in range(1, 1000)
            if not (candidate := path.parent / f"{path.stem}_{i:03d}{path.suffix}").exists()
        ),
        None,
    ) or (_ for _ in ()).throw(RuntimeError(f"cannot generate unique output filename: {path}"))


def should_block_overwrite(output_arg: str | None, output: Path, overwrite: bool) -> bool:
    """Check if the output file write should be blocked."""
    return output_arg is not None and output.exists() and not overwrite


def format_dry_run(files: list[Path]) -> str:
    """Format dry-run output as a single string."""
    header = f"target files ({len(files)}):"
    lines = [f"  {f}" for f in files]
    return "\n".join([header, *lines])


def format_result(result: MergeResult) -> str:
    """Format merge result into a success message."""
    return f"merged {result.file_count} PDFs ({result.page_count} pages) -> {result.output.name}"


# --- Argument parser ---


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-burger",
        description="Stack multiple PDFs and directories into a single file.",
        epilog=(
            "examples:\n"
            "  pdf-burger a.pdf b.pdf                  merge two PDFs (-> merged.pdf)\n"
            "  pdf-burger ./docs/ -o combined.pdf      merge all PDFs in a directory\n"
            "  pdf-burger ./docs/ -r                   search subdirectories recursively\n"
            "  pdf-burger *.pdf --dry-run              preview target files only"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("inputs", nargs="+", help="PDF files or directories to merge")
    parser.add_argument("-o", "--output", default=None, help="output file path (default: merged.pdf)")
    parser.add_argument("-r", "--recursive", action="store_true", help="search directories recursively")
    parser.add_argument("--overwrite", action="store_true", help="allow overwriting an existing output file")
    parser.add_argument("--verbose", action="store_true", help="show detailed log")
    parser.add_argument("--dry-run", action="store_true", help="list target files without merging")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser


# --- Side-effect boundary ---


def run(argv: list[str] | None, con: Console) -> int:
    """Execute the merge pipeline. All I/O goes through the Console."""
    args = build_parser().parse_args(argv)
    con = create_console(verbose=args.verbose)

    try:
        files = collect_pdfs(args.inputs, recursive=args.recursive, on_warning=con.warning)
    except (FileNotFoundError, ValueError) as e:
        con.error(str(e))
        return 1

    output = resolve_output(args.output, tuple(args.inputs))

    if should_block_overwrite(args.output, output, args.overwrite):
        con.error(f"output file already exists: {output}")
        con.info("  use --overwrite to replace it")
        return 1

    if args.dry_run:
        con.info(format_dry_run(files))
        return 0

    try:
        result = merge_pdfs(files, output, on_verbose=con.verbose, rich_console=con.rich)
        con.success(format_result(result))
        con.verbose(f"  output: {result.output}")
    except Exception as e:
        con.error(f"merge failed: {e}")
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv, create_console())
    except KeyboardInterrupt:
        create_console().error("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
