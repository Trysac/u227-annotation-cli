# Stack

## Used

| Tool | Why |
|---|---|
| Python >= 3.10 | Supported runtime for the package; the code uses `from __future__ import annotations` and stdlib typing. |
| hatchling | Build backend declared by the package template. |
| uv | Environment and command runner used by the repository commands. |
| pytest + pytest-cov | Test runner used by `tests/test_annotation_cli.py` with coverage for `annotation_cli`. |
| ruff | Lint and format gate in the repository tooling. |
| mypy (strict) | Type-check gate; the package ships `py.typed`. |
| gitleaks | Secret scanning in the repository gates. |
| GitHub Actions + Dependabot | CI and dependency updates for the repository. |

## Discarded

| Tool | Why not |
|---|---|
| Poetry | uv covers the same dependency and environment needs with standard dependency groups. |
| black + isort + flake8 | ruff provides lint and formatting in one tool. |
| tox / nox | The repository uses a single local check script instead of a matrix runner. |
| Shell scripts for gates | Not portable to Windows; gates are Python. |
