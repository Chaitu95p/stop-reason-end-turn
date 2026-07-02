"""
Domain 3 - Task 3.3: Path-Specific Rules (.claude/rules/)

EXAM CONCEPTS:
  1. .claude/rules/ directory: markdown files with YAML frontmatter.
     Each file's rules only apply when Claude is working with files
     matching the paths: pattern.

  2. YAML frontmatter syntax:
     ---
     paths:
       - "src/api/**/*"       (applies to all files under src/api/)
       - "**/*.test.py"       (applies to any test file)
       - "terraform/**/*"     (applies to all Terraform files)
     ---

  3. Rule file content (below the frontmatter):
     Markdown text describing conventions for matched files.
     Same format as CLAUDE.md but path-scoped.

  4. Why path-specific rules:
     - Project CLAUDE.md would get too long with all conventions.
     - Rules that don't apply everywhere clutter the context needlessly.
     - Developers in src/api/ don't need Terraform rules (and vice versa).

  5. Rule file location: .claude/rules/<name>.md (committed to git).
     Rules are project-scoped — no user-level path-specific rules.

Run: uv run python 03_explain_rules.py
"""

NL = chr(10)


# ---------------------------------------------------------------------------
# Rules directory explanation
# ---------------------------------------------------------------------------
RULE_FILES = [
    {
        "file": ".claude/rules/api-conventions.md",
        "paths": ["src/api/**/*"],
        "description": "Route handler rules: no business logic in routes, auth scopes, OpenAPI docs",
        "active_for": ["src/api/routes/refunds.py", "src/api/routes/credits.py"],
        "NOT_active_for": ["src/billing/refunds.py", "tests/test_refunds.py"],
    },
    {
        "file": ".claude/rules/test-conventions.md",
        "paths": ["tests/**/*.py", "**/*_test.py", "**/*.test.py"],
        "description": "Test naming, fixture patterns, coverage requirements (80%), mock rules",
        "active_for": ["tests/test_refunds.py", "tests/test_credits.py"],
        "NOT_active_for": ["src/billing/refunds.py", "src/api/routes/refunds.py"],
    },
    {
        "file": ".claude/rules/terraform-conventions.md",
        "paths": ["**/*.tf", "**/*.tfvars", "terraform/**/*"],
        "description": "Module structure, naming patterns, safety rules (no -auto-approve in prod)",
        "active_for": ["terraform/environments/prod/main.tf", "terraform/modules/rds/main.tf"],
        "NOT_active_for": ["src/billing/refunds.py", "tests/test_refunds.py"],
    },
]

FRONTMATTER_EXAMPLE = """---
paths:
  - "src/api/**/*"
---

# API Layer Conventions

## Route handler rules
- Route handlers must NOT contain business logic.
- Every route must have Depends(get_auth) for authentication.
..."""

GLOB_PATTERN_GUIDE = [
    {"pattern": "src/api/**/*", "matches": "All files recursively under src/api/"},
    {"pattern": "**/*.py",      "matches": "All Python files in the entire project"},
    {"pattern": "**/*_test.py", "matches": "Python files ending in _test.py anywhere"},
    {"pattern": "terraform/**/*", "matches": "All files recursively under terraform/"},
    {"pattern": "*.json",       "matches": "JSON files in the root directory only (NOT recursive)"},
    {"pattern": "**/*.json",    "matches": "JSON files anywhere in the project"},
]


def print_rules_overview() -> None:
    sep = "=" * 60
    print(sep)
    print(".claude/rules/ DIRECTORY: path-specific rules")
    print(sep)
    print()
    print("Location: <project-root>/.claude/rules/")
    print("Format: Markdown files with YAML frontmatter (paths: pattern)")
    print("Scope: Project-scoped, committed to git")
    print()
    print("How it works:")
    print("  1. Claude reads which files you're working with.")
    print("  2. For each rule file, checks if any file matches the paths: pattern.")
    print("  3. If matched → rule content is injected into context.")
    print("  4. If not matched → rule file is ignored (saves context tokens).")


def print_rule_files() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print("RULE FILE EXAMPLES")
    print(sep)
    for rule in RULE_FILES:
        print()
        print(f"File: {rule['file']}")
        print(f"  Paths: {rule['paths']}")
        print(f"  Content: {rule['description']}")
        print(f"  Active for:     {rule['active_for']}")
        print(f"  NOT active for: {rule['NOT_active_for']}")


def print_frontmatter() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print("FRONTMATTER SYNTAX")
    print(sep)
    print(FRONTMATTER_EXAMPLE)
    print()
    print("Key: The '---' block is YAML frontmatter.")
    print("     Content BELOW the closing '---' is the rule text.")


def print_glob_patterns() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print("GLOB PATTERN GUIDE (for paths: values)")
    print(sep)
    for item in GLOB_PATTERN_GUIDE:
        print(f"  {item['pattern']:30} → {item['matches']}")
    print()
    print("EXAM TIP: ** matches any directory depth. * matches within one directory.")
    print("  'src/api/**/*'  → recursive under src/api/")
    print("  'src/api/*'     → only direct children of src/api/ (not recursive)")


def print_why_path_specific() -> None:
    sep = "-" * 50
    print()
    print(sep)
    print("WHY PATH-SPECIFIC RULES (not just in CLAUDE.md)")
    print(sep)
    print()
    print("Problem with putting everything in project CLAUDE.md:")
    print("  - File becomes very long (200+ lines) and hard to maintain")
    print("  - Terraform conventions injected even when working on Python files")
    print("  - Test conventions injected even when editing API routes")
    print("  - Irrelevant context wastes context window tokens")
    print()
    print("Solution: path-specific rules in .claude/rules/")
    print("  - API conventions ONLY active when touching src/api/ files")
    print("  - Test conventions ONLY active when touching test files")
    print("  - Terraform rules ONLY active when touching .tf files")
    print("  - Each rule file stays focused and maintainable")
    print()
    print("ANALOGY: Like .gitignore patterns — specify which files each rule applies to.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print_rules_overview()
    print_rule_files()
    print_frontmatter()
    print_glob_patterns()
    print_why_path_specific()

    print()
    print("=" * 60)
    print("See the 03_path_specific_rules/ folder for example rule files:")
    print("  api-conventions.md      → paths: src/api/**/*")
    print("  test-conventions.md     → paths: tests/**/*.py, **/*_test.py")
    print("  terraform-conventions.md → paths: **/*.tf, terraform/**/*")

    print()
    print("=" * 60)
    print("KEY TAKEAWAYS:")
    print("  1. .claude/rules/<name>.md: YAML frontmatter + markdown content.")
    print("     Rules are injected ONLY when working with matching file paths.")
    print("  2. paths: uses glob patterns: ** = any depth, * = any name.")
    print("     'src/api/**/*' → all files recursively under src/api/.")
    print("  3. Path-specific rules keep project CLAUDE.md short and focused.")
    print("     Irrelevant rules are NOT injected → saves context window tokens.")
    print("  4. Location: .claude/rules/ (project-scoped, committed to git).")
    print("     No user-level path-specific rules — only project-level.")
    print("  5. Content below the frontmatter '---' is identical to CLAUDE.md format.")
