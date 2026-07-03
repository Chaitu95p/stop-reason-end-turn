"""
06 — Client Basics
===================
What this covers:
  - In-memory client (Client(mcp)) — for testing and same-process use
  - All client operations: list_tools, call_tool, list_resources,
    read_resource, list_resource_templates, list_prompts, get_prompt, ping
  - Handling structured vs text results
  - Client callbacks: log_handler, progress_handler
  - Error handling on the client side
  - Anti-patterns: reusing a closed client, blocking calls outside async

Run: uv run python 06_client_basics.py
"""

import asyncio
import json
from mcp.types import LoggingMessageNotificationParams as LogMessage
from fastmcp import FastMCP, Client, Context
from fastmcp.exceptions import ToolError
from fastmcp.prompts.base import Message

# ── Build a demo server ────────────────────────────────────────────────────
mcp = FastMCP("client-demo-server", instructions="Demo server for client API examples.")


@mcp.tool
def add(x: int, y: int) -> int:
    """Add two integers."""
    return x + y


@mcp.tool
def upper(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()


@mcp.tool
async def slow_task(name: str, ctx: Context) -> str:
    """Simulate a multi-step slow task (produces logs)."""
    await ctx.info(f"Starting: {name}")
    await ctx.report_progress(0, 3)
    await asyncio.sleep(0)
    await ctx.report_progress(1, 3)
    await asyncio.sleep(0)
    await ctx.report_progress(2, 3)
    await asyncio.sleep(0)
    await ctx.report_progress(3, 3)
    await ctx.info(f"Done: {name}")
    return f"Completed: {name}"


@mcp.tool
def fail_always(reason: str) -> str:
    """Always raises ToolError — demonstrates error handling."""
    raise ToolError(f"Intentional failure: {reason}")


@mcp.resource("info://server-stats")
def server_stats() -> str:
    """Server statistics (static resource)."""
    return json.dumps({"uptime_seconds": 12345, "requests_handled": 42, "version": "1.0.0"})


@mcp.resource("data://{collection}/{item_id}")
def get_item(collection: str, item_id: str) -> str:
    """Look up an item in a named collection."""
    return json.dumps({"collection": collection, "item_id": item_id, "data": f"content of {item_id}"})


@mcp.prompt
def analyze(subject: str, depth: str = "brief") -> str:
    """Prompt to analyze a subject."""
    return f"Provide a {depth} analysis of: {subject}"


@mcp.prompt
def compare(item_a: str, item_b: str) -> list[Message]:
    """Set up a comparison discussion."""
    return [
        Message(f"Compare {item_a} and {item_b} across three dimensions.", role="user"),
        Message(f"I'll compare {item_a} and {item_b} for you.", role="assistant"),
    ]


# ── Demo: all client operations ────────────────────────────────────────────
async def demo_list_operations() -> None:
    print("\n── list_tools / list_resources / list_resource_templates / list_prompts ──")
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print(f"  tools     : {[t.name for t in tools]}")

        resources = await client.list_resources()
        print(f"  resources : {[str(r.uri) for r in resources]}")

        templates = await client.list_resource_templates()
        print(f"  templates : {[t.uriTemplate for t in templates]}")

        prompts = await client.list_prompts()
        print(f"  prompts   : {[p.name for p in prompts]}")


async def demo_call_tool() -> None:
    print("\n── call_tool — return types ──")
    async with Client(mcp) as client:
        # Integer result
        r = await client.call_tool("add", {"x": 7, "y": 8})
        print(f"  add(7, 8)           → data={r.data!r}  type={type(r.data).__name__}")

        # String result
        r = await client.call_tool("upper", {"text": "hello mcp"})
        print(f"  upper('hello mcp')  → data={r.data!r}  type={type(r.data).__name__}")

        # Access via content (alternative to .data)
        print(f"  content[0].text     → {r.content[0].text!r}")
        print(f"  is_error            → {r.is_error}")


async def demo_read_resource() -> None:
    print("\n── read_resource — static and template ──")
    async with Client(mcp) as client:
        # Static resource
        content = await client.read_resource("info://server-stats")
        stats = json.loads(content[0].text)
        print(f"  server_stats : {stats}")

        # Template resource
        content = await client.read_resource("data://users/U001")
        item = json.loads(content[0].text)
        print(f"  template item: {item}")


async def demo_get_prompt() -> None:
    print("\n── get_prompt — single and multi-turn ──")
    async with Client(mcp) as client:
        # Single message
        result = await client.get_prompt("analyze", {"subject": "FastMCP", "depth": "detailed"})
        print(f"  analyze messages: {len(result.messages)}")
        print(f"  text: {result.messages[0].content.text!r}")

        # Multi-message
        result = await client.get_prompt("compare", {"item_a": "REST", "item_b": "GraphQL"})
        print(f"\n  compare messages: {len(result.messages)}")
        for msg in result.messages:
            print(f"    [{msg.role}] {msg.content.text!r}")


async def demo_callbacks() -> None:
    print("\n── Callbacks: log_handler and progress_handler ──")
    logs: list[str] = []
    progress: list[tuple] = []

    # log_handler must be ASYNC — takes LoggingMessageNotificationParams
    # message.data is a dict {'msg': '...', 'extra': None} for string logs
    async def on_log(message: LogMessage) -> None:
        text = message.data.get("msg", str(message.data)) if isinstance(message.data, dict) else str(message.data)
        logs.append(f"[{message.level}] {text}")
        print(f"    LOG: [{message.level}] {text}")

    # progress_handler must also be ASYNC — (progress, total, message)
    async def on_progress(progress_val: float, total: float | None, msg: str | None) -> None:
        progress.append((progress_val, total))
        print(f"    PROGRESS: {progress_val}/{total}")

    async with Client(mcp, log_handler=on_log, progress_handler=on_progress) as client:  # type: ignore[arg-type]
        r = await client.call_tool("slow_task", {"name": "demo-task"})
        print(f"  result: {r.data!r}")
        print(f"  logs captured   : {len(logs)}")
        print(f"  progress events : {len(progress)}")


async def demo_error_handling() -> None:
    print("\n── Error handling ──")
    async with Client(mcp) as client:
        # ToolError from server → ToolError raised on client
        try:
            await client.call_tool("fail_always", {"reason": "testing errors"})
        except ToolError as e:
            print(f"  ToolError caught: {e}")

        # Invalid arguments → validation error (different exception)
        try:
            await client.call_tool("add", {"x": "not-a-number", "y": 5})
        except Exception as e:
            print(f"  Validation error type: {type(e).__name__}")
            print(f"  Validation error     : {str(e)[:80]}")

        # Non-existent tool
        try:
            await client.call_tool("nonexistent_tool", {})
        except Exception as e:
            print(f"  Missing tool error: {type(e).__name__}: {str(e)[:60]}")


async def demo_ping() -> None:
    print("\n── ping ──")
    async with Client(mcp) as client:
        await client.ping()
        print("  ping: OK (server is alive)")


async def demo_antipatterns() -> None:
    print("\n── Anti-patterns ──")
    print("  WRONG 1: Using a closed client")
    client = Client(mcp)
    async with client:
        pass  # client is now closed

    try:
        await client.call_tool("add", {"x": 1, "y": 2})
    except Exception as e:
        print(f"    Caught (expected): {type(e).__name__}")

    print("  WRONG 2: Creating a new Client per call — use one client for a session")
    print("    # BAD: creates/tears down transport for each call")
    print("    for item in items:")
    print("        async with Client(mcp) as c: await c.call_tool(...)")
    print("    # GOOD: one client, many calls")
    print("    async with Client(mcp) as c:")
    print("        for item in items: await c.call_tool(...)")


if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("06 — Client Basics")
    print(sep)
    asyncio.run(demo_list_operations())
    asyncio.run(demo_call_tool())
    asyncio.run(demo_read_resource())
    asyncio.run(demo_get_prompt())
    asyncio.run(demo_callbacks())
    asyncio.run(demo_error_handling())
    asyncio.run(demo_ping())
    asyncio.run(demo_antipatterns())

    print()
    print("KEY TAKEAWAYS:")
    print("  1. Client(mcp) = in-memory (testing); Client('http://...') = HTTP; STDIO = subprocess.")
    print("  2. Always use 'async with Client(...) as client:' — manages connection lifecycle.")
    print("  3. result.data = Python value; result.content[0].text = string form; result.is_error = bool.")
    print("  4. read_resource() returns list[TextResourceContents]; use content[0].text.")
    print("  5. ToolError on server → ToolError raised on client — wrap calls in try/except.")
    print("  6. Use log_handler= and progress_handler= callbacks for observability.")
    print("  7. Reuse one Client per session — don't create a new one per call.")
