# annotation-cli

[![PyPI version](https://img.shields.io/pypi/v/trysac-annotation-cli)](https://pypi.org/project/trysac-annotation-cli/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-annotation-cli)](LICENSE)
[![CI](https://github.com/Trysac/u227-annotation-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u227-annotation-cli/actions/workflows/ci.yml)

Label model outputs in the terminal with single-key choices, undo, resumable append-only JSONL storage, safe display of untrusted text and Cohen's kappa agreement

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-annotation-cli
# or
uv add trysac-annotation-cli
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import annotation_cli

# normalize() trims surrounding whitespace and lower-cases the text.
print(annotation_cli.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    annotation_cli.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
