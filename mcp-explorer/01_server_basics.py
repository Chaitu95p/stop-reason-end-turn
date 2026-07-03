"""
01 — FastMCP Server Basics
===========================
What this covers:
  - Creating a FastMCP server (constructor parameters)
  - Registering tools, resources, and prompts via decorators
  - Inspecting server capabilities via in-memory Client
  - Transport options (stdio, http, sse) — where they're used

Run: uv run python 01_server_basics.py
"""

import asyncio
from fastmcp import FastMCP, Client

# ── Creating a server ──────────────────────────────────────────────────────
#
# FastMCP(name, instructions, ...)
#   name         : shown to clients in server info
#   instructions : human-readable description for the LLM (system-prompt level)
#   lifespan     : async context manager for startup/shutdown resources
#   on_duplicate_tools : "error" | "warn" | "replace" | "ignore" (default: "warn")
#   mask_error_details : hide tracebacks from clients in production (default: False)
#   strict_input_validation : enforce schema strictly (default: True)

mcp = FastMCP(
    name="demo-server",
    instructions="A learning server demonstrating FastMCP basics.",
)


# ── Registering tools ──────────────────────────────────────────────────────
@mcp.tool
def echo(text: str) -> str:
    """Return the input text unchanged."""
    return text


@mcp.tool(name="add_numbers", description="Add two integers and return the sum.")
def add(x: int, y: int) -> int:
    return x + y


# ── Registering resources ──────────────────────────────────────────────────
@mcp.resource("config://app")
def app_config() -> str:
    """Application configuration as text."""
    return "version=1.0\nenvironment=dev\ndebug=true"


@mcp.resource("data://users/{user_id}")
def user_data(user_id: str) -> str:
    """Look up a user by ID."""
    return f"User record for: {user_id}"


# ── Registering prompts ────────────────────────────────────────────────────
@mcp.prompt
def code_review(language: str) -> str:
    """System prompt for code review in a specific language."""
    return f"You are an expert {language} code reviewer. Be concise and actionable."


# ── Demo ───────────────────────────────────────────────────────────────────
async def demo_server_inspection() -> None:
    print("── Server Inspection via in-memory Client ──")
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print(f"  Registered tools   : {[t.name for t in tools]}")
        print(f"  Tool descriptions  : {[t.description for t in tools]}")

        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        print(f"  Static resources   : {[str(r.uri) for r in resources]}")
        print(f"  Resource templates : {[t.uriTemplate for t in templates]}")

        prompts = await client.list_prompts()
        print(f"  Registered prompts : {[p.name for p in prompts]}")

        await client.ping()
        print("  Server ping        : OK")


async def demo_basic_calls() -> None:
    print("\n── Basic Tool and Resource Calls ──")
    async with Client(mcp) as client:
        result = await client.call_tool("echo", {"text": "hello MCP"})
        print(f"  echo result        : {result.data!r}")

        result = await client.call_tool("add_numbers", {"x": 10, "y": 32})
        print(f"  add_numbers result : {result.data}")

        content = await client.read_resource("config://app")
        print(f"  config resource    : {content[0].text!r}")

        content = await client.read_resource("data://users/alice")
        print(f"  user resource      : {content[0].text!r}")

        prompt = await client.get_prompt("code_review", {"language": "Python"})
        print(f"  code_review prompt : {prompt.messages[0].content.text!r}")


def demo_transport_info() -> None:
    print("\n── Transport Options (informational — not run here) ──")
    options = [
        ("stdio",           "mcp.run(transport='stdio')",      "subprocess via Claude Code / MCP hosts"),
        ("streamable-http", "mcp.run(transport='http')",        "production web deployments"),
        ("sse",             "mcp.run(transport='sse')",          "legacy SSE (deprecated, prefer http)"),
        ("in-memory",       "Client(mcp)",                      "testing, same-process clients"),
    ]
    for transport, code, use_case in options:
        print(f"  {transport:<18} {code:<35} → {use_case}")
    print()
    print("  Typical production pattern:")
    print("    if __name__ == '__main__':")
    print("        mcp.run()  # defaults to 'stdio' for MCP host compatibility")


if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("01 — FastMCP Server Basics")
    print(sep)
    asyncio.run(demo_server_inspection())
    asyncio.run(demo_basic_calls())
    demo_transport_info()
    print()
    print("KEY TAKEAWAYS:")
    print("  1. FastMCP(name, instructions, ...) — name is client-visible;")
    print("     instructions become the server's system-prompt context.")
    print("  2. Decorators register primitives: @mcp.tool / @mcp.resource / @mcp.prompt.")
    print("  3. @mcp.tool(name=..., description=...) overrides defaults.")
    print("  4. Client(mcp) creates an in-memory client — perfect for testing.")
    print("  5. result.data holds the Python return value from call_tool().")
    print("  6. read_resource() returns list[TextResourceContents]; use [0].text.")
