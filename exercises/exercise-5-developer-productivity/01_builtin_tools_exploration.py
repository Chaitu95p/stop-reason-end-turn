"""
Exercise 5 - Steps 1-2: Built-in Tools for Codebase Exploration

EXAM CONCEPTS:
  1. Built-in tool selection:
       Grep  -> search FILE CONTENTS for patterns (function names, error
                messages, import statements, callers of a function)
       Glob  -> search FILE PATHS by name or extension  (**/*.test.tsx)
       Read  -> load full file contents; follow imports to trace flows
       Edit  -> targeted modification using unique text matching (preferred)
       Write -> full-file replacement; fallback when Edit anchor is not unique
       Bash  -> shell commands for everything else

  2. Incremental codebase exploration:
       START with Grep to find entry points
       FOLLOW imports with Read to trace flows
       NEVER read all files upfront -- context bloat, token waste

  3. Edit-vs-Write decision:
       Edit  -> unique anchor text exists  (preferred: sends only the diff)
       Write -> duplicate anchor or brand-new file  (reliable fallback)

  4. Grep vs Glob distinction (EXAM COMMON TRAP):
       "Find all callers of process_payment()"  -> Grep  (content search)
       "Find all test files"                    -> Glob  (path pattern)
       Students confuse Grep and Glob; both find things -- different axes.

  Mnemonic: GRIGG
    Grep for file Contents, Glob for file Paths
    Read follows imports incrementally
    Incremental discovery > upfront bulk-read
    Go Grep->Read, not Read-then-Grep
    Guide Edit with unique anchors; fallback to Write

Run: uv run python 01_builtin_tools_exploration.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)

# ---------------------------------------------------------------------------
# Simulated codebase (in-memory mock -- no real filesystem I/O)
# ---------------------------------------------------------------------------
MOCK_FILES = {
    "src/payments/processor.py": (
        "def process_payment(order_id, amount):" + NL
        + "    customer = get_customer(order_id)" + NL
        + "    return charge_card(customer, amount)" + NL
    ),
    "src/payments/refund.py": (
        "from payments.processor import process_payment" + NL
        + "def issue_refund(order_id, amount):" + NL
        + "    return process_payment(order_id, -amount)" + NL
    ),
    "src/orders/lookup.py": (
        "def get_order(order_id):" + NL
        + "    return ORDER_DB.get(order_id, {})" + NL
    ),
    "tests/test_processor.py": (
        "from payments.processor import process_payment" + NL
        + "def test_process_payment_success(): ..." + NL
    ),
    "tests/test_refund.py": (
        "from payments.refund import issue_refund" + NL
        + "def test_issue_refund_success(): ..." + NL
    ),
    "src/utils/logger.py": (
        "import logging" + NL
        + "def log_event(event, data): ..." + NL
    ),
}


def mock_grep(pattern: str, path: str = ".") -> dict:
    """Search file CONTENTS for a pattern."""
    matches = []
    for fpath, content in MOCK_FILES.items():
        if path != "." and not fpath.startswith(path):
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if pattern.lower() in line.lower():
                matches.append({"file": fpath, "line": i, "text": line.strip()})
    return {"matches": matches, "count": len(matches)}


def mock_glob(pattern: str) -> dict:
    """Search FILE PATHS by name/extension pattern."""
    import fnmatch
    matched = [p for p in MOCK_FILES if fnmatch.fnmatch(p, pattern)]
    return {"files": matched, "count": len(matched)}


def mock_read(file_path: str) -> dict:
    """Read full file contents."""
    if file_path in MOCK_FILES:
        return {"content": MOCK_FILES[file_path], "lines": len(MOCK_FILES[file_path].splitlines())}
    return {"error": f"File not found: {file_path}"}


def mock_edit(file_path: str, old_text: str, new_text: str) -> dict:
    """Targeted edit using unique anchor text."""
    if file_path not in MOCK_FILES:
        return {"success": False, "error": "File not found"}
    content = MOCK_FILES[file_path]
    count = content.count(old_text)
    if count == 0:
        return {"success": False, "error": "Anchor text not found -- use Write instead"}
    if count > 1:
        return {"success": False, "error": f"Anchor not unique ({count} matches) -- provide more context"}
    MOCK_FILES[file_path] = content.replace(old_text, new_text, 1)
    return {"success": True, "message": "Edit applied"}


TOOLS = [
    {
        "name": "grep",
        "description": (
            "Search FILE CONTENTS across the codebase for a text pattern. "
            "Use for: finding all callers of a function, locating error messages, "
            "finding import statements, tracing function usage. "
            "NOT for finding files by name -- use glob for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Text or regex to search for"},
                "path":    {"type": "string", "description": "Directory to search (default '.')"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "glob",
        "description": (
            "Search for FILES by NAME or EXTENSION pattern. "
            "Use for: 'find all test files' (**/*.test.py), "
            "'find all TypeScript files' (**/*.ts), 'find all configs' (**/config.*). "
            "NOT for searching inside files -- use grep for content search."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern e.g. **/*.test.py"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read the full contents of a specific file. "
            "Use AFTER grep/glob identifies the relevant file. "
            "Avoid reading files speculatively -- only read what grep/glob identified."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Apply a targeted edit to a file by replacing unique anchor text. "
            "Preferred over write_file when the change is small and the anchor is unique. "
            "Returns an error if anchor text appears more than once -- use write_file as fallback."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "old_text":  {"type": "string", "description": "Unique text to replace"},
                "new_text":  {"type": "string", "description": "Replacement text"},
            },
            "required": ["file_path", "old_text", "new_text"],
        },
    },
]

TOOL_MAP = {
    "grep":      lambda inp: mock_grep(inp.get("pattern", ""), inp.get("path", ".")),
    "glob":      lambda inp: mock_glob(inp.get("pattern", "**/*")),
    "read_file": lambda inp: mock_read(inp.get("file_path", "")),
    "edit_file": lambda inp: mock_edit(
        inp.get("file_path", ""), inp.get("old_text", ""), inp.get("new_text", "")
    ),
}


def run_developer_agent(task: str) -> str:
    """Run an agentic loop for a developer productivity task."""
    messages = [{"role": "user", "content": task}]
    system = (
        "You are a developer productivity agent helping engineers explore a Python codebase." + NL
        + "Exploration strategy:" + NL
        + "  1. Use grep to find entry points (function definitions, imports)." + NL
        + "  2. Use read_file to follow imports and understand a specific file." + NL
        + "  3. Use glob to find files by pattern when you need to discover ALL of a type." + NL
        + "  4. Never read files speculatively -- only read what grep/glob identified." + NL
        + "  5. When editing: try edit_file first; if anchor is not unique, use write_file."
    )
    while True:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=TOOLS,
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
                    result = fn(block.input) if fn else {"error": f"unknown tool {block.name}"}
                    print(f"  Tool: {block.name}({block.input}) -> {result}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
            messages.append({"role": "user", "content": results})
        else:
            return f"(unexpected stop_reason: {resp.stop_reason})"


# ---------------------------------------------------------------------------
# DEMO 1: Grep -> Read incremental exploration (correct pattern)
# ---------------------------------------------------------------------------
def demo_incremental_exploration() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 1: Incremental exploration -- Grep -> Read")
    print("Task: 'Find all callers of process_payment and show me where it is defined'")
    print()
    result = run_developer_agent(
        "Find all callers of process_payment() in the codebase "
        "and show me where it is defined."
    )
    print()
    print("Agent response:", result[:400])


# ---------------------------------------------------------------------------
# DEMO 2: Glob for file discovery (correct pattern for path-based search)
# ---------------------------------------------------------------------------
def demo_glob_file_discovery() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 2: Glob for test file discovery")
    print("Task: 'List all test files in the codebase'")
    print()
    result = run_developer_agent(
        "List all test files in the codebase."
    )
    print()
    print("Agent response:", result[:400])


# ---------------------------------------------------------------------------
# ANTI-PATTERN: Using Read on all files upfront (context waste)
# ---------------------------------------------------------------------------
def antipattern_bulk_read() -> None:
    sep = "-" * 50
    print(sep)
    print("ANTI-PATTERN: Bulk-reading all files before understanding the task")
    print("  Problem: Wastes context tokens reading irrelevant files.")
    print("  Exam trap: 'Read every .py file to understand the codebase' is WRONG.")
    print("  Correct:   Grep entry points -> Read only relevant files.")
    files = list(MOCK_FILES.keys())
    total_lines = sum(len(c.splitlines()) for c in MOCK_FILES.values())
    print(f"  If all {len(files)} files were read upfront: {total_lines} lines of context consumed.")
    print("  With Grep->Read: typically 1-2 files read per targeted task.")


if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("DEMO 1: Incremental exploration (Grep -> Read)")
    print(sep)
    demo_incremental_exploration()

    print()
    print(sep)
    print("DEMO 2: Glob for file-path discovery")
    print(sep)
    demo_glob_file_discovery()

    print()
    print(sep)
    print("ANTI-PATTERN: Bulk-read all files upfront")
    print(sep)
    antipattern_bulk_read()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Grep searches file CONTENTS; Glob searches file PATHS -- never swap them.")
    print("  2. Incremental pattern: Grep entry points -> Read only relevant files.")
    print("  3. Edit needs unique anchor text; Write is the reliable fallback.")
    print("  4. Reading all files upfront wastes context; discover incrementally.")
    print("  5. For codebase exploration: Grep for function callers, Glob for file types.")
    print("  Mnemonic GRIGG: Grep=Contents, Glob=Paths, Read incrementally,")
    print("    Incremental>bulk, Guide Edit with unique anchors.")
