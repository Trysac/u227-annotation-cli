# Project record

## Objective

Label model outputs in the terminal with single-key choices, undo, resumable append-only JSONL storage, safe display of untrusted text and Cohen's kappa agreement.

## Scope

- In scope: `LabelSchema` validation; `load_items` JSONL loading with item and line limits; the `annotate` terminal session with resume, skip, undo, quit and legend help; append-only JSONL storage with `latest_labels`; `cohen_kappa` agreement over common ids; the `run` and `agree` CLI subcommands; sanitised and truncated display of id, prompt and output text.
- Out of scope: multi-label or span annotation, curses UI, web UI, and Krippendorff alpha.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays pending measurement.

| Metric | Value |
|---|---|
| Tokens (input / output) | 1579012 / 103621 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.1344 |

## Factory run u227 (measured from API usage)

| Date (UTC) | Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 2026-11-10 | generation | deepseek-v4-pro | yes | 1746 | 27273 | 0 | 3328 | 0.0552 |
| 2026-11-10 | fix-1 | deepseek-flash | no | 21449 | 25207 | 0 | 408064 | 0.0196 |
| 2026-11-10 | fix-2 | deepseek-flash | no | 8743 | 2147 | 0 | 40064 | 0.0027 |
| 2026-11-10 | audit | deepseek-flash | no | 39206 | 20735 | 0 | 403200 | 0.0195 |
| 2026-11-10 | fix-3 | deepseek-flash | no | 19994 | 14131 | 0 | 527232 | 0.0131 |
| 2026-11-10 | docs | deepseek-flash | no | 105730 | 14128 | 0 | 256 | 0.0243 |

Total: $0.1344. Prices: deepseek line, as measured by its adapter. Providers serve the current version of each model id, so the date tells which version answered; versions, launch stages and price sources per line are in the factory's model register (docs/MODELS.md).
