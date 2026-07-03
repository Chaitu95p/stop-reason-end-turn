---
paths:
  - "tests/**/*.py"
  - "**/*_test.py"
  - "**/*.test.py"
---

# Test Conventions

## Test structure
- Use pytest, NOT unittest.TestCase.
- One test file per source module: src/billing/refunds.py → tests/test_refunds.py
- Group tests by function/class with clearly named test_ functions.

## Naming convention
- test_<function>_<scenario>_<expected_outcome>
  Examples:
    test_process_refund_within_limit_returns_approved()
    test_process_refund_exceeds_limit_raises_RefundLimitError()
    test_issue_credit_empty_customer_id_raises_ValueError()

## Required test cases for every billing function
- Happy path (valid input, expected output)
- Boundary values (exactly at limit: $500 refund, $50 credit)
- Above boundary (e.g., $500.01 → should raise error)
- Invalid input types (negative amounts, None, empty string)
- Concurrent access (if the function modifies shared state)

## Fixtures and mocks
- Use pytest fixtures for: database connections, API clients, mock objects.
- Mock external services (payment gateway) with unittest.mock.patch.
- Never make real API calls or database writes in unit tests.

## Coverage requirement
- Minimum 80% line coverage for all modules in src/billing/
- Run: uv run pytest --cov=src/billing --cov-report=term-missing
