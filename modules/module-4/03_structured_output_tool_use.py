"""
Domain 4 - Task 4.3: Structured Output via tool_use

EXAM CONCEPTS:
  1. Reliability ladder (SANE) -- least to most reliable:
       Simple text instruction  → Claude ignores format instructions often
       Assistant prefill        → start with { to nudge JSON output
       Natural schema in prompt → describe the format, Claude usually follows
       Enforced tool_use        → define input_schema; most reliable

  2. tool_choice options:
       "auto"                       → Claude may return text instead of tool
       "any"                        → Claude MUST call a tool, can choose which
       {"type": "tool", "name": "X"} → forces a SPECIFIC named tool

  3. Nullable fields prevent hallucination: use type: ["string", "null"] for
     optional fields. Without null, Claude invents plausible-looking values
     to satisfy required fields. With null, it can honestly report absence.

  4. "other" + detail pattern: include "other" in enums and a parallel
     <field>_detail string so new categories are captured, not discarded.

  5. "unclear" enum value: signals ambiguity rather than forcing a guess.
     Enables targeted human review of only the ambiguous cases.

  6. tool_use eliminates syntax errors (invalid JSON) but NOT semantic
     errors. Always add semantic validation on top of schema validation.

  Mnemonic: SANE
    S → Simple text instruction    (least reliable)
    A → Assistant prefill
    N → Natural schema in prompt
    E → Enforced tool_use          (most reliable)

Run: uv run python 03_structured_output_tool_use.py
"""

import json
import anthropic

client = anthropic.Anthropic()

INVOICE_TOOL = {
    "name": "extract_invoice",
    "description": "Extract structured data from an invoice document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "vendor_name": {"type": "string"},
            "issue_date": {"type": ["string", "null"], "description": "ISO 8601 date or null"},
            "due_date": {"type": ["string", "null"], "description": "ISO 8601 date or null"},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price": {"type": "number"},
                        "total": {"type": "number"},
                    },
                    "required": ["description", "quantity", "unit_price", "total"],
                },
            },
            "subtotal": {"type": ["number", "null"]},
            "tax": {"type": ["number", "null"]},
            "total_due": {"type": "number"},
            "currency": {
                "type": "string",
                "enum": ["USD", "EUR", "GBP", "CAD", "other"],
                "description": "Use other for any unlisted currency",
            },
            "payment_status": {
                "type": "string",
                "enum": ["paid", "unpaid", "overdue", "unclear"],
            },
        },
        "required": ["invoice_number", "vendor_name", "line_items", "total_due", "currency", "payment_status"],
    },
}

SAMPLE_INVOICE = (
    "INVOICE #INV-2024-0042\n"
    "Vendor: Acme Cloud Services\n"
    "Date: March 15, 2024\n"
    "Due: April 14, 2024\n\n"
    "Services rendered:\n"
    "  - API Hosting (500 GB)   x1   $199.00\n"
    "  - Support Premium Plan   x2   $49.00 each\n\n"
    "Subtotal: $297.00\n"
    "Tax (8%): $23.76\n"
    "TOTAL DUE: $320.76\n\n"
    "Payment terms: Net 30\n"
)


def demonstrate_tool_choice_variants():
    sep = "=" * 60

    # --- Mode 1: auto ---
    print("\n" + sep)
    print("tool_choice=auto -- Claude decides whether to call tool")
    print(sep)
    resp_auto = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=[INVOICE_TOOL],
        tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": "What can you tell me about this invoice?\n\n" + SAMPLE_INVOICE}],
    )
    for block in resp_auto.content:
        print(f"  Block type: {block.type}")
        if block.type == "text":
            print(f"  Text preview: {block.text[:100]}...")
        elif block.type == "tool_use":
            print(f"  Tool called: {block.name}")

    # --- Mode 2: any ---
    print("\n" + sep)
    print("tool_choice=any -- MUST call a tool")
    print(sep)
    resp_any = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=[INVOICE_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": "Extract data from:\n\n" + SAMPLE_INVOICE}],
    )
    for block in resp_any.content:
        print(f"  Block type: {block.type}")
        if block.type == "tool_use":
            print(f"  Tool called: {block.name}")

    # --- Mode 3: forced specific tool ---
    print("\n" + sep)
    print("tool_choice=forced -- forces specific tool")
    print(sep)
    resp_forced = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=[INVOICE_TOOL],
        tool_choice={"type": "tool", "name": "extract_invoice"},
        messages=[{"role": "user", "content": "Process this invoice:\n\n" + SAMPLE_INVOICE}],
    )
    extracted = None
    for block in resp_forced.content:
        if block.type == "tool_use":
            extracted = block.input
            break
    if extracted:
        print(json.dumps(extracted, indent=2))
    return extracted


def show_semantic_error_risk(extracted):
    sep = "=" * 60
    print("\n" + sep)
    print("Semantic validation (tool_use does NOT catch these)")
    print(sep)
    if not extracted:
        print("  No extraction to validate.")
        return
    errors = []
    if extracted.get("line_items") and extracted.get("subtotal") is not None:
        calc = sum(i.get("quantity", 0) * i.get("unit_price", 0) for i in extracted["line_items"])
        stated = extracted["subtotal"]
        if abs(calc - stated) > 0.01:
            errors.append(f"  SEMANTIC ERROR: items sum={calc:.2f} != subtotal={stated:.2f}")
    if extracted.get("subtotal") is not None and extracted.get("tax") is not None and extracted.get("total_due") is not None:
        calc = extracted["subtotal"] + extracted["tax"]
        stated = extracted["total_due"]
        if abs(calc - stated) > 0.01:
            errors.append(f"  SEMANTIC ERROR: subtotal+tax={calc:.2f} != total_due={stated:.2f}")
    if errors:
        for e in errors:
            print(e)
    else:
        print("  All semantic checks passed.")
    print("\n  tool_use guarantees valid JSON schema -- semantic checks are YOUR responsibility.")


def show_nullable_field_patterns() -> None:
    sep = "=" * 60
    print("\n" + sep)
    print("Nullable fields, 'other' enum, and 'unclear' value patterns")
    print(sep)

    print()
    print("ANTI-PATTERN -- required field when data may be absent:")
    bad_schema_fragment = {
        "issue_date": {
            "type": "string",
            "description": "ISO 8601 date",
        }
    }
    print("  issue_date:", json.dumps(bad_schema_fragment["issue_date"]))
    print("  -> If document has no date, Claude INVENTS a plausible date.")
    print("     Hallucinated dates pass schema validation silently.")

    print()
    print("CORRECT -- nullable field signals legitimate absence:")
    good_schema_fragment = {
        "issue_date": {
            "type": ["string", "null"],
            "description": "ISO 8601 date, or null if not found in document",
        }
    }
    print("  issue_date:", json.dumps(good_schema_fragment["issue_date"]))
    print("  -> Claude returns null when date is genuinely missing.")
    print("     null is distinguishable from a fabricated value.")

    print()
    print("'other' + detail pattern for extensible enums:")
    currency_schema = {
        "currency": {
            "type": "string",
            "enum": ["USD", "EUR", "GBP", "CAD", "other"],
            "description": "Use 'other' for any currency not in the list",
        },
        "currency_detail": {
            "type": ["string", "null"],
            "description": "Full currency name/code when currency='other', else null",
        },
    }
    print("  currency:", json.dumps(currency_schema["currency"]))
    print("  currency_detail:", json.dumps(currency_schema["currency_detail"]))
    print("  -> AUD invoice: currency='other', currency_detail='AUD'")
    print("     No information is discarded; new values are captured.")

    print()
    print("'unclear' enum for ambiguous cases:")
    status_schema = {
        "payment_status": {
            "type": "string",
            "enum": ["paid", "unpaid", "overdue", "unclear"],
            "description": "'unclear' when payment status cannot be determined from context",
        }
    }
    print("  payment_status:", json.dumps(status_schema["payment_status"]))
    print("  -> Ambiguous invoice: payment_status='unclear'")
    print("     Routes to human review instead of forcing a wrong guess.")


if __name__ == "__main__":
    print("Demonstrating: Structured Output via tool_use")
    print("Mnemonic SANE: Simple->Prefill->Natural->Enforced (tool_use most reliable)")
    extracted = demonstrate_tool_choice_variants()
    show_semantic_error_risk(extracted)
    show_nullable_field_patterns()
    print("\n\nKEY TAKEAWAYS:")
    print("  1. tool_use = guaranteed JSON schema compliance (syntax only).")
    print("     auto may skip tool; any must call a tool; forced runs specific tool.")
    print("  2. Nullable fields prevent hallucination: type: ['string', 'null'] lets")
    print("     Claude return null rather than invent a plausible-but-wrong value.")
    print("  3. 'other' + detail pattern: captures unlisted enum values without data loss.")
    print("  4. 'unclear' enum value: routes ambiguous cases to human review honestly.")
    print("  5. Always add semantic validation on top of schema validation.")
    print("     Schema guarantees structure; it does NOT guarantee correctness.")
