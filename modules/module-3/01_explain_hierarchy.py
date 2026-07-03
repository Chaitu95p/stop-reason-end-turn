"""
Domain 3 - Task 3.1: CLAUDE.md Hierarchy & Context Loading

EXAM CONCEPTS:
  1. CLAUDE.md hierarchy (applied in this order, all active simultaneously):
     ~/.claude/CLAUDE.md        → user-level (personal, not committed to git)
     <project-root>/CLAUDE.md   → project-level (committed to git, team-shared)
     <subdir>/CLAUDE.md         → subdirectory-level (applies when in that dir)

  2. All active CLAUDE.md files are combined — subdirectory does NOT replace
     project-level. All three levels are merged and applied together.

  3. @import syntax: reference other files to inject their content.
     @src/billing/refunds.py → inlines refunds.py into the context.
     Use for: key source files, error definitions, architectural docs.

  4. .claude/rules/ directory: path-specific rules with YAML frontmatter
     (covered in Task 3.3). Rules apply only to matched file paths.

  5. What to put in each level:
     User-level:   personal workflow preferences, tool defaults, style
     Project-level: stack, conventions, important constants, import refs
     Subdir-level: module-specific rules, file inventory, local test commands

Run: uv run python 01_explain_hierarchy.py
"""

NL = chr(10)


# ---------------------------------------------------------------------------
# CLAUDE.md hierarchy explanation
# ---------------------------------------------------------------------------
HIERARCHY = [
    {
        "level": "User-level",
        "path": "~/.claude/CLAUDE.md",
        "scope": "ALL Claude Code sessions on this machine",
        "committed_to_git": False,
        "example_content": [
            "Personal communication style (concise, no emojis)",
            "Never auto-commit; always show diff first",
            "Prefer Edit over Write",
            "Personal package manager: uv",
        ],
    },
    {
        "level": "Project-level",
        "path": "<project-root>/CLAUDE.md",
        "scope": "All sessions in this project",
        "committed_to_git": True,
        "example_content": [
            "Tech stack (Python 3.12, FastAPI, PostgreSQL)",
            "Important constants ($500 refund limit)",
            "@import key source files",
            "Pre-change checklist (run tests, update CHANGELOG)",
        ],
    },
    {
        "level": "Subdirectory-level",
        "path": "<subdir>/CLAUDE.md (e.g. src/billing/CLAUDE.md)",
        "scope": "Sessions with focus on that subdirectory",
        "committed_to_git": True,
        "example_content": [
            "Module-specific coding rules",
            "File inventory (what each file in this dir does)",
            "Local test command for this module",
            "Domain-specific constraints (never use int for money)",
        ],
    },
]

IMPORT_SYNTAX = [
    {"syntax": "@src/billing/refunds.py", "effect": "Inlines full content of refunds.py into context"},
    {"syntax": "@src/errors.py", "effect": "Inlines all custom error class definitions"},
    {"syntax": "@docs/architecture.md", "effect": "Inlines architecture documentation"},
    {"syntax": "@.claude/rules/api-conventions.md", "effect": "Inlines API conventions rule file"},
]

RULES_DIR = {
    "location": "<project-root>/.claude/rules/",
    "purpose": "Path-specific rules with YAML frontmatter (see Task 3.3)",
    "example_files": [
        "api-conventions.md  → paths: ['src/api/**/*']",
        "test-conventions.md → paths: ['**/*.test.*', '**/*_test.py']",
        "terraform.md        → paths: ['**/*.tf']",
    ],
}


def print_hierarchy_explanation() -> None:
    sep = "=" * 60
    print(sep)
    print("CLAUDE.md HIERARCHY (all levels apply simultaneously)")
    print(sep)
    for level in HIERARCHY:
        print(f"\n{level['level']} — {level['path']}")
        print(f"  Scope: {level['scope']}")
        print(f"  Committed to git: {level['committed_to_git']}")
        print(f"  What to put here:")
        for item in level["example_content"]:
            print(f"    - {item}")

    print()
    sep2 = "-" * 50
    print(sep2)
    print("KEY RULE: All active CLAUDE.md files are MERGED, not overridden.")
    print("  Subdirectory CLAUDE.md ADDS context on top of project-level.")
    print("  Subdirectory CLAUDE.md does NOT replace project-level.")
    print()
    print("Loading order (all applied together):")
    print("  1. ~/.claude/CLAUDE.md (user-level, personal)")
    print("  2. <project-root>/CLAUDE.md (project-level, team-shared)")
    print("  3. <subdir>/CLAUDE.md (subdirectory-level, if present)")


def print_import_syntax() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print("@import SYNTAX: inject file content into context")
    print(sep)
    for item in IMPORT_SYNTAX:
        print(f"  {item['syntax']}")
        print(f"    → {item['effect']}")
    print()
    print("Use @import for: key source files, error definitions, architecture docs.")
    print("Avoid @import for: large files (>500 lines) — prefer summaries instead.")


def print_rules_dir() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print(".claude/rules/ DIRECTORY: path-specific rules")
    print(sep)
    print(f"  Location: {RULES_DIR['location']}")
    print(f"  Purpose: {RULES_DIR['purpose']}")
    print(f"  Example files:")
    for f in RULES_DIR["example_files"]:
        print(f"    {f}")
    print()
    print("  Rules are only active when working in matching file paths.")
    print("  See 01_claude_md_hierarchy/03_path_specific_rules/ for examples.")


def compare_user_vs_project() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print("USER-LEVEL vs PROJECT-LEVEL — what goes where")
    print(sep)
    print()
    print("  USER-LEVEL (~/.claude/CLAUDE.md) — personal, NOT in git:")
    print("    ✓ Personal communication style preferences")
    print("    ✓ Tool defaults (uv, pytest, etc.)")
    print("    ✓ Never auto-commit rules")
    print("    ✗ NOT: project constants (wrong place — other devs won't see)")
    print("    ✗ NOT: stack info (wrong place — varies per project)")
    print()
    print("  PROJECT-LEVEL (<root>/CLAUDE.md) — in git, team-shared:")
    print("    ✓ Tech stack, framework versions")
    print("    ✓ Important constants (refund limits, API endpoints)")
    print("    ✓ @import for key source files")
    print("    ✓ Pre-change checklists")
    print("    ✗ NOT: personal style preferences (wrong place — overrides team)")
    print()
    print("  EXAM TIP: If a developer on a different machine needs the rule")
    print("  to apply → project-level. If it's personal to you → user-level.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("DEMO: CLAUDE.md Hierarchy, @import, and .claude/rules/")
    print(sep)

    print_hierarchy_explanation()
    print_import_syntax()
    print_rules_dir()
    compare_user_vs_project()

    print()
    print(sep)
    print("See the 01_claude_md_hierarchy/ folder for example files:")
    print("  user-level-CLAUDE.md      → personal preferences")
    print("  project-level-CLAUDE.md   → team-shared project conventions")
    print("  subdirectory-level-CLAUDE.md → module-specific rules")

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Three CLAUDE.md levels: user → project → subdirectory.")
    print("     All three are MERGED (additive), not overridden.")
    print("  2. User-level: personal, never committed to git.")
    print("     Project-level: team-shared, committed to git.")
    print("     Subdirectory-level: module-specific additions.")
    print("  3. @import syntax: inline file content into context.")
    print("     Best for key source files and error definitions.")
    print("  4. .claude/rules/: path-specific rules with YAML frontmatter.")
    print("     Only active for files matching the paths: pattern.")
    print("  5. Rule: 'Other devs need this?' → project-level. 'Just me?' → user-level.")
