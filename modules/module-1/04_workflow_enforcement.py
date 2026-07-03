"""
Domain 1 - Task 1.4: Multi-Step Workflows with Enforcement and Handoff Patterns

EXAM CONCEPTS:
  1. Programmatic enforcement (hooks, prerequisite gates) vs prompt-based guidance.
     Prompt instructions alone have a NON-ZERO failure rate.

  2. When DETERMINISTIC compliance is required (e.g., identity verification before
     financial operations), use programmatic enforcement -- not prompt instructions.

  3. Structured handoff protocols for escalation must include:
     customer details, root cause analysis, and recommended actions.

  4. Decompose multi-concern requests into DISTINCT items, investigate in PARALLEL
     using shared context, then synthesize a UNIFIED resolution.

  Mnemonic: GATE
    Guard (programmatic prerequisite blocks downstream calls)
    Audit (all calls inspected by enforcement layer)
    Terminate (block policy-violating actions, redirect)
    Escalate (structured handoff with full context)

Run: uv run python 04_workflow_enforcement.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)

# ---------------------------------------------------------------------------
# State machine: tracks which steps have completed (programmatic enforcement)
# ---------------------------------------------------------------------------
class WorkflowState:
    def __init__(self):
        self.customer_verified = False
        self.verified_customer_id = None
        self.verified_customer = None

    def reset(self):
        self.customer_verified = False
        self.verified_customer_id = None
        self.verified_customer = None


CUSTOMER_DB = {
    "C001": {"name": "Alice Smith", "account_status": "active", "tier": "premium"},
}
ORDER_DB = {
    "ORD-100": {"customer_id": "C001", "total": 129.99, "status": "delivered"},
}


# ---------------------------------------------------------------------------
# Tool implementations WITH programmatic enforcement
# ---------------------------------------------------------------------------
def get_customer_enforced(state: WorkflowState, customer_id: str) -> dict:
    if customer_id in CUSTOMER_DB:
        state.customer_verified = True
        state.verified_customer_id = customer_id
        state.verified_customer = CUSTOMER_DB[customer_id]
        return {"success": True, "customer": state.verified_customer}
    return {"success": False, "error": "Customer not found"}


def lookup_order_enforced(state: WorkflowState, order_id: str) -> dict:
    # GATE: block lookup until customer is verified
    if not state.customer_verified:
        return {
            "success": False,
            "error": "PREREQUISITE NOT MET: get_customer must be called first.",
            "required_step": "get_customer",
        }
    if order_id in ORDER_DB:
        return {"success": True, "order": ORDER_DB[order_id]}
    return {"success": False, "error": "Order not found"}


def process_refund_enforced(state: WorkflowState, order_id: str, amount: float) -> dict:
    # GATE: block refund until customer is verified
    if not state.customer_verified:
        return {
            "success": False,
            "error": "PREREQUISITE NOT MET: get_customer must be called first.",
            "required_step": "get_customer",
        }
    if amount > 500:
        # Business rule: large refunds escalate to human
        return {
            "success": False,
            "error": "Refund amount exceeds $500 limit. Escalation required.",
            "escalate": True,
        }
    return {"success": True, "refund_id": "REF-" + order_id, "amount": amount}


def escalate_to_human_enforced(state: WorkflowState, reason: str, summary: str) -> dict:
    return {
        "success": True,
        "ticket_id": "ESC-001",
        "message": "Escalated to human agent with structured handoff.",
    }


# ---------------------------------------------------------------------------
# Tool implementations WITHOUT enforcement (prompt-based only)
# ---------------------------------------------------------------------------
def get_customer_unenforced(customer_id: str) -> dict:
    if customer_id in CUSTOMER_DB:
        return {"success": True, "customer": CUSTOMER_DB[customer_id]}
    return {"success": False, "error": "Customer not found"}


def lookup_order_unenforced(order_id: str) -> dict:
    # No gate -- can be called without prior verification
    if order_id in ORDER_DB:
        return {"success": True, "order": ORDER_DB[order_id]}
    return {"success": False, "error": "Order not found"}


def process_refund_unenforced(order_id: str, amount: float) -> dict:
    # No gate -- can be called without prior verification
    return {"success": True, "refund_id": "REF-" + order_id, "amount": amount}


# ---------------------------------------------------------------------------
# Agentic loop runner (generic)
# ---------------------------------------------------------------------------
def run_loop(tools_def: list, tool_fn: callable, system: str, user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]
    for _ in range(10):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=system,
            tools=tools_def,
            messages=messages,
        )
        if resp.stop_reason == "end_turn":
            for block in resp.content:
                if hasattr(block, "text"):
                    return block.text
            return ""
        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                result = tool_fn(block.name, block.input)
                print(f"  Tool: {block.name}({block.input}) -> {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})
    return "(loop limit)"


# ---------------------------------------------------------------------------
# DEMO 1: Prompt-based ordering (probabilistic -- can skip verification)
# ---------------------------------------------------------------------------
TOOLS_UNENFORCED = [
    {
        "name": "get_customer",
        "description": "Retrieve customer information by customer ID.",
        "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
    },
    {
        "name": "lookup_order",
        "description": "Retrieve order details. Always call get_customer first.",
        "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
    },
    {
        "name": "process_refund",
        "description": "Process refund. Always verify customer identity first.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
            "required": ["order_id", "amount"],
        },
    },
]

SYSTEM_UNENFORCED = (
    "You are a support agent. Use tools to help customers." + NL
    + "You MUST call get_customer before any order or refund operations." + NL
    + "(This instruction is probabilistic -- Claude may occasionally skip it.)"
)


def run_unenforced(user_message: str) -> str:
    def tool_fn(name, inp):
        if name == "get_customer":
            return get_customer_unenforced(**inp)
        elif name == "lookup_order":
            return lookup_order_unenforced(**inp)
        elif name == "process_refund":
            return process_refund_unenforced(**inp)
        return {"error": "unknown tool"}
    return run_loop(TOOLS_UNENFORCED, tool_fn, SYSTEM_UNENFORCED, user_message)


# ---------------------------------------------------------------------------
# DEMO 2: Programmatic enforcement (deterministic)
# ---------------------------------------------------------------------------
def run_enforced(user_message: str) -> str:
    state = WorkflowState()

    TOOLS_ENFORCED = [
        {
            "name": "get_customer",
            "description": "Retrieve verified customer information. MUST be called before lookup_order or process_refund.",
            "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
        },
        {
            "name": "lookup_order",
            "description": "Retrieve order details. Requires prior get_customer call.",
            "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
        },
        {
            "name": "process_refund",
            "description": "Process refund. Requires prior get_customer call.",
            "input_schema": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
                "required": ["order_id", "amount"],
            },
        },
        {
            "name": "escalate_to_human",
            "description": "Escalate to human agent with structured handoff summary.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "summary": {"type": "string", "description": "Structured handoff: customer ID, root cause, amount, recommended action"},
                },
                "required": ["reason", "summary"],
            },
        },
    ]

    def tool_fn(name, inp):
        if name == "get_customer":
            return get_customer_enforced(state, **inp)
        elif name == "lookup_order":
            return lookup_order_enforced(state, **inp)
        elif name == "process_refund":
            return process_refund_enforced(state, **inp)
        elif name == "escalate_to_human":
            return escalate_to_human_enforced(state, **inp)
        return {"error": "unknown tool"}

    system = "You are a support agent. Use tools to help customers."
    return run_loop(TOOLS_ENFORCED, tool_fn, system, user_message)


# ---------------------------------------------------------------------------
# DEMO 3: Structured handoff
# ---------------------------------------------------------------------------
def demonstrate_structured_handoff() -> None:
    sep = "-" * 50
    print(sep)
    print("Structured handoff fields (CORRECT for escalation):")
    handoff = {
        "customer_id": "C001",
        "customer_name": "Alice Smith",
        "issue_summary": "Customer requests refund of $650 on ORD-100",
        "root_cause": "Refund amount $650 exceeds $500 policy limit",
        "actions_taken": ["Verified customer identity", "Looked up order ORD-100 ($129.99 delivered)"],
        "recommended_action": "Supervisor approval required for refund > $500",
        "escalation_reason": "policy_limit_exceeded",
    }
    for k, v in handoff.items():
        print(f"  {k}: {v}")
    print()
    print("BAD handoff (missing context):")
    bad_handoff = {"reason": "Can't process", "customer": "Alice"}
    for k, v in bad_handoff.items():
        print(f"  {k}: {v}")
    print("  -> Human agent has no context to act on this!")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60
    refund_request = "I'm customer C001. Please process a refund of $129.99 for order ORD-100."
    large_refund_request = "I'm customer C001. Please refund $650 for order ORD-100."

    print(sep)
    print("DEMO 1: Prompt-based ordering (probabilistic)")
    print("Request:", refund_request)
    print(sep)
    result1 = run_unenforced(refund_request)
    print("Result:", result1[:300])

    print()
    print(sep)
    print("DEMO 2: Programmatic enforcement (deterministic GATE)")
    print("Request:", refund_request)
    print(sep)
    result2 = run_enforced(refund_request)
    print("Result:", result2[:300])

    print()
    print(sep)
    print("DEMO 3: Large refund triggers business rule (> $500 gate)")
    print("Request:", large_refund_request)
    print(sep)
    result3 = run_enforced(large_refund_request)
    print("Result:", result3[:300])

    print()
    print(sep)
    print("DEMO 4: Structured handoff format")
    print(sep)
    demonstrate_structured_handoff()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Prompt instructions have NON-ZERO failure rate -- use programmatic gates.")
    print("  2. Prerequisite gates BLOCK downstream calls until required steps complete.")
    print("  3. Escalation handoffs MUST include: customer ID, root cause, recommended action.")
    print("  4. Decompose multi-concern requests, investigate in parallel, unify response.")
    print("  Mnemonic GATE: Guard, Audit, Terminate, Escalate.")
