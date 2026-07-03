"""
09 — Real-World Patterns
=========================
What this covers:
  - Lifecycle management with lifespan (startup/shutdown shared state)
  - Concurrent tool calls (asyncio.gather)
  - A complete practical server: customer support agent
    * Tools: get_customer, get_orders, process_refund, escalate
    * Resources: policy catalog, product catalog
    * Prompts: support agent setup, escalation message
  - Using the server with an LLM (anthropic API) in a real agentic loop
  - Patterns for async resource initialization

Run: uv run python 09_real_world_patterns.py
Note: ANTHROPIC_API_KEY must be set for the agentic loop demo (demo 3).
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any
from fastmcp import FastMCP, Client, Context
from fastmcp.exceptions import ToolError
from fastmcp.prompts.base import Message


# ── Shared state via lifespan ──────────────────────────────────────────────
#
# lifespan = asynccontextmanager function that runs at server start/stop.
# Yield a dict → FastMCP stores it and makes it accessible via ctx.state
# (Note: state access is transport-specific; for in-memory clients,
#  lifespan state is initialized once per server instance)

class AppState:
    """Shared server state initialized at startup."""
    customer_db: dict[str, dict] = {}
    order_db: dict[str, dict] = {}
    policy: dict[str, Any] = {}


_state = AppState()


@asynccontextmanager
async def lifespan(server: FastMCP):  # type: ignore[type-arg]
    """Initialize shared state at server startup, clean up at shutdown."""
    # STARTUP
    _state.customer_db = {
        "C001": {"name": "Alice Smith",  "email": "alice@example.com", "tier": "premium"},
        "C002": {"name": "Bob Jones",    "email": "bob@example.com",   "tier": "standard"},
        "C003": {"name": "Carol White",  "email": "carol@example.com", "tier": "premium"},
    }
    _state.order_db = {
        "ORD-100": {"customer_id": "C001", "total": 129.99, "status": "delivered", "item": "Widget Pro"},
        "ORD-200": {"customer_id": "C002", "total":  49.00, "status": "processing", "item": "Gadget Lite"},
        "ORD-300": {"customer_id": "C001", "total": 899.00, "status": "delivered",  "item": "Premium Bundle"},
    }
    _state.policy = {
        "max_refund_no_approval": 500.00,
        "premium_sla_hours": 4,
        "standard_sla_hours": 24,
    }
    print("  [server startup] DB and policy loaded")
    yield

    # SHUTDOWN
    _state.customer_db.clear()
    _state.order_db.clear()
    print("  [server shutdown] State cleared")


mcp = FastMCP(
    "support-agent-server",
    instructions=(
        "You are a customer support agent. "
        "Always verify customer identity before processing refunds. "
        "Use escalate_to_supervisor for requests you cannot resolve."
    ),
    lifespan=lifespan,
)


# ── Tools ─────────────────────────────────────────────────────────────────
@mcp.tool(
    name="get_customer",
    description=(
        "Retrieve verified customer record by customer ID. "
        "MUST be called before any refund or account modification. "
        "Do NOT use for order lookups — use get_orders instead."
    ),
)
def get_customer(customer_id: str) -> dict:
    record = _state.customer_db.get(customer_id)
    if not record:
        raise ToolError(json.dumps({
            "errorCategory": "validation",
            "isRetryable": False,
            "errorCode": "CUSTOMER_NOT_FOUND",
            "humanMessage": f"No customer found with ID {customer_id!r}.",
        }))
    return {"customer_id": customer_id, **record}


@mcp.tool(
    name="get_orders",
    description=(
        "Retrieve all orders for a verified customer ID. "
        "Requires prior get_customer call to verify identity."
    ),
)
def get_orders(customer_id: str) -> list[dict]:
    orders = [
        {"order_id": oid, **order}
        for oid, order in _state.order_db.items()
        if order["customer_id"] == customer_id
    ]
    return orders


@mcp.tool(
    name="process_refund",
    description=(
        "Process a refund for a specific order. "
        "Requires prior get_customer and get_orders verification. "
        "Amounts over $500 require supervisor escalation — do NOT attempt directly."
    ),
)
def process_refund(order_id: str, amount: float) -> dict:
    order = _state.order_db.get(order_id)
    if not order:
        raise ToolError(json.dumps({
            "errorCategory": "validation",
            "isRetryable": False,
            "errorCode": "ORDER_NOT_FOUND",
            "humanMessage": f"Order {order_id!r} not found.",
        }))
    limit = _state.policy["max_refund_no_approval"]
    if amount > limit:
        raise ToolError(json.dumps({
            "errorCategory": "business",
            "isRetryable": False,
            "errorCode": "REFUND_LIMIT_EXCEEDED",
            "humanMessage": f"Refunds over ${limit:.0f} require manager approval. I'll escalate this.",
            "requestedAmount": amount,
            "policyLimit": limit,
        }))
    return {
        "refund_id": f"REF-{order_id}",
        "amount": amount,
        "status": "approved",
        "message": f"Refund of ${amount:.2f} processed for order {order_id}.",
    }


@mcp.tool(
    name="escalate_to_supervisor",
    description=(
        "Escalate a case to a human supervisor. "
        "Use when: amount exceeds policy limit, customer requests human, "
        "or issue cannot be resolved within agent authority."
    ),
)
async def escalate_to_supervisor(reason: str, context: str, ctx: Context) -> dict:
    await ctx.info(f"Escalating: {reason}")
    return {
        "ticket_id": "ESC-001",
        "status": "escalated",
        "message": f"Case escalated to supervisor. Ticket: ESC-001. Reason: {reason}",
    }


# ── Resources ──────────────────────────────────────────────────────────────
@mcp.resource("policy://refund")
def refund_policy() -> str:
    """Current refund policy document."""
    return json.dumps({
        "max_no_approval": _state.policy.get("max_refund_no_approval", 500),
        "approval_required_above": 500,
        "no_receipt_limit": 50,
        "days_to_claim": 30,
    })


@mcp.resource("knowledge://sla")
def sla_knowledge() -> str:
    """Service level agreement details by tier."""
    return json.dumps({
        "premium":  {"response_hours": 4,  "priority": "high"},
        "standard": {"response_hours": 24, "priority": "normal"},
    })


# ── Prompts ────────────────────────────────────────────────────────────────
@mcp.prompt
def support_session(customer_name: str, tier: str) -> list[Message]:
    """Prime the support session with customer context."""
    sla = 4 if tier == "premium" else 24
    return [
        Message(
            f"You are helping {customer_name} ({tier} tier, {sla}h SLA). "
            f"Be professional, empathetic, and resolve issues within policy limits.",
            role="user",
        ),
        Message(
            f"Hello {customer_name}! I'm here to help. What can I assist you with today?",
            role="assistant",
        ),
    ]


@mcp.prompt
def escalation_message(ticket_id: str, reason: str) -> str:
    """Draft escalation notification message."""
    return (
        f"I'm transferring your case (ticket {ticket_id}) to our supervisor team "
        f"because {reason}. You'll receive a response within 2 hours. "
        f"Is there anything else I can note before I transfer?"
    )


# ── Demo 1: server inspection ──────────────────────────────────────────────
async def demo_inspection() -> None:
    print("\n── Demo 1: Server capabilities ──")
    async with Client(mcp) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()
        print(f"  Tools    : {[t.name for t in tools]}")
        print(f"  Resources: {[str(r.uri) for r in resources]}")
        print(f"  Prompts  : {[p.name for p in prompts]}")


# ── Demo 2: tool workflow (get customer → get orders → refund) ─────────────
async def demo_workflow() -> None:
    print("\n── Demo 2: Support workflow (verify → lookup → refund) ──")
    async with Client(mcp) as client:
        # Step 1: Verify customer
        r = await client.call_tool("get_customer", {"customer_id": "C001"})
        customer = r.data
        print(f"  1. Customer verified: {customer['name']} ({customer['tier']})")

        # Step 2: Get orders
        r = await client.call_tool("get_orders", {"customer_id": "C001"})
        orders = r.data
        print(f"  2. Orders found: {[o['order_id'] for o in orders]}")

        # Step 3: Process refund
        r = await client.call_tool("process_refund", {"order_id": "ORD-100", "amount": 129.99})
        print(f"  3. Refund: {r.data}")

        # Step 4: Business error → escalate
        print("\n  4. Refund over limit → escalate:")
        try:
            await client.call_tool("process_refund", {"order_id": "ORD-300", "amount": 899.00})
        except ToolError as e:
            err = json.loads(str(e))
            print(f"     BusinessError: {err['humanMessage']}")
        r = await client.call_tool("escalate_to_supervisor", {
            "reason": "refund over $500 policy limit",
            "context": "ORD-300, $899 refund requested by C001",
        })
        print(f"     Escalation: {r.data}")


# ── Demo 3: concurrent calls ────────────────────────────────────────────────
async def demo_concurrent() -> None:
    print("\n── Demo 3: Concurrent tool calls (asyncio.gather) ──")
    async with Client(mcp) as client:
        # Fetch data for multiple customers simultaneously
        results = await asyncio.gather(
            client.call_tool("get_customer", {"customer_id": "C001"}),
            client.call_tool("get_customer", {"customer_id": "C002"}),
            client.call_tool("get_customer", {"customer_id": "C003"}),
        )
        print(f"  Fetched {len(results)} customers concurrently:")
        for r in results:
            c = r.data
            print(f"    {c['customer_id']}: {c['name']} ({c['tier']})")


# ── Demo 4: agentic loop with Anthropic SDK ────────────────────────────────
async def demo_agentic_loop() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n── Demo 4: Agentic loop (SKIPPED — ANTHROPIC_API_KEY not set) ──")
        return

    print("\n── Demo 4: Real agentic loop with Anthropic SDK ──")
    import anthropic

    anthropic_client = anthropic.Anthropic(api_key=api_key)

    async with Client(mcp) as mcp_client:
        tools_list = await mcp_client.list_tools()

        # Convert fastmcp tool objects to Anthropic API tool format
        tools_for_anthropic = [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema,
            }
            for t in tools_list
        ]

        messages = [{"role": "user", "content":
            "Customer C001 is requesting a full refund of $129.99 on order ORD-100."}]

        print("  Request: Customer C001 wants refund on ORD-100 ($129.99)")
        print()

        iteration = 0
        while True:
            iteration += 1
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                tools=tools_for_anthropic,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                final_text = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                print(f"  Final response: {final_text}")
                break

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"  [iter {iteration}] → {block.name}({json.dumps(block.input)[:60]})")
                        try:
                            result = await mcp_client.call_tool(block.name, block.input)
                            content = json.dumps(result.data)
                        except ToolError as e:
                            content = str(e)
                        print(f"             ← {content[:80]}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": content,
                        })
                messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("09 — Real-World Patterns")
    print(sep)
    asyncio.run(demo_inspection())
    asyncio.run(demo_workflow())
    asyncio.run(demo_concurrent())
    asyncio.run(demo_agentic_loop())

    print()
    print("KEY TAKEAWAYS:")
    print("  1. lifespan=asynccontextmanager loads shared state at startup (DB connections, config).")
    print("  2. Tool descriptions are critical for LLM disambiguation — be explicit about scope.")
    print("  3. asyncio.gather() runs multiple tool calls concurrently — use for independent lookups.")
    print("  4. In an agentic loop: convert FastMCP tools to Anthropic format, then loop on stop_reason.")
    print("  5. Always handle ToolError from mcp_client.call_tool() — pass error back as tool_result.")
    print("  6. Resources hold configuration read by tools via ctx.read_resource() at call time.")
