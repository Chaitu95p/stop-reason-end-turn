"""
Smoke test: 1 tool + 1 resource + 1 prompt, verified via in-memory Client.
Purpose: pin down the actual fastmcp API before writing the full tutorial set.
Run: uv run python 00_smoke_test.py
"""

import asyncio
from fastmcp import FastMCP, Client, Context

mcp = FastMCP("smoke-test")


# --- Tool ---
@mcp.tool
def add(x: int, y: int) -> int:
    """Add two integers."""
    return x + y


# --- Resource ---
@mcp.resource("hello://world")
def hello_resource() -> str:
    """A simple static text resource."""
    return "Hello from MCP resource!"


# --- Prompt ---
@mcp.prompt
def greet(name: str) -> str:
    """Generate a greeting prompt."""
    return f"Please greet {name} warmly."


async def main() -> None:
    async with Client(mcp) as client:

        # ── Tools ─────────────────────────────────────────────
        tools = await client.list_tools()
        print(f"Tools found: {[t.name for t in tools]}")

        result = await client.call_tool("add", {"x": 3, "y": 4})
        print(f"call_tool result type : {type(result)}")
        print(f"call_tool result      : {result}")
        # Check what attribute holds the value
        if hasattr(result, "data"):
            print(f"result.data           : {result.data}")
        if hasattr(result, "content"):
            print(f"result.content        : {result.content}")

        # ── Resources ─────────────────────────────────────────
        resources = await client.list_resources()
        print(f"\nResources found: {[str(r.uri) for r in resources]}")

        content = await client.read_resource("hello://world")
        print(f"read_resource type    : {type(content)}")
        print(f"read_resource result  : {content}")

        # ── Prompts ───────────────────────────────────────────
        prompts = await client.list_prompts()
        print(f"\nPrompts found: {[p.name for p in prompts]}")

        prompt_result = await client.get_prompt("greet", {"name": "Alice"})
        print(f"get_prompt type       : {type(prompt_result)}")
        print(f"get_prompt result     : {prompt_result}")

        # ── Ping ──────────────────────────────────────────────
        await client.ping()
        print("\nPing: OK")


if __name__ == "__main__":
    asyncio.run(main())
