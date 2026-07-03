# MCP Python SDK Explorer

Runnable Python programs covering the complete FastMCP surface area.
Every script is self-contained: runs via `uv run python <script>`, uses an
in-memory `Client(mcp)`, and prints its own output — no server process needed.

## Run a Script

```bash
cd mcp-explorer
uv run python 01_server_basics.py
uv run python 02_tools_deep_dive.py
# ... etc.

# Run all in order
for f in 0*.py; do echo "=== $f ===" && uv run python "$f" 2>/dev/null; done
```

## File Index

| Script | What it covers |
|--------|---------------|
| `00_smoke_test.py` | Minimal end-to-end: 1 tool + 1 resource + 1 prompt |
| `01_server_basics.py` | FastMCP constructor, decorator registration, transport options |
| `02_tools_deep_dive.py` | All tool patterns: sync, async, typed params, Pydantic, annotations, Context, ToolError |
| `03_resources_deep_dive.py` | Static, template, multi-param, binary resources; JSON resources |
| `04_prompts_deep_dive.py` | String return, Message list, typed params, data-driven prompts |
| `05_context_features.py` | ctx.info/debug/warning/error, progress, ctx.read_resource, ctx.get_prompt, request_id |
| `06_client_basics.py` | All client operations, callbacks (log_handler, progress_handler), error handling |
| `07_error_handling.py` | ToolError vs generic exceptions, TVBP categories, mask_error_details, empty vs error |
| `08_server_composition.py` | Mounting servers, gateway pattern, namespace prefixing |
| `09_real_world_patterns.py` | Lifespan, complete support-agent server, concurrent calls, Anthropic agentic loop |
| `10_testing_patterns.py` | pytest-asyncio fixtures, ToolError assertions, parametrize, resource/prompt testing |
| `tips_tricks_gotchas.md` | Reference: gotchas found during development, do/don't, common patterns |

> **Note on transports:** All scripts use the in-memory `Client(mcp)` — no subprocess or network needed.
> `01_server_basics.py` shows stdio/HTTP transport options as a reference table only;
> those transports require a running server process and are not demoed in runnable form here.

## Key Things to Know Upfront

### The critical API asymmetry (Gotcha G-1)

`client.read_resource()` and `ctx.read_resource()` return **different types**:

```python
# Client:  list[TextResourceContents]
content = await client.read_resource("uri://data")
text = content[0].text

# Context: ResourceResult
result = await ctx.read_resource("uri://data")
text = result.contents[0].content        # .content not .text
```

### ToolError raises on the client side

```python
# Server raises → client RAISES (not just is_error=True)
try:
    result = await client.call_tool("might_fail", {"val": -1})
except ToolError as e:
    print(f"Failed: {e}")
```

### Callbacks must be async

```python
# Both log_handler AND progress_handler must be async
from mcp.types import LoggingMessageNotificationParams as LogMessage

async def on_log(message: LogMessage) -> None:
    text = message.data.get("msg", str(message.data)) if isinstance(message.data, dict) else str(message.data)
    print(f"[{message.level}] {text}")

async def on_progress(progress: float, total: float | None, msg: str | None) -> None:
    print(f"{progress}/{total}")
```

### Multi-message prompts use fastmcp's Message, not mcp.types

```python
from fastmcp.prompts.base import Message   # this one

@mcp.prompt
def setup(role: str) -> list[Message]:
    return [
        Message(f"You are a {role}.", role="user"),
        Message("Ready to help.", role="assistant"),
    ]
```
