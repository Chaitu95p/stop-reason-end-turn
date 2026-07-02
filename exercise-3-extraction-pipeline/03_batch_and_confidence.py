"""
Exercise 3 - Steps 14-15: Message Batches API + Confidence-Based Routing

EXAM CONCEPTS:
  1. Message Batches API characteristics:
     - 50% cost savings vs synchronous
     - Up to 24-hour processing window (not real-time)
     - custom_id per request correlates response back to source doc
     - NO multi-turn tool calling within a batch request (single-turn only)
     - Poll for completion; do not block-wait

  2. Batch resubmission strategy:
     - Group failures by error type
     - Oversized document?  chunk and resubmit
     - Rate-limit?           resubmit later
     - Validation failure?   resubmit with sharper prompt or fewer docs
     Track: original custom_id -> resubmission custom_id lineage.

  3. SLA math for batch:
     If your SLA is 6h and batch worst-case is 24h, you CANNOT rely on
     batch for that SLA -- fall back to sync API for the tail.

  4. Field-level confidence enables selective human review:
     - Extract confidence PER FIELD (author, year, category, ...)
       not per document.
     - Route by weighted threshold: safety-relevant fields (e.g. dosage,
       amount) get lower thresholds than nice-to-have fields.

  Mnemonic: BATCH
    Bill 50% less than synchronous
    Async 24h window -- SLA-check before adopting
    Track via custom_id
    Chunk oversized docs on resubmit
    Halt-to-human on low field confidence

Run: uv run python 03_batch_and_confidence.py
"""

import json
import anthropic

client = anthropic.Anthropic()  # not actually called; batch code below is illustrative
NL = chr(10)


# ---------------------------------------------------------------------------
# STEP 14 (a): Building a batch of 100 requests
# ---------------------------------------------------------------------------
def build_batch_requests(documents: list[dict]) -> list[dict]:
    """
    documents: [{"id": "DOC-001", "text": "..."}] x 100
    Returns Message Batches API request objects, each tagged with custom_id.
    """
    requests = []
    for d in documents:
        requests.append({
            "custom_id": d["id"],   # <-- EXAM: this is how you correlate results back
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
                "system": "Extract the record.",
                "tools": [{"name": "record_extraction",
                           "description": "record",
                           "input_schema": {"type": "object", "properties": {}}}],
                "tool_choice": {"type": "tool", "name": "record_extraction"},
                "messages": [{"role": "user",
                              "content": f"document_id={d['id']}" + NL + d["text"]}],
            },
        })
    return requests


# ---------------------------------------------------------------------------
# STEP 14 (b): Handling per-custom_id failures + resubmission
# ---------------------------------------------------------------------------
MAX_TOKENS_PER_REQUEST = 190_000

def classify_batch_failure(request: dict, error_type: str) -> str:
    """Return one of: 'chunk', 'retry_later', 'human_review'."""
    if error_type == "context_length_exceeded":
        return "chunk"
    if error_type in {"rate_limited", "server_error"}:
        return "retry_later"
    return "human_review"


def chunk_document(text: str, chunk_chars: int = 40_000) -> list[str]:
    """Simple char-based chunking. Overlap by 400 to preserve context."""
    if len(text) <= chunk_chars:
        return [text]
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + chunk_chars])
        i += chunk_chars - 400
    return chunks


def resubmit_failed(batch_id: str, failed: list[dict], original_docs: dict[str, str]) -> list[dict]:
    """
    failed: [{"custom_id": "DOC-042", "error_type": "context_length_exceeded"}, ...]
    Returns fresh batch requests. Chunked docs use new custom_ids that
    encode lineage: 'DOC-042__chunk_0', 'DOC-042__chunk_1'.
    """
    new_requests = []
    for f in failed:
        action = classify_batch_failure(f, f["error_type"])
        cid = f["custom_id"]
        if action == "human_review":
            print(f"  {cid}: {f['error_type']} -> route to human review")
            continue
        if action == "retry_later":
            print(f"  {cid}: {f['error_type']} -> requeue as-is")
            new_requests.append({"custom_id": cid + "__retry", "params": {}})
            continue
        # chunk
        for i, chunk in enumerate(chunk_document(original_docs[cid])):
            new_requests.append({
                "custom_id": f"{cid}__chunk_{i}",
                "params": {"messages": [{"role": "user", "content": chunk}]},
            })
    return new_requests


# ---------------------------------------------------------------------------
# STEP 14 (c): SLA math -- 24h worst case
# ---------------------------------------------------------------------------
def can_meet_sla(batch_size: int, sla_hours: float) -> tuple[bool, str]:
    typical_hours = min(1 + batch_size / 500, 6)
    worst_case_hours = 24
    if sla_hours >= worst_case_hours:
        return True, f"OK -- SLA {sla_hours}h >= worst-case 24h"
    if sla_hours >= typical_hours:
        return False, (f"RISKY -- typical ~{typical_hours:.1f}h fits, but worst-case 24h does not. "
                       f"Send tail via sync API for guarantee.")
    return False, f"NO -- typical ~{typical_hours:.1f}h already exceeds SLA {sla_hours}h."


# ---------------------------------------------------------------------------
# STEP 15: Field-level confidence + human-review routing
#                       ^^ LEARNING-MODE contribution point below
# ---------------------------------------------------------------------------

# Suppose the extraction tool now includes a companion confidence field per
# extracted field, produced by the model:
SAMPLE_EXTRACTIONS = [
    {"document_id": "DOC-A",
     "fields": {"author": "K. Ito", "year": 2019, "category": "research", "dosage_mg": 200},
     "confidence": {"author": 0.95, "year": 0.98, "category": 0.90, "dosage_mg": 0.60}},

    {"document_id": "DOC-B",
     "fields": {"author": None, "year": 2024, "category": "other", "dosage_mg": None},
     "confidence": {"author": 1.00, "year": 0.85, "category": 0.55, "dosage_mg": 1.00}},
    #                        ^^ 1.00 because "null with confidence" == certain absence

    {"document_id": "DOC-C",
     "fields": {"author": "Anonymous", "year": 1998, "category": "opinion", "dosage_mg": 500},
     "confidence": {"author": 0.40, "year": 0.75, "category": 0.80, "dosage_mg": 0.70}},
]

FIELD_THRESHOLDS = {
    # Safety-critical fields have STRICTER thresholds.
    "dosage_mg": 0.90,
    "year":      0.70,
    "category":  0.70,
    "author":    0.60,
}


def route_for_human_review(extraction: dict) -> tuple[bool, list[str]]:
    """
    Return (needs_review, reasons).

    ---------------------------------------------------------------------------
    LEARNING-MODE TODO -- your routing policy goes here.

    Exam step 15 says: "have the model output field-level confidence scores,
    route low-confidence extractions to human review, and analyze accuracy
    by document type and field to verify consistent performance."

    Fill in 5-10 lines that:
      1. For each field in extraction["confidence"], compare to FIELD_THRESHOLDS.
      2. If ANY safety-critical field (dosage_mg) is below threshold, ALWAYS route.
      3. If TWO OR MORE non-critical fields are below threshold, route.
      4. If only one non-critical field is low, PASS but flag the field.
      5. Populate `reasons` with human-readable strings ("dosage_mg 0.60 < 0.90").

    Alternative policies to consider (talk trade-offs before implementing):
      - Weighted sum: sum(confidence * field_weight) < 0.85 -> route
      - Per-doc-type thresholds: research papers looser, medical stricter
      - Absolute floor: any field < 0.50 always routes regardless of weights
    ---------------------------------------------------------------------------
    """
    reasons = []
    critical_low = False
    non_critical_low = 0
    for field, conf in extraction["confidence"].items():
        threshold = FIELD_THRESHOLDS.get(field, 0.7)
        if conf < threshold:
            reasons.append(f"{field} {conf:.2f} < {threshold:.2f}")
            if field == "dosage_mg":
                critical_low = True
            else:
                non_critical_low += 1
    needs_review = critical_low or non_critical_low >= 2
    return needs_review, reasons


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Batch request construction (100 docs)")
    print(sep)
    docs = [{"id": f"DOC-{i:03d}", "text": f"sample text {i}"} for i in range(100)]
    reqs = build_batch_requests(docs)
    print(f"  Built {len(reqs)} requests. First custom_id: {reqs[0]['custom_id']}")
    print(f"  Last  custom_id: {reqs[-1]['custom_id']}")
    print("  (Not submitted -- batch submission is out of scope for this exercise.)")

    print()
    print(sep)
    print("DEMO 2: Resubmit failures with lineage-tagged custom_ids")
    print(sep)
    failures = [
        {"custom_id": "DOC-042", "error_type": "context_length_exceeded"},
        {"custom_id": "DOC-057", "error_type": "rate_limited"},
        {"custom_id": "DOC-089", "error_type": "invalid_api_key"},
    ]
    originals = {"DOC-042": "x" * 200_000, "DOC-057": "short", "DOC-089": "short"}
    resub = resubmit_failed("batch_abc", failures, originals)
    print(f"  Resubmit count: {len(resub)}")
    for r in resub[:3]:
        print(f"    -> {r['custom_id']}")

    print()
    print(sep)
    print("DEMO 3: SLA feasibility check")
    print(sep)
    for sla_h in [4, 12, 24, 36]:
        ok, msg = can_meet_sla(batch_size=100, sla_hours=sla_h)
        print(f"  SLA={sla_h}h: {'PASS' if ok else 'FAIL'} -- {msg}")

    print()
    print(sep)
    print("DEMO 4: Confidence-based human review routing")
    print(sep)
    for ex in SAMPLE_EXTRACTIONS:
        needs, reasons = route_for_human_review(ex)
        label = "REVIEW" if needs else "AUTO-ACCEPT"
        print(f"  {ex['document_id']}: {label}  {reasons}")

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Message Batches: 50% cost, up to 24h latency, custom_id correlates")
    print("     each response back to its source document.")
    print("  2. Failure lineage matters: encode 'DOC-042__chunk_0' so you can")
    print("     stitch chunked results back to the original document.")
    print("  3. Do the SLA math BEFORE choosing batch -- worst-case 24h rules")
    print("     out batch for anything with a sub-day SLA guarantee.")
    print("  4. Field-level confidence + PER-FIELD thresholds beat a single")
    print("     doc-level threshold; safety-critical fields (dose, amount) get")
    print("     strictest thresholds regardless of overall document confidence.")
    print("  Mnemonic BATCH: 50% Bill, 24h Async, custom_id Track,")
    print("     Chunk oversized, Halt-to-human on low field confidence.")
