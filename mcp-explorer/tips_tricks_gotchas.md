# MCP Python SDK (FastMCP) — Tips, Tricks & Gotchas

> Based on actual running code in this directory. Every gotcha below was hit during development.

---

## Quick API Cheat Sheet

```python
from fastmcp import FastMCP, Client, Context
from fastmcp.exceptions import ToolError
from fastmcp.prompts.base import Message
from mcp.types import LoggingMessageNotificationParams as LogMessage

mcp = FastMCP("my-server", instructions="...", lifespan=my_lifespan)

@mcp.tool                                       # simplest form
@mcp.tool(name="...", description="...")        # explicit override
@mcp.resource("scheme://path")                 # static resource
@mcp.resource("scheme://{param}/data")         # template resource
@mcp.prompt                                    # becomes a prompt template

async with Client(mcp) as client:              # in-memory (testing)
    result = await client.call_tool("name", {"arg": value})
    result.data                                # Python value (int, str, dict...)
    result.content[0].text                     # string representation
    result.is_error                            # bool

    content = await client.read_resource("uri://path")
    content[0].text                            # text resources

    result = await client.get_prompt("name", {"arg": value})
    result.messages[0].content.text            # prompt text
    result.messages[0].role                    # "user" or "assistant"
```

---

## Gotcha List (Things That Actually Broke)

### G-1: `ctx.read_resource()` vs `client.read_resource()` return different types

```python
# Client method → list[TextResourceContents]
content = await client.read_resource("uri://data")
text = content[0].text                          # ✓

# Context method → ResourceResult (NOT a list!)
result = await ctx.read_resource("uri://data")
text = result.contents[0].content              # ✓  (note: .content not .text)
text = result[0].text                          # ✗  TypeError: not subscriptable
```

### G-2: `log_handler` and `progress_handler` must be ASYNC

```python
# WRONG — sync handler silently receives nothing
def on_log(message, level, **kwargs):
    print(message)                              # never called

# CORRECT — async handler with correct signature
from mcp.types import LoggingMessageNotificationParams as LogMessage

async def on_log(message: LogMessage) -> None:
    # message.data is {'msg': '...', 'extra': None} for string logs
    text = message.data.get("msg", str(message.data)) if isinstance(message.data, dict) else str(message.data)
    print(f"[{message.level}] {text}")

async def on_progress(progress: float, total: float | None, msg: str | None) -> None:
    print(f"{progress}/{total}")

async with Client(mcp, log_handler=on_log, progress_handler=on_progress) as client:
    ...
```

### G-3: `ToolError` on server RAISES on client (not just `is_error=True`)

```python
# WRONG — checking is_error doesn't work because the exception is raised first
result = await client.call_tool("risky", {"val": -1})
if result.is_error: ...                         # ✗  never reached

# CORRECT — wrap in try/except
try:
    result = await client.call_tool("risky", {"val": -1})
except ToolError as e:
    print(f"Tool failed: {e}")                  # ✓
```

### G-4: Multi-message prompts need fastmcp's `Message`, not `mcp.types.PromptMessage`

```python
from mcp.types import PromptMessage, TextContent  # WRONG for list returns

from fastmcp.prompts.base import Message          # CORRECT

@mcp.prompt
def my_prompt(topic: str) -> list[Message]:
    return [
        Message(f"You are an expert in {topic}.", role="user"),
        Message("Ready to help.", role="assistant"),
    ]
```

### G-5: `@mcp.tool` (no parens) vs `@mcp.tool()` (with parens)

```python
@mcp.tool          # simple decorator — docstring becomes description
def add(x: int, y: int) -> int:
    """Add two integers."""
    return x + y

@mcp.tool()        # also valid — empty parens, still uses docstring

@mcp.tool(name="custom_name", description="Override description here.")
def add_impl(x: int, y: int) -> int:
    return x + y   # tool registered as "custom_name"
```

### G-6: Template resource param names MUST match URI template exactly

```python
@mcp.resource("users://{user_id}/orders/{order_id}")
def get_order(user_id: str, order_id: str) -> str:   # ✓ names match
    ...

@mcp.resource("users://{user_id}/orders/{order_id}")
def get_order(uid: str, oid: str) -> str:             # ✗ names don't match → error
    ...
```

### G-7: Reusing a closed client raises RuntimeError

```python
client = Client(mcp)
async with client:
    pass  # client closed here

await client.call_tool(...)   # ✗  RuntimeError: client already closed

# CORRECT: create a new context manager each time, or keep it open
async with Client(mcp) as client:
    await client.call_tool(...)   # ✓
```

### G-8: `log_handler` in-memory client receives messages as `{'msg': '...', 'extra': None}` dicts

```python
async def on_log(message: LogMessage) -> None:
    # message.data is NOT always a plain string!
    # For ctx.info("text"), message.data = {'msg': 'text', 'extra': None}
    
    # WRONG: treating as string
    print(message.data)                         # prints the whole dict

    # CORRECT: extract msg key
    text = message.data.get("msg", str(message.data)) if isinstance(message.data, dict) else str(message.data)
    print(text)
```

### G-9: `mask_error_details=True` affects generic exceptions, NOT ToolError

```python
mcp = FastMCP("prod", mask_error_details=True)

@mcp.tool
def buggy(x: int) -> str:
    return str(1 / x)   # ZeroDivisionError → client sees masked message

@mcp.tool
def validated(x: int) -> str:
    if x < 0:
        raise ToolError("x must be >= 0")   # ToolError message ALWAYS visible
    return str(x)
```

### G-10: Resources appear in `list_resources()` OR `list_resource_templates()`, not both

```python
@mcp.resource("config://app")          # static → list_resources()
@mcp.resource("data://{id}")           # template → list_resource_templates()

# list_resources() shows only the static ones
# list_resource_templates() shows only the template URIs
```

---

## Do's and Don'ts

### Tools

| Do ✓ | Don't ✗ |
|------|---------|
| Use `ToolError` for expected failures (not-found, business rules) | Raise generic `Exception` for expected failures (details get masked) |
| Include disambiguation in tool descriptions ("Use THIS tool for X, not for Y") | Leave two similar tools with vague descriptions |
| Use `Annotated[type, Field(description="...")]` for parameter richness | Leave parameters undescribed |
| Return structured dicts for multi-field results | Return unstructured strings that the LLM has to parse |
| Use `mask_error_details=True` in production | Expose internal tracebacks to clients |
| Use ToolAnnotations hints (`readOnlyHint`, `destructiveHint`) | Ignore hints — the host uses them for safety UI |

### Resources

| Do ✓ | Don't ✗ |
|------|---------|
| Use resources for read-only data that agents look up | Use tools for pure data lookups with no side effects |
| Match template variable names exactly to function params | Mismatch names between URI template and function signature |
| Return JSON strings for structured data | Return raw Python objects (must be serializable str) |
| Use resources for catalogs, configs, knowledge bases | Put mutable state into resources |

### Prompts

| Do ✓ | Don't ✗ |
|------|---------|
| Use `Message(content, role="user"/"assistant")` from `fastmcp.prompts.base` | Use `mcp.types.PromptMessage` in list returns |
| Use prompts for reusable conversation starters | Hard-code all prompt text into the system message |
| Return `list[Message]` for multi-turn conversation priming | Mix `Message` and `PromptMessage` types in the same list |

### Client

| Do ✓ | Don't ✗ |
|------|---------|
| Keep one `Client` open for a session | Create a new `Client` per call (expensive setup/teardown) |
| Use `try/except ToolError` around all tool calls | Check `result.is_error` (exception is raised before you get there) |
| Use `async with Client(mcp) as client:` | Forget `async with` and use raw `Client()` without context manager |
| Use `result.data` for the Python value | Always parse `result.content[0].text` manually |
| Make log/progress handlers async | Make them sync (they'll silently not receive any events) |

---

## Common Patterns

### Pattern 1: Tool + Resource combo (tool reads live config from resource)

```python
@mcp.resource("policy://limits")
def get_limits() -> str:
    return json.dumps({"max_refund": 500, "max_order_qty": 100})

@mcp.tool
async def process_refund(order_id: str, amount: float, ctx: Context) -> dict:
    result = await ctx.read_resource("policy://limits")
    limits = json.loads(result.contents[0].content)   # note: .contents[0].content
    if amount > limits["max_refund"]:
        raise ToolError(f"Amount ${amount} exceeds limit ${limits['max_refund']}")
    ...
```

### Pattern 2: Concurrent tool calls with asyncio.gather

```python
async with Client(mcp) as client:
    # Fetch independently — runs in parallel
    results = await asyncio.gather(
        client.call_tool("get_user", {"id": "U001"}),
        client.call_tool("get_user", {"id": "U002"}),
        client.call_tool("get_user", {"id": "U003"}),
    )
    users = [r.data for r in results]
```

### Pattern 3: Tool result in an Anthropic agentic loop

```python
async with Client(mcp) as mcp_client:
    tools_list = await mcp_client.list_tools()
    tools_for_anthropic = [
        {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
        for t in tools_list
    ]
    
    while True:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6", tools=tools_for_anthropic, messages=messages
        )
        if response.stop_reason == "end_turn":
            break
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        r = await mcp_client.call_tool(block.name, block.input)
                        content = json.dumps(r.data)
                    except ToolError as e:
                        content = str(e)              # pass error back as tool result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content,
                    })
            messages.append({"role": "user", "content": tool_results})
```

### Pattern 4: Server composition (gateway from domain servers)

```python
inventory = FastMCP("inventory")
orders = FastMCP("orders")

gateway = FastMCP("gateway")
gateway.mount(inventory, prefix="inv")   # tools → "inv_toolname"
gateway.mount(orders,    prefix="ord")   # tools → "ord_toolname"

async with Client(gateway) as client:
    await client.call_tool("inv_get_stock", {"product_id": "P001"})
    await client.call_tool("ord_create_order", {...})
```

### Pattern 5: TVBP error categories in ToolError message

```python
from fastmcp.exceptions import ToolError
import json

def process_payment(amount: float) -> dict:
    if amount > 1000:
        raise ToolError(json.dumps({
            "errorCategory": "business",   # T=Transient, V=Validation, B=Business, P=Permission
            "isRetryable": False,
            "humanMessage": "Payments over $1000 require manual approval.",
        }))
    ...
```

---

## Transport Summary

| Transport | Code | Use case |
|-----------|------|---------|
| In-memory | `Client(mcp)` | Testing, same-process |
| stdio | `mcp.run()` or `mcp.run(transport="stdio")` | Claude Code / MCP hosts (subprocess) |
| HTTP | `mcp.run(transport="http", port=8000)` | Production web deployments |
| SSE | `mcp.run(transport="sse")` | Legacy — deprecated, prefer HTTP |

---

## FastMCP Constructor Parameters

```python
mcp = FastMCP(
    name="my-server",              # client-visible server name
    instructions="...",            # LLM-visible server description
    lifespan=my_lifespan_fn,       # asynccontextmanager for startup/shutdown
    on_duplicate_tools="warn",     # "error" | "warn" | "replace" | "ignore"
    mask_error_details=False,      # True = hide tracebacks in production
    strict_input_validation=True,  # enforce input schema strictly
)
```

---

## Key Numbers

| Fact | Value |
|------|-------|
| FastMCP tool decorator (no parens) | Valid ✓ |
| FastMCP tool decorator (with parens) | Valid ✓ |
| ctx.read_resource returns | `ResourceResult` (use `.contents[0].content`) |
| client.read_resource returns | `list[TextResourceContents]` (use `[0].text`) |
| log_handler signature | `async def (LogMessage) -> None` |
| progress_handler signature | `async def (float, float\|None, str\|None) -> None` |
| ToolError on server → client | Raises `ToolError` exception (not `is_error=True`) |
| Multi-turn prompt return type | `list[Message]` from `fastmcp.prompts.base` |
