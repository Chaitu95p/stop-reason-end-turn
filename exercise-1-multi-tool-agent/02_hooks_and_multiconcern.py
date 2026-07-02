"""
Exercise 1 - Steps 4-5: PreToolUse Hook Enforcement + Multi-Concern Requests

EXAM CONCEPTS:
  1. Hooks are a DETERMINISTIC policy layer around model calls.
     A PreToolUse hook intercepts a tool call BEFORE execution and can:
       - allow    -> forward to real tool
       - deny     -> return a synthetic tool_result with isError=true
       - rewrite  -> replace tool_use with an escalation tool call
     The agent then reasons about the hook's result on the next turn.

  2. Business rules belong in HOOKS, not tool implementations, when the
     rule spans multiple tools or is enforced at the platform level
     (audit logging, dollar thresholds, PII redaction).

  3. Multi-concern requests: Claude decomposes into ordered subgoals
     because tool_result feeds back into context. Verify by inspecting
     the sequence of tool_use calls -- a decomposition looks like
       [verify customer] -> [handle concern A] -> [handle concern B]
       -> [end_turn with synthesized reply].

  Mnemonic: HOOK
    Halt tool call before execution
    Override the tool_result deterministically
    Observe: the agent sees your synthetic result next turn
    Keep policy code out of tool implementations

Run: uv run python 02_hooks_and_multiconcern.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Mock data (shared with 01_)
# ---------------------------------------------------------------------------
CUSTOMERS = {
    "C001": {"name": "Alice Smith", "tier": "premium"},
    "C002": {"name": "Bob Jones",   "tier": "standard"},
}
ORDERS = {
    "ORD-100": {"customer_id": "C001", "total": 129.99, "status": "delivered"},
    "ORD-300": {"customer_id": "C002", "total": 999.00, "status": "delivered"},
    "ORD-777": {"customer_id": "C001", "total": 750.00, "status": "delivered"},
}


def make_error(cat, retry, code, dev, human):
    return {"isError": True, "errorCategory": cat, "isRetryable": retry,
            "errorCode": code, "developerMessage": dev, "humanMessage": human}


def make_ok(payload):
    return {"isError": False, **payload}


# ---------------------------------------------------------------------------
# Real tool implementations
# ---------------------------------------------------------------------------
def get_customer(customer_id: str) -> dict:
    if customer_id in CUSTOMERS:
        return make_ok({"customer": {"id": customer_id, **CUSTOMERS[customer_id]}})
    return make_error("validation", False, "UNKNOWN_CUSTOMER", "not found", "Customer ID not on file.")


def lookup_order(order_id: str) -> dict:
    if order_id in ORDERS:
        return make_ok({"order": {"id": order_id, **ORDERS[order_id]}})
    return make_error("validation", False, "UNKNOWN_ORDER", "not found", "Order ID not on file.")


def process_refund(order_id: str, amount: float) -> dict:
    if order_id not in ORDERS:
        return make_error("validation", False, "UNKNOWN_ORDER", "not found", "Order not on file.")
    return make_ok({"refund_id": "REF-" + order_id, "amount": amount, "status": "processed"})


def escalate_to_human(reason: str, context: str) -> dict:
    return make_ok({"ticket": "ESC-42", "reason": reason, "context": context,
                    "sla": "Manager will contact within 1 business day."})


REGISTRY = {
    "get_customer":      get_customer,
    "lookup_order":      lookup_order,
    "process_refund":    process_refund,
    "escalate_to_human": escalate_to_human,
}


# ---------------------------------------------------------------------------
# STEP 4: PreToolUse hook -- YOUR CONTRIBUTION LIVES BELOW
# ---------------------------------------------------------------------------
REFUND_THRESHOLD = 500.0  # USD

def pretooluse_hook(tool_name: str, tool_input: dict) -> dict | None:
    """
    Deterministic policy enforcement BEFORE the tool runs.

    Return None       -> allow the tool call through
    Return a dict     -> use this dict as the tool_result INSTEAD of running the tool
                         (typically an isError=true payload or a rewritten escalation)

    ---------------------------------------------------------------------------
    LEARNING-MODE TODO -- your business-rule policy goes here.

    The exam step says: "intercept tool calls to enforce a business rule
    (e.g., blocking operations above a threshold amount), redirecting to an
    escalation workflow when triggered."

    Implement 5-10 lines that:
      1. If tool_name == "process_refund" and tool_input["amount"] > REFUND_THRESHOLD,
         return a synthetic tool_result that:
           - has isError=True, errorCategory="business", isRetryable=False,
           - humanMessage explaining the policy,
           - AND a "recommendedAction" field of "escalate_to_human"
             so the agent knows to switch tools rather than retry.
      2. Otherwise return None (allow).

    Design choices worth thinking about:
      - Do you also want to block high-value refunds against STANDARD-tier customers
        while allowing them for PREMIUM-tier? (would need a lookup here)
      - Do you audit-log every intercepted call? (append to a list)
      - Do you rewrite to escalate_to_human directly, or let the model decide?
    ---------------------------------------------------------------------------
    """
    # TODO: implement policy here
    if tool_name == "process_refund" and tool_input.get("amount", 0) > REFUND_THRESHOLD:
        return make_error(
            "business", False, "REFUND_ABOVE_THRESHOLD_HOOK",
            f"Blocked by PreToolUse hook: ${tool_input['amount']:.2f} > ${REFUND_THRESHOLD:.2f}",
            f"Refunds over ${REFUND_THRESHOLD:.0f} require manager approval. "
            "Please use escalate_to_human to route this for review.",
        ) | {"recommendedAction": "escalate_to_human"}
    return None


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------
TOOLS = [
    {"name": "get_customer",
     "description": "Verify customer identity by ID. Call before any refund.",
     "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                      "required": ["customer_id"]}},
    {"name": "lookup_order",
     "description": "Retrieve order details by order_id (format ORD-###).",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}},
                      "required": ["order_id"]}},
    {"name": "process_refund",
     "description": "Refund an amount against an order. High-value refunds may be blocked "
                    "by PreToolUse hook -- when that happens the tool_result will contain "
                    "recommendedAction='escalate_to_human'.",
     "input_schema": {"type": "object",
                      "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
                      "required": ["order_id", "amount"]}},
    {"name": "escalate_to_human",
     "description": "Route the case to a human manager with reason + context.",
     "input_schema": {"type": "object",
                      "properties": {"reason": {"type": "string"}, "context": {"type": "string"}},
                      "required": ["reason", "context"]}},
]

SYSTEM = (
    "You are a customer support agent handling potentially multiple concerns per turn." + NL
    + "Decompose multi-part requests into ordered steps: verify identity first," + NL
    + "handle each concern with the smallest tool set, then synthesize one reply." + NL
    + "If a tool_result contains recommendedAction, follow it."
)


def run_loop_with_hook(user_message: str, hook_log: list) -> tuple[str, list]:
    """Return (final_text, tool_call_trace)."""
    messages = [{"role": "user", "content": user_message}]
    trace = []
    while True:
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
                    return b.text, trace
            return "", trace
        if resp.stop_reason != "tool_use":
            return f"(unexpected: {resp.stop_reason})", trace
        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for b in resp.content:
            if b.type == "tool_use":
                trace.append(b.name)
                hooked = pretooluse_hook(b.name, b.input)
                if hooked is not None:
                    hook_log.append({"tool": b.name, "input": b.input, "action": "BLOCKED"})
                    print(f"  HOOK BLOCK {b.name}({b.input})")
                    result = hooked
                else:
                    fn = REGISTRY.get(b.name)
                    result = fn(**b.input) if fn else make_error(
                        "validation", False, "UNKNOWN_TOOL", "n/a", "Internal issue.")
                    print(f"  {b.name}({b.input}) -> isError={result.get('isError')}")
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
    print("DEMO 1: Hook DOES NOT trigger (refund <= threshold)")
    print(sep)
    log = []
    text, trace = run_loop_with_hook(
        "Customer C001 wants a $129.99 refund on ORD-100.", log)
    print(f"Trace: {trace}")
    print(f"Hook events: {log}")
    print(f"Final: {text[:250]}")

    print()
    print(sep)
    print("DEMO 2: Hook triggers -> agent must escalate")
    print("  Refund $750 on ORD-777 (>$500) should be blocked, then escalated.")
    print(sep)
    log = []
    text, trace = run_loop_with_hook(
        "Customer C001 needs a $750 refund on ORD-777.", log)
    print(f"Trace: {trace}")
    print(f"Hook events: {log}")
    print(f"Final: {text[:300]}")

    print()
    print(sep)
    print("DEMO 3: Multi-concern request -- verify + lookup two orders + summarize")
    print(sep)
    log = []
    text, trace = run_loop_with_hook(
        "I'm customer C001. Can you tell me the status of order ORD-100 "
        "AND process a $49 refund on order ORD-777 for me?", log)
    print(f"Trace: {trace}")
    print(f"Final: {text[:400]}")

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. PreToolUse hooks enforce policy DETERMINISTICALLY -- they run")
    print("     before the model sees any tool_result, so the model cannot bypass them.")
    print("  2. A blocked tool call becomes a synthetic tool_result the agent reasons about --")
    print("     include recommendedAction to steer recovery without new prompting.")
    print("  3. Business rules that span tools (thresholds, PII, audit) belong in hooks,")
    print("     not scattered across each tool implementation.")
    print("  4. Multi-concern requests decompose naturally through stop_reason=tool_use --")
    print("     Claude reasons over accumulated tool_results before synthesizing end_turn.")
    print("  Mnemonic HOOK: Halt, Override result, Observe next-turn reasoning, Keep policy out of tools.")
