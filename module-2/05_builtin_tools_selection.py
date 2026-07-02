"""
Domain 2 - Task 2.5: Claude Code Built-in Tool Selection

EXAM CONCEPTS:
  1. Five primary built-in tools and their correct use cases:
     Grep  → search FILE CONTENT by pattern (regex)
     Glob  → find FILE PATHS by name pattern (wildcards)
     Read  → read FULL FILE CONTENT (one file at a time)
     Edit  → targeted text replacement in a file (most efficient for small changes)
     Write → overwrite entire file (use only when creating new or full rewrite)

  2. Incremental exploration pattern:
     Glob → narrow candidates → Read targeted files
     Grep → find usage sites → Read surrounding code
     Never Read all files blindly.

  3. Tool selection traps:
     Using Read to "search" (should use Grep/Glob first)
     Using Write to make small edits (should use Edit)
     Using Glob for content search (should use Grep)
     Using Grep for file name search (should use Glob)

  4. Read+Write fallback: Use ONLY when Edit would require more than 3 separate
     replacements that interact with each other in complex ways.

  Mnemonic: GRREW
    Grep   → content search
    Read   → full file content
    Read+Write → full file rewrite (fallback only)
    Edit   → targeted replacement
    Write  → new file or complete rewrite

  Decision flowchart:
    "Do I need to find files by name?"  → Glob
    "Do I need to find text in files?"  → Grep
    "Do I need to see a full file?"     → Read
    "Do I need to change <5 locations?" → Edit
    "Do I need to create or rewrite?"   → Write

Run: uv run python 05_builtin_tools_selection.py
"""

import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Simulated built-in tool descriptions
# ---------------------------------------------------------------------------
BUILTIN_TOOL_SPECS = {
    "Grep": {
        "primary_use": "Search file CONTENT by regex pattern",
        "when_to_use": [
            "Find all occurrences of a function/class name across files",
            "Find all TODO comments in a codebase",
            "Find all files that import a specific module",
            "Find where a variable is used",
        ],
        "when_NOT_to_use": [
            "Finding files by name/extension (use Glob)",
            "Reading full file content (use Read)",
        ],
        "example_patterns": [
            "Grep('def process_refund', '*.py')",
            "Grep('import anthropic', path='src/')",
            "Grep('TODO|FIXME', '**/*.ts')",
        ],
        "returns": "Matching lines with file path and line number",
    },
    "Glob": {
        "primary_use": "Find FILE PATHS by name/extension pattern",
        "when_to_use": [
            "Find all Python files in a directory",
            "Find all test files matching *_test.py",
            "Find all config files (*.json, *.yaml)",
            "Find files with a specific prefix or suffix",
        ],
        "when_NOT_to_use": [
            "Searching file contents (use Grep)",
            "Reading file contents (use Read)",
        ],
        "example_patterns": [
            "Glob('src/**/*.py')",
            "Glob('tests/*_test.py')",
            "Glob('**/*.mcp.json')",
        ],
        "returns": "List of matching file paths",
    },
    "Read": {
        "primary_use": "Read FULL content of a specific file",
        "when_to_use": [
            "After Glob/Grep identified the target file",
            "Need to understand surrounding context of a function",
            "Need to see the full structure of a config file",
            "Need to verify what code currently does before editing",
        ],
        "when_NOT_to_use": [
            "Searching across files (use Grep first)",
            "Finding files by name (use Glob first)",
            "Making edits (follow Read with Edit, not Read again)",
        ],
        "example_patterns": [
            "Read('src/api/refunds.py')",
            "Read('pyproject.toml')",
        ],
        "returns": "Full file content with line numbers",
    },
    "Edit": {
        "primary_use": "Targeted text REPLACEMENT in a file (PREFERRED for modifications)",
        "when_to_use": [
            "Fix a bug in 1-3 specific locations",
            "Rename a variable in a known block",
            "Add/change a few lines in a known location",
            "Most code modifications (must Read first)",
        ],
        "when_NOT_to_use": [
            "Creating a new file (use Write)",
            "Complete file rewrite with many interdependent changes (use Read+Write)",
        ],
        "example_patterns": [
            "Edit(file='refunds.py', old='amount > 500', new='amount > 1000')",
            "Edit(file='config.py', old='DEBUG = True', new='DEBUG = False')",
        ],
        "returns": "Confirmation of replacement applied",
    },
    "Write": {
        "primary_use": "Create new file or COMPLETE rewrite (use sparingly)",
        "when_to_use": [
            "Creating a brand-new file that doesn't exist yet",
            "Completely replacing a file (e.g., regenerated boilerplate)",
        ],
        "when_NOT_to_use": [
            "Making targeted edits to existing files (use Edit — more efficient)",
            "Any modification where < whole file changes (use Edit)",
        ],
        "example_patterns": [
            "Write('new_module.py', content=<full content>)",
        ],
        "returns": "Confirmation of file written",
    },
}


# ---------------------------------------------------------------------------
# Scenario-based tool selection quiz (used by Claude)
# ---------------------------------------------------------------------------
SELECTION_SCENARIOS = [
    {
        "id": 1,
        "task": "Find all files that define a class named 'RefundProcessor'.",
        "correct_tool": "Grep",
        "correct_pattern": "Grep('class RefundProcessor', '**/*.py')",
        "trap": "Using Glob won't search file contents — it only matches file names.",
    },
    {
        "id": 2,
        "task": "Find all Python files in the tests/ directory.",
        "correct_tool": "Glob",
        "correct_pattern": "Glob('tests/**/*.py')",
        "trap": "Using Grep with a Python-specific pattern searches content, not file paths.",
    },
    {
        "id": 3,
        "task": "Understand the full implementation of src/billing/refunds.py.",
        "correct_tool": "Read",
        "correct_pattern": "Read('src/billing/refunds.py')",
        "trap": "Grep finds patterns but won't show surrounding context of a full module.",
    },
    {
        "id": 4,
        "task": "Change the refund limit from $500 to $1000 in refunds.py (already read).",
        "correct_tool": "Edit",
        "correct_pattern": "Edit(file='refunds.py', old='amount > 500', new='amount > 1000')",
        "trap": "Using Write would overwrite the entire file; Edit is more precise and safe.",
    },
    {
        "id": 5,
        "task": "Create a new file src/billing/credits.py that doesn't exist yet.",
        "correct_tool": "Write",
        "correct_pattern": "Write('src/billing/credits.py', content=<full content>)",
        "trap": "Edit requires the file to already exist and can't create new files.",
    },
    {
        "id": 6,
        "task": "Find all places in the codebase that call process_refund().",
        "correct_tool": "Grep",
        "correct_pattern": "Grep('process_refund\\\\(', 'src/')",
        "trap": "Glob finds file names, not function call sites within files.",
    },
]


def demonstrate_tool_selection_reasoning() -> None:
    """Ask Claude to reason through tool selection for each scenario."""
    sep = "-" * 50

    tool_choice_tool = {
        "name": "select_builtin_tool",
        "description": (
            "Select the correct Claude Code built-in tool for a given task. "
            "Available tools: Grep (content search), Glob (file path search), "
            "Read (full file content), Edit (targeted replacement), Write (new file or full rewrite)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario_id": {"type": "integer"},
                "selected_tool": {
                    "type": "string",
                    "enum": ["Grep", "Glob", "Read", "Edit", "Write"],
                },
                "example_call": {
                    "type": "string",
                    "description": "Example of how you'd call the tool.",
                },
                "reasoning": {
                    "type": "string",
                    "description": "One sentence explanation of why this tool is correct.",
                },
            },
            "required": ["scenario_id", "selected_tool", "example_call", "reasoning"],
        },
    }

    system = (
        "You are a Claude Code expert. For each task, select the MOST appropriate"
        " built-in tool." + NL
        + "Grep → content search. Glob → file path search. Read → full file content."
        + " Edit → targeted change. Write → new file or complete rewrite."
    )

    correct_count = 0
    for scenario in SELECTION_SCENARIOS:
        import json
        messages = [{
            "role": "user",
            "content": f"Task #{scenario['id']}: {scenario['task']}",
        }]
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=system,
            tools=[tool_choice_tool],
            tool_choice={"type": "tool", "name": "select_builtin_tool"},
            messages=messages,
        )
        result = None
        for block in resp.content:
            if block.type == "tool_use":
                result = block.input
                break
        if result:
            is_correct = result["selected_tool"] == scenario["correct_tool"]
            status = "CORRECT" if is_correct else "WRONG"
            if is_correct:
                correct_count += 1
            print(f"{sep}")
            print(f"Scenario {scenario['id']}: {scenario['task']}")
            print(f"  Claude selected: {result['selected_tool']} [{status}]")
            print(f"  Claude's call:   {result['example_call']}")
            print(f"  Claude's reason: {result['reasoning']}")
            if not is_correct:
                print(f"  Expected: {scenario['correct_tool']} — {scenario['correct_pattern']}")
                print(f"  Trap: {scenario['trap']}")

    print()
    print(f"Score: {correct_count}/{len(SELECTION_SCENARIOS)} correct")


# ---------------------------------------------------------------------------
# Incremental exploration pattern (static demo — no API call needed)
# ---------------------------------------------------------------------------
def show_incremental_exploration() -> None:
    sep = "-" * 50
    print(sep)
    print("INCREMENTAL EXPLORATION PATTERN (Glob → Grep → Read)")
    print()
    print("Task: 'Find where refunds are processed and understand the logic'")
    print()
    print("Step 1: Glob('**/*.py', path='src/') → find all Python source files")
    print("  Returns: ['src/api/routes.py', 'src/billing/refunds.py', 'src/utils/money.py']")
    print()
    print("Step 2: Grep('refund', 'src/') → narrow to files mentioning refund")
    print("  Returns: src/billing/refunds.py:12: def process_refund(order_id, amount)")
    print("           src/api/routes.py:45: result = process_refund(order_id, amount)")
    print()
    print("Step 3: Read('src/billing/refunds.py') → read the specific file")
    print("  Returns: Full content of refunds.py with line numbers")
    print()
    print("ANTI-PATTERN: Read all files returned by Glob without filtering first.")
    print("  If Glob returns 200 .py files, don't Read all 200.")
    print("  Use Grep to narrow, then Read only the 1-3 most relevant files.")


# ---------------------------------------------------------------------------
# Edit vs Write decision
# ---------------------------------------------------------------------------
def show_edit_vs_write() -> None:
    sep = "-" * 50
    print(sep)
    print("EDIT vs WRITE: when to use each")
    print()
    print("USE EDIT when:")
    print("  - You've read the file and know exactly what to replace")
    print("  - 1-3 targeted changes in known locations")
    print("  - More efficient (sends only the diff, not the full file)")
    print("  Example: Edit(old='MAX_REFUND = 500', new='MAX_REFUND = 1000')")
    print()
    print("USE WRITE when:")
    print("  - Creating a new file from scratch")
    print("  - > 50% of the file needs to change (full rewrite)")
    print("  - Generating boilerplate (test file, config template)")
    print("  Example: Write('tests/test_refunds.py', content=<full test suite>)")
    print()
    print("Read+Write FALLBACK (use sparingly):")
    print("  - When Edit needs > 3 separate replacements that are interdependent")
    print("  - Read the file → modify in Python → Write the full new content")
    print("  - More expensive (sends full file); prefer Edit when possible")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Built-in tool specifications (GRREW)")
    print(sep)
    for tool_name, spec in BUILTIN_TOOL_SPECS.items():
        print(f"\n{tool_name}:")
        print(f"  Primary use: {spec['primary_use']}")
        print(f"  When to use: {spec['when_to_use'][0]}")
        print(f"  Example: {spec['example_patterns'][0]}")

    print()
    print(sep)
    print("DEMO 2: Claude selects correct tools for scenarios")
    print(sep)
    demonstrate_tool_selection_reasoning()

    print()
    print(sep)
    print("DEMO 3: Incremental exploration pattern")
    print(sep)
    show_incremental_exploration()

    print()
    print(sep)
    print("DEMO 4: Edit vs Write decision guide")
    print(sep)
    show_edit_vs_write()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Grep  = content search (regex patterns inside files)")
    print("     Glob  = path search (file name/extension wildcards)")
    print("     Read  = full file content (after narrowing with Grep/Glob)")
    print("     Edit  = targeted replacement (PREFERRED for modifications)")
    print("     Write = new file or complete rewrite (use sparingly)")
    print("  2. NEVER Read many files blindly. Glob → Grep → Read 1-3 files.")
    print("  3. Edit is more efficient than Write for small changes.")
    print("  4. Read+Write fallback only for complex interdependent multi-site edits.")
    print("  Mnemonic GRREW: Grep→Read→(Read+Write)→Edit→Write")
    print("  Decision: Name? Glob. Content? Grep. Full? Read. Change? Edit. New? Write.")
