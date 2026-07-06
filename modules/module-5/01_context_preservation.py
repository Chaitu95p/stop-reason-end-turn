"""
Domain 5 - Task 5.1: Context Preservation Strategies

EXAM CONCEPTS:
  1. Progressive summarization risk: each compression loses precise numbers
     and specific details. "~40k tokens" becomes "tokens used" after 3 passes.

  2. Case facts extraction pattern: maintain a persistent structured block
     of key facts extracted from tool results. Survives context compression.

  3. Verbose tool output trimming: 40+ field API responses should be trimmed
     to 5-8 relevant fields before storing. Prevents context window bloat.

  4. Lost-in-the-middle: Claude's attention degrades for content buried in
     the middle of long contexts. Place CRITICAL findings at start or end.

  5. Scratchpad pattern: agent writes key findings to a structured block,
     re-reads it at start of each reasoning step.

  6. Upstream agent modification for downstream context budgets:
     When downstream synthesis agents have limited context, modify UPSTREAM
     subagents to return compact structured data (key facts, citations,
     relevance scores) INSTEAD of verbose content and reasoning chains.
     This is an architectural decision — change what the upstream agent returns,
     not just how the downstream agent filters it.

  Mnemonic: FACT-U
    Facts-block (persistent structured key facts)
    Aggregate-trim (trim verbose tool output to relevant fields)
    Cite-positions (critical info at start or end, not middle)
    Track (maintain case facts across tool calls)
    Upstream-compact (modify upstream agents to return structured summaries)

Run: uv run python 01_context_preservation.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Simulated verbose API response (40+ fields)
# ---------------------------------------------------------------------------
VERBOSE_ORDER_RESPONSE = {
    "order_id": "ORD-100",
    "customer_id": "C001",
    "status": "delivered",
    "total": 129.99,
    "subtotal": 119.99,
    "tax": 10.00,
    "discount": 0.00,
    "currency": "USD",
    "created_at": "2024-01-15T10:23:00Z",
    "updated_at": "2024-01-18T14:02:00Z",
    "delivered_at": "2024-01-18T14:02:00Z",
    "estimated_delivery": "2024-01-19T00:00:00Z",
    "shipping_method": "standard",
    "tracking_number": "TRACK-ABC-123",
    "carrier": "FedEx",
    "carrier_code": "fedex",
    "warehouse_id": "WH-WEST-1",
    "fulfillment_center": "Seattle, WA",
    "packaging": "box_medium",
    "weight_oz": 32,
    "dimensions": {"length": 12, "width": 8, "height": 4},
    "ship_to": {"name": "Alice Smith", "line1": "123 Main St", "city": "Portland", "state": "OR", "zip": "97201"},
    "ship_from": {"name": "Acme Corp", "line1": "456 Warehouse Rd", "city": "Seattle", "state": "WA", "zip": "98101"},
    "items": [{"sku": "PROD-A", "name": "Widget Pro", "quantity": 1, "unit_price": 119.99, "subtotal": 119.99}],
    "payment_method": "credit_card",
    "payment_last4": "4242",
    "payment_brand": "Visa",
    "authorization_code": "AUTH-XYZ",
    "risk_score": 5,
    "fraud_check": "passed",
    "internal_notes": "",
    "customer_notes": "Leave at door",
    "gift_message": None,
    "is_gift": False,
    "return_eligible_until": "2024-02-18T00:00:00Z",
    "return_window_days": 30,
    "refund_status": None,
    "refund_amount": None,
    "refund_reason": None,
    "tags": ["premium", "standard_shipping"],
    "metadata": {"session_id": "sess_abc", "referral": "email_campaign"},
    "version": 3,
    "etag": "abc123def456",
}


def trim_to_relevant_fields(verbose_response: dict) -> dict:
    """
    EXAM PATTERN: Trim verbose tool output to only fields needed for the task.
    40+ fields → 6 relevant fields. Reduces context consumption by ~85%.
    """
    return {
        "order_id": verbose_response["order_id"],
        "status": verbose_response["status"],
        "total": verbose_response["total"],
        "delivered_at": verbose_response.get("delivered_at"),
        "return_eligible_until": verbose_response.get("return_eligible_until"),
        "items": [{"name": i["name"], "quantity": i["quantity"]} for i in verbose_response.get("items", [])],
    }


# ---------------------------------------------------------------------------
# Progressive summarization risk demo
# ---------------------------------------------------------------------------
def show_summarization_risk() -> None:
    sep = "-" * 50
    print(sep)
    print("PROGRESSIVE SUMMARIZATION RISK")
    print()

    original_fact = "Customer C001 placed order ORD-100 on 2024-01-15 for exactly $129.99 (includes $10.00 tax). Delivered 2024-01-18. Return window expires 2024-02-18."
    print(f"Original fact: {original_fact}")
    print()

    compressions = [
        "Customer C001's order ORD-100 for ~$130 was delivered on Jan 18. Return window is 30 days.",
        "C001 has a delivered order from January. Return policy applies.",
        "Customer has a recent order that may be returnable.",
    ]
    for i, compressed in enumerate(compressions, 1):
        print(f"After compression #{i}: {compressed}")
        print(f"  Lost: {'exact amount' if i == 1 else 'delivery date' if i == 2 else 'all specific details'}")
    print()
    print("After 3 compressions: specific numbers gone, decisions become unreliable.")
    print("Solution: extract key facts into a structured block BEFORE compression.")


# ---------------------------------------------------------------------------
# Case facts block pattern
# ---------------------------------------------------------------------------
def extract_case_facts(customer_id: str, order_data: dict) -> dict:
    """
    EXAM PATTERN: Extract critical facts into a persistent structured block.
    This block is included at the TOP of every subsequent prompt.
    Survives context compression because it's a structured dict, not prose.
    """
    trimmed = trim_to_relevant_fields(order_data)
    return {
        "case_id": f"CASE-{customer_id}-{trimmed['order_id']}",
        "customer_id": customer_id,
        "order_id": trimmed["order_id"],
        "order_status": trimmed["status"],
        "order_total_usd": trimmed["total"],
        "delivered_at": trimmed["delivered_at"],
        "return_eligible_until": trimmed["return_eligible_until"],
        "items": trimmed["items"],
        # Agent writes decisions here as it works
        "decisions_made": [],
        "current_action": None,
    }


def run_with_case_facts_block(user_request: str, case_facts: dict) -> str:
    """
    Demonstrate the case facts block pattern:
    Critical facts are injected at the start of the system prompt,
    ensuring they survive context compression.
    """
    facts_json = json.dumps(case_facts, indent=2)
    system = (
        "CASE FACTS (authoritative — use these for all decisions):" + NL
        + facts_json + NL + NL
        + "You are a customer support agent. Use the case facts above to answer."
        + " Do not re-derive facts that are already captured — trust the facts block."
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": user_request}],
    )
    return next((b.text for b in resp.content if hasattr(b, "text")), "")


# ---------------------------------------------------------------------------
# Lost-in-the-middle demo
# ---------------------------------------------------------------------------
def show_lost_in_middle_principle() -> None:
    sep = "-" * 50
    print(sep)
    print("LOST-IN-THE-MIDDLE: attention degrades for middle-context content")
    print()
    print("Research finding: Claude's attention to specific facts degrades")
    print("when those facts are buried in the middle of long contexts.")
    print()
    print("ANTI-PATTERN: critical finding buried in middle of long context")
    print("""
  [2000 tokens of tool output]
  ...
  CRITICAL: The return window expires TODAY at midnight.   <-- buried in middle
  ...
  [3000 more tokens of tool output]
  Question: Should we process this return?
    """)
    print("CORRECT: critical info at START or END of context")
    print("""
  CRITICAL DEADLINE: Return window expires TODAY at midnight.   <-- at START
  [tool output follows...]
  ...
  [more tool output]
  REMINDER: Return window expires TODAY at midnight.            <-- at END
  Question: Should we process this return?
    """)


# ---------------------------------------------------------------------------
# Trim comparison demo
# ---------------------------------------------------------------------------
def show_trim_comparison() -> None:
    sep = "-" * 50
    print(sep)
    print("VERBOSE TOOL OUTPUT TRIMMING")
    print()
    full_size = len(json.dumps(VERBOSE_ORDER_RESPONSE))
    trimmed = trim_to_relevant_fields(VERBOSE_ORDER_RESPONSE)
    trimmed_size = len(json.dumps(trimmed))
    reduction = (1 - trimmed_size / full_size) * 100

    print(f"Full API response: {full_size} chars ({len(VERBOSE_ORDER_RESPONSE)} fields)")
    print(f"Trimmed response:  {trimmed_size} chars ({len(trimmed)} fields)")
    print(f"Context reduction: {reduction:.0f}%")
    print()
    print("Trimmed content:")
    print(json.dumps(trimmed, indent=2))
    print()
    print("Dropped fields (irrelevant to support decisions):")
    dropped = [k for k in VERBOSE_ORDER_RESPONSE if k not in trimmed]
    print(f"  {dropped[:8]}... ({len(dropped)} total dropped)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Progressive summarization risk")
    print(sep)
    show_summarization_risk()

    print()
    print(sep)
    print("DEMO 2: Verbose tool output trimming (40 fields → 6)")
    print(sep)
    show_trim_comparison()

    print()
    print(sep)
    print("DEMO 3: Case facts block pattern")
    print(sep)
    case_facts = extract_case_facts("C001", VERBOSE_ORDER_RESPONSE)
    print("Case facts block (injected at top of every prompt):")
    print(json.dumps(case_facts, indent=2))
    print()
    print("Using case facts block to answer customer question...")
    answer = run_with_case_facts_block(
        "Can the customer still return this order? When does the window close?",
        case_facts
    )
    print(f"Agent answer: {answer}")

    print()
    print(sep)
    print("DEMO 4: Lost-in-the-middle principle")
    print(sep)
    show_lost_in_middle_principle()

    print()
    print(sep)
    print("DEMO 5: Upstream agent modification for downstream context budgets")
    print(sep)
    print("EXAM CONCEPT: When a DOWNSTREAM synthesis agent has a limited context budget,")
    print("the fix is to change what the UPSTREAM subagents return -- not to filter")
    print("on the downstream side.")
    print()
    print("ANTI-PATTERN: upstream agent returns verbose content, downstream tries to filter")
    print()

    upstream_verbose = {
        "source": "Annual Market Report 2023",
        "full_text": (
            "The cloud services market grew by 23% in 2022, reaching $580B globally. "
            "Enterprise adoption of AI tools reached 34% of Fortune 500 companies. "
            "Remote work adoption stabilized at 28% of workforce permanently working remotely. "
            "Q1 saw growth in Asia-Pacific... Q2 showed deceleration in EMEA... "
            "[2000 more words of regional breakdown, methodology, appendices...]"
        ),
        "reasoning": (
            "I found this source by searching for 'cloud market growth'. I also checked "
            "3 other sources that were less relevant. The main finding appears on page 4..."
        ),
    }

    upstream_compact = {
        "source": "Annual Market Report 2023",
        "publication_date": "2023-06",
        "key_facts": [
            {"claim": "Cloud market grew 23% in 2022", "stat": "$580B total"},
            {"claim": "Enterprise AI adoption 34%", "segment": "Fortune 500"},
        ],
        "relevance_score": 0.91,
        "citation_page": 4,
    }

    verbose_size = len(str(upstream_verbose))
    compact_size = len(str(upstream_compact))
    print(f"Verbose upstream return: {verbose_size} chars")
    print(f"Compact upstream return: {compact_size} chars ({100*(1-compact_size/verbose_size):.0f}% reduction)")
    print()
    print("CORRECT: modify the upstream agent's output schema to return structured")
    print("facts + citations + relevance score instead of full text + reasoning chain.")
    print()
    print("Compact output (what upstream should return):")
    print(json.dumps(upstream_compact, indent=2))
    print()
    print("EXAM KEY: This is an ARCHITECTURAL decision -- change the upstream agent's")
    print("return format, not just how the downstream agent filters its input.")
    print("The downstream synthesis agent's context budget determines what the")
    print("upstream agent is allowed to return.")

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Progressive summarization loses precise numbers after 2-3 passes.")
    print("     Solution: extract critical facts into a structured block first.")
    print("  2. Trim verbose tool output (40+ fields) to 5-8 relevant fields.")
    print("     Reduces context usage by 80-90% without losing key information.")
    print("  3. Place CRITICAL facts at START or END of context, never middle.")
    print("     Lost-in-the-middle: Claude's attention degrades for buried content.")
    print("  4. Case facts block: structured dict survives compression better than prose.")
    print("  5. Upstream modification: when downstream has a limited context budget,")
    print("     change what UPSTREAM agents return (key facts + citations + relevance")
    print("     scores) instead of verbose text + reasoning chains.")
    print("     This is architectural -- change the return schema, not the downstream filter.")
    print("  Mnemonic FACT-U: Facts-block, Aggregate-trim, Cite-positions, Track, Upstream-compact.")
