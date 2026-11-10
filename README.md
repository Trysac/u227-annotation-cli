# annotation-cli

[![PyPI version](https://img.shields.io/pypi/v/trysac-annotation-cli)](https://pypi.org/project/trysac-annotation-cli/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-annotation-cli)](LICENSE)
[![CI](https://github.com/Trysac/u227-annotation-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u227-annotation-cli/actions/workflows/ci.yml)

Label model outputs in the terminal with single-key choices, undo, resumable append-only JSONL storage, safe display of untrusted text and Cohen's kappa agreement

## Problem

Teams that evaluate model outputs need human labels, but spreadsheets lose context and annotation web tools are heavy to deploy for a few hundred items. A quick script usually forgets where the annotator stopped, has no undo, and prints raw model output that can carry terminal escape sequences. This library runs a keyboard-driven labelling session over JSONL, stores every decision append-only so it can resume, and measures agreement between two annotators.

## Install

```sh
pip install trysac-annotation-cli
# or
uv add trysac-annotation-cli
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

The library reads JSONL items and appends decisions to a store; this example uses the public API:

```python
from pathlib import Path
from annotation_cli import LabelSchema, annotate, latest_labels, load_items, cohen_kappa

items = load_items(Path("items.jsonl"))
result = annotate(
    items, LabelSchema({"g": "good", "b": "bad"}), annotator="alice", store=Path("labels.jsonl")
)
print(result.labelled, result.skipped, result.remaining)
print(cohen_kappa(latest_labels(Path("alice.jsonl")), latest_labels(Path("bob.jsonl"))))
```

The same session is available as `python -m annotation_cli run items.jsonl --store labels.jsonl --annotator alice --labels g=good,b=bad`; `python -m annotation_cli agree alice.jsonl bob.jsonl` compares two stores.

## Public API

- `LabelSchema(keys: Mapping[str, str])` — 1 to 9 single-character keys; labels are non-empty strings of at most 40 characters; `u`, `s`, `q` and `?` are reserved.
- `Item(id: str, prompt: str, output: str)` — frozen dataclass.
- `load_items(path: Path, *, max_items: int = 100_000, max_line_chars: int = 1_000_000) -> list[Item]` — reads JSONL objects with a string `id`, optional string `prompt` (default empty) and string `output`; duplicate ids and invalid lines fail.
- `annotate(items, schema, *, annotator: str, store: Path, input_fn=input, output_fn=print, clock=time.time, max_display_chars: int = 2_000) -> SessionResult` — runs the keyboard session. Items whose id already has a non-null latest label in the store are skipped. A schema key appends one JSON line `{id, label, annotator, at}`; `s` skips, `u` appends a null-label undo record for the last item labelled in this session, `q` stops, and `?` reprints the legend. Displayed id, prompt and output are sanitised and truncated.
- `latest_labels(store: Path, *, max_line_chars: int = 1_000_000) -> dict[str, str]` — returns the latest non-null label per id; a corrupt line raises `corrupt_store`.
- `cohen_kappa(a: Mapping[str, str], b: Mapping[str, str]) -> Agreement` — uses ids present in both maps; returns `n`, `observed`, `expected` and `kappa`.
- `SessionResult(labelled, skipped, remaining)` and `Agreement(n, observed, expected, kappa)` are frozen dataclasses.
- `main(argv: list[str] | None = None) -> int` in `annotation_cli.__main__` implements the `run` and `agree` subcommands.

Invalid input raises `annotation_cli.AnnotationError` with one of `invalid_schema`, `invalid_item`, `duplicate_id`, `line_too_large`, `too_many_items`, `corrupt_store` or `no_overlap`. The CLI exits `0` on success, `1` for domain failures, and `2` for usage or IO errors.

## Why not Label Studio or Argilla

They provide browser and server workflows with project management. This utility has no server and no browser: it reads one JSONL item file and writes one append-only JSONL store that diffs in git.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
