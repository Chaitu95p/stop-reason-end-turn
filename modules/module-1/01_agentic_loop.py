"""
Domain 1 - Task 1.1: Agentic Loops for Autonomous Task Execution

EXAM CONCEPTS:
  1. Agentic loop lifecycle:
       Send request → inspect stop_reason
       "tool_use"  → execute tools → append result → loop
       "end_turn"  → done

  2. Tool results MUST be appended to conversation history so the model
     can reason about the next action from accumulated context.

  3. Model-driven decision-making: Claude chooses WHICH tool to call next
     based on context -- not a pre-configured decision tree.

  ANTI-PATTERNS (avoid these on the exam):
    - Parsing Claude's natural-language text to decide whether to stop.
    - Setting an arbitrary iteration cap as the PRIMARY stopping mechanism.
    - Checking for assistant text content as a completion indicator.

  Mnemonic: STOP
    Send request
    Test stop_reason
    Operate tools
    Proceed (loop) or Terminate

Run: uv run python 01_agentic_loop.py
"""

import json
import anthropic

client = anthropic.Anthropic()

# ---------------------------------------------------------------------------
# Mock tool implementations (simulate MCP backend)
# ---------------------------------------------------------------------------
CUSTOMER_DB = {
    "C001": {"name": "Alice Smith", "email": "alice@example.com", "tier": "premium"},
    "C002": {"name": "Bob Jones",   "email": "bob@example.com",   "tier": "standard"},
}

ORDER_DB = {
    "ORD-100": {"customer_id": "C001", "total": 129.99, "status": "delivered"},
    "ORD-200": {"customer_id": "C002", "total":  49.00, "status": "processing"},
}

NL = chr(10)


def get_customer(customer_id: str) -> dict:
    """Retrieve verified customer record."""
    if customer_id in CUSTOMER_DB:
        return {"success": True, "customer": CUSTOMER_DB[customer_id]}
    return {"success": False, "error": "Customer not found"}


def lookup_order(order_id: str) -> dict:
    """Retrieve order details."""
    if order_id in ORDER_DB:
        return {"success": True, "order": ORDER_DB[order_id]}
    return {"success": False, "error": "Order not found"}


def process_refund(order_id: str, amount: float) -> dict:
    """Process a refund for an order."""
    if order_id in ORDER_DB:
        return {"success": True, "refund_id": "REF-" + order_id, "amount": amount}
    return {"success": False, "error": "Order not found"}


TOOL_REGISTRY = {
    "get_customer":  get_customer,
    "lookup_order":  lookup_order,
    "process_refund": process_refund,
}

TOOLS = [
    {
        "name": "get_customer",
        "description": "Retrieve verified customer information by customer ID. "
                       "MUST be called before any order or refund operations to verify identity.",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string", "description": "Customer ID (e.g. C001)"}},
            "required": ["customer_id"],
        },
    },
    {
        "name": "lookup_order",
        "description": "Retrieve order details by order ID. Returns order status, total, and customer ID.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "Order ID (e.g. ORD-100)"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "process_refund",
        "description": "Process a refund for a specific order amount. "
                       "Requires prior customer verification via get_customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount":   {"type": "number", "description": "Refund amount in USD"},
            },
            "required": ["order_id", "amount"],
        },
    },
]

SYSTEM = (
    "You are a customer support agent. Use available tools to resolve requests." + NL
    + "Always verify the customer's identity with get_customer before processing refunds."
)


# ---------------------------------------------------------------------------
# CORRECT agentic loop
# ---------------------------------------------------------------------------
def run_agentic_loop(user_message: str, label: str) -> str:
    """
    Correct implementation: loop on stop_reason == 'tool_use',
    terminate on stop_reason == 'end_turn'.
    """
    messages = [{"role": "user", "content": user_message}]
    iteration = 0

    while True:
        iteration += 1
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        # KEY EXAM FACT: inspect stop_reason to control loop
        if response.stop_reason == "end_turn":
            # Extract final text response
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "(no text in final response)"

        if response.stop_reason == "tool_use":
            # Append assistant message (with tool_use blocks) to history
            messages.append({"role": "assistant", "content": response.content})

            # Execute ALL requested tools in this response
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    fn = TOOL_REGISTRY.get(block.name)
                    if fn:
                        result = fn(**block.input)
                    else:
                        result = {"error": f"Unknown tool: {block.name}"}
                    print(f"  [iter {iteration}] Tool call: {block.name}({block.input})")
                    print(f"              Result: {result}")
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     json.dumps(result),
                    })

            # KEY EXAM FACT: append tool results so model reasons from them next
            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason -- treat as terminal
            return f"(unexpected stop_reason: {response.stop_reason})"


# ---------------------------------------------------------------------------
# ANTI-PATTERN 1: parsing natural language to decide when to stop
# ---------------------------------------------------------------------------
def antipattern_nl_parsing(user_message: str) -> str:
    """
    WRONG: checking assistant text for 'DONE' or 'complete' to terminate.
    Fragile -- Claude may phrase completion differently each run.
    """
    messages = [{"role": "user", "content": user_message}]
    for _ in range(10):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=SYSTEM + NL + "When you are done, say DONE.",
            tools=TOOLS,
            messages=messages,
        )
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text
        if "DONE" in text.upper():   # <-- ANTI-PATTERN
            return text
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    fn = TOOL_REGISTRY.get(block.name, lambda **k: {"error": "unknown"})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(fn(**block.input)),
                    })
            messages.append({"role": "user", "content": tool_results})
    return "(loop exhausted without DONE signal)"


# ---------------------------------------------------------------------------
# ANTI-PATTERN 2: fixed iteration cap as primary stopping mechanism
# ---------------------------------------------------------------------------
def antipattern_fixed_cap(user_message: str, max_iters: int = 2) -> str:
    """
    WRONG: stopping after N iterations regardless of stop_reason.
    Cuts off legitimate multi-step reasoning.
    """
    messages = [{"role": "user", "content": user_message}]
    for i in range(max_iters):     # <-- ANTI-PATTERN as primary stop
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                fn = TOOL_REGISTRY.get(block.name, lambda **k: {"error": "unknown"})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(fn(**block.input)),
                })
        messages.append({"role": "user", "content": tool_results})
    return f"(loop capped at {max_iters} iterations -- response may be incomplete)"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60
    request = (
        "Customer C001 is asking for a refund on order ORD-100 for $129.99. "
        "Please process this."
    )

    print(sep)
    print("DEMO 1: CORRECT agentic loop (stop_reason driven)")
    print(sep)
    print("Request:", request)
    print()
    result = run_agentic_loop(request, "CORRECT")
    print()
    print("Final response:", result)

    print()
    print(sep)
    print("DEMO 2: ANTI-PATTERN -- fixed iteration cap (max_iters=2)")
    print("  A 3-step task (verify → lookup → refund) gets cut off at 2.")
    print(sep)
    capped = antipattern_fixed_cap(request, max_iters=2)
    print("Result:", capped)

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Loop condition: continue on 'tool_use', terminate on 'end_turn'.")
    print("  2. ALWAYS append tool results to history before the next request.")
    print("  3. NEVER parse natural language or use fixed caps as primary stop.")
    print("  4. Claude chooses WHICH tool to call -- not a pre-configured sequence.")
    print("  Mnemonic STOP: Send, Test stop_reason, Operate tools, Proceed/Terminate.")
