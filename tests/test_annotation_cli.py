"""Tests for annotation_cli public API and CLI."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from annotation_cli import (
    AnnotationError,
    Item,
    LabelSchema,
    SessionResult,
    annotate,
    cohen_kappa,
    latest_labels,
    load_items,
)
from annotation_cli.__main__ import main


def write_lines(path: Path, lines: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for obj in lines:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_store(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------- LabelSchema ----------
def test_label_schema_valid():
    schema = LabelSchema({"g": "good", "b": "bad"})
    assert schema.mapping == {"g": "good", "b": "bad"}


def test_label_schema_reserved_keys():
    for key in ["u", "s", "q", "?"]:
        with pytest.raises(AnnotationError) as exc:
            LabelSchema({key: "value"})
        assert exc.value.code == "invalid_schema"


def test_label_schema_reserved_quit_ish():
    with pytest.raises(AnnotationError) as exc:
        LabelSchema({"q": "quit-ish"})
    assert exc.value.code == "invalid_schema"


def test_label_schema_key_length():
    with pytest.raises(AnnotationError, match="single-character"):
        LabelSchema({"ab": "value"})
    with pytest.raises(AnnotationError):
        LabelSchema({"": "value"})


def test_label_schema_label_length():
    with pytest.raises(AnnotationError):
        LabelSchema({"a": ""})
    with pytest.raises(AnnotationError):
        LabelSchema({"a": "x" * 41})


def test_label_schema_entry_count():
    with pytest.raises(AnnotationError):
        LabelSchema({})
    many = {chr(ord("a") + i): "v" for i in range(10)}
    with pytest.raises(AnnotationError):
        LabelSchema(many)


def test_label_schema_non_mapping():
    with pytest.raises(AnnotationError):
        LabelSchema(["a", "b"])  # type: ignore[arg-type]


# ---------- load_items ----------
def test_load_items_basic(tmp_path: Path):
    p = tmp_path / "items.jsonl"
    write_lines(
        p,
        [
            {"id": "i1", "prompt": "hello", "output": "world"},
            {"id": "i2", "output": "no prompt"},
        ],
    )
    items = load_items(p)
    assert len(items) == 2
    assert items[0] == Item("i1", "hello", "world")
    assert items[1].prompt == ""


def test_load_items_empty(tmp_path: Path):
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    assert load_items(p) == []


def test_load_items_invalid_json(tmp_path: Path):
    p = tmp_path / "bad.jsonl"
    p.write_text("not json\n", encoding="utf-8")
    with pytest.raises(AnnotationError) as exc:
        load_items(p)
    assert exc.value.code == "invalid_item"


def test_load_items_missing_output(tmp_path: Path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"id": "i1"}\n', encoding="utf-8")
    with pytest.raises(AnnotationError, match="output"):
        load_items(p)


def test_load_items_bad_prompt_type(tmp_path: Path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"id": "i1", "output": "o", "prompt": 5}\n', encoding="utf-8")
    with pytest.raises(AnnotationError, match="prompt"):
        load_items(p)


def test_load_items_invalid_utf8(tmp_path: Path):
    p = tmp_path / "bad.jsonl"
    p.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(AnnotationError) as exc:
        load_items(p)
    assert exc.value.code == "invalid_item"


def test_load_items_duplicate_id(tmp_path: Path):
    p = tmp_path / "dup.jsonl"
    write_lines(
        p,
        [
            {"id": "i1", "output": "o1"},
            {"id": "i1", "output": "o2"},
        ],
    )
    with pytest.raises(AnnotationError) as exc:
        load_items(p)
    assert exc.value.code == "duplicate_id"
    assert "line 2" in str(exc.value)


def test_load_items_line_too_large_default_limit(tmp_path: Path):
    p = tmp_path / "big.jsonl"
    p.write_text(json.dumps({"id": "i1", "output": "x" * 1_000_001}), encoding="utf-8")
    with pytest.raises(AnnotationError) as exc:
        load_items(p)
    assert exc.value.code == "line_too_large"


def test_load_items_line_too_large(tmp_path: Path):
    p = tmp_path / "large.jsonl"
    big_line = '{"id": "i1", "output": "' + "x" * 100 + '"}\n'
    p.write_text(big_line, encoding="utf-8")
    with pytest.raises(AnnotationError, match="line_too_large"):
        load_items(p, max_line_chars=10)


def test_load_items_too_many_items(tmp_path: Path):
    p = tmp_path / "many.jsonl"
    lines = [{"id": f"i{i}", "output": "o"} for i in range(5)]
    write_lines(p, lines)
    with pytest.raises(AnnotationError, match="too_many_items"):
        load_items(p, max_items=3)


# ---------- latest_labels ----------
def test_latest_labels_basic(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    write_lines(
        store,
        [
            {"id": "i1", "label": "good", "annotator": "a", "at": 1.0},
            {"id": "i2", "label": "bad", "annotator": "a", "at": 2.0},
        ],
    )
    assert latest_labels(store) == {"i1": "good", "i2": "bad"}


def test_latest_labels_undo(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    write_lines(
        store,
        [
            {"id": "i1", "label": "good", "annotator": "a", "at": 1.0},
            {"id": "i1", "label": None, "annotator": "a", "at": 2.0},
        ],
    )
    assert latest_labels(store) == {}


def test_latest_labels_corrupt_line(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    store.write_text("not json\n", encoding="utf-8")
    with pytest.raises(AnnotationError) as exc:
        latest_labels(store)
    assert exc.value.code == "corrupt_store"
    assert "line 1" in str(exc.value)


def test_latest_labels_invalid_utf8(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    store.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(AnnotationError) as exc:
        latest_labels(store)
    assert exc.value.code == "corrupt_store"


def test_latest_labels_missing_file(tmp_path: Path):
    assert latest_labels(tmp_path / "nonexistent") == {}


# ---------- annotate ----------
def fake_clock():
    start = 100.0

    def clock() -> float:
        nonlocal start
        start += 1.0
        return start

    return clock


def make_items() -> list[Item]:
    return [
        Item("i1", "prompt1", "output1"),
        Item("i2", "prompt2", "output2"),
        Item("i3", "prompt3", "output3"),
    ]


def run_annotate(
    inputs: list[str],
    items: list[Item],
    store: Path,
    schema: LabelSchema | None = None,
    max_display_chars: int = 2000,
) -> tuple[SessionResult, list[str], list[dict]]:
    output_lines: list[str] = []
    clock = fake_clock()
    if schema is None:
        schema = LabelSchema({"g": "good", "b": "bad"})
    result = annotate(
        items,
        schema,
        annotator="tester",
        store=store,
        input_fn=lambda prompt: inputs.pop(0) if inputs else "q",
        output_fn=lambda s: output_lines.append(s),
        clock=clock,
        max_display_chars=max_display_chars,
    )
    return result, output_lines, read_store(store)


def test_annotate_empty_items(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    result = annotate(
        [],
        LabelSchema({"g": "good"}),
        annotator="t",
        store=store,
        input_fn=lambda prompt: "q",
        output_fn=lambda s: None,
    )
    assert result == SessionResult(labelled=0, skipped=0, remaining=0)
    assert not store.exists()


def test_annotate_uses_schema_insertion_order_in_legend(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    prompts: list[str] = []

    def input_fn(prompt: str) -> str:
        prompts.append(prompt)
        return "q"

    annotate(
        [Item("i1", "", "o")],
        LabelSchema({"g": "good", "b": "bad"}),
        annotator="t",
        store=store,
        input_fn=input_fn,
        output_fn=lambda s: None,
    )
    assert prompts == ["label [g=good b=bad s=skip u=undo q=quit]: "]


def test_annotate_unicode_output_intact(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    items = [Item("i1", "🚀 café", "naïve 你好")]
    result, out, _records = run_annotate(["g", "q"], items, store)
    assert result == SessionResult(labelled=1, skipped=0, remaining=0)
    assert out[1] == "🚀 café"
    assert out[2] == "naïve 你好"
    assert "\\u" not in out[1] and "\\u" not in out[2]
    assert latest_labels(store) == {"i1": "good"}


def test_annotate_basic_acceptance_1(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    inputs = ["g", "x", "b", "q"]
    items = make_items()
    result, out, records = run_annotate(inputs, items, store)
    assert result == SessionResult(labelled=2, skipped=0, remaining=1)
    assert len(records) == 2
    assert records[0]["id"] == "i1" and records[0]["label"] == "good"
    assert records[1]["id"] == "i2" and records[1]["label"] == "bad"
    assert "unknown key 'x'" in out


def test_annotate_resume(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    write_lines(
        store,
        [
            {"id": "i1", "label": "good", "annotator": "other", "at": 1.0},
            {"id": "i2", "label": "bad", "annotator": "other", "at": 2.0},
        ],
    )
    items = make_items()
    inputs = ["g", "q"]
    result, out, records = run_annotate(inputs, items, store)
    assert result == SessionResult(labelled=1, skipped=0, remaining=0)
    assert "i1" not in out and "i2" not in out and "i3" in out
    assert len(records) == 3
    assert records[-1]["id"] == "i3" and records[-1]["label"] == "good"


def test_annotate_undo_acceptance_3(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    items = make_items()
    inputs = ["g", "u", "b", "q"]
    result, _out, records = run_annotate(inputs, items, store)
    assert result == SessionResult(labelled=1, skipped=0, remaining=2)
    assert len(records) == 3
    assert [r["label"] for r in records] == ["good", None, "bad"]
    assert latest_labels(store) == {"i1": "bad"}


def test_annotate_undo_nothing_to_undo(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    items = make_items()
    inputs = ["u", "g", "q"]
    result, out, _records = run_annotate(inputs, items, store)
    assert "nothing to undo" in out
    assert result == SessionResult(labelled=1, skipped=0, remaining=2)


def test_annotate_eof_treated_as_quit(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    items = make_items()

    def eof_input(prompt: str) -> str:
        raise EOFError

    output: list[str] = []
    result = annotate(
        items,
        LabelSchema({"g": "good"}),
        annotator="t",
        store=store,
        input_fn=eof_input,
        output_fn=output.append,
        clock=time.time,
    )
    assert result == SessionResult(0, 0, 3)


def test_annotate_question_mark_reprints_legend(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    items = make_items()
    inputs = ["?", "g", "q"]
    result, out, _records = run_annotate(inputs, items, store)
    assert any("label [" in line for line in out)
    assert result.labelled == 1


def test_annotate_skip(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    items = make_items()
    inputs = ["g", "s", "q"]
    result, _out, records = run_annotate(inputs, items, store)
    assert result == SessionResult(labelled=1, skipped=1, remaining=2)
    assert len(records) == 1


def test_annotate_sanitize_escape(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    item = Item("i1", "", "red \x1b[31m text")
    items = [item]
    inputs = ["g", "q"]
    _result, out, _records = run_annotate(inputs, items, store)
    output_line = out[2] if len(out) >= 3 else ""
    assert "\x1b" not in output_line
    assert "\\x1b[31m" in output_line
    assert output_line == "red \\x1b[31m text"


def test_annotate_truncation(tmp_path: Path):
    store = tmp_path / "store.jsonl"
    long_output = "a" * 2500
    item = Item("i1", "", long_output)
    items = [item]
    inputs = ["g", "q"]
    _result, out, _records = run_annotate(inputs, items, store, max_display_chars=2000)
    output_line = out[2]
    assert output_line.startswith("a" * 2000)
    assert output_line.endswith(" [truncated 500 chars]")
    assert len(output_line) == 2000 + len(" [truncated 500 chars]")


# ---------- cohen_kappa ----------
def test_cohen_kappa_acceptance():
    a = {
        "i1": "g",
        "i2": "g",
        "i3": "b",
        "i4": "b",
        "i5": "g",
        "i6": "b",
        "i7": "g",
        "i8": "g",
    }
    b = {
        "i1": "g",
        "i2": "b",
        "i3": "b",
        "i4": "b",
        "i5": "g",
        "i6": "g",
        "i7": "g",
        "i8": "g",
    }
    agreement = cohen_kappa(a, b)
    assert agreement.n == 8
    assert agreement.observed == pytest.approx(0.75, abs=1e-12)
    assert agreement.expected == pytest.approx(0.53125, abs=1e-12)
    assert agreement.kappa == pytest.approx(0.4666666666666667, abs=1e-12)


def test_cohen_kappa_no_overlap():
    a = {"i1": "g"}
    b = {"i2": "g"}
    with pytest.raises(AnnotationError) as exc:
        cohen_kappa(a, b)
    assert exc.value.code == "no_overlap"


# ---------- CLI main ----------
def test_main_agree(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    a_path = tmp_path / "a.jsonl"
    b_path = tmp_path / "b.jsonl"
    write_lines(
        a_path,
        [
            {"id": f"i{i}", "label": label, "annotator": "a", "at": 0.0}
            for i, label in enumerate(["g", "g", "b", "b", "g", "b", "g", "g"], start=1)
        ],
    )
    write_lines(
        b_path,
        [
            {"id": f"i{i}", "label": label, "annotator": "b", "at": 0.0}
            for i, label in enumerate(["g", "b", "b", "b", "g", "g", "g", "g"], start=1)
        ],
    )
    rc = main(["agree", str(a_path), str(b_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip() == "n=8 observed=0.750 expected=0.531 kappa=0.467"


def test_main_agree_no_overlap(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    a_path = tmp_path / "a.jsonl"
    b_path = tmp_path / "b.jsonl"
    write_lines(a_path, [{"id": "i1", "label": "g", "annotator": "a", "at": 0.0}])
    write_lines(b_path, [{"id": "i2", "label": "g", "annotator": "b", "at": 0.0}])
    rc = main(["agree", str(a_path), str(b_path)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "no_overlap" in captured.err


def test_main_usage_error_returns_2(capsys: pytest.CaptureFixture[str]):
    rc = main(["run"])
    assert rc == 2


def test_main_run_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    rc = main(
        [
            "run",
            str(tmp_path / "missing.jsonl"),
            "--store",
            str(tmp_path / "store.jsonl"),
            "--annotator",
            "a",
            "--labels",
            "g=good",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "error" in captured.err


def test_main_run_invalid_labels_args(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    rc = main(
        [
            "run",
            str(tmp_path / "items.jsonl"),
            "--store",
            str(tmp_path / "store.jsonl"),
            "--annotator",
            "a",
            "--labels",
            "g",  # missing =value
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "invalid label format" in captured.err


def test_main_run_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    items_file = tmp_path / "items.jsonl"
    store_file = tmp_path / "store.jsonl"
    write_lines(items_file, [{"id": "i1", "output": "o"}])

    called = {}

    def fake_annotate(items, schema, **kwargs):
        called["items"] = items
        called["schema"] = schema
        called.update(kwargs)
        return SessionResult(1, 0, 0)

    monkeypatch.setattr("annotation_cli.__main__.annotate", fake_annotate)
    rc = main(
        [
            "run",
            str(items_file),
            "--store",
            str(store_file),
            "--annotator",
            "a",
            "--labels",
            "g=good",
        ]
    )
    assert rc == 0
    assert called["annotator"] == "a"
    assert called["store"] == store_file
    assert called["schema"].mapping == {"g": "good"}
    assert called["max_display_chars"] == 2000
