"""
07 — Error Handling
====================
What this covers:
  - ToolError: expected, known failures (business logic, not-found, validation)
  - Generic exceptions: unexpected internal errors
  - mask_error_details: hiding tracebacks in production
  - MCP-level isError flag vs Python exceptions on the client
  - Error patterns that map to CCA-F TVBP error categories
    (Transient / Validation / Business / Permission)
  - Resource errors
  - Client-side error handling patterns

Run: uv run python 07_error_handling.py
"""

import asyncio
import json
from fastmcp import FastMCP, Client, Context
from fastmcp.exceptions import ToolError

# ── Two servers: one dev (errors visible), one prod (errors masked) ────────
dev_server  = FastMCP("dev-server",  mask_error_details=False)
prod_server = FastMCP("prod-server", mask_error_details=True)


# ── TVBP error categories — matching CCA-F structured error pattern ────────
#
# For MCP tools, ToolError is the signaling mechanism.
# For an agent consuming these tools, the error message should include
# enough info to drive the right recovery action.

# @mcp.tool returns the original function unchanged, so stacking decorators
# across two servers works — each server registers the same function.
@dev_server.tool
@prod_server.tool
def transient_lookup(resource_id: str) -> dict:
    """
    Simulates transient failure (DB timeout).
    Category: Transient — isRetryable=True
    Agent behavior: retry once, then escalate if still failing.
    """
    if resource_id == "TIMEOUT":
        raise ToolError(
            json.dumps({
                "errorCategory": "transient",
                "isRetryable": True,
                "errorCode": "DB_TIMEOUT",
                "humanMessage": "We're experiencing a brief delay. Please try again.",
            })
        )
    return {"id": resource_id, "data": f"record-{resource_id}"}


@dev_server.tool
@prod_server.tool
def validate_customer_id(customer_id: str) -> dict:
    """
    Simulates validation failure.
    Category: Validation — isRetryable=False (fix input, then retry)
    """
    if not customer_id.startswith("C") or not customer_id[1:].isdigit():
        raise ToolError(
            json.dumps({
                "errorCategory": "validation",
                "isRetryable": False,
                "errorCode": "INVALID_ID_FORMAT",
                "humanMessage": "Customer ID must be C followed by digits (e.g., C001).",
            })
        )
    return {"customer_id": customer_id, "valid": True}


@dev_server.tool
@prod_server.tool
def process_refund(order_id: str, amount: float) -> dict:
    """
    Simulates business rule violation.
    Category: Business — isRetryable=False (explain policy, don't retry)
    """
    if amount > 500:
        raise ToolError(
            json.dumps({
                "errorCategory": "business",
                "isRetryable": False,
                "errorCode": "REFUND_LIMIT_EXCEEDED",
                "humanMessage": f"Refunds over $500 require manager approval.",
                "requestedAmount": amount,
                "limit": 500,
            })
        )
    return {"refund_id": f"REF-{order_id}", "amount": amount, "status": "processed"}


@dev_server.tool
@prod_server.tool
def access_restricted_account(account_id: str) -> dict:
    """
    Simulates permission error.
    Category: Permission — isRetryable=False (escalate immediately)
    """
    if account_id.startswith("RESTRICTED"):
        raise ToolError(
            json.dumps({
                "errorCategory": "permission",
                "isRetryable": False,
                "errorCode": "ACCESS_DENIED",
                "humanMessage": "I don't have access to this account. Escalating to supervisor.",
            })
        )
    return {"account_id": account_id, "balance": 1234.56}


# ── Generic exception (not ToolError) ─────────────────────────────────────
@dev_server.tool
@prod_server.tool
def buggy_tool(x: int) -> str:
    """Tool with a bug — raises a generic (unhandled) exception."""
    result = 1 / x  # ZeroDivisionError when x=0
    return str(result)


# ── Empty result vs error — CRITICAL EXAM DISTINCTION ─────────────────────
@dev_server.tool
@prod_server.tool
def search_customers(query: str) -> dict:
    """
    Returns empty result when query matches nothing — NOT an error.
    Empty result ≠ access failure. Distinguish using querySuccessful=True.
    """
    db = {"alice": {"id": "C001"}, "bob": {"id": "C002"}}
    matches = [v for k, v in db.items() if query.lower() in k]
    return {
        "isError": False,
        "querySuccessful": True,   # ← marks successful query (even with 0 results)
        "results": matches,
        "count": len(matches),
    }


# ── Demo helper ────────────────────────────────────────────────────────────
def show_error(e: Exception) -> None:
    """Print error info in a readable format."""
    raw = str(e)
    try:
        data = json.loads(raw)
        print(f"    category    : {data.get('errorCategory')}")
        print(f"    isRetryable : {data.get('isRetryable')}")
        print(f"    humanMessage: {data.get('humanMessage')}")
    except json.JSONDecodeError:
        print(f"    raw error   : {raw}")


# ── Demo runner ────────────────────────────────────────────────────────────
async def main() -> None:
    sep = "=" * 60
    print(sep)
    print("07 — Error Handling")
    print(sep)

    # ── TVBP error scenarios ────────────────────────────────────────────
    print("\n── TVBP Error Categories ──")

    async with Client(dev_server) as client:

        print("\n  T — Transient (retry makes sense):")
        try:
            await client.call_tool("transient_lookup", {"resource_id": "TIMEOUT"})
        except ToolError as e:
            show_error(e)
        r = await client.call_tool("transient_lookup", {"resource_id": "R123"})
        print(f"  Success case: {r.data}")

        print("\n  V — Validation (fix input, don't retry):")
        try:
            await client.call_tool("validate_customer_id", {"customer_id": "email@example.com"})
        except ToolError as e:
            show_error(e)
        r = await client.call_tool("validate_customer_id", {"customer_id": "C001"})
        print(f"  Valid case: {r.data}")

        print("\n  B — Business (explain policy, don't retry):")
        try:
            await client.call_tool("process_refund", {"order_id": "ORD-100", "amount": 750.0})
        except ToolError as e:
            show_error(e)
        r = await client.call_tool("process_refund", {"order_id": "ORD-200", "amount": 49.99})
        print(f"  Within limit: {r.data}")

        print("\n  P — Permission (escalate immediately):")
        try:
            await client.call_tool("access_restricted_account", {"account_id": "RESTRICTED-001"})
        except ToolError as e:
            show_error(e)
        r = await client.call_tool("access_restricted_account", {"account_id": "ACC-123"})
        print(f"  Accessible: {r.data}")

    # ── Generic exception: dev vs prod behavior ─────────────────────────
    print("\n── Generic Exception: dev (full trace) vs prod (masked) ──")

    async with Client(dev_server) as client:
        try:
            await client.call_tool("buggy_tool", {"x": 0})
        except Exception as e:
            print(f"  dev_server ToolError: {str(e)[:100]}")

    async with Client(prod_server) as client:
        try:
            await client.call_tool("buggy_tool", {"x": 0})
        except Exception as e:
            print(f"  prod_server error  : {str(e)[:100]}")  # masked message

    # ── Empty result vs error ────────────────────────────────────────────
    print("\n── Empty result ≠ Access failure ──")
    async with Client(dev_server) as client:
        r = await client.call_tool("search_customers", {"query": "alice"})
        print(f"  Found match  : {r.data}")

        r = await client.call_tool("search_customers", {"query": "nobody"})
        print(f"  Empty result : {r.data}")
        print(f"  querySuccessful={r.data['querySuccessful']} — query RAN, just no matches")

    print()
    print("KEY TAKEAWAYS:")
    print("  1. ToolError = expected failure (business logic). Raise it intentionally.")
    print("  2. Generic exception = unexpected bug. FastMCP catches it, but details may be masked.")
    print("  3. mask_error_details=True hides tracebacks in production — use it.")
    print("  4. TVBP in ToolError message: category tells the agent HOW to recover:")
    print("     Transient → retry | Validation → fix input | Business → explain | Permission → escalate")
    print("  5. Empty result ≠ error. Use querySuccessful=True to distinguish from access failure.")
    print("  6. Client receives ToolError as a raised Python exception — always try/except.")


if __name__ == "__main__":
    asyncio.run(main())
