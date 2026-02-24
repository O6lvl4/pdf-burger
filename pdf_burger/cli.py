"""CLI entry point for pdf-burger."""

import argparse
import sys
from pathlib import Path

from pdf_burger.collector import collect_pdfs
from pdf_burger.logger import logger, setup_logging
from pdf_burger.merger import merge_pdfs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-burger",
        description="複数のPDFファイルやディレクトリを1つのPDFに結合します。",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="結合するPDFファイルまたはディレクトリ",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="出力ファイルパス",
    )
    parser.add_argument(
        "--recursive",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_logging(verbose=args.verbose)

    output = Path(args.output)
    if output.exists() and not args.overwrite:
        logger.error("出力ファイルが既に存在します: %s (--overwrite で上書き許可)", output)
        return 1

    try:
        files = collect_pdfs(args.inputs, recursive=args.recursive)
    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        return 1

    if args.dry_run:
        logger.info("結合対象 (%d 件):", len(files))
        for f in files:
            logger.info("  %s", f)
        return 0

    try:
        merge_pdfs(files, output)
    except Exception as e:
        logger.error("結合に失敗しました: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
