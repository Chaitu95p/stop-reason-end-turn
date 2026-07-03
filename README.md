# stop-reason-end-turn

Runnable Python demos and Claude Code config examples for the **Claude Certified Architect – Foundations (CCA-F)** exam.

Each **module** maps to one exam domain. Each **exercise** works through one of the four Preparation Exercises in the CCA-F Exam Guide (pages 31-34).

## Layout

```
.
├── modules/
│   ├── module-1/  ← Domain 1: Agentic Architecture & Orchestration        (27%)
│   ├── module-2/  ← Domain 2: Tool Design & MCP Integration               (18%)
│   ├── module-3/  ← Domain 3: Claude Code Configuration & Workflows       (20%)
│   ├── module-4/  ← Domain 4: Prompt Engineering & Structured Output      (20%)
│   └── module-5/  ← Domain 5: Context Management & Reliability            (15%)
│
├── exercises/
│   ├── exercise-1-multi-tool-agent/       ← Prep Exercise 1: agent + escalation
│   ├── exercise-2-team-workflow/          ← Prep Exercise 2: Claude Code config (no Python)
│   ├── exercise-3-extraction-pipeline/    ← Prep Exercise 3: structured extraction
│   └── exercise-4-multi-agent-research/   ← Prep Exercise 4: multi-agent research
│
├── pyproject.toml   ← uv workspace root
├── uv.lock          ← single shared lock file
└── CLAUDE.md        ← agent-facing project instructions
```

## Getting started

Prerequisites: [`uv`](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
git clone <this repo>
cd stop-reason-end-turn

# One sync at the root sets up the shared .venv for every module and exercise
uv sync

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Run any demo
cd modules/module-1 && uv run python 01_agentic_loop.py

# Run every script in a module in order
cd modules/module-2 && for f in 0*.py; do echo "=== $f ===" && uv run python "$f"; done
```

## uv workspace

The repo is a single [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/) — one `.venv` and one `uv.lock` at the root serve every member. Each member still owns its own `pyproject.toml` so members can declare distinct dependencies (e.g. `exercise-3` adds `pydantic`).

`exercises/exercise-2-team-workflow/` is intentionally excluded from the workspace — it contains only Claude Code configuration files (`CLAUDE.md`, `.claude/`, `.mcp.json`) as a pedagogical example of a team's project setup. There is no Python code to install.

## Script contract

Every numbered script (`0N_name.py`) follows the same shape so you can jump between them:

- Module docstring: `Domain N - Task N.M: <name>` → `EXAM CONCEPTS:` numbered list → `Mnemonic:` acronym → `Run:` command
- `client = anthropic.Anthropic()` with `model="claude-sonnet-4-6"`
- `NL = chr(10)` for multi-line string building (never `\n` inline)
- Mock tool functions — no real network or DB calls
- `# DEMO N` / `# ANTI-PATTERN N` section markers
- `KEY TAKEAWAYS:` bullets at the bottom, always ≥ 3 points

See `modules/module-1/01_agentic_loop.py` and `modules/module-2/02_structured_error_responses.py` as canonical examples.

## Custom slash commands

Available in this Claude Code session (defined in `.claude/commands/`):

| Command | Purpose |
|---------|---------|
| `/run-module <N>` | Run every script in `modules/module-N/` in order |
| `/run-script <path>` | Run one script and summarize its output |
| `/review-script <path>` | Quality-check a demo script against the contract |
| `/new-demo <module> <task-num>` | Scaffold a new numbered demo |

Custom skills in `.claude/skills/`:

- **explore-module** — deep-analyze a module and produce a study summary
- **generate-quiz** — 10 exam-style multiple-choice questions from a module
- **check-exam-coverage** — cross-check demos against the exam domain list

## Exam reference

The authoritative exam guide is `CCA-F Latest Exam+Guide v1.pdf` in this repo. The domain weightings and Preparation Exercises 1-4 come directly from it.

## No tests

There is no test suite — the "test" is running each script and verifying the printed output makes sense (correct tool call sequence, expected `stop_reason` transitions, structured error payloads formatted right, etc.).

See `CLAUDE.md` for the full contributor / agent guide.
