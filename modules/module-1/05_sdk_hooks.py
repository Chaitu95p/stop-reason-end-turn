"""
Domain 1 - Task 1.5: Agent SDK Hooks for Tool Call Interception and Normalization

EXAM CONCEPTS:
  1. PostToolUse hooks: intercept tool RESULTS before the model processes them.
     Use for data normalization (timestamps, status codes, formats).

  2. PreToolUse hooks: intercept OUTGOING tool calls to enforce compliance rules.
     Use for blocking policy-violating actions.

  3. Hooks provide DETERMINISTIC guarantees -- prompt instructions give
     only PROBABILISTIC compliance.

  KEY PATTERNS:
    PostToolUse: normalize heterogeneous data formats from different MCP tools
      - Unix timestamps → ISO 8601
      - Numeric status codes → human-readable strings
      - Currency in different formats → normalized decimal

    PreToolUse: policy enforcement
      - Block refunds > $500 → redirect to escalation workflow

  Mnemonic: HINT
    Hook Intercepts (all tool interactions)
    Normalizes (heterogeneous data formats)
    Transforms (outgoing calls for policy compliance)

Run: uv run python 05_sdk_hooks.py
"""

import json
import datetime
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Raw tool outputs (heterogeneous formats from different MCP backends)
# ---------------------------------------------------------------------------
RAW_TOOL_OUTPUTS = {
    "get_order": {
        "order_id": "ORD-100",
        "created_at": 1709558400,          # Unix timestamp (needs normalization)
        "shipped_at": 1709731200,          # Unix timestamp
        "status_code": 3,                  # Numeric code (needs normalization)
        "amount_cents": 12999,             # Cents (needs conversion to dollars)
    },
    "get_customer": {
        "customer_id": "C001",
        "name": "Alice Smith",
        "member_since": 1640995200,        # Unix timestamp
        "account_status": 1,              # 1=active, 2=suspended, 3=closed
        "credit_limit_pence": 50000,      # British pence (different currency unit)
    },
    "get_refund_policy": {
        "max_refund_usd": 500,
        "approval_required_above": 250,
        "policy_version": "v2.3",
    },
}

ORDER_STATUS_MAP = {1: "pending", 2: "processing", 3: "delivered", 4: "returned", 5: "cancelled"}
ACCOUNT_STATUS_MAP = {1: "active", 2: "suspended", 3: "closed"}


# ---------------------------------------------------------------------------
# PostToolUse hook: normalize heterogeneous data formats
# ---------------------------------------------------------------------------
def post_tool_use_normalization_hook(tool_name: str, raw_result: dict) -> dict:
    """
    EXAM CONCEPT: PostToolUse hook intercepts tool results BEFORE the model
    processes them. Normalizes formats so the model works with clean data.
    """
    normalized = dict(raw_result)

    # Normalize Unix timestamps → ISO 8601
    for field in ["created_at", "shipped_at", "member_since"]:
        if field in normalized and isinstance(normalized[field], int):
            dt = datetime.datetime.fromtimestamp(normalized[field], tz=datetime.timezone.utc)
            normalized[field] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"  [PostToolUse hook] Normalized {field}: {raw_result[field]} → {normalized[field]}")

    # Normalize numeric status codes → strings
    if "status_code" in normalized:
        raw_code = normalized["status_code"]
        normalized["status"] = ORDER_STATUS_MAP.get(raw_code, f"unknown({raw_code})")
        del normalized["status_code"]
        print(f"  [PostToolUse hook] Normalized status_code {raw_code} → '{normalized['status']}'")

    if "account_status" in normalized and isinstance(normalized["account_status"], int):
        raw_code = normalized["account_status"]
        normalized["account_status"] = ACCOUNT_STATUS_MAP.get(raw_code, f"unknown({raw_code})")
        print(f"  [PostToolUse hook] Normalized account_status {raw_code} → '{normalized['account_status']}'")

    # Normalize currency units → USD decimal
    if "amount_cents" in normalized:
        normalized["amount_usd"] = normalized.pop("amount_cents") / 100.0
        print(f"  [PostToolUse hook] Normalized amount_cents → amount_usd: ${normalized['amount_usd']:.2f}")

    if "credit_limit_pence" in normalized:
        # Convert pence to GBP
        normalized["credit_limit_gbp"] = normalized.pop("credit_limit_pence") / 100.0
        print(f"  [PostToolUse hook] Normalized credit_limit_pence → credit_limit_gbp: £{normalized['credit_limit_gbp']:.2f}")

    return normalized


# ---------------------------------------------------------------------------
# PreToolUse hook: policy enforcement (block + redirect)
# ---------------------------------------------------------------------------
class PolicyViolation(Exception):
    def __init__(self, tool_name: str, reason: str, redirect_to: str):
        self.tool_name = tool_name
        self.reason = reason
        self.redirect_to = redirect_to
        super().__init__(reason)


def pre_tool_use_policy_hook(tool_name: str, tool_input: dict) -> dict:
    """
    EXAM CONCEPT: PreToolUse hook intercepts OUTGOING tool calls.
    Blocks policy-violating actions and redirects to alternative workflows.
    Returns modified input (or raises PolicyViolation to block).
    """
    if tool_name == "process_refund":
        amount = tool_input.get("amount", 0)
        if amount > 500:
            print(f"  [PreToolUse hook] BLOCKED: refund ${amount:.2f} exceeds $500 limit")
            raise PolicyViolation(
                tool_name=tool_name,
                reason=f"Refund amount ${amount:.2f} exceeds $500 policy limit",
                redirect_to="escalate_to_human",
            )
        elif amount > 250:
            # Allow but flag for audit
            print(f"  [PreToolUse hook] FLAGGED: refund ${amount:.2f} requires approval (> $250)")
            tool_input["requires_approval"] = True

    return tool_input


# ---------------------------------------------------------------------------
# Simulated agentic loop WITH hooks
# ---------------------------------------------------------------------------
TOOLS_DEF = [
    {
        "name": "get_order",
        "description": "Get order details including status and amount.",
        "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
    },
    {
        "name": "get_customer",
        "description": "Get customer account information.",
        "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
    },
    {
        "name": "process_refund",
        "description": "Process a refund. Maximum $500 per transaction.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
            "required": ["order_id", "amount"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Escalate to human agent for policy exceptions.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}, "customer_id": {"type": "string"}},
            "required": ["reason", "customer_id"],
        },
    },
]


def execute_tool_with_hooks(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool with pre-call and post-result hooks applied."""
    # 1. Pre-call hook
    try:
        tool_input = pre_tool_use_policy_hook(tool_name, tool_input)
    except PolicyViolation as pv:
        print(f"  [PreToolUse hook] Redirecting to {pv.redirect_to}")
        return {
            "error": pv.reason,
            "blocked": True,
            "redirect": pv.redirect_to,
            "suggested_action": f"Call {pv.redirect_to} instead",
        }

    # 2. Execute tool (simulated backend call)
    if tool_name in RAW_TOOL_OUTPUTS:
        raw_result = dict(RAW_TOOL_OUTPUTS[tool_name])
    elif tool_name == "process_refund":
        raw_result = {"success": True, "refund_id": "REF-" + tool_input.get("order_id", "X")}
    elif tool_name == "escalate_to_human":
        raw_result = {"success": True, "ticket_id": "ESC-001"}
    else:
        raw_result = {"error": "unknown tool"}

    # 3. PostToolUse hook
    normalized_result = post_tool_use_normalization_hook(tool_name, raw_result)
    return normalized_result


def run_with_hooks(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]
    for _ in range(10):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system="You are a support agent. Use tools to help customers.",
            tools=TOOLS_DEF,
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
                print(f"  Claude calls: {block.name}({block.input})")
                result = execute_tool_with_hooks(block.name, dict(block.input))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})
    return "(loop limit)"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: PostToolUse normalization hook (raw data → clean data)")
    print(sep)
    print("Raw order data from backend:")
    print(json.dumps(RAW_TOOL_OUTPUTS["get_order"], indent=2))
    print()
    normalized = post_tool_use_normalization_hook("get_order", RAW_TOOL_OUTPUTS["get_order"])
    print("Normalized result:")
    print(json.dumps(normalized, indent=2))

    print()
    print(sep)
    print("DEMO 2: PreToolUse policy hook (block refund > $500)")
    print(sep)
    print("Attempting refund of $650...")
    try:
        pre_tool_use_policy_hook("process_refund", {"order_id": "ORD-100", "amount": 650})
    except PolicyViolation as pv:
        print(f"  BLOCKED: {pv.reason} → redirect to {pv.redirect_to}")

    print()
    print("Attempting refund of $300 (between $250 and $500)...")
    result = pre_tool_use_policy_hook("process_refund", {"order_id": "ORD-100", "amount": 300})
    print(f"  Allowed with flag: {result}")

    print()
    print(sep)
    print("DEMO 3: Full agentic loop with hooks (large refund triggers escalation)")
    print(sep)
    final = run_with_hooks(
        "Customer C001 wants a refund of $650 for order ORD-100. Please process."
    )
    print("Final response:", final[:400])

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. PostToolUse hooks normalize heterogeneous data BEFORE the model sees it.")
    print("  2. PreToolUse hooks enforce policy by BLOCKING or MODIFYING outgoing calls.")
    print("  3. Hooks = DETERMINISTIC; prompt instructions = PROBABILISTIC compliance.")
    print("  4. Use hooks for business rules requiring GUARANTEED enforcement.")
    print("  Mnemonic HINT: Hook Intercepts, Normalizes, Transforms.")
