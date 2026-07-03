"""
Domain 2 - Task 2.3: Tool Distribution & Scoped Subagents

EXAM CONCEPTS:
  1. Tool overload: giving an agent 15-20 tools causes unreliable selection.
     Claude struggles to pick the right tool when many similar options exist.

  2. Scoped subagents: each subagent receives only 4-5 relevant tools.
     Reduces decision complexity → more reliable tool selection.

  3. tool_choice modes:
     "auto"  → Claude may return text OR call a tool (default)
     "any"   → Claude MUST call SOME tool (won't return plain text)
     {"type": "tool", "name": "X"} → forces a SPECIFIC tool

  4. Cross-role tools: a single tool given to MULTIPLE subagents when
     each needs it (e.g., verify_fact given to both research & synthesis).

  5. Anti-pattern: one giant agent with all tools. Correct: coordinator
     routes to scoped subagents with minimal, relevant tool sets.

  Mnemonic: FOCUS
    Fewer tools per agent
    Orchestrator routes requests
    Cross-role tools shared selectively
    Unreliable selection avoided
    Scoped context stays clean

Run: uv run python 03_tool_distribution.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Mock tool implementations
# ---------------------------------------------------------------------------
def search_knowledge_base(query: str) -> dict:
    return {"results": [f"KB article about '{query}'", "Related policy doc"], "count": 2}

def get_customer_profile(customer_id: str) -> dict:
    return {"id": customer_id, "name": "Alice Smith", "tier": "premium", "since": "2020"}

def get_order_history(customer_id: str, limit: int = 5) -> dict:
    return {"orders": [{"id": "ORD-100", "total": 129.99, "status": "delivered"}], "total_count": 12}

def get_subscription_details(customer_id: str) -> dict:
    return {"plan": "Pro", "next_billing": "2024-02-15", "seats": 3}

def process_refund(order_id: str, amount: float) -> dict:
    return {"refund_id": "REF-" + order_id, "amount": amount, "status": "approved"}

def issue_credit(customer_id: str, amount: float, reason: str) -> dict:
    return {"credit_id": "CRD-001", "amount": amount, "expires": "2024-12-31"}

def update_subscription(customer_id: str, new_plan: str) -> dict:
    return {"updated": True, "old_plan": "Basic", "new_plan": new_plan}

def cancel_subscription(customer_id: str, reason: str) -> dict:
    return {"cancelled": True, "effective_date": "2024-02-15", "refund_prorated": 12.50}

def escalate_to_human(reason: str, context: str) -> dict:
    return {"ticket": "ESC-001", "queue": "tier2", "eta_minutes": 8}

def log_interaction(customer_id: str, summary: str, outcome: str) -> dict:
    return {"logged": True, "interaction_id": "INT-" + customer_id}

def send_email(customer_id: str, template: str, variables: dict) -> dict:
    return {"sent": True, "message_id": "MSG-001", "template": template}

def check_fraud_signals(customer_id: str, action: str) -> dict:
    return {"risk_score": 12, "flags": [], "recommendation": "allow"}

def get_product_catalog(category: str = "") -> dict:
    return {"products": [{"id": "P1", "name": "Pro Plan", "price": 49.99}]}

def apply_discount(customer_id: str, discount_code: str) -> dict:
    return {"applied": True, "discount_pct": 15, "new_total": 42.49}

def get_support_tickets(customer_id: str) -> dict:
    return {"tickets": [{"id": "TKT-55", "status": "open", "issue": "billing question"}]}

def verify_identity(customer_id: str, last4_digits: str) -> dict:
    return {"verified": True, "confidence": "high"}

def schedule_callback(customer_id: str, preferred_time: str) -> dict:
    return {"scheduled": True, "callback_time": preferred_time, "agent": "Support Team"}

def get_usage_metrics(customer_id: str, period: str) -> dict:
    return {"api_calls": 45230, "storage_gb": 128, "period": period}


# ---------------------------------------------------------------------------
# ALL 18 TOOLS: anti-pattern (overwhelms the model)
# ---------------------------------------------------------------------------
ALL_18_TOOLS = [
    {"name": "search_knowledge_base", "description": "Search internal KB", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "get_customer_profile", "description": "Get customer profile", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "get_order_history", "description": "Get order history", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["customer_id"]}},
    {"name": "get_subscription_details", "description": "Get subscription", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "process_refund", "description": "Process refund", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}}, "required": ["order_id", "amount"]}},
    {"name": "issue_credit", "description": "Issue account credit", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "amount": {"type": "number"}, "reason": {"type": "string"}}, "required": ["customer_id", "amount", "reason"]}},
    {"name": "update_subscription", "description": "Update subscription plan", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "new_plan": {"type": "string"}}, "required": ["customer_id", "new_plan"]}},
    {"name": "cancel_subscription", "description": "Cancel subscription", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["customer_id", "reason"]}},
    {"name": "escalate_to_human", "description": "Escalate to human agent", "input_schema": {"type": "object", "properties": {"reason": {"type": "string"}, "context": {"type": "string"}}, "required": ["reason", "context"]}},
    {"name": "log_interaction", "description": "Log interaction", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "summary": {"type": "string"}, "outcome": {"type": "string"}}, "required": ["customer_id", "summary", "outcome"]}},
    {"name": "send_email", "description": "Send email to customer", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "template": {"type": "string"}, "variables": {"type": "object"}}, "required": ["customer_id", "template", "variables"]}},
    {"name": "check_fraud_signals", "description": "Check fraud signals", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "action": {"type": "string"}}, "required": ["customer_id", "action"]}},
    {"name": "get_product_catalog", "description": "Get product catalog", "input_schema": {"type": "object", "properties": {"category": {"type": "string"}}, "required": []}},
    {"name": "apply_discount", "description": "Apply discount code", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "discount_code": {"type": "string"}}, "required": ["customer_id", "discount_code"]}},
    {"name": "get_support_tickets", "description": "Get support tickets", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "verify_identity", "description": "Verify customer identity", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "last4_digits": {"type": "string"}}, "required": ["customer_id", "last4_digits"]}},
    {"name": "schedule_callback", "description": "Schedule callback", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "preferred_time": {"type": "string"}}, "required": ["customer_id", "preferred_time"]}},
    {"name": "get_usage_metrics", "description": "Get usage metrics", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "period": {"type": "string"}}, "required": ["customer_id", "period"]}},
]


# ---------------------------------------------------------------------------
# SCOPED TOOL SETS: 4-5 tools per subagent role
# ---------------------------------------------------------------------------
LOOKUP_TOOLS = [
    {"name": "get_customer_profile", "description": "Get full customer profile including tier and account age.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "get_order_history", "description": "Get recent orders for a customer. Use limit to control how many.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["customer_id"]}},
    {"name": "get_subscription_details", "description": "Get subscription plan, seats, and next billing date.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "get_support_tickets", "description": "Get open and recent support tickets for this customer.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "get_usage_metrics", "description": "Get API calls, storage usage for a billing period (e.g. '2024-01').", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "period": {"type": "string"}}, "required": ["customer_id", "period"]}},
]

BILLING_TOOLS = [
    {"name": "process_refund", "description": "Process a refund for a specific order. Requires order_id and exact refund amount in USD.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}}, "required": ["order_id", "amount"]}},
    {"name": "issue_credit", "description": "Issue account credit (not tied to a specific order). Use for goodwill credits.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "amount": {"type": "number"}, "reason": {"type": "string"}}, "required": ["customer_id", "amount", "reason"]}},
    {"name": "apply_discount", "description": "Apply a discount code to the customer's current subscription.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "discount_code": {"type": "string"}}, "required": ["customer_id", "discount_code"]}},
    {"name": "check_fraud_signals", "description": "Check fraud risk before processing high-value refunds or credits.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "action": {"type": "string"}}, "required": ["customer_id", "action"]}},
]

SUBSCRIPTION_TOOLS = [
    {"name": "get_subscription_details", "description": "Get current plan, seats, and billing cycle.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "update_subscription", "description": "Upgrade or downgrade the subscription plan.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "new_plan": {"type": "string"}}, "required": ["customer_id", "new_plan"]}},
    {"name": "cancel_subscription", "description": "Cancel subscription. Always confirm reason before cancelling.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["customer_id", "reason"]}},
    {"name": "get_product_catalog", "description": "Get available plans and pricing to offer alternatives.", "input_schema": {"type": "object", "properties": {"category": {"type": "string"}}, "required": []}},
    {"name": "schedule_callback", "description": "Schedule a callback if the customer prefers to decide later.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "preferred_time": {"type": "string"}}, "required": ["customer_id", "preferred_time"]}},
]

ESCALATION_TOOLS = [
    {"name": "escalate_to_human", "description": "Escalate to a human agent with reason and full context summary.", "input_schema": {"type": "object", "properties": {"reason": {"type": "string"}, "context": {"type": "string"}}, "required": ["reason", "context"]}},
    {"name": "send_email", "description": "Send a templated email to the customer (e.g. 'refund_confirmation', 'escalation_notice').", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "template": {"type": "string"}, "variables": {"type": "object"}}, "required": ["customer_id", "template", "variables"]}},
    {"name": "log_interaction", "description": "Log this interaction with summary and outcome for the next agent.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "summary": {"type": "string"}, "outcome": {"type": "string"}}, "required": ["customer_id", "summary", "outcome"]}},
    {"name": "schedule_callback", "description": "Schedule a callback if issue cannot be resolved immediately.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "preferred_time": {"type": "string"}}, "required": ["customer_id", "preferred_time"]}},
]


ALL_TOOL_FNS = {
    "search_knowledge_base": search_knowledge_base,
    "get_customer_profile": get_customer_profile,
    "get_order_history": get_order_history,
    "get_subscription_details": get_subscription_details,
    "process_refund": process_refund,
    "issue_credit": issue_credit,
    "update_subscription": update_subscription,
    "cancel_subscription": cancel_subscription,
    "escalate_to_human": escalate_to_human,
    "log_interaction": log_interaction,
    "send_email": send_email,
    "check_fraud_signals": check_fraud_signals,
    "get_product_catalog": get_product_catalog,
    "apply_discount": apply_discount,
    "get_support_tickets": get_support_tickets,
    "verify_identity": verify_identity,
    "schedule_callback": schedule_callback,
    "get_usage_metrics": get_usage_metrics,
}


def run_single_turn(system: str, user: str, tools: list, tool_choice: dict = None) -> dict:
    """Run ONE API call and return (stop_reason, tool_calls_made, text_response)."""
    kwargs = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 512,
        "system": system,
        "tools": tools,
        "messages": [{"role": "user", "content": user}],
    }
    if tool_choice:
        kwargs["tool_choice"] = tool_choice

    resp = client.messages.create(**kwargs)
    tools_called = [b.name for b in resp.content if b.type == "tool_use"]
    text = next((b.text for b in resp.content if hasattr(b, "text")), "")
    return {"stop_reason": resp.stop_reason, "tools_called": tools_called, "text": text[:120]}


def run_scoped_loop(system: str, user: str, tools: list, label: str) -> str:
    """Run a full agentic loop with scoped tools. Return final response text."""
    messages = [{"role": "user", "content": user}]
    calls_made = []
    for _ in range(8):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=system,
            tools=tools,
            messages=messages,
        )
        if resp.stop_reason == "end_turn":
            return next((b.text for b in resp.content if hasattr(b, "text")), "")
        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                calls_made.append(block.name)
                fn = ALL_TOOL_FNS.get(block.name, lambda **k: {"error": "unknown"})
                result = fn(**block.input)
                print(f"    [{label}] Tool: {block.name}({list(block.input.keys())})")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})
    return "(loop limit)"


# ---------------------------------------------------------------------------
# Demo 1: Anti-pattern — 18 tools, observe tool selection quality
# ---------------------------------------------------------------------------
def demo_tool_overload() -> None:
    sep = "-" * 50
    print(sep)
    print("ANTI-PATTERN: 18-tool agent")
    print(f"  Agent has {len(ALL_18_TOOLS)} tools available")
    print("  Task: 'Customer C001 wants a refund on ORD-100 for $129.99'")
    result = run_single_turn(
        system="You are a customer support agent. Use tools to help.",
        user="Customer C001 wants a refund on order ORD-100 for $129.99. Please process it.",
        tools=ALL_18_TOOLS,
    )
    print(f"  stop_reason: {result['stop_reason']}")
    print(f"  tools_called: {result['tools_called']}")
    if not result["tools_called"]:
        print("  -> Model returned text instead of calling tools (unreliable selection)")
    print()


# ---------------------------------------------------------------------------
# Demo 2: Scoped subagents — correct pattern
# ---------------------------------------------------------------------------
def demo_scoped_subagents() -> None:
    sep = "-" * 50
    print(sep)
    print("CORRECT: Scoped subagents (4-5 tools each)")
    print()

    # Lookup subagent
    print("  [Lookup Subagent] — 5 tools: profile, orders, subscription, tickets, usage")
    result = run_scoped_loop(
        system="You are a customer lookup specialist. Retrieve customer account information.",
        user="Get the profile and recent orders for customer C001.",
        tools=LOOKUP_TOOLS,
        label="lookup",
    )
    print(f"  Result preview: {result[:150]}")
    print()

    # Billing subagent
    print("  [Billing Subagent] — 4 tools: refund, credit, discount, fraud-check")
    result = run_scoped_loop(
        system="You are a billing specialist. Process refunds and credits. Always check fraud signals for amounts over $100.",
        user="Process a refund of $129.99 for order ORD-100.",
        tools=BILLING_TOOLS,
        label="billing",
    )
    print(f"  Result preview: {result[:150]}")
    print()


# ---------------------------------------------------------------------------
# Demo 3: tool_choice modes
# ---------------------------------------------------------------------------
def demo_tool_choice_modes() -> None:
    sep = "-" * 50
    print(sep)
    print("tool_choice MODES: auto | any | forced")
    print()

    simple_tools = [
        {"name": "get_customer_profile", "description": "Get customer profile by ID.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
        {"name": "process_refund", "description": "Process a refund for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}}, "required": ["order_id", "amount"]}},
    ]

    # auto: Claude may or may not call a tool
    r_auto = run_single_turn(
        system="You are a helpful assistant.",
        user="What is the capital of France?",  # intentionally unrelated to tools
        tools=simple_tools,
        tool_choice={"type": "auto"},
    )
    print(f"  auto  (unrelated question): stop_reason={r_auto['stop_reason']}, tools={r_auto['tools_called']}")
    print(f"        text preview: {r_auto['text'][:80]}")

    # any: Claude MUST call some tool
    r_any = run_single_turn(
        system="You are a helpful assistant.",
        user="What is the capital of France?",
        tools=simple_tools,
        tool_choice={"type": "any"},
    )
    print(f"  any   (unrelated question): stop_reason={r_any['stop_reason']}, tools={r_any['tools_called']}")
    print(f"  -> Claude forced to call a tool even for unrelated question")

    # forced: specific tool
    r_forced = run_single_turn(
        system="You are a helpful assistant.",
        user="Tell me about customer C001.",
        tools=simple_tools,
        tool_choice={"type": "tool", "name": "get_customer_profile"},
    )
    print(f"  forced(get_customer_profile): stop_reason={r_forced['stop_reason']}, tools={r_forced['tools_called']}")
    print()


# ---------------------------------------------------------------------------
# Demo 4: Cross-role tool (shared across subagents)
# ---------------------------------------------------------------------------
def demo_cross_role_tool() -> None:
    sep = "-" * 50
    print(sep)
    print("CROSS-ROLE TOOL: verify_identity shared by multiple subagents")
    print()

    verify_tool = {
        "name": "verify_identity",
        "description": "Verify customer identity before sensitive operations. Pass last 4 digits of payment method.",
        "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "last4_digits": {"type": "string"}}, "required": ["customer_id", "last4_digits"]},
    }

    # Both billing and subscription subagents share verify_identity
    billing_with_verify = BILLING_TOOLS + [verify_tool]
    subscription_with_verify = SUBSCRIPTION_TOOLS + [verify_tool]

    print(f"  Billing subagent: {[t['name'] for t in billing_with_verify]}")
    print(f"  Subscription subagent: {[t['name'] for t in subscription_with_verify]}")
    print()
    print("  Both subagents can verify identity before sensitive operations.")
    print("  Cross-role tools are added SELECTIVELY — not to every subagent.")
    print("  (Lookup and Escalation subagents do NOT have verify_identity)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Anti-pattern — 18-tool overload")
    print(sep)
    demo_tool_overload()

    print()
    print(sep)
    print("DEMO 2: Correct — scoped subagents (4-5 tools each)")
    print(sep)
    demo_scoped_subagents()

    print()
    print(sep)
    print("DEMO 3: tool_choice modes (auto / any / forced)")
    print(sep)
    demo_tool_choice_modes()

    print()
    print(sep)
    print("DEMO 4: Cross-role tools (shared across subagents)")
    print(sep)
    demo_cross_role_tool()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Tool overload (15+ tools) degrades selection reliability.")
    print("     Solution: scope each subagent to 4-5 relevant tools.")
    print("  2. auto: Claude may call a tool or return text.")
    print("     any: Claude MUST call some tool (guarantees tool use).")
    print("     forced: Claude MUST call a specific named tool.")
    print("  3. Cross-role tools (e.g., verify_identity) are added to")
    print("     MULTIPLE subagents only when each genuinely needs them.")
    print("  4. Coordinator routes to the right scoped subagent; it does")
    print("     NOT hold all tools itself.")
    print("  Mnemonic FOCUS: Fewer tools, Orchestrator routes, Cross-role")
    print("  shared, Unreliable selection avoided, Scoped context clean.")
