"""
Domain 3 - Task 3.2: Custom Commands & Skills

EXAM CONCEPTS:
  1. Custom slash commands (.claude/commands/*.md):
     - Simple text files defining what Claude should do when /command is invoked.
     - $ARGUMENTS: placeholder for text after the command (e.g., /review src/billing/)
     - Scoped to project when in .claude/commands/ (committed to git).
     - User-scoped when in ~/.claude/commands/ (personal, not committed).

  2. Skills (.claude/skills/<name>/SKILL.md):
     More powerful than commands — support YAML frontmatter with:
     - description: what the skill does (shown in skill list)
     - argument-hint: placeholder text shown in UI
     - allowed-tools: restrict which tools this skill can use
     - context: "fork" → runs in isolated forked session (safe for read-only exploration)

  3. context: fork — EXAM KEY CONCEPT:
     The skill runs in a copy of the current session. Changes in the fork
     do NOT affect the main session. Use for: exploratory analysis, risky operations.

  4. Scoping rules:
     Project:  .claude/commands/, .claude/skills/   → team-shared, in git
     User:     ~/.claude/commands/, ~/.claude/skills/ → personal, not in git

  5. Commands vs Skills:
     Command → simple invocation pattern, no frontmatter, plain markdown
     Skill   → rich frontmatter (allowed-tools, context, description, arg-hint)

Run: uv run python 02_explain_skills.py
"""

NL = chr(10)


# ---------------------------------------------------------------------------
# Command vs Skill comparison
# ---------------------------------------------------------------------------
COMMAND_PROPERTIES = {
    "file": ".claude/commands/<name>.md",
    "trigger": "/name [optional arguments]",
    "arguments": "$ARGUMENTS placeholder replaced with text after command",
    "frontmatter": "None — plain markdown",
    "isolation": "Runs in current session context",
    "tool_restriction": "None — can use any tool available in the session",
    "use_case": "Simple repetitive workflows (review, commit, test)",
}

SKILL_PROPERTIES = {
    "file": ".claude/skills/<name>/SKILL.md",
    "trigger": "/<name> [optional arguments]",
    "arguments": "argument-hint: shows placeholder in UI",
    "frontmatter": (
        "YAML frontmatter with: description, argument-hint, "
        "allowed-tools, context"
    ),
    "isolation": "context: fork → isolated copy of session (safe for exploration)",
    "tool_restriction": "allowed-tools: ['Glob', 'Grep', 'Read'] → restrict available tools",
    "use_case": "Complex multi-step tasks with safety constraints",
}

SCOPING_RULES = [
    {"location": ".claude/commands/review.md", "scope": "Project-scoped", "committed": True},
    {"location": ".claude/commands/commit.md", "scope": "Project-scoped", "committed": True},
    {"location": "~/.claude/commands/my-note.md", "scope": "User-scoped", "committed": False},
    {"location": ".claude/skills/analyze-codebase/SKILL.md", "scope": "Project-scoped", "committed": True},
    {"location": "~/.claude/skills/personal-tool/SKILL.md", "scope": "User-scoped", "committed": False},
]

CONTEXT_FORK_EXPLANATION = {
    "what_it_means": (
        "context: fork creates an isolated copy of the current session."
        " Changes made by the skill do NOT propagate to the main session."
    ),
    "use_when": [
        "Exploratory analysis (read codebase, don't change it)",
        "Risky multi-step operations (experiment safely)",
        "Read-only skills that should never modify files",
    ],
    "without_fork": (
        "Without context: fork, the skill runs in the current session."
        " Any file edits it makes are permanent. Use for: commit skills, refactor skills."
    ),
}


def print_command_vs_skill() -> None:
    sep = "=" * 60
    print(sep)
    print("COMMANDS vs SKILLS: feature comparison")
    print(sep)
    print()

    print("COMMANDS (.claude/commands/*.md):")
    for key, value in COMMAND_PROPERTIES.items():
        print(f"  {key:20}: {value}")

    print()
    print("SKILLS (.claude/skills/<name>/SKILL.md):")
    for key, value in SKILL_PROPERTIES.items():
        print(f"  {key:20}: {value}")

    print()
    print("WHEN TO USE COMMANDS:")
    print("  - Simple, well-defined workflow (e.g., /review, /commit)")
    print("  - No tool restrictions needed")
    print("  - Works in current session context")
    print()
    print("WHEN TO USE SKILLS:")
    print("  - Need to restrict tools (read-only exploration)")
    print("  - Need context: fork (isolated, safe)")
    print("  - Complex task with structured steps and description")


def print_scoping_rules() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print("SCOPING: project vs user")
    print(sep)
    for rule in SCOPING_RULES:
        committed = "in git" if rule["committed"] else "NOT in git (personal)"
        print(f"  {rule['location']}")
        print(f"    → {rule['scope']}, {committed}")
    print()
    print("EXAM RULE: Files in .claude/ (project root) → committed, team-shared.")
    print("           Files in ~/.claude/ → personal, not in git.")


def print_context_fork() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print("context: fork — EXAM KEY CONCEPT")
    print(sep)
    print(f"\nWhat it means: {CONTEXT_FORK_EXPLANATION['what_it_means']}")
    print()
    print("Use context: fork when:")
    for use in CONTEXT_FORK_EXPLANATION["use_when"]:
        print(f"  - {use}")
    print()
    print(f"Without context: fork: {CONTEXT_FORK_EXPLANATION['without_fork']}")


def print_frontmatter_anatomy() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print("SKILL frontmatter anatomy (YAML at top of SKILL.md)")
    print(sep)
    example = """---
description: Deeply analyze the codebase and produce architecture summary
argument-hint: "[optional: module path to focus on]"
allowed-tools: Glob, Grep, Read
context: fork
---"""
    print(example)
    print()
    print("Fields:")
    print("  description   : What this skill does (shown in /skills list)")
    print("  argument-hint : Placeholder hint shown after /skill-name in UI")
    print("  allowed-tools : Comma-separated tool names Claude may use in this skill")
    print("                  RESTRICTS to only listed tools (security boundary)")
    print("  context       : 'fork' → isolated session, omit for current session")


def print_arguments_substitution() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print("$ARGUMENTS substitution in commands")
    print(sep)
    print()
    print("In .claude/commands/review.md:")
    print("  'Review the file at $ARGUMENTS for the following...'")
    print()
    print("When user types: /review src/billing/refunds.py")
    print("  $ARGUMENTS → 'src/billing/refunds.py'")
    print("  Claude sees: 'Review the file at src/billing/refunds.py for...'")
    print()
    print("When user types: /review (no argument)")
    print("  $ARGUMENTS → '' (empty string)")
    print("  Command should handle empty $ARGUMENTS gracefully")
    print("  (e.g., 'If no path given, review the most recently edited file')")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print_command_vs_skill()
    print_scoping_rules()
    print_context_fork()
    print_frontmatter_anatomy()
    print_arguments_substitution()

    print()
    print("=" * 60)
    print("See the 02_custom_commands_skills/ folder for examples:")
    print("  commands-review.md     → /review command")
    print("  commands-commit.md     → /commit command")
    print("  skill-analyze-codebase-SKILL.md → skills with frontmatter")

    print()
    print("=" * 60)
    print("KEY TAKEAWAYS:")
    print("  1. Commands: plain .md files in .claude/commands/, triggered with /name.")
    print("     $ARGUMENTS is replaced with text after the command name.")
    print("  2. Skills: .claude/skills/<name>/SKILL.md with YAML frontmatter.")
    print("     Supports: description, argument-hint, allowed-tools, context.")
    print("  3. context: fork → skill runs in isolated session (changes don't stick).")
    print("     Use for read-only exploration or risky experimental operations.")
    print("  4. allowed-tools: restricts which tools the skill can use.")
    print("     Example: ['Glob', 'Grep', 'Read'] prevents any file modifications.")
    print("  5. Project-scoped: .claude/commands/ and .claude/skills/ (in git).")
    print("     User-scoped: ~/.claude/commands/ and ~/.claude/skills/ (personal).")
