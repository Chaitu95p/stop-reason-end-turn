# Exercise 3: Structured Data Extraction Pipeline

**Source:** CCA-F Exam Guide, Preparation Exercise 3
**Domains reinforced:** Domain 4 (Prompt Engineering & Structured Output), Domain 5 (Context & Reliability)

## Steps covered

| Step | Script | Concept |
|------|--------|---------|
| 11. JSON schema: required/optional, enum + "other", nullable fields | `01_schema_and_extract.py` | tool_use as structured output |
| 12. Pydantic validation-retry loop | `02_validation_retry.py` | Distinguish resolvable vs unresolvable errors |
| 13. Few-shot examples for structural variety | `02_validation_retry.py` | Format demonstration |
| 14. Message Batches API — 100 docs, custom_id, resubmit failures | `03_batch_and_confidence.py` | Batch API + SLA math (mocked submission) |
| 15. Field-level confidence + human review routing | `03_batch_and_confidence.py` | Confidence-based routing |

## Run

```bash
cd exercise-3-extraction-pipeline
uv sync
export ANTHROPIC_API_KEY=sk-ant-...
uv run python 01_schema_and_extract.py
uv run python 02_validation_retry.py
uv run python 03_batch_and_confidence.py
```

## Mnemonic — EXTRACT

- **E**num with "other" + free-text detail to prevent forced categorization
- **X** (cross): nullable fields prevent fabrication when info absent
- **T**ool_use for guaranteed JSON structure (schema in `input_schema`)
- **R**etry loop feeding the validation error back to the model
- **A**ttribution: track document_id + field to enable review routing
- **C**onfidence scores per field (not per document)
- **T**hreshold routing: low-confidence -> human review queue
