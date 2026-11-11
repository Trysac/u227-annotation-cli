"""Command-line entry point for annotation-cli."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from annotation_cli import (
    AnnotationError,
    LabelSchema,
    annotate,
    cohen_kappa,
    latest_labels,
    load_items,
)


def _parse_labels(labels_arg: str) -> dict[str, str]:
    """Parse comma-separated key=value label definitions."""
    pairs = labels_arg.split(",")
    result: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise argparse.ArgumentTypeError(f"invalid label format: {pair!r}")
        key, _, value = pair.partition("=")
        if not key or not value:
            raise argparse.ArgumentTypeError(f"invalid label format: {pair!r}")
        result[key] = value
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="annotation-cli", description="Terminal annotation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run annotation session")
    run_parser.add_argument("items_file", type=Path, help="JSONL file with items")
    run_parser.add_argument("--store", type=Path, required=True, help="Annotation store JSONL file")
    run_parser.add_argument("--annotator", required=True, help="Annotator name")
    run_parser.add_argument(
        "--labels", required=True, help="Comma-separated key=value label definitions"
    )
    run_parser.add_argument("--max-items", type=int, default=100_000)
    run_parser.add_argument("--max-line-chars", type=int, default=1_000_000)
    run_parser.add_argument("--max-display-chars", type=int, default=2_000)

    agree_parser = subparsers.add_parser("agree", help="Compute Cohen's kappa between two stores")
    agree_parser.add_argument("store_a", type=Path)
    agree_parser.add_argument("store_b", type=Path)
    return parser


def run_cmd(args: argparse.Namespace) -> int:
    try:
        labels = _parse_labels(args.labels)
    except argparse.ArgumentTypeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    schema = LabelSchema(labels)
    items = load_items(
        args.items_file,
        max_items=args.max_items,
        max_line_chars=args.max_line_chars,
    )
    annotate(
        items,
        schema,
        annotator=args.annotator,
        store=args.store,
        max_display_chars=args.max_display_chars,
    )
    return 0


def agree_cmd(args: argparse.Namespace) -> int:
    a = latest_labels(args.store_a)
    b = latest_labels(args.store_b)
    agreement = cohen_kappa(a, b)
    print(
        f"n={agreement.n} observed={agreement.observed:.3f} "
        f"expected={agreement.expected:.3f} kappa={agreement.kappa:.3f}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    try:
        if args.command == "run":
            return run_cmd(args)
        elif args.command == "agree":
            return agree_cmd(args)
        else:
            parser.print_help()
            return 2
    except AnnotationError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
