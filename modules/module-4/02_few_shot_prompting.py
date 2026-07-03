"""
Module 3 - Task 4.2: Few-Shot Prompting for Consistency

EXAM CONCEPTS:
  Few-shot (2-5 examples): most effective technique for consistent output.
  Many-shot (10+): complex classification with subtle nuances, 200K context.

  Mnemonic FADE -- when few-shot beats instructions alone:
    Format inconsistency
    Ambiguous edge cases
    Decision boundaries unclear
    Extraction from varied documents

  The exam tests three specific uses of few-shot:
    (a) Code review -- decision boundary (TRUE positive, TRUE negative, edge case)
    (b) Tool selection -- ambiguous requests, choosing among multiple tools
    (c) Extraction -- varied document structures, empty/null field handling

Run: uv run python 02_few_shot_prompting.py
"""

import json
import anthropic

client = anthropic.Anthropic()

# ============================================================
# PART A: Code review -- decision boundary examples
# ============================================================

NL = chr(10)  # newline -- used to build strings without triggering bash heredoc issues

FEW_SHOT_EXAMPLES = [
    # TRUE POSITIVE: comment says X, code does Y
    {
        "code": "# Rounds result to 2 decimal places" + NL + "result = round(value, 3)",
        "expected": "ISSUE | Line 2 | Comment says 2 decimal places but code uses 3. | bug",
    },
    # TRUE NEGATIVE: imprecise wording but not wrong (exam: include this to reduce false positives)
    {
        "code": "# Validates user input" + NL + "if not data or len(data) > 1000:" + NL + "    raise ValueError('Invalid')",
        "expected": "OK | No mismatch. Comment says validates which is broad but accurate.",
    },
    # TRUE POSITIVE: security severity
    {
        "code": "# Hashes password with MD5 for storage" + NL + "return hashlib.md5(password.encode()).hexdigest()",
        "expected": "ISSUE | Line 2 | Comment accurately describes MD5, but MD5 is broken for passwords. | security",
    },
]


def build_code_review_system() -> str:
    examples_text = ""
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        examples_text += f"Example {i}:" + NL
        examples_text += "Code:" + NL + "```python" + NL + ex["code"] + NL + "```" + NL
        examples_text += "Output: " + ex["expected"] + NL + NL
    return (
        "You are a code reviewer checking comment-code mismatches." + NL + NL
        + "Output format:" + NL
        + "  ISSUE | Line <n> | <description> | <severity: bug|security>" + NL
        + "  OK    | <reason no issue>" + NL + NL
        + examples_text
        + "Apply the same judgment shown above. Flag only genuine mismatches."
    )


INSTRUCTION_ONLY_SYSTEM = (
    "You are a code reviewer. Check if code comments accurately describe behavior." + NL
    + "Output either ISSUE or OK with a brief reason."
)

CODE_REVIEW_CASES = [
    {
        "label": "True positive (obvious mismatch)",
        "code": "# Returns the maximum of two numbers" + NL + "def get_min(a, b):" + NL + "    return min(a, b)",
    },
    {
        "label": "True negative (vague but acceptable)",
        "code": "# Processes the request" + NL + "def handle(req):" + NL + "    req.body = req.body.strip()" + NL + "    return req",
    },
    {
        "label": "Edge case (comment technically correct but misleading)",
        "code": "# Sorts the list" + NL + "def order(items):" + NL + "    return sorted(items, reverse=True)",
    },
]


# ============================================================
# PART B: Tool selection -- ambiguous request examples
# (FADE: Ambiguous edge cases, Decision boundaries unclear)
# ============================================================

TOOL_SELECTION_TOOLS = [
    {
        "name": "search_docs",
        "description": "Search internal documentation and knowledge base articles.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "query_database",
        "description": "Run a SQL query against the production database for live data.",
        "input_schema": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
    },
    {
        "name": "create_ticket",
        "description": "Create a support or engineering ticket for tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["title", "description"],
        },
    },
]

# Few-shot examples teach TOOL SELECTION JUDGMENT for ambiguous requests.
# Without examples, "how many users signed up last month" might incorrectly use search_docs.
TOOL_SELECTION_SYSTEM = (
    "You are a support agent assistant. Choose the RIGHT tool for each request." + NL + NL
    + 'Example 1: "What does the onboarding flow look like?"' + NL
    + "  -> search_docs (asking about a process, not live data)" + NL + NL
    + 'Example 2: "How many users signed up in the last 7 days?"' + NL
    + "  -> query_database (asking for live metrics, not documentation)" + NL + NL
    + 'Example 3: "The login page is broken for enterprise users"' + NL
    + "  -> create_ticket (reporting an incident that needs tracking)" + NL + NL
    + 'Example 4: "What is our SLA for P1 incidents?"  [AMBIGUOUS]' + NL
    + "  -> search_docs (policy questions live in docs, even if data exists in DB)" + NL + NL
    + "Apply this judgment to new requests. Always pick the most specific tool."
)


# ============================================================
# PART C: Extraction -- varied document structures + null handling
# (FADE: Extraction from varied documents, Format inconsistency)
# ============================================================

EXTRACT_TOOL = {
    "name": "extract_citation",
    "description": "Extract citation details from a research document excerpt.",
    "input_schema": {
        "type": "object",
        "properties": {
            "authors": {"type": "array", "items": {"type": "string"}},
            "year": {"type": ["integer", "null"]},
            "title": {"type": ["string", "null"]},
            "journal": {"type": ["string", "null"]},
            "doi": {"type": ["string", "null"]},
        },
        "required": ["authors"],
    },
}

# Few-shot handles varied document structures.
# Without examples, inline citation "(Smith 2020)" might produce empty authors[].
EXTRACTION_SYSTEM = (
    "Extract citation details from research documents." + NL + NL
    + "Example 1 (bibliography format):" + NL
    + "  Text: Smith, J., Lee, K. (2020). Deep learning for NLP. J. of AI. DOI: 10.1/j" + NL
    + '  Output: authors=["J. Smith", "K. Lee"], year=2020, title="Deep learning for NLP",' + NL
    + '           journal="Journal of AI", doi="10.1/j"' + NL + NL
    + "Example 2 (inline narrative citation -- partial data is CORRECT):" + NL
    + "  Text: As demonstrated by Chen et al. (2019), transformer architectures excel at..." + NL
    + '  Output: authors=["Chen et al."], year=2019, title=null, journal=null, doi=null' + NL + NL
    + "Example 3 (embedded reference, no formal citation):" + NL
    + "  Text: Following the approach described in the seminal work on BERT..." + NL
    + '  Output: authors=[], year=null, title="BERT (inferred)", journal=null, doi=null' + NL + NL
    + "Key rules:" + NL
    + "  - Never fabricate values. Use null when information is absent." + NL
    + "  - For inline citations, partial data is correct -- do not hallucinate a full title." + NL
    + '  - For "et al." lists, use ["Author et al."] as the authors array.'
)


def run_review(system: str, code: str) -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": "Review:" + NL + "```python" + NL + code + NL + "```"}],
    )
    return resp.content[0].text.strip()


def run_tool_selection(user_request: str) -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=128,
        system=TOOL_SELECTION_SYSTEM,
        tools=TOOL_SELECTION_TOOLS,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_request}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return f"Tool: {block.name} | Args: {block.input}"
    return "No tool called"


def run_extraction(doc: str) -> dict:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=EXTRACTION_SYSTEM,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "extract_citation"},
        messages=[{"role": "user", "content": "Extract citation from: " + doc}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    return {}


if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("PART A: Code Review -- Decision Boundary via Few-Shot")
    print(sep)
    few_shot_system = build_code_review_system()
    for tc in CODE_REVIEW_CASES:
        out_base = run_review(INSTRUCTION_ONLY_SYSTEM, tc["code"])
        out_few = run_review(few_shot_system, tc["code"])
        print()
        print("Test: " + tc["label"])
        print("  [No examples] : " + out_base)
        print("  [Few-shot]    : " + out_few)

    print()
    print(sep)
    print("PART B: Tool Selection -- Few-Shot for Ambiguous Requests")
    print(sep)
    for req in [
        "How many orders were placed today?",
        "What is our refund policy?",
        "Users cannot log in after the latest deploy",
    ]:
        result = run_tool_selection(req)
        print("  Request: " + req)
        print("  -> " + result)
        print()

    print(sep)
    print("PART C: Extraction -- Varied Document Structures + Null Handling")
    print(sep)
    for doc in [
        "Smith, J., Jones, B. (2021). Efficient transformers. NeurIPS. DOI: 10.5555/123",
        "As noted by Wang et al. (2022), the model performance plateaus...",
        "Following techniques from the original attention paper...",
    ]:
        result = run_extraction(doc)
        print("  Doc: " + doc[:60] + "...")
        print("  -> " + json.dumps(result))
        print()

    print("KEY TAKEAWAY:")
    print("  Few-shot examples teach judgment, not just format.")
    print("  Use for: code review decisions, tool selection, varied-format extraction.")
    print("  Always include TRUE NEGATIVE examples to reduce false positives.")
    print("  Mnemonic FADE: Format/Ambiguous/Decision/Extraction.")
