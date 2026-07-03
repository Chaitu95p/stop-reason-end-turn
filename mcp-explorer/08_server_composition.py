"""
08 — Server Composition
========================
What this covers:
  - Mounting one FastMCP server into another (namespacing)
  - Importing tools/resources/prompts from a sub-server
  - Prefix namespacing to avoid name collisions
  - Building a gateway server from multiple domain servers
  - Inspecting the composed server's full capability set

Run: uv run python 08_server_composition.py
"""

import asyncio
import json
from fastmcp import FastMCP, Client

# ── Domain servers — each focused on one area ──────────────────────────────

inventory_server = FastMCP("inventory-service")

@inventory_server.tool
def get_stock(product_id: str) -> dict:
    """Get current stock level for a product."""
    stock = {"P001": 150, "P002": 23, "P003": 0}
    return {"product_id": product_id, "stock": stock.get(product_id, -1)}

@inventory_server.tool
def reserve_stock(product_id: str, quantity: int) -> dict:
    """Reserve stock for an order (simulated)."""
    return {"reserved": True, "product_id": product_id, "quantity": quantity}

@inventory_server.resource("inventory://summary")
def inventory_summary() -> str:
    return json.dumps({"total_products": 3, "low_stock_items": ["P002", "P003"]})


# ── Second domain server ────────────────────────────────────────────────────
orders_server = FastMCP("orders-service")

@orders_server.tool
def create_order(customer_id: str, product_id: str, quantity: int) -> dict:
    """Create a new order."""
    import random
    order_id = f"ORD-{random.randint(1000, 9999)}"
    return {"order_id": order_id, "customer_id": customer_id,
            "product_id": product_id, "quantity": quantity, "status": "pending"}

@orders_server.tool
def get_order(order_id: str) -> dict:
    """Retrieve an order by ID."""
    return {"order_id": order_id, "status": "shipped", "eta": "2026-07-05"}

@orders_server.resource("orders://recent")
def recent_orders() -> str:
    return json.dumps({"orders": ["ORD-1234", "ORD-5678"], "count": 2})

@orders_server.prompt
def order_confirmation(order_id: str, customer_name: str) -> str:
    """Confirmation message prompt for a placed order."""
    return f"Please generate a friendly confirmation email for order {order_id} for customer {customer_name}."


# ── Third domain server ─────────────────────────────────────────────────────
analytics_server = FastMCP("analytics-service")

@analytics_server.tool
def get_sales_report(period: str) -> dict:
    """Generate a sales report for a given period."""
    return {"period": period, "total_sales": 45678.90, "units_sold": 342, "top_product": "P001"}

@analytics_server.resource("analytics://kpis")
def kpis() -> str:
    return json.dumps({"revenue_mtd": 45678.90, "orders_mtd": 342, "avg_order_value": 133.56})


# ── Gateway server — composes all domain servers ───────────────────────────
#
# mount(server, prefix="prefix") registers all tools/resources/prompts
# from sub-server with the given prefix.
# Tools become: "prefix_toolname"
# Resources become: "prefix+original_uri"
# Prompts become: "prefix_promptname"

gateway = FastMCP("gateway", instructions="Unified API gateway for inventory, orders, and analytics.")

gateway.mount(inventory_server, prefix="inventory")
gateway.mount(orders_server,    prefix="orders")
gateway.mount(analytics_server, prefix="analytics")


# ── Demo runner ────────────────────────────────────────────────────────────
async def main() -> None:
    sep = "=" * 60
    print(sep)
    print("08 — Server Composition")
    print(sep)

    # ── Inspect individual servers ────────────────────────────────────────
    print("\n── Individual server capabilities ──")
    for name, server in [
        ("inventory", inventory_server),
        ("orders",    orders_server),
        ("analytics", analytics_server),
    ]:
        async with Client(server) as c:
            tools = await c.list_tools()
            resources = await c.list_resources()
            prompts = await c.list_prompts()
            print(f"  {name:12}: {len(tools)} tools, {len(resources)} resources, {len(prompts)} prompts")
            print(f"    tools: {[t.name for t in tools]}")

    # ── Inspect gateway (composed server) ────────────────────────────────
    print("\n── Gateway (composed) capabilities ──")
    async with Client(gateway) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        prompts = await client.list_prompts()

        print(f"  total tools    : {len(tools)}")
        print(f"  tool names     : {[t.name for t in tools]}")
        print(f"  total resources: {len(resources)}")
        print(f"  resource uris  : {[str(r.uri) for r in resources]}")
        print(f"  total prompts  : {len(prompts)}")
        print(f"  prompt names   : {[p.name for p in prompts]}")

    # ── Use tools through the gateway ────────────────────────────────────
    print("\n── Calling tools through the gateway ──")
    async with Client(gateway) as client:

        # Inventory tools
        r = await client.call_tool("inventory_get_stock", {"product_id": "P001"})
        print(f"  inventory_get_stock: {r.data}")

        r = await client.call_tool("inventory_reserve_stock", {
            "product_id": "P001", "quantity": 5
        })
        print(f"  inventory_reserve_stock: {r.data}")

        # Orders tools
        r = await client.call_tool("orders_create_order", {
            "customer_id": "C001", "product_id": "P001", "quantity": 2
        })
        print(f"  orders_create_order: {r.data}")

        order_id = r.data["order_id"]
        r = await client.call_tool("orders_get_order", {"order_id": order_id})
        print(f"  orders_get_order: {r.data}")

        # Analytics tool
        r = await client.call_tool("analytics_get_sales_report", {"period": "July 2026"})
        print(f"  analytics_get_sales_report: {r.data}")

    # ── Use resources through the gateway ─────────────────────────────────
    print("\n── Reading resources through the gateway ──")
    async with Client(gateway) as client:
        resources = await client.list_resources()
        for res in resources:
            content = await client.read_resource(str(res.uri))
            data = json.loads(content[0].text)
            print(f"  {str(res.uri)}: {data}")

    # ── Prompts through the gateway ────────────────────────────────────────
    print("\n── Getting prompt through the gateway ──")
    async with Client(gateway) as client:
        result = await client.get_prompt("orders_order_confirmation", {
            "order_id": "ORD-1234", "customer_name": "Alice Smith"
        })
        print(f"  prompt: {result.messages[0].content.text!r}")

    print()
    print("KEY TAKEAWAYS:")
    print("  1. gateway.mount(server, prefix='name') composes multiple servers into one.")
    print("  2. Tools are prefixed: 'inventory_get_stock', 'orders_create_order', etc.")
    print("  3. Resources are prefixed in URI: 'inventory+inventory://summary'.")
    print("  4. Gateway exposes all sub-server tools/resources/prompts via one Client connection.")
    print("  5. Ideal pattern: domain-specific servers + one gateway for clients.")
    print("  6. No-prefix mount is also valid: gateway.mount(server) — uses tool names as-is.")


if __name__ == "__main__":
    asyncio.run(main())
