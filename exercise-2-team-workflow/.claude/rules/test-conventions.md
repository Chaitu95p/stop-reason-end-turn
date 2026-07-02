---
name: test-conventions
description: Testing rules applied when editing any test file
paths:
  - "**/*.test.*"
  - "**/test_*.py"
  - "**/conftest.py"
---

# Test conventions (Step 7 — path-scoped rule)

Loaded automatically when editing test files anywhere in the tree.

## Integration tests hit a REAL database

- Use the `db_session` fixture from `conftest.py` — it points at a
  disposable `test_<n>` schema, wiped after each run.
- Do NOT mock `sqlalchemy.Session`. We got burned in Q2 2025 when a mock
  passed but the production migration failed silently. Mocks and prod
  schemas diverge.

## Test naming

- `test_<function_or_endpoint>_<scenario>_<expected>()`
  e.g. `test_create_order_missing_customer_returns_404`

## Assertion style

- Prefer explicit `assert response.status_code == 201`, not helper wrappers.
- Assert response bodies via `.model_dump()` against a Pydantic model
  literal — string equality on JSON is brittle.

## Verify this rule loads path-scoped

Open `src/payments.test.md` and ask "how do we assert response bodies?".
Expected: Claude references the Pydantic-model-literal rule above.
Now open `CLAUDE.md` and ask the same — Claude should NOT reference it.
