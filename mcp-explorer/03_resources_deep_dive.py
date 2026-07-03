"""
03 — Resources Deep Dive
==========================
What this covers:
  - Static resources (fixed URI)
  - URI template resources (RFC 6570 — parameterized paths)
  - Multi-parameter templates
  - JSON resources (returned as string, parsed by client)
  - Binary resources (bytes)
  - Context injection in resources
  - Resources vs Tools — when to use which
  - Anti-pattern: using a tool when a resource is correct

Run: uv run python 03_resources_deep_dive.py
"""

import asyncio
import json
from fastmcp import FastMCP, Client, Context

mcp = FastMCP("resources-demo")


# ── 1. Static resource — fixed URI ────────────────────────────────────────
#
# URI conventions:
#   scheme://path   e.g.  config://app, file://readme, docs://intro
#   No authority (host) needed for internal resources.

@mcp.resource("config://app/settings")
def app_settings() -> str:
    """Application settings as key=value text."""
    return "timeout=30\nmax_retries=3\nlog_level=INFO\nregion=us-east-1"


@mcp.resource("docs://getting-started")
def getting_started_doc() -> str:
    """The getting-started guide."""
    return "# Getting Started\n\n1. Install the package.\n2. Create a client.\n3. Call a tool."


# ── 2. JSON resource — return dict/list, received as JSON string ───────────
@mcp.resource("catalog://products")
def product_catalog() -> str:
    """Full product catalog as JSON."""
    catalog = [
        {"id": "P001", "name": "Widget",  "price": 9.99,  "category": "tools"},
        {"id": "P002", "name": "Gadget",  "price": 24.99, "category": "electronics"},
        {"id": "P003", "name": "Doohickey","price": 4.99, "category": "tools"},
    ]
    return json.dumps(catalog, indent=2)


# ── 3. URI template — one parameter ───────────────────────────────────────
#
# RFC 6570 URI templates: {param} captures a path segment.
# The function parameter name must match the template variable name.

@mcp.resource("users://{user_id}/profile")
def user_profile(user_id: str) -> str:
    """User profile data for a specific user ID."""
    profiles = {
        "alice": {"name": "Alice Smith", "email": "alice@example.com", "tier": "premium"},
        "bob":   {"name": "Bob Jones",   "email": "bob@example.com",   "tier": "standard"},
    }
    data = profiles.get(user_id, {"name": "Unknown", "email": None, "tier": None})
    return json.dumps(data)


# ── 4. URI template — multiple parameters ────────────────────────────────
@mcp.resource("orders://{customer_id}/{year}/summary")
def order_summary(customer_id: str, year: str) -> str:
    """Order summary for a customer in a given year."""
    return json.dumps({
        "customer_id": customer_id,
        "year": year,
        "order_count": 12,
        "total_spent": 1234.56,
        "most_purchased": "Widget",
    })


# ── 5. Binary resource — return bytes ─────────────────────────────────────
#
# When a function returns bytes, FastMCP sets mimeType appropriately.
# The client receives BlobResourceContents instead of TextResourceContents.

@mcp.resource("images://{image_id}/thumbnail")
def image_thumbnail(image_id: str) -> bytes:
    """Return a mock PNG thumbnail (real apps would read from disk)."""
    # Minimal valid 1x1 white PNG
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"          # PNG signature
        b"\x00\x00\x00\rIHDR"         # IHDR chunk header
        b"\x00\x00\x00\x01"           # width = 1
        b"\x00\x00\x00\x01"           # height = 1
        b"\x08\x02"                   # bit depth=8, color type=RGB
        b"\x00\x00\x00"               # compression, filter, interlace
        b"\x90wS\xde"                 # CRC
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return png_bytes


# ── 6. Context injection in resource ──────────────────────────────────────
@mcp.resource("reports://{report_id}")
async def generate_report(report_id: str, ctx: Context) -> str:
    """Generate a report with logging (context available in resources too)."""
    await ctx.info(f"Generating report: {report_id}")
    return json.dumps({
        "report_id": report_id,
        "generated_at": "2026-07-03",
        "rows": 42,
        "status": "complete",
    })


# ── Demo runner ────────────────────────────────────────────────────────────
async def main() -> None:
    sep = "=" * 60
    print(sep)
    print("03 — Resources Deep Dive")
    print(sep)

    async with Client(mcp) as client:
        # Static resources appear in list_resources()
        # Template resources appear in list_resource_templates()
        static = await client.list_resources()
        templates = await client.list_resource_templates()

        print(f"\nStatic resources   ({len(static)}):")
        for r in static:
            print(f"  {str(r.uri)}")

        print(f"\nTemplate resources ({len(templates)}):")
        for t in templates:
            print(f"  {t.uriTemplate}")

        # ── 1. Static text resource ────────────────────────────────────
        print("\n── 1. Static text resource ──")
        content = await client.read_resource("config://app/settings")
        print(f"  app_settings:\n{content[0].text}")

        # ── 2. JSON resource ──────────────────────────────────────────
        print("\n── 2. JSON resource ──")
        content = await client.read_resource("catalog://products")
        catalog = json.loads(content[0].text)
        print(f"  product count : {len(catalog)}")
        print(f"  first product : {catalog[0]}")

        # ── 3. Template resource — one param ──────────────────────────
        print("\n── 3. Template resource — one param ──")
        content = await client.read_resource("users://alice/profile")
        profile = json.loads(content[0].text)
        print(f"  alice profile : {profile}")

        content = await client.read_resource("users://bob/profile")
        print(f"  bob profile   : {json.loads(content[0].text)}")

        # ── 4. Template resource — multiple params ─────────────────────
        print("\n── 4. Template resource — multi-param ──")
        content = await client.read_resource("orders://alice/2026/summary")
        summary = json.loads(content[0].text)
        print(f"  order summary : {summary}")

        # ── 5. Binary resource ────────────────────────────────────────
        print("\n── 5. Binary resource ──")
        content = await client.read_resource("images://logo/thumbnail")
        blob = content[0]
        print(f"  blob type     : {type(blob).__name__}")
        has_data = hasattr(blob, "blob")
        print(f"  has .blob     : {has_data}")
        if has_data:
            print(f"  blob size     : {len(blob.blob)} bytes")

        # ── 6. Context in resource ────────────────────────────────────
        print("\n── 6. Context in resource (logs emitted during read) ──")
        content = await client.read_resource("reports://monthly-q1")
        report = json.loads(content[0].text)
        print(f"  report data   : {report}")

    print()
    print("KEY TAKEAWAYS:")
    print("  1. @mcp.resource('uri://path') = static resource; exact URI required for read.")
    print("  2. @mcp.resource('x://{param}') = template; appears in list_resource_templates().")
    print("  3. Template params MUST match function parameter names exactly.")
    print("  4. Return str for text; return bytes for binary (client gets BlobResourceContents).")
    print("  5. read_resource() always returns a list — use [0].text or [0].blob.")
    print("  6. Resources = read-only data; Tools = actions with side effects.")
    print("  7. Use resources for: configs, docs, catalogs, user data lookups (no writes).")


if __name__ == "__main__":
    asyncio.run(main())
