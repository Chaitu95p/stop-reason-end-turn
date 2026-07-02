"""
Domain 5 - Task 5.5: Human Review Routing via Confidence Scores

EXAM CONCEPTS:
  1. Field-level confidence scores: instead of one overall confidence,
     assign a confidence score (0.0-1.0) to each extracted field.
     Enables surgical routing — only uncertain fields go to human review.

  2. Stratified sampling: sample BOTH high-confidence and low-confidence
     outputs for quality measurement. Sampling only low-confidence outputs
     misses systematic errors in "confident" extractions.

  3. Routing logic thresholds:
     confidence >= 0.9  → auto-process (high confidence)
     0.7 <= conf < 0.9  → flag for spot-check (medium confidence)
     confidence < 0.7   → route to human review (low confidence)

  4. Aggregate accuracy hides per-segment issues:
     "97% overall accuracy" may hide 60% accuracy on handwritten forms.
     Report accuracy by document type AND field, not just overall.

  5. Human-in-the-loop integration: agent produces output + confidence,
     routes to review queue for uncertain fields only.
     Full human review reserved for low-confidence documents.

Run: uv run python 05_human_review_confidence.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Extraction tool with per-field confidence
# ---------------------------------------------------------------------------
EXTRACT_WITH_CONFIDENCE_TOOL = {
    "name": "extract_invoice_with_confidence",
    "description": (
        "Extract invoice fields and assign a confidence score (0.0-1.0) to each field. "
        "confidence=1.0: unambiguous. confidence=0.7-0.9: minor uncertainty. "
        "confidence<0.7: ambiguous, unclear, or possibly OCR error."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "invoice_number_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "vendor_name": {"type": "string"},
            "vendor_name_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "total_due": {"type": "number"},
            "total_due_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "issue_date": {"type": ["string", "null"]},
            "issue_date_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "due_date": {"type": ["string", "null"]},
            "due_date_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "payment_status": {
                "type": "string",
                "enum": ["paid", "unpaid", "overdue", "unclear"],
            },
            "payment_status_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "invoice_number", "invoice_number_confidence",
            "vendor_name", "vendor_name_confidence",
            "total_due", "total_due_confidence",
            "issue_date", "issue_date_confidence",
            "due_date", "due_date_confidence",
            "payment_status", "payment_status_confidence",
        ],
    },
}


def extract_invoice(invoice_text: str) -> dict:
    """Extract invoice fields with per-field confidence scores."""
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="You are an invoice extraction specialist. Assign confidence scores honestly — do not inflate confidence for unclear fields.",
        tools=[EXTRACT_WITH_CONFIDENCE_TOOL],
        tool_choice={"type": "tool", "name": "extract_invoice_with_confidence"},
        messages=[{"role": "user", "content": f"Extract from this invoice:\n\n{invoice_text}"}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    return {}


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------
HIGH_CONFIDENCE_THRESHOLD = 0.90
REVIEW_THRESHOLD = 0.70


def route_extraction(extracted: dict) -> dict:
    """
    Route each field based on its confidence score.
    Returns: auto_process fields, spot_check fields, human_review fields.
    """
    auto_process = {}
    spot_check = {}
    human_review = {}

    fields = ["invoice_number", "vendor_name", "total_due", "issue_date", "due_date", "payment_status"]
    for field in fields:
        value = extracted.get(field)
        confidence = extracted.get(f"{field}_confidence", 0.0)

        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            auto_process[field] = {"value": value, "confidence": confidence}
        elif confidence >= REVIEW_THRESHOLD:
            spot_check[field] = {"value": value, "confidence": confidence}
        else:
            human_review[field] = {"value": value, "confidence": confidence}

    # Document-level routing decision
    low_conf_count = len(human_review)
    needs_full_review = low_conf_count >= 2  # 2+ low-confidence fields → full human review

    return {
        "auto_process": auto_process,
        "spot_check": spot_check,
        "human_review": human_review,
        "needs_full_document_review": needs_full_review,
        "routing_summary": f"{len(auto_process)} auto / {len(spot_check)} spot-check / {len(human_review)} human-review",
    }


# ---------------------------------------------------------------------------
# Stratified sampling demo
# ---------------------------------------------------------------------------
def show_stratified_sampling() -> None:
    sep = "-" * 50
    print(sep)
    print("STRATIFIED SAMPLING: measure accuracy across confidence tiers")
    print()

    # Simulated batch results
    batch_results = [
        {"field": "invoice_number", "confidence": 0.99, "correct": True},
        {"field": "total_due", "confidence": 0.95, "correct": True},
        {"field": "vendor_name", "confidence": 0.92, "correct": True},
        {"field": "invoice_number", "confidence": 0.85, "correct": True},
        {"field": "due_date", "confidence": 0.80, "correct": False},   # wrong
        {"field": "issue_date", "confidence": 0.75, "correct": True},
        {"field": "payment_status", "confidence": 0.60, "correct": False},  # wrong
        {"field": "total_due", "confidence": 0.55, "correct": False},       # wrong
        {"field": "vendor_name", "confidence": 0.45, "correct": True},
        {"field": "due_date", "confidence": 0.40, "correct": False},        # wrong
    ]

    # Overall accuracy
    overall_correct = sum(1 for r in batch_results if r["correct"])
    print(f"Overall accuracy: {overall_correct}/{len(batch_results)} = {overall_correct/len(batch_results)*100:.0f}%")
    print("(aggregate hides per-tier issues)")
    print()

    # Stratified by confidence tier
    tiers = {
        "high (≥0.9)": [r for r in batch_results if r["confidence"] >= 0.9],
        "medium (0.7-0.9)": [r for r in batch_results if 0.7 <= r["confidence"] < 0.9],
        "low (<0.7)": [r for r in batch_results if r["confidence"] < 0.7],
    }
    for tier, items in tiers.items():
        if items:
            correct = sum(1 for r in items if r["correct"])
            acc = correct / len(items) * 100
            print(f"  {tier}: {correct}/{len(items)} = {acc:.0f}% accuracy")

    print()
    print("ANTI-PATTERN: sample only low-confidence outputs for review.")
    print("  -> Misses systematic errors in high-confidence extractions.")
    print("CORRECT: stratified sample across ALL confidence tiers.")


# ---------------------------------------------------------------------------
# Test invoices
# ---------------------------------------------------------------------------
CLEAR_INVOICE = """
INVOICE #INV-2024-0042
Vendor: Acme Cloud Services
Date: March 15, 2024
Due: April 14, 2024
TOTAL DUE: $320.76
Payment: UNPAID
"""

AMBIGUOUS_INVOICE = """
invoice # INV2024-042 (or INV-2024-42?)
vendor: Acme Cloude Servces (OCR uncertain)
date: 3/15 (year unclear)
due: sometime in April
Total: $3,20.76 (digit grouping unclear)
Paymnt status: (field missing)
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Extract clear invoice with confidence scores")
    print(sep)
    extracted_clear = extract_invoice(CLEAR_INVOICE)
    print("Extracted:")
    print(json.dumps(extracted_clear, indent=2))
    print()
    routing_clear = route_extraction(extracted_clear)
    print("Routing decision:")
    print(f"  {routing_clear['routing_summary']}")
    print(f"  Needs full human review: {routing_clear['needs_full_document_review']}")
    if routing_clear["auto_process"]:
        print(f"  Auto-process: {list(routing_clear['auto_process'].keys())}")
    if routing_clear["spot_check"]:
        print(f"  Spot-check:   {list(routing_clear['spot_check'].keys())}")
    if routing_clear["human_review"]:
        print(f"  Human review: {list(routing_clear['human_review'].keys())}")

    print()
    print(sep)
    print("DEMO 2: Extract ambiguous invoice with confidence scores")
    print(sep)
    extracted_ambig = extract_invoice(AMBIGUOUS_INVOICE)
    print("Extracted:")
    print(json.dumps(extracted_ambig, indent=2))
    print()
    routing_ambig = route_extraction(extracted_ambig)
    print("Routing decision:")
    print(f"  {routing_ambig['routing_summary']}")
    print(f"  Needs full human review: {routing_ambig['needs_full_document_review']}")
    if routing_ambig["human_review"]:
        print(f"  Human review: {list(routing_ambig['human_review'].keys())}")

    print()
    print(sep)
    print("DEMO 3: Stratified sampling for accuracy measurement")
    print(sep)
    show_stratified_sampling()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Field-level confidence (not overall) enables surgical routing.")
    print("     Per-field routing: high→auto, medium→spot-check, low→human review.")
    print("  2. Routing thresholds: ≥0.9 auto-process, 0.7-0.9 spot-check, <0.7 human.")
    print("  3. 2+ low-confidence fields → route entire document for human review.")
    print("  4. Stratified sampling: sample across ALL confidence tiers, not just low.")
    print("     97% overall accuracy may hide 60% accuracy on one document type.")
    print("  5. Aggregate accuracy masks per-segment issues — always disaggregate.")
