"""
Domain 4 - Task 4.4: Validation-Retry Loop

EXAM CONCEPTS:
  Pattern:
    1. Claude generates structured output.
    2. Your code validates it (schema + semantic checks).
    3. If validation fails, send the error BACK with the original document.
    4. Claude self-corrects. Typically 1-2 retries resolve formatting issues.

  CRITICAL exam nuances:
    Retries FIX: format errors, structural errors, wrong field types.
    Retries CANNOT FIX: required information absent from the source document.
      -> Info in an external document not provided = retries just fabricate values.

  detected_pattern field (exam-tested):
    Add to each finding to track WHAT code construct triggered the finding.
    Enables systematic analysis of WHY developers dismiss false positives.

  conflict_detected pattern:
    Extract both calculated_total and stated_total.
    Add conflict_detected boolean for inconsistent source data.
    This catches semantic errors that tool_use cannot prevent.

Run: uv run python 04_validation_retry_loop.py
"""

import json
import anthropic

client = anthropic.Anthropic()

NL = chr(10)

ORDER_TOOL = {
    "name": "extract_order",
    "description": "Extract order data from a purchase document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "customer_email": {"type": "string"},
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string"},
                        "qty": {"type": "integer", "minimum": 1},
                        "unit_price": {"type": "number"},
                        # detected_pattern: tracks the exact code construct that triggered
                        # this finding, enabling systematic dismissal-pattern analysis.
                        "detected_pattern": {
                            "type": ["string", "null"],
                            "description": "Pattern detected (e.g., missing_discount, price_mismatch) or null",
                        },
                    },
                    "required": ["sku", "qty", "unit_price"],
                },
            },
            "calculated_total": {
                "type": "number",
                "description": "Sum of qty*unit_price for all items (compute it yourself)",
            },
            "stated_total": {
                "type": ["number", "null"],
                "description": "Total as written in document, or null",
            },
            "conflict_detected": {
                "type": "boolean",
                "description": "True if calculated_total != stated_total (semantic validation)",
            },
        },
        "required": [
            "order_id", "customer_email", "items",
            "calculated_total", "stated_total", "conflict_detected",
        ],
    },
}

# Deliberate mismatch: items sum to $82.50 but document says $80.00
SAMPLE_ORDER = (
    "Order Confirmation" + NL
    + "Order ID: ORD-20240315-001" + NL
    + "Customer: alice@example.com" + NL + NL
    + "Items ordered:" + NL
    + "  Widget A (SKU-001)   qty: 3   @ $12.50 each" + NL
    + "  Gadget B (SKU-002)   qty: 1   @ $45.00 each" + NL + NL
    + "Total charged: $80.00" + NL
)


def validate_extraction(data: dict) -> list:
    """Return list of validation error strings. Empty list = valid."""
    errors = []

    # Semantic check 1: verify calculated_total matches actual math
    if data.get("items"):
        actual_calc = sum(item["qty"] * item["unit_price"] for item in data["items"])
        stated_calc = data.get("calculated_total", 0)
        if abs(actual_calc - stated_calc) > 0.01:
            errors.append(
                "calculated_total {:.2f} is wrong; actual sum is {:.2f}".format(
                    stated_calc, actual_calc
                )
            )

    # Semantic check 2: conflict_detected must match reality
    if data.get("stated_total") is not None and data.get("calculated_total") is not None:
        should_conflict = abs(data["calculated_total"] - data["stated_total"]) > 0.01
        if should_conflict != data.get("conflict_detected", False):
            errors.append(
                "conflict_detected={} is wrong; calculated={} stated={}".format(
                    data.get("conflict_detected"),
                    data.get("calculated_total"),
                    data.get("stated_total"),
                )
            )

    return errors


def extract_with_retry(document: str, max_retries: int = 2):
    messages = [{"role": "user", "content": "Extract order data from:" + NL + NL + document}]

    for attempt in range(max_retries + 1):
        print("  Attempt {}/{}".format(attempt + 1, max_retries + 1))

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=[ORDER_TOOL],
            tool_choice={"type": "tool", "name": "extract_order"},
            messages=messages,
        )

        extracted = None
        tool_use_block = None
        for block in response.content:
            if block.type == "tool_use":
                extracted = block.input
                tool_use_block = block
                break

        if not extracted:
            print("  ERROR: No tool_use block returned.")
            break

        print("  Extracted: " + json.dumps(extracted, indent=4))

        errors = validate_extraction(extracted)
        if not errors:
            print("  VALIDATION PASSED")
            return extracted

        print("  VALIDATION FAILED: " + str(errors))

        if attempt >= max_retries:
            print("  Max retries reached. Returning last extraction.")
            return extracted

        # Feed specific validation errors back for self-correction
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": "Validation errors:" + NL + NL.join("- " + e for e in errors),
                }
            ],
        })

    return None


def demonstrate_absent_info():
    print()
    print("=" * 60)
    print("Retries CANNOT fix absent information")
    print("=" * 60)
    print("Scenario: doc says 'see attached pricing sheet' -- sheet not provided.")
    print("-> Retries will fabricate prices. Solution: nullable fields + flag for human review.")
    print()
    print("Retries CAN fix:")
    print("  - Format errors (wrong date format, wrong field name)")
    print("  - Structural errors (list instead of object)")
    print("  - Semantic errors (calculated_total math is wrong)")
    print()
    print("Retries CANNOT fix:")
    print("  - Information that does not exist in the provided document")
    print("  - Data in an external document that was not included in the prompt")


if __name__ == "__main__":
    print("Demonstrating: Validation-Retry Loop")
    print("Document has conflict: items sum to $82.50 but stated total is $80.00")
    print("=" * 60)

    result = extract_with_retry(SAMPLE_ORDER)

    if result:
        print()
        print("Final result summary:")
        print("  calculated_total : " + str(result.get("calculated_total")))
        print("  stated_total     : " + str(result.get("stated_total")))
        print("  conflict_detected: " + str(result.get("conflict_detected")))
        patterns = [item.get("detected_pattern") for item in result.get("items", [])]
        print("  detected_patterns: " + str(patterns))

    demonstrate_absent_info()

    print()
    print("KEY TAKEAWAY:")
    print("  Retries fix FORMAT errors. They cannot fix absent data.")
    print("  Always extract both calculated_total and stated_total.")
    print("  Add conflict_detected boolean for downstream alerting.")
    print("  Use detected_pattern field to analyze false positive dismissal patterns.")
    print("  Cap retries at 2-3 to avoid infinite loops.")
