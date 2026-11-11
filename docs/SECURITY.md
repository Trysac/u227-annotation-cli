# Security notes

## Threat model

`trysac-annotation-cli` reads untrusted JSONL items and renders their text to a terminal, then appends decisions to a local store.

### Defended

- **Terminal escape injection**: `annotate` sanitises every displayed id, prompt and output. Characters in Unicode categories Cc and Cf, except newline and tab, are replaced with their Python escape form; the result is truncated at `max_display_chars` (default 2,000) with `[truncated N chars]`.
- **Untrusted JSONL**: `load_items` rejects invalid items with `invalid_item`, duplicate ids with `duplicate_id`, oversized lines with `line_too_large`, and more than `max_items` (default 100,000) items with `too_many_items`. Reads use `max_line_chars` (default 1,000,000) so an oversized line is rejected before it is fully materialised.
- **Store corruption**: `latest_labels` reads the append-only store, keeps the latest non-null record per id, and raises `corrupt_store` naming the line number for invalid JSON, missing fields or wrong types. Store reads also use `max_line_chars` (default 1,000,000).
- **No code execution**: the library parses JSON with `json.loads` and never calls `eval`, `exec` or a shell. The store is data, not code.

### Not defended

- **Annotator identity**: `annotator` is a caller-supplied string written into the store; the library does not authenticate or authorise annotators.
- **File access and concurrency**: the library does not enforce file permissions, lock the store, or coordinate concurrent writers. Callers choose the items and store paths and are responsible for filesystem access.
- **Confidentiality and integrity**: the store is not encrypted or signed, and the library provides no cryptographic integrity check. The store records contain `id`, `label`, `annotator` and `at`; the items file itself contains the prompt and output text.
- **Terminal side effects beyond Cc/Cf**: newline and tab are displayed unchanged, and the library does not inspect the terminal type or sanitise text after `latest_labels` returns it.

## Publishing

Releases are published to PyPI with trusted publishing (OIDC) when available, never with a long-lived token stored in the repository.

To report a vulnerability, see [SECURITY.md](../SECURITY.md).
