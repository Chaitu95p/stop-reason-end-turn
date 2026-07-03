---
description: Deeply analyze the codebase structure and produce an architecture summary with dependency graph
argument-hint: "[optional: specific module or path to focus on]"
allowed-tools: Glob, Grep, Read
context: fork
---

# Skill: analyze-codebase
# Invoked as: /analyze-codebase [optional: src/billing/]

## What this skill does
Perform a thorough static analysis of the codebase (or the specified module)
and produce:
1. **Architecture summary**: layers, modules, and their responsibilities
2. **Dependency graph**: which modules import from which
3. **Key entry points**: API routes, CLI commands, background workers
4. **Hotspots**: files with highest import fan-in (most depended upon)
5. **Gaps**: areas with low test coverage, missing error handling, or no docs

## Steps

1. Use Glob to enumerate all Python files: `Glob('**/*.py')`
2. Use Grep to find import statements: `Grep('^from|^import', '**/*.py')`
3. Use Glob to find test files: `Glob('tests/**/*.py')`
4. Read key entry point files identified in step 2.
5. Synthesize findings into the output format below.

## Output format

```
## Architecture Summary
[2-3 paragraphs]

## Module Dependency Graph
[ASCII or text representation]

## Key Entry Points
- src/api/routes.py: FastAPI router with N endpoints
- src/worker/tasks.py: Celery tasks (if present)

## Hotspots (most depended upon)
1. src/errors.py — imported by N files
2. src/billing/refunds.py — imported by N files

## Gaps & Recommendations
- [specific, actionable findings]
```

## Notes
- `context: fork` means this skill runs in a forked session (isolated context).
- `allowed-tools: Glob, Grep, Read` — this skill cannot write or edit files.
- Results are shown to the user; no auto-commit occurs.
