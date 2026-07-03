"""
10 — Testing Patterns
======================
What this covers:
  - pytest-asyncio: how to write async tests for FastMCP servers
  - Fixtures: shared Client(mcp) across tests (function, module, session scope)
  - Testing tools: success cases, ToolError, validation errors
  - Testing resources: static URIs, template URIs, binary
  - Testing prompts: single-message and multi-turn
  - Parametrize: table-driven tests for tool inputs
  - Mocking external dependencies inside MCP tools
  - Running pytest programmatically (so this file is also a runnable script)

Run as a script:
  uv run python 10_testing_patterns.py

Run with pytest directly:
  uv run pytest 10_testing_patterns.py -v

Configuration (either in pyproject.toml or pytest.ini):
  [tool.pytest.ini_options]
  asyncio_mode = "auto"    # makes async def test_* work without @pytest.mark.asyncio
"""

import asyncio
import json
import sys
from collections.abc import AsyncIterator
import pytest
import pytest_asyncio
from fastmcp import FastMCP, Client, Context
from fastmcp.exceptions import ToolError
from fastmcp.prompts.base import Message


# ── Server under test ──────────────────────────────────────────────────────
#
# Define the server once at module level.
# Tests import and use it via the shared fixture below.

mcp = FastMCP("test-server", instructions="Demo server for testing patterns.")

PRODUCTS = {
    "P001": {"name": "Widget",  "price": 9.99,  "stock": 150},
    "P002": {"name": "Gadget",  "price": 24.99, "stock": 5},
    "P003": {"name": "Doohick", "price": 4.99,  "stock": 0},
}


@mcp.tool
def get_product(product_id: str) -> dict:
    """Return product info; raises ToolError if not found."""
    if product_id not in PRODUCTS:
        raise ToolError(json.dumps({
            "errorCategory": "validation",
            "isRetryable": False,
            "errorCode": "PRODUCT_NOT_FOUND",
            "humanMessage": f"No product with ID {product_id!r}.",
        }))
    return {"product_id": product_id, **PRODUCTS[product_id]}


@mcp.tool
def calculate_total(product_id: str, quantity: int) -> dict:
    """Calculate order total; raises ToolError for out-of-stock."""
    if product_id not in PRODUCTS:
        raise ToolError("Product not found")
    product = PRODUCTS[product_id]
    if product["stock"] < quantity:
        raise ToolError(json.dumps({
            "errorCategory": "business",
            "isRetryable": False,
            "errorCode": "INSUFFICIENT_STOCK",
            "humanMessage": f"Only {product['stock']} units available.",
            "available": product["stock"],
        }))
    return {
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": product["price"],
        "total": round(product["price"] * quantity, 2),
    }


@mcp.tool
async def slow_lookup(item_id: str, ctx: Context) -> dict:
    """Async tool that logs progress — tests async tool handling."""
    await ctx.info(f"Looking up: {item_id}")
    await ctx.report_progress(0.5, 1.0)
    await ctx.info(f"Found: {item_id}")
    return {"item_id": item_id, "found": True}


@mcp.resource("catalog://products")
def product_catalog() -> str:
    """Full product catalog."""
    return json.dumps(list(PRODUCTS.values()))


@mcp.resource("products://{product_id}/details")
def product_details(product_id: str) -> str:
    """Per-product detail resource (template)."""
    if product_id in PRODUCTS:
        return json.dumps({"product_id": product_id, **PRODUCTS[product_id]})
    return json.dumps({"error": "not found"})


@mcp.resource("products://{product_id}/thumbnail")
def product_thumbnail(product_id: str) -> bytes:
    """Simulated binary thumbnail."""
    return b"PNG" + product_id.encode() + b"\x00" * 16


@mcp.prompt
def order_confirmation(product_name: str, quantity: int, total: float) -> str:
    """Single-message prompt: order confirmation text."""
    return f"Confirm order: {quantity}x {product_name} for ${total:.2f}. Proceed?"


@mcp.prompt
def support_session(customer_name: str) -> list[Message]:
    """Multi-turn prompt: primes a support conversation."""
    return [
        Message(f"Help {customer_name} with their order.", role="user"),
        Message(f"Hi {customer_name}! Happy to help.", role="assistant"),
    ]


# ── Fixtures ───────────────────────────────────────────────────────────────
#
# Function scope (default): opens a new Client per test.
# - Safest: each test is fully isolated.
# - OK for all test sets (read-only or stateful).
#
# Module scope: one Client shared across all tests in the file.
# - Requires asyncio_default_fixture_loop_scope = "module" in pytest config
#   to match the test loop scope; without it, the fixture deadlocks.
# - Only worth it if server startup is expensive (e.g., real network connection).
#
# For FastMCP in-memory transports (Client(mcp)), function scope is fine.

@pytest_asyncio.fixture
async def client() -> AsyncIterator[Client]:
    """Function-scoped Client — new connection per test, fully isolated."""
    async with Client(mcp) as c:
        yield c


# ── Tests: server introspection ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_server_has_expected_tools(client: Client) -> None:
    tools = await client.list_tools()
    tool_names = {t.name for t in tools}
    assert "get_product"     in tool_names
    assert "calculate_total" in tool_names
    assert "slow_lookup"     in tool_names


@pytest.mark.asyncio
async def test_server_has_expected_resources(client: Client) -> None:
    resources = await client.list_resources()
    resource_uris = {str(r.uri) for r in resources}
    assert "catalog://products" in resource_uris

    templates = await client.list_resource_templates()
    template_uris = {t.uriTemplate for t in templates}
    assert "products://{product_id}/details"   in template_uris
    assert "products://{product_id}/thumbnail" in template_uris


@pytest.mark.asyncio
async def test_server_has_expected_prompts(client: Client) -> None:
    prompts = await client.list_prompts()
    prompt_names = {p.name for p in prompts}
    assert "order_confirmation" in prompt_names
    assert "support_session"    in prompt_names


# ── Tests: tools ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_product_success(client: Client) -> None:
    result = await client.call_tool("get_product", {"product_id": "P001"})
    assert result.data["product_id"] == "P001"
    assert result.data["name"]       == "Widget"
    assert result.data["price"]      == 9.99
    assert result.is_error is False


@pytest.mark.asyncio
async def test_get_product_not_found_raises_tool_error(client: Client) -> None:
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool("get_product", {"product_id": "INVALID"})

    # Parse the structured error payload from the ToolError message
    error_data = json.loads(str(exc_info.value))
    assert error_data["errorCategory"]  == "validation"
    assert error_data["isRetryable"]    is False
    assert error_data["errorCode"]      == "PRODUCT_NOT_FOUND"
    assert "INVALID" in error_data["humanMessage"]


@pytest.mark.asyncio
async def test_calculate_total_success(client: Client) -> None:
    result = await client.call_tool("calculate_total", {"product_id": "P001", "quantity": 3})
    assert result.data["total"]     == 29.97
    assert result.data["quantity"]  == 3


@pytest.mark.asyncio
async def test_calculate_total_insufficient_stock_raises(client: Client) -> None:
    with pytest.raises(ToolError) as exc_info:
        # P003 has stock=0
        await client.call_tool("calculate_total", {"product_id": "P003", "quantity": 1})

    error_data = json.loads(str(exc_info.value))
    assert error_data["errorCategory"] == "business"
    assert error_data["available"]     == 0


@pytest.mark.asyncio
async def test_async_tool_with_context(client: Client) -> None:
    result = await client.call_tool("slow_lookup", {"item_id": "X42"})
    assert result.data["found"]   is True
    assert result.data["item_id"] == "X42"


# ── Parametrized test: table-driven inputs ─────────────────────────────────
@pytest.mark.asyncio
@pytest.mark.parametrize("product_id,quantity,expected_total", [
    ("P001", 1,  9.99),
    ("P001", 10, 99.90),
    ("P002", 2,  49.98),
])
async def test_calculate_total_parametrized(
    client: Client,
    product_id: str,
    quantity: int,
    expected_total: float,
) -> None:
    result = await client.call_tool("calculate_total", {"product_id": product_id, "quantity": quantity})
    assert abs(result.data["total"] - expected_total) < 0.01


# ── Tests: resources ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_static_resource(client: Client) -> None:
    content = await client.read_resource("catalog://products")
    # read_resource returns list[TextResourceContents]
    products = json.loads(content[0].text)
    assert isinstance(products, list)
    assert len(products) == 3


@pytest.mark.asyncio
async def test_template_resource_text(client: Client) -> None:
    content = await client.read_resource("products://P002/details")
    details = json.loads(content[0].text)
    assert details["name"]  == "Gadget"
    assert details["price"] == 24.99


@pytest.mark.asyncio
async def test_template_resource_binary(client: Client) -> None:
    from mcp.types import BlobResourceContents
    content = await client.read_resource("products://P001/thumbnail")
    assert isinstance(content[0], BlobResourceContents)
    # BlobResourceContents has .blob attribute (base64-encoded bytes from server)
    assert content[0].blob is not None


# ── Tests: prompts ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_single_message_prompt(client: Client) -> None:
    result = await client.get_prompt("order_confirmation", {
        "product_name": "Widget",
        "quantity": 3,
        "total": 29.97,
    })
    assert len(result.messages) == 1
    text = result.messages[0].content.text
    assert "Widget" in text
    assert "29.97" in text


@pytest.mark.asyncio
async def test_multi_turn_prompt(client: Client) -> None:
    result = await client.get_prompt("support_session", {"customer_name": "Alice"})
    assert len(result.messages)          == 2
    assert result.messages[0].role       == "user"
    assert result.messages[1].role       == "assistant"
    assert "Alice" in result.messages[0].content.text
    assert "Alice" in result.messages[1].content.text


# ── Tests: client lifecycle (function-scoped fixture) ──────────────────────
@pytest.mark.asyncio
async def test_reuse_closed_client_raises() -> None:
    """Demonstrates that a closed client raises on reuse."""
    client_obj = Client(mcp)
    async with client_obj:
        pass  # client is now closed

    with pytest.raises(Exception):
        await client_obj.call_tool("get_product", {"product_id": "P001"})


# ── Tests: ping ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_ping(client: Client) -> None:
    await client.ping()  # raises if server is not alive


# ── Run script mode ────────────────────────────────────────────────────────
#
# When run as `uv run python 10_testing_patterns.py`, invoke pytest
# programmatically so the output matches the other scripts in this directory.

if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("10 — Testing Patterns")
    print(sep)
    print()
    print("Running tests via pytest...")
    print()

    ret = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "--no-header",
        "-q",
    ])

    print()
    print("KEY TAKEAWAYS:")
    print("  1. Use pytest-asyncio with asyncio_mode='auto' for async def test_* functions.")
    print("  2. @pytest_asyncio.fixture(scope='module') shares one Client across all tests.")
    print("  3. ToolError raises on client — use pytest.raises(ToolError) to assert failures.")
    print("  4. Parse JSON from str(exc_info.value) to assert structured error payloads.")
    print("  5. read_resource() returns list[TextResourceContents]; binary → BlobResourceContents.")
    print("  6. @pytest.mark.parametrize: table-driven tests for multiple input/expected combos.")
    print("  7. Keep the server defined at module level; share it across tests via a fixture.")
    print("  8. Function-scope fixtures give isolation; module-scope fixtures give speed.")

    sys.exit(ret)
