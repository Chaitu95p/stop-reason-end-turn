# Module 4 — Prompt Engineering & Structured Output

**Exam domain weight: 20%**

Covers how to write explicit criteria, use few-shot examples, enforce structured output via `tool_use`, validate and retry, batch-process at scale, and run multi-pass reviews.

## Scripts

| Script | Task | Key concept |
|--------|------|-------------|
| `01_explicit_criteria.py` | 4.1 Explicit Criteria | Measurable rubrics over vague adjectives |
| `02_few_shot_prompting.py` | 4.2 Few-Shot Prompting | Example count and diversity for consistency |
| `03_structured_output_tool_use.py` | 4.3 Structured Output via tool_use | `tool_choice: {"type": "tool", "name": "X"}` forces schema |
| `04_validation_retry_loop.py` | 4.4 Validation-Retry Loop | Send validation errors back; `conflict_detected`; `detected_pattern` |
| `05_batch_processing.py` | 4.5 Batch Processing | Message Batches API; SLA formula; `custom_id` correlation |
| `06_multi_pass_review.py` | 4.6 Multi-Pass Review | Per-file pass → cross-file integration; independent reviewer |
| `07_prefill_technique.py` | Bonus **(OUT OF SCOPE)** | Prefill, temperature, XML prompts — not in 27 task statements |

## Run

```bash
# All in-scope scripts in order (skip bonus)
cd modules/module-4 && for f in 01 02 03 04 05 06; do echo "=== 0${f##0}_*.py ===" && uv run python 0${f}*.py; done

# Single script
uv run python 04_validation_retry_loop.py
```

## Key exam facts

- **`tool_choice: {"type": "tool", "name": "X"}`** forces Claude to call a specific tool — the most reliable way to get structured output.
- **Validation-retry loop:** retries fix format/structural/semantic errors; they **cannot** fix information absent from the source document.
- **`detected_pattern` field:** tracks which code construct triggered a finding — enables false positive analysis.
- **Message Batches API:** 50% cost savings, up to 24-hour window, no guaranteed latency SLA, no multi-turn tool calling.
- **SLA formula:** `submission_window = SLA_hours - max_batch_duration_hours`. Example: SLA=30h → submit every 6h max.
- **Multi-pass review:** Pass 1 = per-file (prevents attention dilution); Pass 2 = cross-file integration (catches spanning issues).
- **`07_prefill_technique.py` is out of scope** for the CCA-F exam — study it only after covering all 27 in-scope task statements.
