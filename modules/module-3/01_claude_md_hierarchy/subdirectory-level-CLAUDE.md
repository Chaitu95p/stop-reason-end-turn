# Subdirectory-Level CLAUDE.md
# Location: src/billing/CLAUDE.md (applies only when working in src/billing/)

## Billing module — additional context for this subdirectory

### Files in this directory
- refunds.py     — RefundProcessor class; $500 limit; uses pay.internal/v3/refunds
- credits.py     — CreditManager class; $50 goodwill cap; promo code lookup
- subscriptions.py — SubscriptionManager; annual/monthly plan switching
- __init__.py    — exports: RefundProcessor, CreditManager, SubscriptionManager

### Rules for this directory
- Every public method must have a docstring with Args and Returns.
- Raise domain errors (RefundLimitError, CreditLimitError) never generic Exception.
- All monetary amounts are stored as Python float in USD. Never use integers for money.
- Run: uv run pytest tests/test_billing/ before committing any change here.

## Notes
# Subdirectory CLAUDE.md adds context on top of project-level CLAUDE.md.
# It does NOT replace it — both are applied together.
# Use subdirectory CLAUDE.md for module-specific rules that would clutter the root.
