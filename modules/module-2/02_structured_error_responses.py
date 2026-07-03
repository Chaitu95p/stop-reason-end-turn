"""
Domain 2 - Task 2.2: Implement Structured Error Responses for MCP Tools

EXAM CONCEPTS:
  1. MCP isError flag: communicate tool failures back to the agent.

  2. Error categories (TVBP):
     Transient  → timeout, service unavailable (retry makes sense)
     Validation → invalid input format (retry won't help without fix)
     Business   → policy violation (retry won't help, explain to user)
     Permission → access denied (retry won't help, escalate)

  3. UNIFORM error responses ("Operation failed") PREVENT the agent from
     making appropriate recovery decisions.

  4. Structured error metadata enables intelligent agent recovery:
     - errorCategory: tells agent HOW to respond
     - isRetryable: tells agent WHETHER to retry
     - humanMessage: what to tell the customer

  5. Local recovery: subagents handle transient failures locally.
     Only propagate errors they CANNOT resolve, with partial results.

  6. Empty results vs access failures are DISTINCT:
     Empty result = successful query, no matches
     Access failure = query couldn't complete

Run: uv run python 02_structured_error_responses.py
"""

import json
import time
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Structured error response format
# ---------------------------------------------------------------------------
def make_error(
    error_category: str,
    is_retryable: bool,
    error_code: str,
    developer_message: str,
    human_message: str,
    partial_result: dict = None,
) -> dict:
    """
    Structured MCP error response.
    isError=True signals to the agent that this is a failure, not a result.
    """
    error = {
        "isError": True,
        "errorCategory": error_category,   # transient | validation | business | permission
        "isRetryable": is_retryable,
        "errorCode": error_code,
        "developerMessage": developer_message,
        "humanMessage": human_message,
    }
    if partial_result:
        error["partialResult"] = partial_result
    return error


def make_empty_result(resource: str, query: str) -> dict:
    """
    EXAM KEY: Empty result is NOT an error.
    isError=False, empty list is a valid response.
    """
    return {
        "isError": False,
        "results": [],
        "message": f"No {resource} found matching: {query}",
        "querySuccessful": True,  # distinguishes from access failure
    }


# ---------------------------------------------------------------------------
# Mock tools with structured error responses
# ---------------------------------------------------------------------------
def get_customer_with_errors(customer_id: str) -> dict:
    if customer_id == "TIMEOUT":
        return make_error(
            error_category="transient",
            is_retryable=True,
            error_code="DB_TIMEOUT",
            developer_message="Database connection timed out after 5000ms",
            human_message="We're experiencing a brief delay. Please try again in a moment.",
        )
    elif customer_id.startswith("email:"):
        return make_error(
            error_category="validation",
            is_retryable=False,
            error_code="INVALID_ID_FORMAT",
            developer_message=f"Customer IDs must be C### format, got: {customer_id}",
            human_message="I need your customer ID (format: C followed by numbers), not your email address.",
        )
    elif customer_id == "RESTRICTED":
        return make_error(
            error_category="permission",
            is_retryable=False,
            error_code="ACCESS_DENIED",
            developer_message="This record requires elevated permissions to access",
            human_message="I don't have access to this account. Let me connect you with a supervisor.",
        )
    elif customer_id == "NOTFOUND":
        # EXAM KEY: Empty result is NOT an error -- successful query with no matches
        return make_empty_result("customer", customer_id)
    else:
        return {"isError": False, "customer": {"id": customer_id, "name": "Alice Smith", "tier": "premium"}}


def process_refund_with_errors(order_id: str, amount: float) -> dict:
    if amount > 500:
        return make_error(
            error_category="business",
            is_retryable=False,
            error_code="REFUND_LIMIT_EXCEEDED",
            developer_message=f"Refund amount ${amount:.2f} exceeds policy limit of $500",
            human_message=f"Refunds over $500 require manager approval. I've noted your request for ${amount:.2f}.",
        )
    return {"isError": False, "refund_id": "REF-" + order_id, "amount": amount, "status": "processed"}


TOOLS_DEF = [
    {
        "name": "get_customer",
        "description": "Retrieve customer record. Returns structured error on failure.",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    },
    {
        "name": "process_refund",
        "description": "Process a refund. Returns business error if amount exceeds $500 policy limit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number"},
            },
            "required": ["order_id", "amount"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Escalate case to human agent when resolution is outside agent capabilities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "context": {"type": "string"},
            },
            "required": ["reason", "context"],
        },
    },
]

SYSTEM = (
    "You are a customer support agent. Use tools to help customers." + NL
    + "When a tool returns isError=true:" + NL
    + "  transient (isRetryable=true): retry once, then escalate if still failing" + NL
    + "  validation (isRetryable=false): ask the customer for correct information" + NL
    + "  business (isRetryable=false): explain the policy limit using humanMessage" + NL
    + "  permission (isRetryable=false): escalate to a human agent" + NL
    + "When a tool returns isError=false with empty results: the query succeeded but no records exist."
)


def run_loop_with_structured_errors(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]
    retry_counts = {}

    for _ in range(15):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=SYSTEM,
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
                tool_name = block.name
                inp = block.input
                # Execute tool
                if tool_name == "get_customer":
                    result = get_customer_with_errors(**inp)
                elif tool_name == "process_refund":
                    result = process_refund_with_errors(**inp)
                elif tool_name == "escalate_to_human":
                    result = {"isError": False, "ticket": "ESC-001", "message": "Escalated successfully"}
                else:
                    result = {"isError": True, "errorCategory": "validation", "isRetryable": False,
                              "errorCode": "UNKNOWN_TOOL", "developerMessage": f"Unknown: {tool_name}",
                              "humanMessage": "Internal error"}
                print(f"  Tool: {tool_name}({inp}) -> isError={result.get('isError')}, "
                      f"category={result.get('errorCategory', 'none')}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})
    return "(loop limit)"


# ---------------------------------------------------------------------------
# Show contrast: uniform vs structured errors
# ---------------------------------------------------------------------------
def compare_error_formats() -> None:
    sep = "-" * 50
    print(sep)
    print("UNIFORM error (ANTI-PATTERN):")
    uniform = {"error": "Operation failed"}
    print("  " + json.dumps(uniform))
    print("  -> Agent cannot determine: retry? explain? escalate?")

    print()
    print("STRUCTURED error (CORRECT) -- business error:")
    structured = make_error(
        error_category="business",
        is_retryable=False,
        error_code="REFUND_LIMIT_EXCEEDED",
        developer_message="Amount $650 exceeds $500 policy limit",
        human_message="Refunds over $500 require manager approval.",
    )
    print("  " + json.dumps(structured, indent=2))
    print("  -> Agent knows: not retryable, use humanMessage to explain policy")

    print()
    print("EMPTY RESULT (not an error -- EXAM: distinguish from access failure):")
    empty = make_empty_result("customer", "C999")
    print("  " + json.dumps(empty))
    print("  -> Agent knows: query succeeded, no records found, no need to retry")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Error format comparison (uniform vs structured)")
    print(sep)
    compare_error_formats()

    print()
    print(sep)
    print("DEMO 2: Agent handles transient error (timeout → retry)")
    print(sep)
    result = run_loop_with_structured_errors(
        "Please look up customer TIMEOUT and check their account."
    )
    print("Final:", result[:300])

    print()
    print(sep)
    print("DEMO 3: Validation error (wrong format → ask for correction)")
    print(sep)
    result = run_loop_with_structured_errors(
        "Look up customer email:alice@example.com"
    )
    print("Final:", result[:300])

    print()
    print(sep)
    print("DEMO 4: Business error (refund > $500 → explain policy)")
    print(sep)
    result = run_loop_with_structured_errors(
        "Process a refund of $650 for order ORD-100."
    )
    print("Final:", result[:300])

    print()
    print(sep)
    print("DEMO 5: Empty result (no customer found -- successful query)")
    print(sep)
    result = run_loop_with_structured_errors("Look up customer NOTFOUND")
    print("Final:", result[:300])

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Four error categories: Transient (retry), Validation (fix input),")
    print("     Business (policy limit), Permission (escalate). Mnemonic: TVBP")
    print("  2. isRetryable=False prevents wasted retry attempts for non-fixable errors.")
    print("  3. Uniform errors block intelligent recovery -- always use structured errors.")
    print("  4. EMPTY result ≠ ACCESS FAILURE: distinguish using querySuccessful field.")
    print("  5. Local recovery: subagents handle transient errors before propagating.")
