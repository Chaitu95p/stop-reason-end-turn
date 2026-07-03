# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Runnable Python demos for the **Claude Certified Architect – Foundations (CCA-F)** exam. Each module is a fully independent `uv` project that maps to one exam domain.

| Module | Exam Domain | Weight |
|--------|-------------|--------|
| module-1 | Agentic Architecture & Orchestration | 27% |
| module-2 | Tool Design & MCP Integration | 18% |
| module-3 | Claude Code Configuration & Workflows | 20% |
| module-4 | Prompt Engineering & Structured Output | 20% |
| module-5 | Context Management & Reliability | 15% |

## Commands

This is a **uv workspace**. One shared `.venv` at the repo root serves every module and exercise. Sync once from root, then `uv run` from any member folder resolves against the shared env.

```bash
# Install dependencies (first time, or after cloning) -- run at REPO ROOT
uv sync

# Run a single demo script (uv resolves the workspace env automatically)
cd modules/module-1 && uv run python 01_agentic_loop.py

# Run all demo scripts in a module in order
cd modules/module-2 && for f in 0*.py; do echo "=== $f ===" && uv run python "$f"; done

# Add a dependency to one member (writes to that member's pyproject.toml)
cd modules/module-3 && uv add <package>
```

Custom slash commands (available in this Claude Code session):
- `/run-module 2` — runs all scripts in modules/module-2 in order
- `/run-script modules/module-1/01_agentic_loop.py` — runs one script and summarizes it
- `/review-script modules/module-3/04_plan_vs_direct.py` — quality-checks a demo script
- `/new-demo modules/module-1 1.8` — scaffolds a new numbered demo script

There are no automated tests. The "test" is running the script and verifying the printed output.

## Architecture

### uv workspace layout

The repo is a uv workspace declared at the root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["modules/module-*", "exercises/exercise-*"]
exclude = ["exercises/exercise-2-team-workflow"]   # config-only, no Python
```

- One `.venv` and one `uv.lock` live at the repo root; there are no per-member venvs or locks.
- Each member (`modules/module-N/`, `exercises/exercise-N-*/`) still owns its `pyproject.toml` — that's how `exercise-3-extraction-pipeline` adds `pydantic` without contaminating other members.
- All members target Python ≥ 3.12. Common dep: `anthropic>=0.115.1`.
- `exercises/exercise-2-team-workflow` is config-only (`.claude/`, `.mcp.json`, `CLAUDE.md`) and is excluded from the workspace on purpose — it has no Python code.

`main.py` in each module is uv-generated boilerplate (prints a hello string) and is not used by any demo. All content is in the numbered `0N_name.py` scripts.

### Numbered script structure

Every `0N_name.py` script follows this exact pattern:

```
Module docstring:
  Line 1: "Domain N - Task N.M: <Task Name>"
  EXAM CONCEPTS: numbered list of concepts demonstrated
  Mnemonic: WORD with letter-by-letter expansion
  Run: uv run python 0N_name.py

Imports → client = anthropic.Anthropic() → NL = chr(10)

Mock tool functions (pure Python dicts/callables, no real I/O)

Demo functions labeled with # DEMO N / # ANTI-PATTERN N comments

if __name__ == "__main__":
  Runs all demos with sep = "=" * 60 headers
  Ends with KEY TAKEAWAYS: printed bullet list (≥3 points)
```

`NL = chr(10)` is used for all multi-line string concatenation throughout every script — never `\n` inline.

### How scripts call the API

All scripts use the synchronous `anthropic.Anthropic()` client with `model="claude-sonnet-4-6"`. Agentic loops always check `resp.stop_reason`: loop on `"tool_use"`, terminate on `"end_turn"`. Tool results are appended as `{"role": "user", "content": [{"type": "tool_result", "tool_use_id": ..., "content": ...}]}`.

### Module-3 is unique

modules/module-3 contains Python scripts AND three example subdirectories of Claude Code config files:
- `01_claude_md_hierarchy/` — CLAUDE.md at user/project/subdirectory levels
- `02_custom_commands_skills/` — command `.md` and skill `SKILL.md` frontmatter format
- `03_path_specific_rules/` — `.claude/rules/` files with YAML `paths:` frontmatter

These are pedagogical demos of config concepts for the exam — not the real project config. The actual project config lives in `.claude/` at the repo root.

### .claude/ project config (real, for this repo)

- `settings.json` — model, Bash allow/deny list, PreToolUse + PostToolUse hook wiring
- `hooks/pre-tool-use.sh` — blocks `rm -rf`, `git push --force`, `pip install`
- `hooks/post-tool-use.sh` — appends every tool call to `.claude/tool-usage.log`
- `commands/` — run-module, run-script, review-script, new-demo
- `skills/` — explore-module, generate-quiz, check-exam-coverage (all `context: fork`, read-only)
- `rules/demo-scripts.md` — injected when editing `modules/module-*/0*.py`
- `rules/config-examples.md` — injected when editing `modules/module-3/**/*.md`

## Constraints when editing demo scripts

- `NL = chr(10)` for newlines in string building — never `\n` inline.
- All tool functions must be pure Python mock implementations — no real external calls.
- `ANTHROPIC_API_KEY` comes from the environment; never set it in code.
- Every script must stay runnable as `uv run python <filename>` from its module directory.
- KEY TAKEAWAYS section must remain accurate after any change.

@modules/module-1/01_agentic_loop.py
@modules/module-2/02_structured_error_responses.py
