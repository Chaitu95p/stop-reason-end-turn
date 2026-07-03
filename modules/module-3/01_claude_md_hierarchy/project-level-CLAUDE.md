# Project-Level CLAUDE.md
# Location: <project-root>/CLAUDE.md (committed to git — shared with team)

## Project: Billing Service API

### Stack
- Python 3.12, FastAPI, PostgreSQL
- Package manager: uv
- Testing: pytest with coverage ≥ 80%

### Code conventions
- All API handlers in src/api/routes/
- Business logic in src/billing/ (not in route handlers)
- Error classes in src/errors.py — always use RefundLimitError, CreditLimitError etc.
- Log to /var/log/billing/ — never use print() in production code.

### Important context
- Refund limit: $500 (configured in src/billing/refunds.py:MAX_AMOUNT)
- Goodwill credit cap: $50/year per customer
- Payment gateway: internal v3 API at https://pay.internal/v3/

### Before modifying billing logic
1. Read src/billing/refunds.py and src/billing/credits.py first.
2. Check that tests/test_refunds.py still passes.
3. Update CHANGELOG.md under the [Unreleased] section.

### Import more context
@src/billing/refunds.py
@src/errors.py

## Notes
# This file IS committed to git — the whole team shares these instructions.
# More specific sub-directory rules live in .claude/rules/ (see Task 3.3).
