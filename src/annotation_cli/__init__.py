"""Terminal annotation for model outputs with undo, resume, and agreement metrics."""

from __future__ import annotations

import json
import logging
import time
import unicodedata
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

__all__ = [
    "Agreement",
    "AnnotationError",
    "Item",
    "LabelSchema",
    "SessionResult",
    "annotate",
    "cohen_kappa",
    "latest_labels",
    "load_items",
]

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

ErrorCode = Literal[
    "invalid_schema",
    "invalid_item",
    "duplicate_id",
    "line_too_large",
    "too_many_items",
    "corrupt_store",
    "no_overlap",
]


class AnnotationError(Exception):
    """Base error for the annotation library."""

    def __init__(self, code: ErrorCode, message: str = "") -> None:
        super().__init__(message)
        self.code = code

    def __str__(self) -> str:
        msg = super().__str__()
        return f"{self.code}: {msg}" if msg else self.code


@dataclass(frozen=True)
class Item:
    """An item to annotate: id, prompt, and output."""

    id: str
    prompt: str
    output: str


@dataclass(frozen=True)
class SessionResult:
    """Outcome of an annotation session."""

    labelled: int
    skipped: int
    remaining: int


@dataclass(frozen=True)
class Agreement:
    """Cohen's kappa agreement between two annotators."""

    n: int
    observed: float
    expected: float
    kappa: float


class LabelSchema:
    """Mapping from single-character keys to label values."""

    RESERVED_KEYS = frozenset({"u", "s", "q", "?"})

    def __init__(self, keys: Mapping[str, str]) -> None:
        if not isinstance(keys, Mapping):
            raise AnnotationError("invalid_schema", "keys must be a mapping")
        if not (1 <= len(keys) <= 9):
            raise AnnotationError("invalid_schema", "schema must have between 1 and 9 keys")
        for key, value in keys.items():
            if not isinstance(key, str) or len(key) != 1:
                raise AnnotationError("invalid_schema", "keys must be single-character strings")
            if key in self.RESERVED_KEYS:
                raise AnnotationError("invalid_schema", f"reserved key {key!r} cannot be used")
            if not isinstance(value, str) or not (1 <= len(value) <= 40):
                raise AnnotationError(
                    "invalid_schema", "labels must be non-empty strings of at most 40 characters"
                )
        self.mapping: dict[str, str] = dict(keys)


def _sanitize(text: str, max_display_chars: int) -> str:
    """Replace control/format characters with escape form, then truncate."""
    out_chars: list[str] = []
    for ch in text:
        if ch in ("\n", "\t"):
            out_chars.append(ch)
        elif unicodedata.category(ch) in ("Cc", "Cf"):
            escaped = ch.encode("unicode_escape").decode("ascii")
            out_chars.append(escaped)
        else:
            out_chars.append(ch)
    result = "".join(out_chars)
    if len(result) > max_display_chars:
        truncated = len(result) - max_display_chars
        return result[:max_display_chars] + f" [truncated {truncated} chars]"
    return result


def _read_lines(
    path: Path, *, max_line_chars: int, code: ErrorCode, decode_code: ErrorCode | None = None
) -> Iterator[tuple[int, str]]:
    """Yield ``(line_number, line)`` from ``path`` without reading whole files.

    The read is bounded so an oversized line is rejected before it is fully
    materialised in memory, and decoding errors become ``AnnotationError``.
    """
    error_code = code if decode_code is None else decode_code
    try:
        with path.open("r", encoding="utf-8") as f:
            line_no = 0
            while True:
                chunk = f.readline(max_line_chars + 1)
                if not chunk:
                    break
                line_no += 1
                line = chunk[:-1] if chunk.endswith("\n") else chunk
                if len(line) > max_line_chars:
                    raise AnnotationError(
                        code, f"line {line_no} exceeds {max_line_chars} characters"
                    )
                yield line_no, line
    except UnicodeDecodeError as e:
        raise AnnotationError(error_code, "file is not valid UTF-8") from e


def load_items(
    path: Path,
    *,
    max_items: int = 100_000,
    max_line_chars: int = 1_000_000,
) -> list[Item]:
    """Read JSONL items from ``path``, enforcing limits and validation."""
    items: list[Item] = []
    seen_ids: set[str] = set()
    for line_no, line in _read_lines(
        path,
        max_line_chars=max_line_chars,
        code="line_too_large",
        decode_code="invalid_item",
    ):
        if len(items) >= max_items:
            raise AnnotationError("too_many_items", f"more than {max_items} items")
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise AnnotationError("invalid_item", f"line {line_no}: invalid JSON") from e
        if not isinstance(obj, dict):
            raise AnnotationError("invalid_item", f"line {line_no}: not an object")
        if "id" not in obj or not isinstance(obj["id"], str):
            raise AnnotationError("invalid_item", f"line {line_no}: missing or invalid 'id'")
        if "output" not in obj or not isinstance(obj["output"], str):
            raise AnnotationError("invalid_item", f"line {line_no}: missing or invalid 'output'")
        prompt = obj.get("prompt", "")
        if not isinstance(prompt, str):
            raise AnnotationError("invalid_item", f"line {line_no}: 'prompt' must be a string")
        item_id = obj["id"]
        if item_id in seen_ids:
            raise AnnotationError("duplicate_id", f"line {line_no}: duplicate id {item_id!r}")
        seen_ids.add(item_id)
        items.append(Item(id=item_id, prompt=prompt, output=obj["output"]))
    return items


def _append_record(store: Path, record: dict[str, object]) -> None:
    with store.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def latest_labels(store: Path, *, max_line_chars: int = 1_000_000) -> dict[str, str]:
    """Return the latest non-None label for each id in the store."""
    if not store.exists():
        return {}
    latest: dict[str, str] = {}
    for line_no, line in _read_lines(
        store,
        max_line_chars=max_line_chars,
        code="corrupt_store",
        decode_code="corrupt_store",
    ):
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise AnnotationError("corrupt_store", f"line {line_no}: invalid JSON") from e
        if not isinstance(obj, dict) or "id" not in obj or "label" not in obj:
            raise AnnotationError("corrupt_store", f"line {line_no}: missing id or label")
        item_id = obj["id"]
        label = obj["label"]
        if not isinstance(item_id, str):
            raise AnnotationError("corrupt_store", f"line {line_no}: id must be string")
        if label is None:
            latest.pop(item_id, None)
        elif isinstance(label, str):
            latest[item_id] = label
        else:
            raise AnnotationError("corrupt_store", f"line {line_no}: label must be string or null")
    return latest


def annotate(
    items: Sequence[Item],
    schema: LabelSchema,
    *,
    annotator: str,
    store: Path,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    clock: Callable[[], float] = time.time,
    max_display_chars: int = 2_000,
) -> SessionResult:
    """Run an interactive annotation session over ``items``."""
    latest = latest_labels(store)
    remaining_items = [item for item in items if item.id not in latest]
    session_labelled_ids: set[str] = set()
    skipped_count = 0
    last_labelled_id: str | None = None

    # Build legend, preserving the caller's key order.
    schema_parts = [f"{k}={v}" for k, v in schema.mapping.items()]
    legend = "label [" + " ".join(schema_parts) + " s=skip u=undo q=quit]: "

    index = 0
    while index < len(remaining_items):
        item = remaining_items[index]
        display_id = _sanitize(item.id, max_display_chars)
        display_prompt = _sanitize(item.prompt, max_display_chars)
        display_output = _sanitize(item.output, max_display_chars)
        output_fn(display_id)
        output_fn(display_prompt)
        output_fn(display_output)

        try:
            raw = input_fn(legend).strip()
        except EOFError:
            break  # treated as 'q'

        if raw == "q":
            break
        elif raw == "?":
            output_fn(legend[:-2])  # legend without trailing ": "
            continue
        elif raw == "s":
            skipped_count += 1
            index += 1
            continue
        elif raw == "u":
            if last_labelled_id is None:
                output_fn("nothing to undo")
                continue
            prev_item = next((it for it in remaining_items if it.id == last_labelled_id), None)
            if prev_item is None:
                output_fn("nothing to undo")
                continue
            undo_record: dict[str, object] = {
                "id": last_labelled_id,
                "label": None,
                "annotator": annotator,
                "at": clock(),
            }
            _append_record(store, undo_record)
            session_labelled_ids.discard(last_labelled_id)
            last_labelled_id = None
            index = remaining_items.index(prev_item)
            continue
        elif raw in schema.mapping:
            label_value = schema.mapping[raw]
            record: dict[str, object] = {
                "id": item.id,
                "label": label_value,
                "annotator": annotator,
                "at": clock(),
            }
            _append_record(store, record)
            session_labelled_ids.add(item.id)
            last_labelled_id = item.id
            index += 1
            continue
        else:
            key_display = raw[:20]
            output_fn(f"unknown key '{key_display}'")
            continue

    final_latest = latest_labels(store)
    remaining_count = sum(1 for item in items if item.id not in final_latest)
    return SessionResult(
        labelled=len(session_labelled_ids), skipped=skipped_count, remaining=remaining_count
    )


def cohen_kappa(a: Mapping[str, str], b: Mapping[str, str]) -> Agreement:
    """Compute Cohen's kappa between two annotators over common ids."""
    common_ids = [id for id in a if id in b]
    if not common_ids:
        raise AnnotationError("no_overlap", "no common ids between the two annotations")
    n = len(common_ids)
    observed = sum(1 for id in common_ids if a[id] == b[id]) / n
    labels = sorted(set(a.values()) | set(b.values()))
    pa_counts = {label: sum(1 for id in common_ids if a[id] == label) / n for label in labels}
    pb_counts = {label: sum(1 for id in common_ids if b[id] == label) / n for label in labels}
    expected = sum(pa_counts[label] * pb_counts[label] for label in labels)
    kappa = 1.0 if observed == 1.0 else 0.0
    if expected != 1.0:
        kappa = (observed - expected) / (1 - expected)
    return Agreement(n=n, observed=observed, expected=expected, kappa=kappa)
