"""
05 — Context Features
======================
What this covers:
  - Injecting Context into tools AND resources
  - Logging: ctx.info / ctx.debug / ctx.warning / ctx.error
  - Progress reporting: ctx.report_progress(current, total)
  - Reading resources from within a tool: ctx.read_resource()
  - Getting prompts from within a tool: ctx.get_prompt()
  - Request metadata: ctx.request_id, ctx.session_id
  - Client-side: receiving log messages via log_handler callback
    (handler must be ASYNC and takes LoggingMessageNotificationParams)

Run: uv run python 05_context_features.py
"""

import asyncio
import json
from mcp.types import LoggingMessageNotificationParams as LogMessage
from fastmcp import FastMCP, Client, Context

mcp = FastMCP("context-demo")


# ── Data set up for ctx.read_resource() demo ──────────────────────────────
@mcp.resource("catalog://prices")
def prices_resource() -> str:
    """Price catalog accessed by tools via ctx.read_resource."""
    return json.dumps({"widget": 9.99, "gadget": 24.99, "doohickey": 4.99})


@mcp.prompt
def analysis_instructions(focus: str) -> str:
    """Instructions for analysis — accessed by tool via ctx.get_prompt."""
    return f"Analyze the following data with a focus on {focus}. Be concise."


# ── 1. ctx.info / ctx.debug / ctx.warning / ctx.error ─────────────────────
@mcp.tool
async def logging_demo(level: str) -> str:
    """Demonstrate all four log levels."""
    # This will be captured in FastMCP — this is how ctx.info works
    # In practice you'd do this inside the function that needs it
    return f"Would log at level: {level}"


@mcp.tool
async def process_with_logging(data: str, ctx: Context) -> dict:
    """Process data with structured logging at each stage."""
    await ctx.debug(f"Received input: {data!r}")

    if not data.strip():
        await ctx.warning("Empty input received — processing anyway")

    await ctx.info(f"Processing: {data}")
    result = {"original": data, "length": len(data), "upper": data.upper()}

    await ctx.info("Processing complete")
    return result


# ── 2. Progress reporting ──────────────────────────────────────────────────
@mcp.tool
async def multi_step_process(steps: int, ctx: Context) -> list[str]:
    """Simulate a multi-step process with progress updates."""
    await ctx.report_progress(0, steps)
    results = []
    for i in range(1, steps + 1):
        await asyncio.sleep(0)  # simulate work
        result = f"Step {i} of {steps} complete"
        results.append(result)
        await ctx.info(result)
        await ctx.report_progress(i, steps)
    return results


# ── 3. ctx.read_resource() — access server data within a tool ─────────────
#
# This is how tools compose with resources:
# The tool reads current data from the resource at call time
# rather than hard-coding it at server startup.

@mcp.tool
async def calculate_price(product: str, quantity: int, ctx: Context) -> dict:
    """Look up current price from resource and calculate total."""
    await ctx.info(f"Fetching price for: {product}")

    # ctx.read_resource returns ResourceResult (NOT a list!)
    # Access via: result.contents[0].content (different from client.read_resource)
    result = await ctx.read_resource("catalog://prices")
    prices = json.loads(result.contents[0].content)

    if product not in prices:
        await ctx.warning(f"Product {product!r} not in catalog")
        return {"error": f"Product '{product}' not found"}

    unit_price = prices[product]
    total = unit_price * quantity
    await ctx.info(f"Price: {unit_price} × {quantity} = {total}")
    return {"product": product, "unit_price": unit_price, "quantity": quantity, "total": total}


# ── 4. ctx.get_prompt() — access prompt templates from within a tool ───────
@mcp.tool
async def analyze_with_template(topic: str, ctx: Context) -> dict:
    """Get analysis instructions via prompt, then simulate analysis."""
    await ctx.info(f"Fetching analysis template for topic: {topic}")

    # ctx.get_prompt returns GetPromptResult — same as client.get_prompt
    prompt_result = await ctx.get_prompt("analysis_instructions", {"focus": topic})
    instructions = prompt_result.messages[0].content.text

    await ctx.info(f"Template loaded: {instructions[:50]}...")
    return {
        "topic": topic,
        "instructions_loaded": True,
        "instructions_preview": instructions[:100],
        "analysis": f"[Simulated analysis of {topic}]",
    }


# ── 5. ctx.request_id and ctx.session_id — request metadata ───────────────
@mcp.tool
async def echo_request_info(message: str, ctx: Context) -> dict:
    """Echo the message back with request metadata."""
    return {
        "message": message,
        "request_id": ctx.request_id,    # unique per tool call
        "session_id": str(ctx.session_id) if ctx.session_id else None,
    }


# ── Client-side log capture ────────────────────────────────────────────────
#
# log_handler must be ASYNC and accept LoggingMessageNotificationParams.
# message.level = "info" | "debug" | "warning" | "error"
# message.data  = the string passed to ctx.info(...) etc.

captured_logs: list[dict] = []


async def capture_log(message: LogMessage) -> None:
    """Client-side log handler — receives server ctx.info/debug/warning/error.
    message.data is a dict {'msg': '...', 'extra': None} for string logs.
    """
    # message.data can be dict or raw value; extract 'msg' if available
    text = message.data.get("msg", str(message.data)) if isinstance(message.data, dict) else str(message.data)
    captured_logs.append({"level": message.level, "message": text})
    print(f"  [client log] [{message.level}] {text}")


# ── Demo runner ────────────────────────────────────────────────────────────
async def main() -> None:
    sep = "=" * 60
    print(sep)
    print("05 — Context Features")
    print(sep)

    async with Client(mcp, log_handler=capture_log) as client:

        # ── 1. Logging ──────────────────────────────────────────────────
        print("\n── 1. Structured logging (process_with_logging) ──")
        print("  Server logs arrive via client log_handler:")
        r = await client.call_tool("process_with_logging", {"data": "hello world"})
        print(f"  result.data: {r.data}")

        print(f"\n  Total log messages captured: {len(captured_logs)}")
        captured_logs.clear()

        # ── 2. Progress reporting ────────────────────────────────────────
        print("\n── 2. Progress reporting (multi_step_process) ──")
        r = await client.call_tool("multi_step_process", {"steps": 3})
        print(f"  Steps completed: {len(r.data)}")
        for step in r.data:
            print(f"    {step}")
        captured_logs.clear()

        # ── 3. ctx.read_resource() from within a tool ────────────────────
        print("\n── 3. Tool reading resource via ctx.read_resource() ──")
        r = await client.call_tool("calculate_price", {"product": "widget", "quantity": 5})
        print(f"  result: {r.data}")
        captured_logs.clear()

        print("\n  Missing product:")
        r = await client.call_tool("calculate_price", {"product": "gizmo", "quantity": 1})
        print(f"  result: {r.data}")
        captured_logs.clear()

        # ── 4. ctx.get_prompt() from within a tool ───────────────────────
        print("\n── 4. Tool reading prompt via ctx.get_prompt() ──")
        r = await client.call_tool("analyze_with_template", {"topic": "cost reduction"})
        print(f"  result: {r.data}")
        captured_logs.clear()

        # ── 5. Request metadata ──────────────────────────────────────────
        print("\n── 5. Request metadata (request_id) ──")
        r1 = await client.call_tool("echo_request_info", {"message": "first call"})
        r2 = await client.call_tool("echo_request_info", {"message": "second call"})
        print(f"  call 1 request_id: {r1.data['request_id']}")
        print(f"  call 2 request_id: {r2.data['request_id']}")
        print(f"  IDs are different: {r1.data['request_id'] != r2.data['request_id']}")

    print()
    print("KEY TAKEAWAYS:")
    print("  1. Add 'ctx: Context' anywhere in the parameter list to inject context.")
    print("  2. ctx.info/debug/warning/error → messages sent to client's log_handler.")
    print("  3. ctx.report_progress(current, total) → progress notifications to client.")
    print("  4. ctx.read_resource('uri') → ResourceResult; use result.contents[0].content")
    print("     (NOT result[0].text — ctx and client have different return shapes!)")
    print("  5. ctx.get_prompt('name', args) → lets tools retrieve prompt templates.")
    print("  6. ctx.request_id is unique per call; ctx.session_id is per connection.")
    print("  7. Client receives logs via log_handler=callable in Client() constructor.")


if __name__ == "__main__":
    asyncio.run(main())
