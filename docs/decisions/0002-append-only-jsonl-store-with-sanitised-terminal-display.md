# Append-only JSONL store with sanitised terminal display

Status: accepted (generated, pending human review)

## Context

A terminal annotation tool must be resumable, support undo, and safely display untrusted model output. The data must be diffable and portable.

## Decision

Store every annotation decision as an append-only JSONL record with a timestamp. The latest non-null record per item defines its label. Display text is sanitised to replace control/format characters with escape sequences and truncated to a named limit.

## Consequences

Resume and undo are trivial by scanning the store; each record is immutable and diffable. Sanitisation prevents terminal escape injection. The store can grow indefinitely, but line size and item count limits bound per-file memory.
