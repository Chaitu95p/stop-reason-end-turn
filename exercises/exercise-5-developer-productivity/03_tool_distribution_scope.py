"""
Exercise 5 - Steps 5-6: Tool Distribution and Scoped Access

EXAM CONCEPTS:
  1. Too many tools degrade selection reliability:
       An agent with 18 tools has higher decision complexity than one with 4-5.
       Each additional tool increases the chance of misrouting.
       RULE: give each agent ONLY the tools it needs for its role.

  2. Cross-specialization misuse:
       A synthesis agent with web search tools will attempt web searches.
       A report agent with database write tools may accidentally mutate state.
       Solution: scoped tool sets per agent role.

  3. Replacing generic tools with constrained alternatives:
       fetch_url (any URL)    ->  load_document (validates doc URLs only)
       analyze_document (all) ->  extract_data_points / summarize_content /
                                  verify_claim_against_source (distinct purposes)

  4. Cross-role scoped tools for high-frequency needs:
       The synthesis agent needs simple fact verification but NOT full web search.
       Give it a narrow verify_fact tool; route complex cases through coordinator.

  5. tool_choice configuration options:
       "auto"   -> model may call a tool OR return text (default)
       "any"    -> model MUST call a tool, not return text
       forced   -> {"type": "tool", "name": "X"} - model MUST call tool X
       Use "any" when you need guaranteed structured output (not conversational text).

  Mnemonic: SCREW
    Scope each agent's tools to its role
    Constrained alternatives replace generic tools
    Route complex cases through coordinator
    Each role gets only what it needs
    Wide tool sets lower selection accuracy

Run: uv run python 03_tool_distribution_scope.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)

# ---------------------------------------------------------------------------
# Mock tool implementations
# ---------------------------------------------------------------------------
def web_search(query: str) -> dict:
    return {"results": [f"Result for '{query}': Mock article 1", "Mock article 2"]}


def load_document(doc_url: str) -> dict:
    """Constrained alternative to fetch_url -- validates doc URLs only."""
    valid_prefixes = ("docs.", "confluence.", "wiki.")
    if not any(doc_url.startswith(p) for p in valid_prefixes):
        return {
            "isError": True,
            "errorCategory": "validation",
            "isRetryable": False,
            "errorCode": "INVALID_DOC_URL",
            "developerMessage": f"load_document only accepts doc URLs (docs.*, confluence.*, wiki.*), got: {doc_url}",
        }
    return {"content": f"Mock documentation content from {doc_url}", "wordCount": 1500}


def extract_data_points(doc_content: str) -> dict:
    return {"dataPoints": ["datapoint_1", "datapoint_2"], "count": 2}


def summarize_content(doc_content: str, max_words: int = 100) -> dict:
    return {"summary": f"Mock summary of content ({max_words} word limit applied)"}


def verify_claim_against_source(claim: str, source_url: str) -> dict:
    return {"supported": True, "confidence": 0.85, "evidence": "Mock evidence excerpt"}


def verify_fact(fact: str) -> dict:
    """Scoped verify_fact for synthesis agent -- simpler than full web_search."""
    return {"verified": True, "confidence": 0.9, "source": "Mock source"}


def write_report(title: str, sections: list) -> dict:
    return {"success": True, "report_id": "RPT-001", "title": title, "sections_count": len(sections)}


# ---------------------------------------------------------------------------
# Tool sets: over-provisioned (ANTI-PATTERN) vs correctly scoped (CORRECT)
# ---------------------------------------------------------------------------
SYNTHESIS_TOOLS_OVERPROVISION = [
    # ANTI-PATTERN: synthesis agent given ALL tools
    {"name": "web_search",         "description": "Search the web.", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "load_document",      "description": "Load a document.", "input_schema": {"type": "object", "properties": {"doc_url": {"type": "string"}}, "required": ["doc_url"]}},
    {"name": "extract_data_points","description": "Extract data.", "input_schema": {"type": "object", "properties": {"doc_content": {"type": "string"}}, "required": ["doc_content"]}},
    {"name": "summarize_content",  "description": "Summarize.", "input_schema": {"type": "object", "properties": {"doc_content": {"type": "string"}}, "required": ["doc_content"]}},
    {"name": "verify_claim_against_source", "description": "Verify claim.", "input_schema": {"type": "object", "properties": {"claim": {"type": "string"}, "source_url": {"type": "string"}}, "required": ["claim", "source_url"]}},
    {"name": "verify_fact",        "description": "Quick fact check.", "input_schema": {"type": "object", "properties": {"fact": {"type": "string"}}, "required": ["fact"]}},
    {"name": "write_report",       "description": "Write report.", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "sections": {"type": "array", "items": {"type": "string"}}}, "required": ["title", "sections"]}},
]

SYNTHESIS_TOOLS_SCOPED = [
    # CORRECT: synthesis agent gets only what it needs
    {
        "name": "verify_fact",
        "description": (
            "Quick fact verification for simple lookups: dates, names, statistics. "
            "Use during synthesis when you need to confirm a specific claim. "
            "For complex multi-source investigations, return to coordinator."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"fact": {"type": "string", "description": "Claim to verify"}},
            "required": ["fact"],
        },
    },
    {
        "name": "write_report",
        "description": (
            "Write the final structured report once synthesis is complete. "
            "Call ONLY when all findings are ready to publish. "
            "Pass a title and ordered list of section strings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title":    {"type": "string"},
                "sections": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "sections"],
        },
    },
]

TOOL_MAP = {
    "web_search":          lambda inp: web_search(inp.get("query", "")),
    "load_document":       lambda inp: load_document(inp.get("doc_url", "")),
    "extract_data_points": lambda inp: extract_data_points(inp.get("doc_content", "")),
    "summarize_content":   lambda inp: summarize_content(inp.get("doc_content", ""), inp.get("max_words", 100)),
    "verify_claim_against_source": lambda inp: verify_claim_against_source(inp.get("claim", ""), inp.get("source_url", "")),
    "verify_fact":         lambda inp: verify_fact(inp.get("fact", "")),
    "write_report":        lambda inp: write_report(inp.get("title", ""), inp.get("sections", [])),
}


def run_synthesis_agent(task: str, tools: list, label: str) -> str:
    """Run synthesis agent with given tool set, print tool calls made."""
    messages = [{"role": "user", "content": task}]
    system = (
        "You are a synthesis agent. Your job is to combine research findings "
        "into a coherent report, verify key facts, and write the final output."
    )
    tools_called = []
    for _ in range(10):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=system,
            tools=tools,
            messages=messages,
        )
        if resp.stop_reason == "end_turn":
            for block in resp.content:
                if hasattr(block, "text"):
                    print(f"  [{label}] Tools called: {tools_called}")
                    return block.text
            return "(no text)"
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    fn = TOOL_MAP.get(block.name)
                    result = fn(block.input) if fn else {"error": "unknown"}
                    tools_called.append(block.name)
                    print(f"    [{label}] tool_use: {block.name}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
            messages.append({"role": "user", "content": results})
        else:
            return f"(unexpected: {resp.stop_reason})"
    return "(loop limit)"


# ---------------------------------------------------------------------------
# DEMO 1: Show tool_choice options
# ---------------------------------------------------------------------------
def demo_tool_choice_options() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 1: tool_choice configuration options")
    print()
    options = [
        ("auto",   "Model may call a tool OR return text -- default behavior"),
        ("any",    "Model MUST call a tool (not return conversational text) -- use for guaranteed structured output"),
        ("forced", '{"type": "tool", "name": "extract_metadata"} -- model MUST call that specific tool'),
    ]
    for opt, desc in options:
        print(f"  tool_choice={opt!r:8s}  {desc}")
    print()
    print("EXAM: Use 'any' when you need guaranteed structured output from any available tool.")
    print("      Use forced when a specific tool MUST run first (e.g., extract_metadata before enrichment).")


# ---------------------------------------------------------------------------
# DEMO 2: Over-provisioned vs scoped synthesis agent
# ---------------------------------------------------------------------------
def demo_scoped_tool_access() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 2: Over-provisioned vs scoped tool access for synthesis agent")
    print()
    task = (
        "Synthesize these research findings into a report: "
        "'AI adoption in healthcare is at 34% (2024 survey). "
        "Key benefits: diagnostic accuracy +18%, admin efficiency +40%.' "
        "Verify the 34% figure and write the final report."
    )
    print(f"Task: {task[:80]}...")
    print()
    print(f"Over-provisioned agent has {len(SYNTHESIS_TOOLS_OVERPROVISION)} tools:")
    print("  " + ", ".join(t["name"] for t in SYNTHESIS_TOOLS_OVERPROVISION))
    print("  Problem: synthesis agent may attempt web searches instead of using verify_fact.")
    print()
    print(f"Scoped agent has {len(SYNTHESIS_TOOLS_SCOPED)} tools:")
    print("  " + ", ".join(t["name"] for t in SYNTHESIS_TOOLS_SCOPED))
    print()

    print("--- Running SCOPED agent ---")
    result_scoped = run_synthesis_agent(task, SYNTHESIS_TOOLS_SCOPED, "SCOPED")
    print("  Result:", result_scoped[:200])


# ---------------------------------------------------------------------------
# DEMO 3: Constrained alternatives vs generic tools
# ---------------------------------------------------------------------------
def demo_constrained_tools() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 3: Constrained tool alternatives")
    print()
    comparisons = [
        ("fetch_url (generic)",    "ANY URL -- can fetch social media, CDNs, etc."),
        ("load_document (scoped)", "ONLY docs.*/confluence.*/wiki.* -- validates input"),
        ("",                       ""),
        ("analyze_document (generic)",       "Does everything -- ambiguous purpose"),
        ("extract_data_points (specific)",   "ONLY extracts structured data points"),
        ("summarize_content (specific)",     "ONLY summarizes -- won't attempt extraction"),
        ("verify_claim_against_source (specific)", "ONLY verifies claims against sources"),
    ]
    for tool, desc in comparisons:
        if not tool:
            print()
        else:
            print(f"  {tool:40s} {desc}")
    print()
    print("Testing load_document with invalid URL (validates boundary):")
    result = load_document("https://social-media.com/posts/123")
    print("  Result:", result)
    print()
    print("Testing load_document with valid doc URL:")
    result = load_document("docs.company.com/api/payments")
    print("  Result:", result)


if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("DEMO 1: tool_choice configuration options")
    print(sep)
    demo_tool_choice_options()

    print()
    print(sep)
    print("DEMO 2: Over-provisioned vs scoped tool access")
    print(sep)
    demo_scoped_tool_access()

    print()
    print(sep)
    print("DEMO 3: Constrained tool alternatives")
    print(sep)
    demo_constrained_tools()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. More tools = higher selection complexity; cap agent tool sets at 4-5.")
    print("  2. Scoped tool access prevents cross-specialization misuse.")
    print("  3. Replace generic tools (fetch_url) with constrained variants (load_document).")
    print("  4. Provide a narrow cross-role tool (verify_fact) for high-frequency needs;")
    print("     route complex cases through the coordinator.")
    print("  5. tool_choice: 'any' guarantees the model calls a tool (not conversational text).")
    print("     Forced tool selection ensures a specific tool runs first.")
    print("  Mnemonic SCREW: Scope/Constrained alternatives/Route complex/Each role/Wide=worse.")
