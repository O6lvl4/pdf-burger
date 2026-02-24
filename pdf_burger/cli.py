"""CLI entry point for pdf-burger."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pdf_burger import __version__, console
from pdf_burger.collector import collect_pdfs
from pdf_burger.merger import merge_pdfs


def _resolve_output(output_arg: str | None, inputs: list[str]) -> Path:
    """Determine output path. Auto-generates a unique name when -o is omitted."""
    if output_arg is not None:
        return Path(output_arg)

    if len(inputs) == 1 and Path(inputs[0]).is_dir():
        candidate = Path.cwd() / f"{Path(inputs[0]).name}.pdf"
    else:
        candidate = Path.cwd() / "merged.pdf"

    return _unique_path(candidate)


def _unique_path(path: Path) -> Path:
    """If path exists, append _001, _002, etc."""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    for i in range(1, 1000):
        candidate = parent / f"{stem}_{i:03d}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"cannot generate unique output filename: {path}")


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
    parser.add_argument(
        "inputs",
        nargs="+",
        help="PDF files or directories to merge",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="output file path (default: merged.pdf)",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="search directories recursively",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="allow overwriting an existing output file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="show detailed log",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list target files without merging",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    console.set_verbose(args.verbose)

    try:
        files = collect_pdfs(args.inputs, recursive=args.recursive)
    except (FileNotFoundError, ValueError) as e:
        console.error(str(e))
        return 1

    output = _resolve_output(args.output, args.inputs)

    if args.output is not None and output.exists() and not args.overwrite:
        console.error(f"output file already exists: {output}")
        console.info("  use --overwrite to replace it")
        return 1

    if args.dry_run:
        console.info(f"target files ({len(files)}):")
        for f in files:
            console.info(f"  {f}")
        return 0

    try:
        merge_pdfs(files, output)
    except Exception as e:
        console.error(f"merge failed: {e}")
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _run(argv)
    except KeyboardInterrupt:
        console.error("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
