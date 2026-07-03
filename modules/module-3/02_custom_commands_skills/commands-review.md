# .claude/commands/review.md
# Custom slash command: /review
# Invoked as: /review src/billing/refunds.py

Review the file at $ARGUMENTS for the following:

1. **Security issues**: SQL injection, hardcoded secrets, unvalidated inputs, missing auth checks
2. **Error handling**: Are domain-specific errors raised? Is every exception caught specifically?
3. **Test coverage**: Are edge cases (0 amounts, negative values, concurrent requests) tested?
4. **Code conventions**: Does this file follow the project conventions in CLAUDE.md?
5. **Performance**: Any N+1 queries, blocking I/O in async handlers, or missing pagination?

For each finding, output:
- **Severity**: critical | high | medium | low | info
- **Location**: file:line_number
- **Description**: what the issue is
- **Suggestion**: specific fix

At the end, output a summary table and an overall risk rating.
