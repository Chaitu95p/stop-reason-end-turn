"""
02 — Tools Deep Dive
=====================
What this covers:
  - Sync tools (simple return types: str, int, float, dict, list)
  - Async tools
  - Typed parameters with Annotated + Field for descriptions
  - Pydantic model parameters (auto-validated)
  - Named/described tools via @mcp.tool(name=..., description=...)
  - Context injection (ctx: Context) for logging and progress
  - ToolAnnotations: readOnlyHint, destructiveHint, idempotentHint
  - ToolError for controlled failure signaling
  - Anti-patterns: what NOT to do

Run: uv run python 02_tools_deep_dive.py
"""

import asyncio
from typing import Annotated
from pydantic import BaseModel, Field
from fastmcp import FastMCP, Client, Context
from fastmcp.exceptions import ToolError

mcp = FastMCP("tools-demo")


# ── 1. Sync tool — simplest form ──────────────────────────────────────────
@mcp.tool
def greet(name: str) -> str:
    """Generate a greeting message."""
    return f"Hello, {name}!"


# ── 2. Async tool — natively supported ────────────────────────────────────
@mcp.tool
async def fetch_joke(category: str) -> str:
    """Simulate fetching a joke (async I/O friendly)."""
    await asyncio.sleep(0)  # simulate async work
    jokes = {
        "programming": "Why do programmers prefer dark mode? Light attracts bugs.",
        "math":        "Why was the math book sad? It had too many problems.",
    }
    return jokes.get(category, "Why don't scientists trust atoms? They make up everything.")


# ── 3. Multiple return types ───────────────────────────────────────────────
@mcp.tool
def get_stats(values: list[float]) -> dict:
    """Compute basic statistics for a list of numbers."""
    if not values:
        return {"count": 0, "sum": 0, "mean": None, "min": None, "max": None}
    return {
        "count": len(values),
        "sum": sum(values),
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }


# ── 4. Annotated parameters — rich descriptions for the LLM ───────────────
@mcp.tool
def convert_temperature(
    value: Annotated[float, Field(description="Temperature value to convert")],
    from_unit: Annotated[str, Field(description="Source unit: 'celsius', 'fahrenheit', or 'kelvin'")],
    to_unit: Annotated[str, Field(description="Target unit: 'celsius', 'fahrenheit', or 'kelvin'")],
) -> float:
    """Convert a temperature between Celsius, Fahrenheit, and Kelvin."""
    # Normalize to Celsius first
    if from_unit == "fahrenheit":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "kelvin":
        celsius = value - 273.15
    else:
        celsius = value

    if to_unit == "fahrenheit":
        return celsius * 9 / 5 + 32
    elif to_unit == "kelvin":
        return celsius + 273.15
    return celsius


# ── 5. Pydantic model parameter — auto-validated ───────────────────────────
class OrderItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, description="Quantity must be at least 1")
    unit_price: float = Field(gt=0, description="Price per unit in USD")


@mcp.tool
def calculate_order_total(item: OrderItem, discount_pct: float = 0.0) -> dict:
    """Calculate the total cost for an order item with optional discount."""
    subtotal = item.quantity * item.unit_price
    discount = subtotal * (discount_pct / 100)
    return {
        "product_id": item.product_id,
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "total": round(subtotal - discount, 2),
    }


# ── 6. Named and described tool ────────────────────────────────────────────
@mcp.tool(
    name="search_database",
    description=(
        "Search the customer database by query string. "
        "Use this for broad searches. "
        "Use get_customer_by_id for direct ID lookup."  # disambiguates from a sibling tool
    ),
)
def db_search(query: str, limit: int = 10) -> list[dict]:
    """Internal: search customer DB."""
    mock_results = [
        {"id": "C001", "name": "Alice Smith"},
        {"id": "C002", "name": "Bob Jones"},
    ]
    return [r for r in mock_results if query.lower() in r["name"].lower()][:limit]


# ── 7. Context injection — logging and progress ────────────────────────────
@mcp.tool
async def process_batch(items: list[str], ctx: Context) -> dict:
    """Process a list of items with progress reporting."""
    await ctx.info(f"Starting batch of {len(items)} items")
    results = []
    for i, item in enumerate(items):
        await ctx.report_progress(i, len(items))
        await ctx.debug(f"Processing item: {item}")
        results.append(item.upper())
    await ctx.report_progress(len(items), len(items))
    await ctx.info("Batch complete")
    return {"processed": len(results), "results": results}


# ── 8. ToolAnnotations — hint tool behavior to the host ───────────────────
@mcp.tool(
    annotations={
        "readOnlyHint":   True,   # does not modify state
        "idempotentHint": True,   # safe to call multiple times
    }
)
def lookup_product(product_id: str) -> dict:
    """Read-only product lookup — safe to call multiple times."""
    catalog = {
        "P001": {"name": "Widget", "price": 9.99},
        "P002": {"name": "Gadget", "price": 24.99},
    }
    return catalog.get(product_id, {"error": "Product not found"})


@mcp.tool(
    annotations={
        "destructiveHint": True,   # modifies state, cannot be undone
        "idempotentHint":  False,
    }
)
def delete_record(record_id: str) -> dict:
    """DESTRUCTIVE: deletes a record permanently."""
    return {"deleted": record_id, "status": "ok"}


# ── 9. ToolError — controlled failure ─────────────────────────────────────
#
# ToolError: the tool failed for a known, expected reason.
#   The client receives ToolError (raises on client side — use try/except).
#   Use for: invalid input, business rule violations, not-found cases.
#
# Generic Exception: unexpected internal error.
#   FastMCP catches it and returns an error result too,
#   but message may be masked if mask_error_details=True.

@mcp.tool
def divide(a: float, b: float) -> float:
    """Divide a by b. Raises ToolError if b is zero."""
    if b == 0:
        raise ToolError("Division by zero: b must be non-zero.")
    return a / b


@mcp.tool
def get_user(user_id: str) -> dict:
    """Retrieve a user by ID. Raises ToolError if not found."""
    users = {"U001": {"name": "Alice"}, "U002": {"name": "Bob"}}
    if user_id not in users:
        raise ToolError(f"User '{user_id}' not found.")
    return users[user_id]


# ── Demo runner ────────────────────────────────────────────────────────────
async def main() -> None:
    sep = "=" * 60
    print(sep)
    print("02 — Tools Deep Dive")
    print(sep)

    async with Client(mcp) as client:
        tools = await client.list_tools()
        print(f"\nRegistered tools ({len(tools)} total):")
        for t in tools:
            print(f"  {t.name:<25} — {(t.description or '')[:55]}")

        # 1. Simple string tool
        print("\n── 1. Simple sync tool ──")
        r = await client.call_tool("greet", {"name": "World"})
        print(f"  greet → {r.data!r}")

        # 2. Async tool
        print("\n── 2. Async tool ──")
        r = await client.call_tool("fetch_joke", {"category": "programming"})
        print(f"  fetch_joke → {r.data!r}")

        # 3. Dict return
        print("\n── 3. Dict return (stats) ──")
        r = await client.call_tool("get_stats", {"values": [1.0, 2.5, 3.0, 4.5, 5.0]})
        print(f"  get_stats → {r.data}")

        # 4. Annotated parameters
        print("\n── 4. Annotated parameters (temperature) ──")
        r = await client.call_tool("convert_temperature", {
            "value": 100.0, "from_unit": "celsius", "to_unit": "fahrenheit"
        })
        print(f"  100°C in Fahrenheit → {r.data}")

        # 5. Pydantic model parameter
        print("\n── 5. Pydantic model parameter ──")
        r = await client.call_tool("calculate_order_total", {
            "item": {"product_id": "P001", "quantity": 3, "unit_price": 9.99},
            "discount_pct": 10.0,
        })
        print(f"  order total → {r.data}")

        # 6. Named tool
        print("\n── 6. Named tool (search_database) ──")
        r = await client.call_tool("search_database", {"query": "alice"})
        print(f"  search_database → {r.data}")

        # 7. Context injection (progress logged to stderr)
        print("\n── 7. Context injection (process_batch) ──")
        r = await client.call_tool("process_batch", {
            "items": ["apple", "banana", "cherry"]
        })
        print(f"  process_batch → {r.data}")

        # 8. Tool annotations
        print("\n── 8. ToolAnnotations ──")
        r = await client.call_tool("lookup_product", {"product_id": "P001"})
        print(f"  lookup_product (readOnly) → {r.data}")

        # 9. ToolError — raises on client
        print("\n── 9. ToolError ──")
        try:
            await client.call_tool("divide", {"a": 10.0, "b": 0.0})
        except ToolError as e:
            print(f"  divide by zero → ToolError: {e}")

        r = await client.call_tool("divide", {"a": 10.0, "b": 4.0})
        print(f"  10 / 4 → {r.data}")

        try:
            await client.call_tool("get_user", {"user_id": "NOTEXIST"})
        except ToolError as e:
            print(f"  get_user missing → ToolError: {e}")

    print()
    print("KEY TAKEAWAYS:")
    print("  1. @mcp.tool (no parens) = simplest registration; docstring = description.")
    print("  2. @mcp.tool(name=..., description=...) = explicit override — use for disambiguation.")
    print("  3. Annotated[type, Field(description=...)] enriches LLM tool-selection accuracy.")
    print("  4. Pydantic models as parameters are auto-validated before the function runs.")
    print("  5. result.data holds the Python return value (str, int, dict, list, etc.).")
    print("  6. ToolError on server → ToolError raised on client → wrap in try/except.")
    print("  7. ctx: Context enables logging (ctx.info/debug) and progress (ctx.report_progress).")
    print("  8. ToolAnnotations are HINTS to the host — not enforcement.")


if __name__ == "__main__":
    asyncio.run(main())
