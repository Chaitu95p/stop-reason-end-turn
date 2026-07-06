"""
Exercise 5 - Steps 3-4: MCP Server Integration for Developer Productivity

EXAM CONCEPTS:
  1. MCP server scoping:
       Project-level  (.mcp.json)         -> shared with all team members via VCS
       User-level     (~/.claude.json)     -> personal / experimental servers only
       NEVER put personal experiments in .mcp.json -- they affect the whole team

  2. Environment variable expansion in .mcp.json:
       "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
       Credentials never hard-coded or committed to VCS.

  3. MCP resources vs MCP tools:
       Resources -> expose CONTENT CATALOGS (issue summaries, doc hierarchies,
                    DB schemas) so the agent sees what exists WITHOUT tool calls
       Tools     -> actions with side effects (create issue, run query)
       Resources reduce exploratory tool calls by giving the agent upfront
       visibility into available data.

  4. MCP tool descriptions must be BETTER than built-in tool descriptions:
       If an MCP tool's description is vague, Claude uses Grep instead.
       E.g., a jira_search tool with no description loses to built-in Grep
       because Claude defaults to what it knows will work.

  5. Community MCP servers vs custom:
       Use community servers for standard integrations (GitHub, Jira, Slack).
       Build custom only for team-specific internal workflows.

  Mnemonic: SPACE
    Scope servers correctly (project vs user)
    Pass credentials via env vars, never hard-code
    Add detailed descriptions or Claude ignores MCP tools
    Catalogs via Resources reduce exploratory tool calls
    Existing community servers beat custom for standard tools

Run: uv run python 02_mcp_integration_patterns.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)

# ---------------------------------------------------------------------------
# Mock MCP tool implementations (no real server I/O)
# ---------------------------------------------------------------------------
MOCK_ISSUES = [
    {"id": "PROJ-101", "title": "Payment timeout on checkout", "status": "open",  "priority": "high"},
    {"id": "PROJ-102", "title": "Refund not reflected in balance", "status": "open",  "priority": "medium"},
    {"id": "PROJ-103", "title": "Order lookup slow for large accounts", "status": "closed", "priority": "low"},
]

MOCK_PR_FILES = {
    "PR-42": ["src/payments/processor.py", "src/orders/lookup.py", "tests/test_processor.py"]
}


def jira_search(query: str, status: str = None) -> dict:
    """Mock Jira search via MCP."""
    results = [i for i in MOCK_ISSUES if query.lower() in i["title"].lower()]
    if status:
        results = [i for i in results if i["status"] == status]
    return {"issues": results, "total": len(results)}


def github_list_pr_files(pr_number: str) -> dict:
    """Mock GitHub MCP tool: list files changed in a PR."""
    files = MOCK_PR_FILES.get(f"PR-{pr_number}", [])
    return {"files": files, "count": len(files)}


def github_post_comment(pr_number: str, body: str) -> dict:
    """Mock GitHub MCP tool: post a comment on a PR."""
    return {"success": True, "comment_id": f"CMT-{pr_number}-001", "body": body[:80]}


# ---------------------------------------------------------------------------
# Tool definitions: GOOD descriptions vs BAD descriptions
# ---------------------------------------------------------------------------
TOOLS_GOOD_DESCRIPTIONS = [
    {
        "name": "jira_search",
        "description": (
            "Search Jira issues by keyword with optional status filter. "
            "Use for: finding existing bugs before creating duplicates, "
            "checking if a known issue covers reported behavior, "
            "looking up issue IDs for linking. "
            "Returns id, title, status, priority. "
            "NOT for GitHub PRs -- use github_list_pr_files for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query":  {"type": "string", "description": "Keywords to search in issue titles"},
                "status": {"type": "string", "enum": ["open", "closed"], "description": "Optional filter"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "github_list_pr_files",
        "description": (
            "List all files changed in a GitHub pull request. "
            "Use BEFORE code review to understand the PR scope. "
            "Returns file paths relative to repo root. "
            "NOT for searching file contents -- use the grep built-in for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pr_number": {"type": "string", "description": "PR number without # (e.g. '42')"},
            },
            "required": ["pr_number"],
        },
    },
    {
        "name": "github_post_comment",
        "description": (
            "Post a review comment on a GitHub pull request. "
            "Use AFTER completing analysis to deliver findings. "
            "body should be markdown-formatted. "
            "Side-effectful: only call when review is complete."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pr_number": {"type": "string"},
                "body":      {"type": "string", "description": "Markdown comment body"},
            },
            "required": ["pr_number", "body"],
        },
    },
]

TOOLS_WEAK_DESCRIPTIONS = [
    {
        "name": "jira_search",
        "description": "Search issues.",  # ANTI-PATTERN: too vague
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "github_list_pr_files",
        "description": "Get PR files.",  # ANTI-PATTERN: no context, no boundary
        "input_schema": {
            "type": "object",
            "properties": {"pr_number": {"type": "string"}},
            "required": ["pr_number"],
        },
    },
    {
        "name": "github_post_comment",
        "description": "Post comment.",  # ANTI-PATTERN: Claude doesn't know when to use it
        "input_schema": {
            "type": "object",
            "properties": {"pr_number": {"type": "string"}, "body": {"type": "string"}},
            "required": ["pr_number", "body"],
        },
    },
]

TOOL_MAP = {
    "jira_search":          lambda inp: jira_search(inp.get("query", ""), inp.get("status")),
    "github_list_pr_files": lambda inp: github_list_pr_files(inp.get("pr_number", "")),
    "github_post_comment":  lambda inp: github_post_comment(inp.get("pr_number", ""), inp.get("body", "")),
}


def run_agent(task: str, tools: list) -> str:
    """Run a developer agent with the given tool definitions."""
    messages = [{"role": "user", "content": task}]
    system = (
        "You are a developer productivity agent. "
        "Use tools to research issues and review pull requests. "
        "Always look up PR files before reviewing."
    )
    while True:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=tools,
            messages=messages,
        )
        if resp.stop_reason == "end_turn":
            for block in resp.content:
                if hasattr(block, "text"):
                    return block.text
            return "(no text)"
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    fn = TOOL_MAP.get(block.name)
                    result = fn(block.input) if fn else {"error": f"unknown: {block.name}"}
                    print(f"  Tool: {block.name}({block.input}) -> {result}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
            messages.append({"role": "user", "content": results})
        else:
            return f"(unexpected: {resp.stop_reason})"


# ---------------------------------------------------------------------------
# DEMO 1: MCP server scope comparison
# ---------------------------------------------------------------------------
def demo_mcp_scope_config() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 1: MCP server configuration patterns")
    print()
    project_config = {
        "mcpServers": {
            "github": {
                "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
                "scope": "PROJECT -- shared via .mcp.json in VCS",
            },
            "jira": {
                "command": "npx", "args": ["-y", "@modelcontextprotocol/server-atlassian"],
                "env": {"JIRA_TOKEN": "${JIRA_TOKEN}"},
                "scope": "PROJECT -- shared via .mcp.json in VCS",
            },
        }
    }
    user_config = {
        "mcpServers": {
            "my-experimental-db": {
                "command": "python", "args": ["-m", "my_custom_mcp"],
                "env": {"DB_URL": "${PERSONAL_DB_URL}"},
                "scope": "USER -- personal ~/.claude.json, NOT in VCS",
            }
        }
    }
    print("Project-scoped .mcp.json (shared via version control):")
    print(json.dumps(project_config, indent=2))
    print()
    print("User-scoped ~/.claude.json (personal experiments only):")
    print(json.dumps(user_config, indent=2))
    print()
    print("KEY: ${GITHUB_TOKEN} expands from environment -- credentials never committed.")


# ---------------------------------------------------------------------------
# DEMO 2: Good vs weak tool descriptions
# ---------------------------------------------------------------------------
def demo_tool_description_quality() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 2: Tool description quality impact on agent tool selection")
    print()
    print("Task: 'Review PR 42 for payment-related issues and check for existing Jira tickets'")
    print()
    print("--- With GOOD descriptions ---")
    result_good = run_agent(
        "Review PR 42 for payment-related issues and check for existing Jira tickets about payments.",
        TOOLS_GOOD_DESCRIPTIONS,
    )
    print("Result:", result_good[:300])

    print()
    print("--- With WEAK descriptions (anti-pattern) ---")
    print("  (With vague descriptions, Claude may skip MCP tools and use built-in Grep instead)")
    print("  Weak descriptions: 'Search issues.' / 'Get PR files.' / 'Post comment.'")
    print("  Result: Claude often bypasses MCP tools entirely when descriptions don't tell it WHEN to use them.")


if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("DEMO 1: MCP server scope configuration")
    print(sep)
    demo_mcp_scope_config()

    print()
    print(sep)
    print("DEMO 2: Tool description quality for MCP adoption")
    print(sep)
    demo_tool_description_quality()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Project-level .mcp.json is shared via VCS; user ~/.claude.json is personal.")
    print("  2. Always use ${ENV_VAR} expansion -- never hard-code credentials.")
    print("  3. MCP tool descriptions must explain WHEN and WHAT -- vague descriptions")
    print("     cause Claude to prefer familiar built-in tools (Grep) over MCP tools.")
    print("  4. MCP Resources expose content catalogs (schemas, issue lists) upfront,")
    print("     reducing exploratory tool calls.")
    print("  5. Use community MCP servers for standard integrations; build custom")
    print("     only for team-specific internal workflows.")
    print("  Mnemonic SPACE: Scope/Pass env vars/Add descriptions/Catalogs via Resources/Existing servers.")
