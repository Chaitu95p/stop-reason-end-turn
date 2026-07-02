"""
Domain 2 - Task 2.1: Design Effective Tool Interfaces with Clear Descriptions

EXAM CONCEPTS:
  1. Tool descriptions are the PRIMARY mechanism LLMs use for tool selection.
     Minimal descriptions → unreliable selection among similar tools.

  2. Effective descriptions include:
     - Input formats and example queries
     - Edge cases and boundary conditions
     - When to use this tool vs similar alternatives

  3. Ambiguous or overlapping descriptions cause MISROUTING.
     Example: analyze_content vs analyze_document with near-identical descriptions.

  4. System prompt wording can create unintended tool associations (keyword-sensitive).

  5. SPLITTING a generic tool into purpose-specific tools with defined
     input/output contracts reduces selection confusion.

  Mnemonic: SEEB
    Scope (what exactly this tool does vs what it doesn't)
    Examples (show typical input/output)
    Edge-cases (what to do at boundaries)
    Boundaries (when to use this tool vs alternatives)

Run: uv run python 01_tool_interface_design.py
"""

import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# DEMO 1: Minimal vs detailed tool descriptions
# ---------------------------------------------------------------------------
TOOLS_MINIMAL = [
    {
        "name": "get_customer",
        "description": "Retrieves customer information",
        "input_schema": {
            "type": "object",
            "properties": {"identifier": {"type": "string"}},
            "required": ["identifier"],
        },
    },
    {
        "name": "lookup_order",
        "description": "Retrieves order details",
        "input_schema": {
            "type": "object",
            "properties": {"identifier": {"type": "string"}},
            "required": ["identifier"],
        },
    },
]

TOOLS_DETAILED = [
    {
        "name": "get_customer",
        "description": (
            "Retrieve a customer record by customer ID (format: C followed by digits, e.g. C001)." + NL
            + "Returns: name, email, account tier, account status, member_since date." + NL
            + "Use this ONLY for customer identity lookup." + NL
            + "Do NOT use for order lookups -- use lookup_order for that." + NL
            + "Example: get_customer('C001') returns Alice Smith's full profile." + NL
            + "Edge case: if the customer ID is an email, this tool will fail -- "
            + "use find_customer_by_email instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Customer ID in format C### (e.g. C001, C042)",
                },
            },
            "required": ["identifier"],
        },
    },
    {
        "name": "lookup_order",
        "description": (
            "Retrieve an order record by order ID (format: ORD- followed by digits, e.g. ORD-100)." + NL
            + "Returns: order status, total amount, line items, customer_id, shipping info." + NL
            + "Use this ONLY for order information -- NOT for customer profiles." + NL
            + "Do NOT use get_customer for orders." + NL
            + "Example: lookup_order('ORD-100') returns the full order including status." + NL
            + "Edge case: if you have a customer ID but no order ID, call get_customer first "
            + "to retrieve their recent_order_ids field."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "Order ID in format ORD-### (e.g. ORD-100, ORD-999)",
                },
            },
            "required": ["identifier"],
        },
    },
]


def test_tool_selection(tools: list, request: str, label: str) -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=128,
        tools=tools,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": request}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return f"Tool: {block.name} | Input: {block.input}"
    return "(no tool called)"


# ---------------------------------------------------------------------------
# DEMO 2: Ambiguous overlapping tools → misrouting
# ---------------------------------------------------------------------------
TOOLS_AMBIGUOUS = [
    {
        "name": "analyze_content",
        "description": "Analyzes content from documents and web sources",
        "input_schema": {
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
    },
    {
        "name": "analyze_document",
        "description": "Analyzes documents and content from various sources",
        "input_schema": {
            "type": "object",
            "properties": {"document": {"type": "string"}},
            "required": ["document"],
        },
    },
]

# Fixed: renamed + differentiated
TOOLS_DIFFERENTIATED = [
    {
        "name": "extract_web_results",
        "description": (
            "Extract and structure results from web search output or scraped webpage content." + NL
            + "Input: raw HTML or search result text from a web URL." + NL
            + "Returns: structured list of facts, links, and publication dates." + NL
            + "Do NOT use for PDF or Word documents -- use extract_document_data for those."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Raw web page text or search result"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "extract_document_data",
        "description": (
            "Extract structured data from uploaded PDF, Word (.docx), or spreadsheet (.xlsx) documents." + NL
            + "Input: document text extracted from a file (not a URL)." + NL
            + "Returns: tables, key-value pairs, section headers, and metadata." + NL
            + "Do NOT use for web content -- use extract_web_results for URLs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "document": {"type": "string", "description": "Text extracted from a PDF/Word/Excel file"},
            },
            "required": ["document"],
        },
    },
]


# ---------------------------------------------------------------------------
# DEMO 3: Splitting a generic tool into purpose-specific tools
# ---------------------------------------------------------------------------
TOOLS_GENERIC = [
    {
        "name": "analyze_document",
        "description": "Analyze a document",
        "input_schema": {
            "type": "object",
            "properties": {"doc": {"type": "string"}, "task": {"type": "string"}},
            "required": ["doc", "task"],
        },
    },
]

# Split into three purpose-specific tools
TOOLS_SPLIT = [
    {
        "name": "extract_data_points",
        "description": (
            "Extract specific numerical data points, statistics, or key facts from a document." + NL
            + "Use when you need: numbers, dates, amounts, metrics, measurements." + NL
            + "Returns: list of {value, unit, context} objects."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"doc": {"type": "string"}},
            "required": ["doc"],
        },
    },
    {
        "name": "summarize_content",
        "description": (
            "Create a concise prose summary of a document's main points." + NL
            + "Use when you need: overview, executive summary, key themes." + NL
            + "Returns: 3-5 sentence summary preserving the document's main argument."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"doc": {"type": "string"}},
            "required": ["doc"],
        },
    },
    {
        "name": "verify_claim_against_source",
        "description": (
            "Verify whether a specific claim is supported, contradicted, or not mentioned in a document." + NL
            + "Use when: fact-checking a statement against a source document." + NL
            + "Returns: {verdict: supported|contradicted|not_found, evidence: str, confidence: float}"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "doc": {"type": "string"},
                "claim": {"type": "string", "description": "The claim to verify"},
            },
            "required": ["doc", "claim"],
        },
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Minimal vs Detailed descriptions")
    print(sep)
    requests = [
        ("Check my order #ORD-100", "order lookup"),
        ("What's my customer account C001?", "customer lookup"),
    ]
    for req, label in requests:
        result_min = test_tool_selection(TOOLS_MINIMAL, req, "minimal")
        result_det = test_tool_selection(TOOLS_DETAILED, req, "detailed")
        print(f"Request: {req}")
        print(f"  [Minimal descriptions] -> {result_min}")
        print(f"  [Detailed descriptions] -> {result_det}")
        print()

    print(sep)
    print("DEMO 2: Ambiguous overlapping tools")
    print(sep)
    overlap_req = "Analyze this web article about AI trends"
    result_ambig = test_tool_selection(TOOLS_AMBIGUOUS, overlap_req, "ambiguous")
    result_diff = test_tool_selection(TOOLS_DIFFERENTIATED, overlap_req, "differentiated")
    print(f"Request: {overlap_req}")
    print(f"  [Ambiguous]       -> {result_ambig}")
    print(f"  [Differentiated]  -> {result_diff}")

    print()
    print(sep)
    print("DEMO 3: Generic tool split into purpose-specific tools")
    print(sep)
    print("Generic tool 'analyze_document' has unclear selection when:")
    print("  - Request A: 'Extract the revenue figures from this report'")
    print("  - Request B: 'Is this article's claim about growth rates accurate?'")
    print()
    r_a = test_tool_selection(TOOLS_SPLIT, "Extract revenue figures from this financial report", "split")
    r_b = test_tool_selection(TOOLS_SPLIT, "Is the claim that revenue grew 40% supported by this report?", "split")
    print(f"Request A (extract data) -> {r_a}")
    print(f"Request B (verify claim) -> {r_b}")
    print("^ Purpose-specific tools select correctly via descriptions alone")

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Descriptions are the PRIMARY tool selection mechanism -- make them rich.")
    print("  2. Include: scope, example inputs, edge cases, and when NOT to use the tool.")
    print("  3. Ambiguous descriptions → misrouting; differentiate with distinct naming.")
    print("  4. Split generic tools into purpose-specific tools with clear contracts.")
    print("  5. Review system prompts for keyword-sensitive instructions that override descriptions.")
    print("  Mnemonic SEEB: Scope, Examples, Edge-cases, Boundaries.")
