---
paths:
  - "module-3/01_claude_md_hierarchy/*.md"
  - "module-3/02_custom_commands_skills/*.md"
  - "module-3/03_path_specific_rules/*.md"
---

# Config Example File Conventions

These rules apply to the Markdown files inside module-3's example subdirectories.
These files are PEDAGOGICAL DEMONSTRATIONS of Claude Code config concepts —
they are NOT the real project config (which lives in `.claude/` at the repo root).

## Purpose of each subdirectory

- `01_claude_md_hierarchy/` — shows the three CLAUDE.md levels (user/project/subdirectory)
- `02_custom_commands_skills/` — shows command `.md` format and skill SKILL.md frontmatter
- `03_path_specific_rules/` — shows `.claude/rules/` YAML frontmatter + path patterns

## Required header comment

Every file in these directories must start with a comment explaining its pedagogical role:

```markdown
# <Real config file path this represents>
# <One sentence: what this file demonstrates>
```

Examples:
```markdown
# .claude/commands/review.md
# Demonstrates: custom slash command format with $ARGUMENTS substitution
```

```markdown
# src/billing/CLAUDE.md  (subdirectory-level)
# Demonstrates: module-specific rules that augment (not replace) project-level CLAUDE.md
```

## Rule files in 03_path_specific_rules/

Files that represent `.claude/rules/` entries MUST include YAML frontmatter:
```yaml
---
paths:
  - "glob/pattern/**/*"
---
```

The `paths:` values must be realistic globs matching the file type being described
(e.g., `src/api/**/*` for API conventions, `**/*.tf` for Terraform).

## Editing guidelines

- These are examples for exam study — keep them aligned with what Claude Code actually supports.
- Do not simplify frontmatter away; it is the key learning element.
- If adding a new example file, give it a realistic name that matches what it represents
  (e.g., `commands-deploy.md` for a `/deploy` command example).
- Do not add real credentials, tokens, or connection strings in examples —
  use `${ENV_VAR}` placeholders as shown in the existing files.
