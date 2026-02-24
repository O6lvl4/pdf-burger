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
    raise RuntimeError(f"一意の出力ファイル名を生成できません: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-burger",
        description="複数のPDFファイルやディレクトリを1つのPDFに結合します。",
        epilog=(
            "examples:\n"
            "  pdf-burger a.pdf b.pdf                  2つのPDFを結合 (-> merged.pdf)\n"
            "  pdf-burger ./docs/ -o combined.pdf      ディレクトリ内のPDFを結合\n"
            "  pdf-burger ./docs/ -r                   サブディレクトリも再帰的に検索\n"
            "  pdf-burger *.pdf --dry-run              対象ファイルの確認のみ"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="結合するPDFファイルまたはディレクトリ",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="出力ファイルパス (省略時: merged.pdf)",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="ディレクトリを再帰的に検索する",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="出力ファイルが既に存在する場合に上書きを許可する",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細ログを表示する",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際には結合せず、対象ファイルの一覧を表示する",
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
        console.error(f"出力ファイルが既に存在します: {output}")
        console.info("  --overwrite で上書きを許可できます")
        return 1

    if args.dry_run:
        console.info(f"結合対象 ({len(files)} 件):")
        for f in files:
            console.info(f"  {f}")
        return 0

    try:
        merge_pdfs(files, output)
    except Exception as e:
        console.error(f"結合に失敗しました: {e}")
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _run(argv)
    except KeyboardInterrupt:
        console.error("中断されました")
        return 130


if __name__ == "__main__":
    sys.exit(main())
