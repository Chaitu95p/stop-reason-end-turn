"""
Exercise 1 - Steps 1-3: Multi-Tool Agent with Structured Errors

EXAM CONCEPTS:
  1. Tool description QUALITY differentiates similar tools.
     Two tools that look alike (search_orders vs lookup_order_by_id) MUST
     spell out boundary conditions in their descriptions or the model picks
     the wrong one.

  2. Agentic loop driven ONLY by stop_reason (not NL parsing, not iter caps).

  3. Structured error responses -- TVBP categories:
       Transient  (isRetryable=true)  -> retry once
       Validation (isRetryable=false) -> ask user for correction
       Business   (isRetryable=false) -> explain policy via humanMessage
       Permission (isRetryable=false) -> escalate

  4. Tool naming reduces ambiguity: use verbs + qualifiers.
       BAD:  search / lookup / find
       GOOD: search_orders_by_customer / lookup_order_by_id

  Mnemonic: DESCRIBE
    Differentiate similar tools
    Explicit boundary conditions
    Structured input schema
    Concrete verbs + qualifiers in names
    Retryability signalled in errors
    Include humanMessage for policy explanations
    Boundary between empty result and access failure
    Escalate on permission errors

Run: uv run python 01_tools_and_loop.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------
CUSTOMERS = {
    "C001": {"name": "Alice Smith", "tier": "premium", "email": "alice@example.com"},
    "C002": {"name": "Bob Jones",   "tier": "standard", "email": "bob@example.com"},
}

ORDERS = {
    "ORD-100": {"customer_id": "C001", "total": 129.99, "status": "delivered"},
    "ORD-200": {"customer_id": "C001", "total":  49.00, "status": "processing"},
    "ORD-300": {"customer_id": "C002", "total": 999.00, "status": "delivered"},
}


# ---------------------------------------------------------------------------
# Structured error helpers
# ---------------------------------------------------------------------------
def make_error(category: str, retryable: bool, code: str, dev_msg: str, human_msg: str) -> dict:
    return {
        "isError":         True,
        "errorCategory":   category,
        "isRetryable":     retryable,
        "errorCode":       code,
        "developerMessage": dev_msg,
        "humanMessage":    human_msg,
    }


def make_ok(payload: dict) -> dict:
    return {"isError": False, **payload}


# ---------------------------------------------------------------------------
# Tool implementations -- NOTE the deliberately similar pair below
# ---------------------------------------------------------------------------
def lookup_order_by_id(order_id: str) -> dict:
    """Exact-match lookup by primary key."""
    if order_id in ORDERS:
        return make_ok({"order": {"id": order_id, **ORDERS[order_id]}})
    return {"isError": False, "results": [], "querySuccessful": True,
            "message": f"No order with id {order_id}"}


def search_orders_by_customer(customer_id: str, status: str = None) -> dict:
    """Fuzzy multi-row search by foreign key + optional status filter."""
    if customer_id not in CUSTOMERS:
        return make_error(
            "validation", False, "UNKNOWN_CUSTOMER",
            f"customer_id {customer_id} not present",
            "I couldn't find that customer ID -- can you double-check the format (C###)?",
        )
    hits = [{"id": oid, **o} for oid, o in ORDERS.items()
            if o["customer_id"] == customer_id
            and (status is None or o["status"] == status)]
    return make_ok({"results": hits, "count": len(hits)})


def get_customer(customer_id: str) -> dict:
    if customer_id == "TIMEOUT":
        return make_error(
            "transient", True, "DB_TIMEOUT",
            "Customer DB timeout after 5000ms",
            "Small delay looking that up -- one moment.",
        )
    if customer_id in CUSTOMERS:
        return make_ok({"customer": {"id": customer_id, **CUSTOMERS[customer_id]}})
    return make_error(
        "validation", False, "UNKNOWN_CUSTOMER",
        f"customer_id {customer_id} not present",
        "That customer ID isn't on file -- can you re-check?",
    )


def process_refund(order_id: str, amount: float) -> dict:
    if order_id not in ORDERS:
        return make_error(
            "validation", False, "UNKNOWN_ORDER",
            f"order_id {order_id} not present",
            "I don't see that order -- can you re-check the ID?",
        )
    if amount > 500:
        return make_error(
            "business", False, "REFUND_LIMIT_EXCEEDED",
            f"Refund ${amount:.2f} exceeds $500 policy",
            f"Refunds over $500 need manager approval. I've flagged your ${amount:.2f} request.",
        )
    return make_ok({"refund_id": "REF-" + order_id, "amount": amount, "status": "processed"})


REGISTRY = {
    "lookup_order_by_id":      lookup_order_by_id,
    "search_orders_by_customer": search_orders_by_customer,
    "get_customer":            get_customer,
    "process_refund":          process_refund,
}


# ---------------------------------------------------------------------------
# Tool schemas -- EXAM: descriptions must disambiguate the similar pair
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "lookup_order_by_id",
        "description": (
            "Retrieve ONE order by its exact primary-key order_id (format: ORD-###). "
            "Use this when the user gives you a specific order ID. "
            "For browsing a customer's history use search_orders_by_customer instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "Exact order id, e.g. ORD-100"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "search_orders_by_customer",
        "description": (
            "List ALL orders belonging to a given customer, optionally filtered by status. "
            "Use this when the user does NOT know an order id (e.g. 'show me my recent orders'). "
            "For a specific known order id use lookup_order_by_id instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "status":      {"type": "string", "enum": ["processing", "delivered", "cancelled"]},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_customer",
        "description": "Verify a customer identity by ID. MUST be called before process_refund.",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    },
    {
        "name": "process_refund",
        "description": (
            "Refund a specific amount against an order. "
            "Requires prior identity verification via get_customer. "
            "Refunds > $500 return a business error -- do NOT retry, explain policy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount":   {"type": "number"},
            },
            "required": ["order_id", "amount"],
        },
    },
]

SYSTEM = (
    "You are a customer support agent." + NL
    + "Choose tools using their descriptions -- lookup_order_by_id needs a known ID," + NL
    + "search_orders_by_customer is for browsing without an ID." + NL
    + "Always verify identity with get_customer before process_refund." + NL
    + "On isError=true responses:" + NL
    + "  transient (isRetryable=true)  -> retry ONCE then escalate" + NL
    + "  validation                    -> ask user for corrected input" + NL
    + "  business                      -> quote humanMessage, do not retry" + NL
    + "  permission                    -> escalate immediately"
)


def run_loop(user_message: str) -> tuple[str, int]:
    messages = [{"role": "user", "content": user_message}]
    iteration = 0
    while True:
        iteration += 1
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        if resp.stop_reason == "end_turn":
            for b in resp.content:
                if hasattr(b, "text"):
                    return b.text, iteration
            return "", iteration
        if resp.stop_reason != "tool_use":
            return f"(unexpected stop_reason: {resp.stop_reason})", iteration
        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for b in resp.content:
            if b.type == "tool_use":
                fn = REGISTRY.get(b.name)
                result = fn(**b.input) if fn else make_error(
                    "validation", False, "UNKNOWN_TOOL", f"Unknown: {b.name}", "Internal issue.")
                print(f"  [iter {iteration}] {b.name}({b.input}) -> "
                      f"isError={result.get('isError')}, cat={result.get('errorCategory','ok')}")
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": b.id,
                    "content":     json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Similar-tool disambiguation")
    print("  Request has a known order id -> should pick lookup_order_by_id.")
    print(sep)
    text, iters = run_loop("Please pull up order ORD-100 for me.")
    print(f"[{iters} iters]  {text[:250]}")

    print()
    print(sep)
    print("DEMO 2: Similar-tool disambiguation (no id known)")
    print("  Request has no order id -> should pick search_orders_by_customer.")
    print(sep)
    text, iters = run_loop("What orders does customer C001 have that are still processing?")
    print(f"[{iters} iters]  {text[:250]}")

    print()
    print(sep)
    print("DEMO 3: Structured business error (refund > $500)")
    print(sep)
    text, iters = run_loop("Customer C002 wants a full refund on order ORD-300 for $999.")
    print(f"[{iters} iters]  {text[:300]}")

    print()
    print(sep)
    print("DEMO 4: Structured transient error (should retry)")
    print(sep)
    text, iters = run_loop("Look up customer TIMEOUT and tell me their tier.")
    print(f"[{iters} iters]  {text[:250]}")

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Tool descriptions must explicitly differentiate similar tools --")
    print("     naming alone is not enough; call out boundary conditions.")
    print("  2. stop_reason drives loop control: 'tool_use' -> execute + append;")
    print("     'end_turn' -> return final text. Never parse NL for completion.")
    print("  3. Structured errors carry errorCategory + isRetryable + humanMessage")
    print("     so the agent can pick the right recovery (retry/ask/explain/escalate).")
    print("  4. Empty result != access failure. Use querySuccessful=true for empty.")
    print("  Mnemonic DESCRIBE: differentiate, explicit boundaries, schema,")
    print("     concrete names, retryable flag, humanMessage, boundary of empty, escalate.")
