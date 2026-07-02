# /review-script
# Usage: /review-script $ARGUMENTS  (e.g. /review-script module-3/04_plan_vs_direct.py)
# Reviews a demo script for quality and exam coverage completeness.

The argument is a relative path to a demo script.

Steps:
1. Read the script at $ARGUMENTS in full.

2. Check the HEADER DOCSTRING:
   - [ ] Docstring starts with "Domain N - Task N.M: <description>"
   - [ ] Lists "EXAM CONCEPTS:" with numbered points
   - [ ] Contains a "Mnemonic:" or "Mnemonic WORD:" line
   - [ ] Has "Run: uv run python <filename>" line

3. Check CODE CONVENTIONS:
   - [ ] Uses `model="claude-sonnet-4-6"` (not any other model)
   - [ ] Uses `NL = chr(10)` for newlines (not `\n` in f-strings for multi-line strings)
   - [ ] All tools are Python dicts/callables — no real external API calls
   - [ ] No hardcoded API keys, tokens, or passwords
   - [ ] `ANTHROPIC_API_KEY` is assumed from environment, not set in code

4. Check STRUCTURE:
   - [ ] Has `if __name__ == "__main__":` block
   - [ ] Ends with `KEY TAKEAWAYS:` section (at least 3 bullet points)
   - [ ] Demo sections are labeled (`DEMO 1:`, `DEMO 2:`, etc.)
   - [ ] Anti-patterns are labeled as such (if present)

5. Check EXAM COVERAGE:
   - [ ] Every exam concept listed in the docstring is demonstrated in at least one DEMO
   - [ ] The mnemonic is explained in the KEY TAKEAWAYS

6. Output a review report:
   - Pass/Fail for each checklist item above
   - Specific issues found with file:line references
   - Overall quality rating: Excellent / Good / Needs Work
   - Suggested fixes for any failed items
