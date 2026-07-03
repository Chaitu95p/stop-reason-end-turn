---
paths:
  - "src/api/**/*"
---

# API Layer Conventions

## Route handler rules
- Route handlers in src/api/routes/ must NOT contain business logic.
  Delegate all logic to src/billing/ or src/services/ classes.
- Every route must have a `Depends(get_auth)` parameter for authentication.
- Return types must use Pydantic response models (not raw dicts).
- HTTP status codes: 200 OK, 201 Created, 422 Unprocessable Entity (validation),
  403 Forbidden (auth), 404 Not Found, 500 Internal Server Error.

## Error handling in routes
- Catch domain errors and convert to HTTP responses:
  RefundLimitError  → HTTP 422 with detail message
  CreditLimitError  → HTTP 422 with detail message
  PermissionError   → HTTP 403
  KeyError          → HTTP 404

## Required auth scopes
- GET  endpoints: billing:read
- POST endpoints: billing:write
- DELETE endpoints: billing:admin
- Verify that Depends(get_auth) checks the correct scope for each route.

## OpenAPI documentation
- Every route must have: summary=, description=, response_model=
- Tags must match the module name (e.g., tags=["refunds"], tags=["credits"])
