"""
Module 3 - Task 4.1: Explicit Criteria Over Vague Instructions

EXAM CONCEPTS:
  1. Vague instructions -> inconsistent results.
     Explicit, testable criteria -> consistent, reliable results.

  2. "Be conservative"/"only report high-confidence findings" fail
     because they are subjective. Use CATEGORICAL criteria instead.

  3. High false positive rates in one category undermine ALL categories.

  4. Temporarily DISABLE high-FP categories to restore developer trust
     while you fix the prompt. Keep accurate categories enabled.

  5. Define explicit severity criteria with CONCRETE CODE EXAMPLES
     for each level to achieve consistent severity classification.

Run: uv run python 01_explicit_criteria.py
"""

import anthropic

client = anthropic.Anthropic()

CODE_SNIPPET = """
def calculate_discount(price: float, user_type: str) -> float:
    # Returns 20% discount for premium users, 10% for regular users
    if user_type == "premium":
        return price * 0.85   # BUG: 15% discount, not 20% as comment says
    elif user_type == "regular":
        return price * 0.90   # OK: 10% discount matches comment
    return price
"""

VAGUE_SYSTEM = """
You are a code reviewer. Check that comments are accurate and report any issues.
Only report high-confidence findings.
"""

EXPLICIT_SYSTEM = """
You are a code reviewer. Apply ONLY these criteria -- skip everything else:

REPORT when:
  - A comment claims a function returns/computes X but the code computes Y.
  - A variable has a hardcoded value that contradicts its name or comment.

DO NOT REPORT:
  - Style issues (naming, spacing, formatting).
  - Missing docstrings or type hints.
  - Architectural suggestions.

Output: Line: <n> | Issue: <description> | Severity: bug
"""

SEVERITY_SYSTEM = """
You are a security code reviewer. Assign severity using these rules:

CRITICAL -- hardcoded credentials in source code
  Example: API_KEY = "sk-abc123"
  Rule: Any secret, key, or password as a string literal in code.

HIGH -- user input concatenated into SQL/HTML/commands without sanitization
  Example: query = "SELECT * FROM users WHERE id=" + user_id
  Rule: Any user-supplied data used directly in query/command construction.

MEDIUM -- broken/weak crypto for security-sensitive data
  Example: hashlib.md5(password.encode()).hexdigest()
  Rule: MD5/SHA1 for passwords; ECB mode; deprecated algorithms.

LOW -- missing defensive validation with exploitable edge cases
  Example: data = request.body  # no size check
  Rule: Missing input validation exploitable under specific conditions.

Output: SEVERITY | Line <n> | Category | Description
"""

DISABLED_CATEGORY_SYSTEM = """
You are a code reviewer. Apply ONLY these ENABLED categories:

ENABLED:
  - Security issues (hardcoded secrets, injection, weak crypto)
  - Logic bugs (code behavior contradicts comment description)

TEMPORARILY DISABLED (skip entirely):
  - Style issues -- disabled: false positive rate too high, prompt being improved
  - Performance suggestions -- disabled: too many false positives on idiomatic code

Report: CATEGORY | Severity | Line <n> | Description
"""

SECURITY_CODE = """
import hashlib
API_KEY = "sk-live-abc123xyz"  # hardcoded secret

def store_password(pw: str) -> str:
    return hashlib.md5(pw.encode()).hexdigest()

def get_user(user_id: str) -> str:
    return "SELECT * FROM users WHERE id=" + user_id
"""


def review(system_prompt: str, label: str, code: str = CODE_SNIPPET) -> None:
    nl = chr(10)
    prompt = "Review:" + nl + nl + ""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    print()
    print("=" * 60)
    print(" " + label)
    print("=" * 60)
    print(response.content[0].text)


if __name__ == "__main__":
    print("DEMO 1: Vague vs Explicit Criteria")
    print("Code has ONE real bug: 0.85 gives 15% discount, comment says 20%")
    review(VAGUE_SYSTEM, "VAGUE: Only report high-confidence findings")
    review(EXPLICIT_SYSTEM, "EXPLICIT: Categorical criteria (report THIS, skip THAT)")

    print()
    print("DEMO 2: Consistent Severity via Concrete Code Examples")
    review(SEVERITY_SYSTEM, "SEVERITY CRITERIA with concrete code examples", SECURITY_CODE)

    print()
    print("DEMO 3: Temporarily Disable High-FP Categories")
    print("Style disabled; security + logic remain active")
    review(DISABLED_CATEGORY_SYSTEM, "HIGH-FP CATEGORIES DISABLED", SECURITY_CODE)

    print()
    print("KEY TAKEAWAYS:")
    print("  1. Categorical criteria beat confidence-based filtering.")
    print("  2. Disable high-FP categories while fixing prompts -- keep accurate ones.")
    print("  3. Severity criteria need CONCRETE CODE EXAMPLES per level.")
    print("  Mnemonic: PRECISE -- criteria must be testable, not subjective.")
