"""
Domain 5 - Task 5.2: Escalation Patterns & Decision Criteria

EXAM CONCEPTS:
  1. Explicit escalation criteria in system prompt: named triggers with
     few-shot examples (escalate vs resolve) outperform vague instructions.

  2. Anti-patterns for escalation triggers:
     Sentiment-based   → "escalate if customer seems upset" (too vague)
     Self-reported      → "escalate if Claude is not confident" (unreliable)

  3. Correct triggers are OBJECTIVE and POLICY-BASED:
     - Immediate human request: "speak to a manager"
     - Policy gap: situation not covered by current policy
     - Multiple matches: can't disambiguate without more info
     - Regulatory domain: legal, medical, financial advice needed
     - Repeated failures: same issue attempted 3+ times without resolution

  4. Acknowledge-first: before escalating, Claude should acknowledge the
     customer's frustration. Escalating without acknowledgment feels dismissive.

  5. Partial resolution + escalation: resolve what can be resolved locally,
     escalate only the part that needs human judgment.

Run: uv run python 02_escalation_patterns.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Escalation tool definition
# ---------------------------------------------------------------------------
ESCALATE_TOOL = {
    "name": "escalate_to_human",
    "description": (
        "Escalate this case to a human support agent. Use when: "
        "(1) customer explicitly requests a human, "
        "(2) situation falls outside current policy, "
        "(3) customer account matches multiple records and disambiguation requires human judgment, "
        "(4) legal, medical, or regulated financial advice is needed, "
        "(5) same issue attempted 3+ times without resolution."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "trigger": {
                "type": "string",
                "enum": [
                    "human_requested",
                    "policy_gap",
                    "multiple_matches",
                    "regulatory_domain",
                    "repeated_failure",
                ],
                "description": "Objective trigger that mandates escalation.",
            },
            "acknowledgment": {
                "type": "string",
                "description": "What Claude said to acknowledge the customer's situation before escalating.",
            },
            "context_summary": {
                "type": "string",
                "description": "Full context for the human agent (what was tried, what is known, what is needed).",
            },
            "partial_resolution": {
                "type": "string",
                "description": "What was resolved before escalating (if anything). Empty string if nothing resolved.",
            },
        },
        "required": ["trigger", "acknowledgment", "context_summary", "partial_resolution"],
    },
}

RESOLVE_TOOL = {
    "name": "resolve_locally",
    "description": "Mark this case as resolved locally without escalation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "resolution": {
                "type": "string",
                "description": "What action was taken to resolve the issue.",
            },
            "customer_message": {
                "type": "string",
                "description": "Message to send to the customer.",
            },
        },
        "required": ["resolution", "customer_message"],
    },
}

REQUEST_CLARIFICATION_TOOL = {
    "name": "request_clarification",
    "description": (
        "Ask the customer for additional identifying information when multiple accounts "
        "match their details. Use BEFORE escalating on multiple_matches. "
        "Examples of identifiers to ask for: order number, email address, "
        "phone number, billing address, last 4 digits of payment method."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_message": {
                "type": "string",
                "description": "Polite question asking for additional identifier(s) to disambiguate accounts.",
            },
            "identifiers_requested": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Which identifiers you're asking for (email, order_number, phone, etc.).",
            },
        },
        "required": ["customer_message", "identifiers_requested"],
    },
}


# ---------------------------------------------------------------------------
# System prompt with explicit criteria and few-shot examples
# ---------------------------------------------------------------------------
SYSTEM_WITH_EXPLICIT_CRITERIA = (
    "You are a customer support agent." + NL + NL
    + "ESCALATION TRIGGERS (objective criteria — use escalate_to_human):" + NL
    + "  human_requested   : Customer says 'speak to manager', 'human please', 'real person'" + NL
    + "  policy_gap        : Situation not covered in our refund/return/billing policies" + NL
    + "  multiple_matches  : Customer account info matches 2+ records" + NL
    + "  regulatory_domain : Customer asks for legal, medical, or investment advice" + NL
    + "  repeated_failure  : Same resolution attempted 3+ times without success" + NL + NL
    + "ALWAYS acknowledge the customer's situation before escalating." + NL
    + "NEVER escalate based on: sentiment, tone, or your own confidence level." + NL + NL
    + "FEW-SHOT EXAMPLES:" + NL
    + "  Q: 'I want to cancel and get a full refund for my annual plan (day 200)'" + NL
    + "  A: RESOLVE — policy covers pro-rated refunds for annual plans. Process it." + NL + NL
    + "  Q: 'I need a refund for a purchase made 18 months ago'" + NL
    + "  A: ESCALATE (policy_gap) — policy covers 30 days; 18 months is outside scope." + NL + NL
    + "  Q: 'Can you just get me a real person please?'" + NL
    + "  A: ESCALATE (human_requested) — always honor immediate human requests." + NL + NL
    + "  Q: 'My name is John Smith, please look up my account'" + NL
    + "  A: CLARIFY — multiple Johns found. Ask for email or order number to disambiguate." + NL + NL
    + "  Q: 'My account is showing two different email addresses'" + NL
    + "  A: ESCALATE (multiple_matches) — account merge issue needs human merge/dedup." + NL + NL
    + "  Q: 'Is this a good investment? Should I put money into your premium plan?'" + NL
    + "  A: ESCALATE (regulatory_domain) — investment advice is regulated."
)

SYSTEM_VAGUE_ANTIPATTERN = (
    "You are a customer support agent. Escalate to a human if you are not confident"
    " handling a situation or if the customer seems upset."
)


def run_escalation_decision(user_message: str, system: str, label: str) -> dict:
    """Run one turn and return the tool call result."""
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system,
        tools=[ESCALATE_TOOL, RESOLVE_TOOL],
        messages=[{"role": "user", "content": user_message}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return {"tool": block.name, "input": block.input, "label": label}
    text = next((b.text for b in resp.content if hasattr(b, "text")), "")
    return {"tool": "text", "input": {"text": text[:200]}, "label": label}


# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------
SCENARIOS = [
    {
        "id": 1,
        "message": "I'd like a refund on my order from last week. Order #ORD-200.",
        "expected": "resolve_locally",
        "reason": "Standard refund request, within policy",
    },
    {
        "id": 2,
        "message": "I need a refund for an order I made two years ago. It was a gift.",
        "expected": "escalate_to_human",
        "reason": "policy_gap — 2 years is outside 30-day return window",
    },
    {
        "id": 3,
        "message": "Can I just speak with a real person about this?",
        "expected": "escalate_to_human",
        "reason": "human_requested — always honor",
    },
    {
        "id": 4,
        "message": "Should I upgrade to annual or is monthly better for my tax situation?",
        "expected": "escalate_to_human",
        "reason": "regulatory_domain — tax advice is regulated",
    },
    {
        "id": 5,
        "message": "I'm finding two accounts under my name — alice@example.com and alice.smith@example.com",
        "expected": "escalate_to_human",
        "reason": "multiple_matches — account disambiguation",
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Explicit criteria vs vague criteria comparison")
    print(sep)
    print()

    for scenario in SCENARIOS[:3]:
        print(f"Scenario {scenario['id']}: \"{scenario['message']}\"")
        print(f"  Expected: {scenario['expected']} ({scenario['reason']})")
        print()

        # Test with explicit criteria
        result_explicit = run_escalation_decision(
            scenario["message"],
            SYSTEM_WITH_EXPLICIT_CRITERIA,
            "explicit"
        )
        tool_explicit = result_explicit["tool"]
        trigger = result_explicit["input"].get("trigger", "n/a")
        ack = result_explicit["input"].get("acknowledgment", result_explicit["input"].get("customer_message", ""))
        print(f"  [Explicit criteria] → {tool_explicit} (trigger: {trigger})")
        print(f"    Acknowledgment: {ack[:100]}")

        # Test with vague criteria
        result_vague = run_escalation_decision(
            scenario["message"],
            SYSTEM_VAGUE_ANTIPATTERN,
            "vague"
        )
        tool_vague = result_vague["tool"]
        print(f"  [Vague criteria]    → {tool_vague} (may be inconsistent across runs)")
        print()

    print(sep)
    print("DEMO 2: All escalation triggers")
    print(sep)
    print()

    for scenario in SCENARIOS:
        result = run_escalation_decision(
            scenario["message"],
            SYSTEM_WITH_EXPLICIT_CRITERIA,
            "explicit"
        )
        tool = result["tool"]
        status = "CORRECT" if tool == scenario["expected"] else "WRONG"
        trigger = result["input"].get("trigger", "")
        print(f"Scenario {scenario['id']}: [{status}]")
        print(f"  Input: \"{scenario['message']}\"")
        print(f"  Tool: {tool}" + (f" (trigger: {trigger})" if trigger else ""))
        if tool == "escalate_to_human":
            ack = result["input"].get("acknowledgment", "")
            partial = result["input"].get("partial_resolution", "")
            print(f"  Acknowledgment: {ack[:100]}")
            if partial:
                print(f"  Partial resolution: {partial[:80]}")
        print()

    print(sep)
    print("DEMO 3: Multiple matches → clarify first, escalate only if unresolvable")
    print(sep)
    print()
    system_clarify = (
        "You are a customer support agent. When a customer lookup returns multiple "
        "matching accounts, ask for an additional identifier to disambiguate." + NL
        + "Use request_clarification to ask for: email address, order number, phone, "
        "or last 4 digits of payment method. Only escalate if clarification still "
        "leaves ambiguity." + NL
        + "Use resolve_locally when you can complete the request."
    )
    # Scenario: customer gives their name, which matches two accounts
    clarify_message = (
        "Hi, I'm John Smith. I'd like a refund on my last order please."
    )
    print(f"Input: \"{clarify_message}\"")
    print("  (Two accounts found matching 'John Smith')")
    print()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=system_clarify,
        tools=[ESCALATE_TOOL, RESOLVE_TOOL, REQUEST_CLARIFICATION_TOOL],
        messages=[{"role": "user", "content": clarify_message}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            print(f"  Tool: {block.name}")
            if block.name == "request_clarification":
                ids = block.input.get("identifiers_requested", [])
                msg = block.input.get("customer_message", "")
                print(f"  Identifiers requested: {ids}")
                print(f"  Message: {msg[:150]}")
                print()
                print("  CORRECT: asks for email/order number before escalating.")
            elif block.name == "escalate_to_human":
                trigger = block.input.get("trigger", "")
                print(f"  Trigger: {trigger}")
                print()
                print("  ANTI-PATTERN: escalating without first asking for identifiers.")
    print()
    print("EXAM KEY: multiple_matches → request_clarification first.")
    print("Only escalate if customer can't provide any disambiguating identifier.")

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Use OBJECTIVE, POLICY-BASED triggers:")
    print("     human_requested, policy_gap, multiple_matches,")
    print("     regulatory_domain, repeated_failure.")
    print("  2. NEVER escalate on: sentiment, tone, or Claude confidence level.")
    print("  3. ALWAYS acknowledge before escalating (avoids feeling dismissive).")
    print("  4. Few-shot examples in system prompt anchor Claude to correct decisions.")
    print("  5. Partial resolution + escalate: resolve what you can locally, then")
    print("     escalate only the part that requires human judgment.")
    print("  6. Multiple matches → ask for additional identifier first (email, order")
    print("     number, phone). Escalate only if clarification still leaves ambiguity.")
