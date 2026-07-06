# Module 2 — Tool Design & MCP Integration

**Exam domain weight: 18%**

Covers how to design effective tool interfaces, structure error responses, distribute tools across subagents, configure MCP servers, and select Claude Code's built-in tools.

## Scripts

| Script | Task | Key concept |
|--------|------|-------------|
| `01_tool_interface_design.py` | 2.1 Tool Interface Design | Description quality as primary tool selection mechanism |
| `02_structured_error_responses.py` | 2.2 Structured Error Responses | `isError`, `errorCategory`, `isRetryable`, `humanMessage` |
| `03_tool_distribution.py` | 2.3 Tool Distribution | Scoped subagents; which tools each subagent gets |
| `04_mcp_server_config.py` | 2.4 MCP Server Configuration | `.mcp.json` (project) vs `~/.claude.json` (user) scope |
| `05_builtin_tools_selection.py` | 2.5 Built-in Tool Selection | When to use Bash vs Read vs Edit vs Write vs WebFetch |

## Run

```bash
# All scripts in order
cd modules/module-2 && for f in 0*.py; do echo "=== $f ===" && uv run python "$f"; done

# Single script
uv run python 02_structured_error_responses.py
```

## Key exam facts

- **Tool description is the LLM's primary signal** for which tool to call — it must describe WHEN to call, not just what it does.
- **Error categories (TVBP):** Transient (retry), Validation (fix input), Business (explain policy), Permission (escalate).
- **`isRetryable: false`** prevents wasted retries for non-fixable errors.
- **Empty result ≠ access failure:** `isError: false` + empty list = successful query with no matches; `isError: true` = query couldn't complete.
- **MCP scope:** `.mcp.json` at project root = project scope; `~/.claude.json` = user scope (single file at `$HOME`, not `~/.claude/mcp.json`).
