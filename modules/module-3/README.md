# Module 3 — Claude Code Configuration & Workflows

**Exam domain weight: 20%**

Covers how Claude Code is configured via CLAUDE.md hierarchy, custom commands, skills, path-scoped rules, plan mode, iterative refinement, and CI/CD integration.

## Scripts

| Script | Task | Key concept |
|--------|------|-------------|
| `01_explain_hierarchy.py` | 3.1 CLAUDE.md Hierarchy | User → project → directory loading order; override semantics |
| `02_explain_skills.py` | 3.2 Custom Commands & Skills | `context: fork`; `allowed-tools`; `argument-hint` frontmatter |
| `03_explain_rules.py` | 3.3 Path-Specific Rules | `.claude/rules/` files with YAML `paths:` glob frontmatter |
| `04_plan_vs_direct.py` | 3.4 Plan Mode vs Direct Execution | When plan mode triggers; multi-file and architectural thresholds |
| `05_iterative_refinement.py` | 3.5 Iterative Refinement | Checkpoint patterns; progressive elaboration |
| `06_cicd_integration.py` | 3.6 CI/CD Integration | Non-interactive flags; `--output-format json`; exit codes |

## Config example subdirectories

These directories contain pedagogical config file examples for the exam — **not** the real project config (which lives in `.claude/` at the repo root):

- `01_claude_md_hierarchy/` — CLAUDE.md at user / project / subdirectory levels
- `02_custom_commands_skills/` — command `.md` and skill `SKILL.md` frontmatter
- `03_path_specific_rules/` — `.claude/rules/` files with YAML `paths:` frontmatter

## Run

```bash
# All scripts in order
cd modules/module-3 && for f in 0*.py; do echo "=== $f ===" && uv run python "$f"; done

# Single script
uv run python 01_explain_hierarchy.py
```

## Key exam facts

- **CLAUDE.md load order:** user (`~/.claude/CLAUDE.md`) → project root → subdirectory. Each level can extend or override the previous.
- **Skill frontmatter:** `context: fork` runs the skill in an isolated subagent; `allowed-tools` restricts which tools the skill can use; `argument-hint` describes expected input.
- **`.claude/rules/` files** are injected only when the active file matches the `paths:` glob — not globally.
- **Plan mode triggers:** multi-file changes, architectural decisions, multiple valid approaches, or unclear scope.
- **CI/CD:** use `claude --output-format json` for machine-readable output; non-zero exit code on failure.
