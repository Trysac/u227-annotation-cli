# Testing

## Running

```sh
uv run pytest --cov=annotation_cli
uv run python scripts/check.py
```

## Policy

- Tests exercise the public API (`import annotation_cli`) and assert return values, raised exceptions and their messages.
- Tests use temporary files via pytest's `tmp_path`; they do not use the network.
- The package is tested with pytest; coverage is reported for `annotation_cli`.

## Tiers

The supplied repository has one test tier: the pytest suite in `tests/test_annotation_cli.py`. No separate conformance tests or external-tool downloads are configured in the supplied files.

## Layout

`tests/test_annotation_cli.py` is the only test module. It imports from `annotation_cli` and `annotation_cli.__main__`, and defines local helpers `write_lines` and `read_store` for writing fixture files and inspecting the JSONL store.

The module covers:

- `LabelSchema`: valid mappings, reserved keys `u`, `s`, `q`, `?`, key length, label length, entry-count limits and non-mapping input.
- `load_items`: valid JSONL, empty files, invalid JSON, missing `output`, non-string `prompt`, invalid UTF-8, duplicate ids, oversized lines (default and explicit limits) and the item-count limit.
- `latest_labels`: latest-record selection, null-label undo records, corrupt lines and invalid UTF-8.
- The interactive `annotate` session, `cohen_kappa` and `main` against the acceptance criteria.
