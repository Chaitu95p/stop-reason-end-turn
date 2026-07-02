---
description: Scaffold a new REST endpoint under src/api/ with request/response Pydantic models and a matching *.test.py file.
argument-hint: <resource-name> <http-method>
---

# /new-endpoint (example custom slash command)

Given: `/new-endpoint orders POST`

Do this:

1. Create `src/api/{resource}/routes.py` with a FastAPI handler for
   `{method} /{resource}`. Include the Pydantic request + response models
   inline at the top of the file.
2. Follow the RFC 7807 error envelope from `.claude/rules/api-conventions.md`.
3. Create `src/api/{resource}/routes.test.py` with:
   - one happy-path integration test
   - one input-validation test (missing required field)
   Use the `db_session` fixture — no mocks.
4. Register the router in `src/api/__init__.py`.
5. Print the file paths you created so the user can review.

Do NOT run migrations. Do NOT commit. Stop after the files exist.
