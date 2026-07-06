"""
Domain 2 - Task 2.4: MCP Server Configuration & Scope

EXAM CONCEPTS:
  1. .mcp.json location determines scope:
     Project-scoped  → <project-root>/.mcp.json  (shared with team via git)
     User-scoped     → ~/.claude.json            (personal, not shared)

  2. Environment variable expansion: ${VAR_NAME} in .mcp.json is
     substituted at runtime from the shell environment. Tokens should
     NEVER be hard-coded in config files (security risk).

  3. MCP resources vs tools:
     Tools     → actively invoked by Claude (function calls with arguments)
     Resources → passively consulted context (like documents or data feeds)

  4. Transport types:
     "stdio"   → spawns a subprocess, communicates over stdin/stdout
     "sse"     → connects to a running HTTP server via Server-Sent Events

  5. Tool description quality affects adoption: if developers can't
     understand the tool from its MCP description, they won't use it.
     Good MCP tool descriptions follow the same SEEB rules as API tools.

  6. Always-on vs on-demand servers:
     Some MCP servers should run always (e.g., filesystem, web search).
     Others should be project-specific (e.g., your internal CI/CD API).

Run: uv run python 04_mcp_server_config.py
"""

import json

NL = chr(10)


# ---------------------------------------------------------------------------
# Generate .mcp.json examples
# ---------------------------------------------------------------------------
def project_mcp_json() -> dict:
    """
    Project-scoped .mcp.json — lives at <project-root>/.mcp.json
    Committed to git so the whole team shares the same servers.
    Tokens referenced via ${ENV_VAR} — never hard-coded.
    """
    return {
        "mcpServers": {
            "github": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
                }
            },
            "internal-ci": {
                "type": "sse",
                "url": "https://ci.internal.example.com/mcp",
                "headers": {
                    "Authorization": "Bearer ${CI_API_KEY}"
                }
            },
            "postgres-readonly": {
                "type": "stdio",
                "command": "uvx",
                "args": ["mcp-server-postgres", "--read-only"],
                "env": {
                    "DATABASE_URL": "${DATABASE_URL}"
                }
            }
        }
    }


def user_mcp_json() -> dict:
    """
    User-scoped ~/.claude.json — personal servers, not committed to git.
    Contains personal tokens and tools irrelevant to other team members.
    """
    return {
        "mcpServers": {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem",
                         "/home/user/projects", "/home/user/documents"],
                "description": "Personal filesystem access"
            },
            "brave-search": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "env": {
                    "BRAVE_API_KEY": "${BRAVE_API_KEY}"
                }
            },
            "obsidian-notes": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "mcp-obsidian", "/home/user/vault"],
                "description": "Personal knowledge base (Obsidian vault)"
            }
        }
    }


# ---------------------------------------------------------------------------
# MCP tool description quality examples
# ---------------------------------------------------------------------------
POOR_TOOL_DESCRIPTION = {
    "name": "run_query",
    "description": "Runs a query.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "q": {"type": "string"}
        }
    }
}

GOOD_TOOL_DESCRIPTION = {
    "name": "run_readonly_sql",
    "description": (
        "Execute a read-only SQL SELECT query against the production analytics database. "
        "Use for reporting, dashboards, and data exploration. "
        "Examples: 'SELECT COUNT(*) FROM orders WHERE status = $1', "
        "'SELECT user_id, SUM(amount) FROM payments GROUP BY user_id LIMIT 100'. "
        "Constraints: SELECT only — INSERT, UPDATE, DELETE, DROP are rejected. "
        "Max 10,000 rows returned. Use LIMIT clause for large tables. "
        "Pass parameterized queries with $1, $2 placeholders when using user input."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "A read-only SQL SELECT statement. Use $1, $2 for parameters."
            },
            "params": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Parameter values for $1, $2, ... placeholders (prevents SQL injection)."
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Query timeout in seconds (default: 30, max: 120).",
                "default": 30
            }
        },
        "required": ["sql"]
    }
}


# ---------------------------------------------------------------------------
# MCP resources vs tools
# ---------------------------------------------------------------------------
def show_resources_vs_tools() -> None:
    sep = "-" * 50
    print(sep)
    print("MCP RESOURCES vs TOOLS")
    print()
    print("TOOLS (actively invoked — function calls):")
    print("  Claude calls them with arguments to perform actions or fetch data.")
    print("  Examples:")
    print("    create_issue(title, body, labels) -> {issue_url}")
    print("    run_readonly_sql(sql, params) -> {rows}")
    print("    search_codebase(pattern, path_glob) -> {matches}")
    print()
    print("RESOURCES (passively consulted — ambient context):")
    print("  Claude can read them like documents (URI-addressed).")
    print("  Examples:")
    print("    mcp://github/repo/README.md")
    print("    mcp://postgres/schema/orders")
    print("    mcp://internal-ci/pipeline-status/main")
    print()
    print("KEY DISTINCTION:")
    print("  Tool  = Claude initiates a call with specific arguments.")
    print("  Resource = Claude reads static/semi-static content passively.")
    print("  Most MCP integrations are TOOLS. Resources are for read-only context.")


# ---------------------------------------------------------------------------
# Transport type comparison
# ---------------------------------------------------------------------------
def show_transport_types() -> None:
    sep = "-" * 50
    print(sep)
    print("TRANSPORT TYPES: stdio vs sse")
    print()
    print("stdio (process-based):")
    print("  - Claude Code spawns the server as a subprocess")
    print("  - Communicates over stdin/stdout (JSON-RPC)")
    print("  - Good for: local tools, CLI-based servers (npx, uvx, python)")
    print("  - Config: 'command' + 'args' fields")
    print("  - Server lifecycle: managed by Claude Code")
    print()
    print("sse (HTTP-based):")
    print("  - Claude Code connects to a RUNNING HTTP server")
    print("  - Server-Sent Events for streaming responses")
    print("  - Good for: remote servers, team infrastructure, long-running services")
    print("  - Config: 'url' + optional 'headers' fields")
    print("  - Server lifecycle: you manage it (deploy, scale, monitor)")


# ---------------------------------------------------------------------------
# Env var expansion security example
# ---------------------------------------------------------------------------
def show_env_var_security() -> None:
    sep = "-" * 50
    print(sep)
    print("ENVIRONMENT VARIABLE EXPANSION (security pattern)")
    print()
    print("WRONG — hard-coded token in .mcp.json (NEVER do this):")
    bad = {
        "mcpServers": {
            "github": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_abc123realTokenHere"  # BAD
                }
            }
        }
    }
    print("  " + json.dumps(bad, indent=4).replace(NL, NL + "  "))
    print()
    print("CORRECT — reference via ${ENV_VAR}:")
    good = {
        "mcpServers": {
            "github": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"  # GOOD
                }
            }
        }
    }
    print("  " + json.dumps(good, indent=4).replace(NL, NL + "  "))
    print()
    print("  -> Set GITHUB_TOKEN in your shell profile (.bashrc / .zshrc)")
    print("  -> .mcp.json can be safely committed to git without leaking secrets")


# ---------------------------------------------------------------------------
# Scope decision guide
# ---------------------------------------------------------------------------
def show_scope_decision() -> None:
    sep = "-" * 50
    print(sep)
    print("SCOPE DECISION: project vs user")
    print()
    print("Use PROJECT-SCOPED (.mcp.json in project root) when:")
    print("  - The server is specific to this project's tech stack")
    print("  - All team members need the same MCP tools")
    print("  - You want server config version-controlled with the code")
    print("  - Examples: project DB, project CI, project-specific APIs")
    print()
    print("Use USER-SCOPED (~/.claude.json) when:")
    print("  - The server is useful across ALL your projects")
    print("  - It contains personal credentials or personal data")
    print("  - Other team members don't need or want it")
    print("  - Examples: personal filesystem, personal notes, brave search")


# ---------------------------------------------------------------------------
# Community vs custom MCP server decision
# ---------------------------------------------------------------------------
def show_community_vs_custom() -> None:
    sep = "-" * 50
    print(sep)
    print("COMMUNITY vs CUSTOM MCP servers: decision rule")
    print()
    print("PREFER community MCP servers when:")
    print("  - A maintained server already exists for the service (Jira, GitHub,")
    print("    Slack, Postgres, filesystem, web search, etc.)")
    print("  - You need standard read/write operations the community server covers")
    print("  - You want to avoid maintenance burden and security review")
    print("  Examples: @modelcontextprotocol/server-github, mcp-server-postgres,")
    print("            mcp-obsidian, @modelcontextprotocol/server-brave-search")
    print()
    print("BUILD a custom MCP server only when:")
    print("  - Your team has internal systems with no community equivalent")
    print("    (proprietary CI/CD API, internal ticketing, legacy SOAP services)")
    print("  - You need business-specific tool descriptions and parameter names")
    print("  - You need to enforce team-specific constraints (read-only, audit log,")
    print("    row-level security) the community server does not provide")
    print()
    print("DECISION TABLE:")
    cases = [
        ("Use GitHub Issues",     "community",  "@modelcontextprotocol/server-github"),
        ("Use Jira tickets",      "community",  "jira-mcp (community server)"),
        ("Query prod DB",         "community",  "mcp-server-postgres (read-only flag)"),
        ("Internal CI/CD API",    "custom",     "Build: exposes run/cancel/status tools"),
        ("Proprietary CRM",       "custom",     "Build: CRM tools with auth + audit log"),
        ("Team config registry",  "custom",     "Build: team-specific schema + constraints"),
    ]
    for use_case, decision, rationale in cases:
        print(f"  {decision.upper():9} | {use_case:28} -> {rationale}")

    print()
    print("MCP RESOURCES for content catalogs (exam concept):")
    print("  Resources expose semi-static content at URI addresses.")
    print("  Use when Claude needs to consult a catalog without a query:")
    print("    mcp://github/repo/README.md       → project context")
    print("    mcp://jira/project/SPRNT/backlog   → sprint issue list")
    print("    mcp://postgres/schema/public       → table/column names")
    print("  Benefit: reduces exploratory tool calls by giving Claude ambient context.")
    print("  Rule of thumb: if Claude would always call a tool just to read the")
    print("  same document, expose it as a Resource instead.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Project-scoped .mcp.json (team-shared)")
    print(sep)
    print("File: <project-root>/.mcp.json")
    print(json.dumps(project_mcp_json(), indent=2))

    print()
    print(sep)
    print("DEMO 2: User-scoped ~/.claude.json (personal)")
    print(sep)
    print("File: ~/.claude.json")
    print(json.dumps(user_mcp_json(), indent=2))

    print()
    print(sep)
    print("DEMO 3: MCP Tool description quality comparison")
    print(sep)
    print("POOR description (one line, no examples, ambiguous parameter):")
    print("  " + json.dumps(POOR_TOOL_DESCRIPTION, indent=2).replace(NL, NL + "  "))
    print()
    print("GOOD description (scope, examples, constraints, parameter docs):")
    print("  " + json.dumps(GOOD_TOOL_DESCRIPTION, indent=2).replace(NL, NL + "  "))

    print()
    print(sep)
    print("DEMO 4: Environment variable security")
    print(sep)
    show_env_var_security()

    print()
    print(sep)
    print("DEMO 5: Resources vs Tools")
    print(sep)
    show_resources_vs_tools()

    print()
    print(sep)
    print("DEMO 6: Transport types")
    print(sep)
    show_transport_types()

    print()
    print(sep)
    print("DEMO 7: Scope decision guide")
    print(sep)
    show_scope_decision()

    print()
    print(sep)
    print("DEMO 8: Community vs custom MCP decision + Resources for content catalogs")
    print(sep)
    show_community_vs_custom()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. PROJECT-SCOPED .mcp.json → team tools, version-controlled.")
    print("     USER-SCOPED ~/.claude.json → personal tools, not committed.")
    print("  2. ALWAYS use ${ENV_VAR} for tokens. NEVER hard-code credentials.")
    print("  3. stdio spawns a subprocess; sse connects to a running HTTP server.")
    print("  4. TOOLS: Claude actively calls with arguments.")
    print("     RESOURCES: Claude passively reads (URI-addressed content catalogs).")
    print("     Use Resources to reduce repeated exploratory tool calls.")
    print("  5. Good MCP tool descriptions follow SEEB rules — poor descriptions")
    print("     lead to low adoption even if the server is technically correct.")
    print("  6. PREFER community MCP servers over custom ones.")
    print("     BUILD custom only for internal systems with no community equivalent.")
