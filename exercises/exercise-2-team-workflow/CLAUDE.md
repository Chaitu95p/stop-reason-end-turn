# CLAUDE.md — Project-Level Standards (Step 6)

This file is loaded automatically at the start of every session in this
project directory. Instructions here apply to ALL team members. Personal
overrides go in `~/.claude/CLAUDE.md`; subdirectory refinements go in
`src/<area>/CLAUDE.md`.

## Universal coding standards

- Python 3.12+. Type-hint every public function signature.
- Prefer `pathlib.Path` over `os.path`.
- No `print()` for non-user-facing output — use the `logging` module.
- Handlers in `src/api/**` MUST validate input via Pydantic before touching
  the DB. See `.claude/rules/api-conventions.md` for the full rule set
  (loaded automatically when you edit files under `src/api/`).
- All tests live next to source under a `*.test.py` name and use `pytest`.
  See `.claude/rules/test-conventions.md`.

## Universal testing conventions

- Every new endpoint requires an integration test that hits a real
  test-scoped database (no mocks — see rule file for the "why").
- Fixtures go in `conftest.py`, not inside individual test files.

## @imports (cascade of authoritative docs)

@src/api/README.md
@src/payments.test.md

## Verify this file loads

From this directory, start Claude Code and ask "What are our API rules?".
The response should reference Pydantic validation without any prompting
from you — that confirms the CLAUDE.md was loaded.
