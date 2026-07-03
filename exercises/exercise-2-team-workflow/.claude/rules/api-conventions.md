---
name: api-conventions
description: Conventions applied when editing HTTP handlers under src/api/
paths:
  - "src/api/**/*"
---

# API conventions (Step 7 — path-scoped rule)

This rule is injected into context ONLY when the current tool call touches
a file matching `src/api/**/*`. Editing a file under `src/db/` will NOT
load this rule — that keeps context lean and prevents rule pollution.

<!--
LEARNING-MODE TODO — this is one of your contribution points.

Fill in the 5-10 bullets below with the API conventions YOUR team enforces.
The exam wants to see:
  - Rules concrete enough to change behavior when loaded
  - Not so many rules that the context bloats past usefulness
  - Domain knowledge only YOU have (auth model, error envelope, versioning)

Suggested categories to consider:
  - Input validation (Pydantic? manual? which library?)
  - Auth model (JWT bearer? session cookie? API key?)
  - Error envelope shape (RFC 7807 problem+json? bespoke?)
  - Response pagination (cursor vs offset)
  - Idempotency keys for mutations
  - Rate-limit headers required in responses
-->

## Handler contract

- Every handler under `src/api/**` MUST accept a Pydantic model as its
  request body — never a raw dict.
- Every handler MUST return a Pydantic response model — never a raw dict.
- Reject unknown fields at the schema level (`extra="forbid"`).

## Error envelope

- Errors follow RFC 7807 problem+json shape:
  `{ "type": "...", "title": "...", "status": 4xx, "detail": "...", "traceId": "..." }`
- Never leak stack traces or ORM errors — map them at the handler boundary.

## Auth

- All routes require `Authorization: Bearer <jwt>` unless annotated `@public`.
- Extract `user_id` via `Depends(get_current_user)` — never read the token yourself.

## Verify this rule loads path-scoped

1. Open a file under `src/db/` and ask Claude "what's our API error envelope?".
   Expected: Claude does NOT quote the RFC 7807 rule (this file didn't load).
2. Open a file under `src/api/` and ask the same question.
   Expected: Claude quotes the problem+json shape verbatim (this file loaded).
