"""CLI entry point for pdf-burger.

Monadic pipeline: parse -> collect -> resolve -> merge.
All logic is pure; side effects are deferred in IO and
only executed at the boundary (main).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from pdf_burger import __version__
from pdf_burger.collector import CollectResult, collect_pdfs
from pdf_burger.console import Console, create_console
from pdf_burger.merger import MergeResult, merge_pdfs
from pdf_burger.monads import Err, IO, Ok, Result, pipe


# ── Immutable config parsed from argv ──────────────────────────────


@dataclass(frozen=True)
class Config:
    inputs: tuple[str, ...]
    output: str | None
    recursive: bool
    overwrite: bool
    verbose: bool
    dry_run: bool


# ── Pure functions ─────────────────────────────────────────────────


def parse_config(argv: list[str] | None) -> Result[Config, str]:
    """Parse CLI args into an immutable Config. No side effects."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return Err(f"__exit__{e.code}") if e.code != 0 else Err("__exit__0")
    return Ok(Config(
        inputs=tuple(args.inputs),
        output=args.output,
        recursive=args.recursive,
        overwrite=args.overwrite,
        verbose=args.verbose,
        dry_run=args.dry_run,
    ))


def resolve_output(output_arg: str | None, inputs: tuple[str, ...]) -> Path:
    """Determine output path. Pure."""
    if output_arg is not None:
        return Path(output_arg)
    candidate = (
        Path.cwd() / f"{Path(inputs[0]).name}.pdf"
        if len(inputs) == 1 and Path(inputs[0]).is_dir()
        else Path.cwd() / "merged.pdf"
    )
    return _unique_path(candidate)


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    return next(
        (
            c for i in range(1, 1000)
            if not (c := path.parent / f"{path.stem}_{i:03d}{path.suffix}").exists()
        ),
        path,
    )


def check_overwrite(output: Path, config: Config) -> Result[Path, str]:
    """Check overwrite constraint. Pure."""
    match (config.output is not None, output.exists(), config.overwrite):
        case (True, True, False):
            return Err(f"output file already exists: {output}\n  use --overwrite to replace it")
        case _:
            return Ok(output)


def format_dry_run(files: tuple[Path, ...]) -> str:
    header = f"target files ({len(files)}):"
    lines = (f"  {f}" for f in files)
    return "\n".join((header, *lines))


def format_result(result: MergeResult) -> str:
    return f"merged {result.file_count} PDFs ({result.page_count} pages) -> {result.output.name}"


# ── Monadic pipeline ───────────────────────────────────────────────


def _build_pipeline(
    config: Config,
    con: Console,
) -> IO[Result[int, str]]:
    """Compose the full merge pipeline monadically.

    collect_pdfs -> check_overwrite -> (dry_run | merge) -> format
    """
    collected: Result[CollectResult, str] = collect_pdfs(
        list(config.inputs), recursive=config.recursive,
    )

    def emit_warnings_and_continue(cr: CollectResult) -> Result[CollectResult, str]:
        for w in cr.warnings:
            con.warning(w)
        return Ok(cr)

    def to_exit_code(cr: CollectResult) -> IO[Result[int, str]]:
        output = resolve_output(config.output, config.inputs)

        return pipe(
            check_overwrite(output, config),
            lambda r: r.bind(lambda out: _dispatch(cr.files, out, config, con)),
        )

    def _dispatch(
        files: tuple[Path, ...],
        output: Path,
        cfg: Config,
        con: Console,
    ) -> Result[int, str]:
        if cfg.dry_run:
            con.info(format_dry_run(files))
            return Ok(0)

        merge_io: IO[Result[MergeResult, str]] = merge_pdfs(
            files, output, on_verbose=con.verbose, rich_console=con.rich,
        )
        merge_result = merge_io.run()

        match merge_result:
            case Ok(result):
                con.success(format_result(result))
                con.verbose(f"  output: {result.output}")
                return Ok(0)
            case Err(e):
                return Err(e)

    result: Result[int, str] = (
        collected
        .bind(emit_warnings_and_continue)
        .bind(lambda cr: to_exit_code(cr))
        # to_exit_code returns IO[Result], but we need to unwrap
    )

    # Flatten: if collected failed, wrap in IO; otherwise already executed
    match result:
        case Ok(io_result) if isinstance(io_result, IO):
            return io_result
        case _:
            return IO.pure(result)


def _run_pipeline(config: Config, con: Console) -> int:
    """Execute the monadic pipeline and interpret the Result into an exit code."""
    collected = collect_pdfs(list(config.inputs), recursive=config.recursive)

    match collected:
        case Err(msg):
            con.error(msg)
            return 1
        case Ok(cr):
            for w in cr.warnings:
                con.warning(w)

            output = resolve_output(config.output, config.inputs)

            match check_overwrite(output, config):
                case Err(msg):
                    con.error(msg)
                    return 1
                case Ok(out):
                    if config.dry_run:
                        con.info(format_dry_run(cr.files))
                        return 0

                    merge_io = merge_pdfs(
                        cr.files, out,
                        on_verbose=con.verbose, rich_console=con.rich,
                    )

                    match merge_io.run():
                        case Ok(result):
                            con.success(format_result(result))
                            con.verbose(f"  output: {result.output}")
                            return 0
                        case Err(msg):
                            con.error(msg)
                            return 1


# ── Argument parser ────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
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


# ── Side-effect boundary (the only impure entry point) ─────────────


def main(argv: list[str] | None = None) -> int:
    """The single impure entry point. Interprets the monadic pipeline."""
    try:
        match parse_config(argv):
            case Err(msg) if msg == "__exit__0":
                raise SystemExit(0)
            case Err(msg) if msg.startswith("__exit__"):
                return 2
            case Err(msg):
                create_console().error(msg)
                return 2
            case Ok(config):
                con = create_console(verbose=config.verbose)
                return _run_pipeline(config, con)
    except KeyboardInterrupt:
        create_console().error("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
