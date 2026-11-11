# Architecture

## Purpose

`trysac-annotation-cli` is a dependency-free Python library for terminal annotation of model outputs: single-key labels, undo, resumable append-only JSONL storage, sanitised display of untrusted text and Cohen's kappa agreement.

## Shape

```text
CLI (python -m annotation_cli) or caller code
        |
        v
annotation_cli (public API in __init__.py)
        |
        +-- load_items / latest_labels read JSONL from disk
        +-- annotate appends JSONL decision records to the store
        +-- cohen_kappa computes agreement over two label maps
```

- **Public API**: the names listed in `__all__` of `src/annotation_cli/__init__.py`: `Agreement`, `AnnotationError`, `Item`, `LabelSchema`, `SessionResult`, `annotate`, `cohen_kappa`, `latest_labels`, `load_items`. The CLI entry point is `annotation_cli.__main__.main`.
- **Errors**: invalid schemas, malformed items, oversized lines and corrupt stores raise `AnnotationError` with code `invalid_schema`, `invalid_item`, `duplicate_id`, `line_too_large`, `too_many_items`, `corrupt_store` or `no_overlap`.
- **Side effects**: `load_items` and `latest_labels` read the items and store files; `annotate` appends one JSON object per decision to the store. Displayed id, prompt and output are sanitised and truncated. Interactive input, output and clock are injectable via `input_fn`, `output_fn` and `clock`.

## Quality contract

The package has no runtime dependencies, ships `py.typed`, and its tests live in `tests/test_annotation_cli.py`. See [TESTING.md](TESTING.md).

## Decisions

No architecture decision records are included in the supplied source. The behaviour above is defined by `src/annotation_cli/__init__.py` and `src/annotation_cli/__main__.py`.
