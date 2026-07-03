"""
Domain 3 - Task 3.5: Iterative Refinement Techniques

EXAM CONCEPTS:
  1. Input/output examples: show Claude the exact transformation you want
     via before/after pairs rather than describing it in words.
     Most effective when the transformation is non-obvious from description alone.

  2. Test-driven iteration: share failing test output as the next prompt.
     Claude reads the failure and makes targeted fixes. Repeat until all pass.
     Especially useful because test failures are unambiguous.

  3. Interview pattern: Claude asks clarifying questions BEFORE writing code.
     Use when requirements are vague or there are multiple valid approaches.
     Prevents writing code that needs to be thrown away and restarted.

  4. Single-message vs sequential iteration:
     Single-message: provide ALL context upfront (examples, constraints, format)
     Sequential: start basic, refine in subsequent turns based on output

  5. When to use each technique:
     Examples     → transformation is visual/structural, hard to describe
     TDD          → correctness matters, tests already exist or can be written
     Interview    → requirements are underspecified, multiple valid approaches

Run: uv run python 05_iterative_refinement.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Technique 1: Input/output examples
# ---------------------------------------------------------------------------
def technique_io_examples() -> None:
    sep = "-" * 50
    print(sep)
    print("TECHNIQUE 1: Input/Output Examples")
    print()

    # WITHOUT examples: vague description
    prompt_without_examples = (
        "Convert the log entries to a structured format."
    )

    # WITH examples: show exact transformation
    prompt_with_examples = (
        "Convert each log entry to structured JSON. Here are examples:" + NL + NL
        + "Input: '2024-01-15 10:23:45 ERROR billing: RefundLimitError amount=650 limit=500'" + NL
        + "Output: {\"timestamp\": \"2024-01-15T10:23:45\", \"level\": \"ERROR\", \"module\": \"billing\", "
        + "\"error\": \"RefundLimitError\", \"amount\": 650, \"limit\": 500}" + NL + NL
        + "Input: '2024-01-15 10:24:01 INFO billing: refund processed refund_id=REF-100 amount=129.99'" + NL
        + "Output: {\"timestamp\": \"2024-01-15T10:24:01\", \"level\": \"INFO\", \"module\": \"billing\", "
        + "\"message\": \"refund processed\", \"refund_id\": \"REF-100\", \"amount\": 129.99}" + NL + NL
        + "Now convert this log entry:" + NL
        + "2024-01-15 11:05:22 WARN billing: credit limit approaching customer_id=C001 used=45.00 cap=50.00"
    )

    print("WITHOUT examples (vague description):")
    print(f"  Prompt: '{prompt_without_examples}'")
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt_without_examples}],
    )
    out = next((b.text for b in resp.content if hasattr(b, "text")), "")
    print(f"  Output: {out[:150]}")
    print()

    print("WITH examples (exact before/after pairs):")
    print(f"  Prompt shows 2 examples then asks for conversion")
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt_with_examples}],
    )
    out = next((b.text for b in resp.content if hasattr(b, "text")), "")
    print(f"  Output: {out[:200]}")
    print()
    print("  -> Examples make the exact format unambiguous without long descriptions.")


# ---------------------------------------------------------------------------
# Technique 2: Test-driven iteration
# ---------------------------------------------------------------------------
def technique_tdd_iteration() -> None:
    sep = "-" * 50
    print(sep)
    print("TECHNIQUE 2: Test-Driven Iteration")
    print()

    # Simulated failing test output
    failing_tests = """
FAILED tests/test_refunds.py::test_process_refund_exceeds_limit - AssertionError:
  Expected RefundLimitError to be raised for amount=650, but no exception was raised.

FAILED tests/test_refunds.py::test_process_refund_negative_amount - AssertionError:
  Expected ValueError for negative amount, but got RefundResult(status='approved').

2 failed, 8 passed
"""

    # First turn: write code
    first_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system="You are an expert Python developer. Write clean, correct code.",
        messages=[{
            "role": "user",
            "content": "Write a RefundProcessor.process(order_id, amount) method that validates amounts.",
        }],
    )
    first_code = next((b.text for b in first_response.content if hasattr(b, "text")), "")
    print(f"Initial code (first turn):")
    print(f"  {first_code[:300]}")
    print()

    # Second turn: share test failures
    second_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system="You are an expert Python developer. Fix code based on test failures.",
        messages=[
            {"role": "user", "content": "Write a RefundProcessor.process(order_id, amount) method."},
            {"role": "assistant", "content": first_code},
            {"role": "user", "content": f"These tests are failing:\n{failing_tests}\n\nFix the code to make them pass."},
        ],
    )
    fixed_code = next((b.text for b in second_response.content if hasattr(b, "text")), "")
    print(f"Fixed code (after sharing test failures):")
    print(f"  {fixed_code[:300]}")
    print()
    print("  -> Test failures are unambiguous — Claude makes targeted fixes.")
    print("  -> Repeat until all tests pass: share failures → fix → verify.")


# ---------------------------------------------------------------------------
# Technique 3: Interview pattern
# ---------------------------------------------------------------------------
def technique_interview_pattern() -> None:
    sep = "-" * 50
    print(sep)
    print("TECHNIQUE 3: Interview Pattern (Claude asks clarifying questions)")
    print()

    vague_request = (
        "Add caching to the billing service."
    )

    print(f"Vague request: '{vague_request}'")
    print()
    print("Without interview pattern: Claude might implement Redis caching when")
    print("the developer wanted in-memory caching, or cache everything when only")
    print("the get_customer call needed caching. Code gets thrown away.")
    print()

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=(
            "You are a Claude Code expert. When a request is underspecified and there"
            " are multiple valid approaches, ask 3-5 clarifying questions BEFORE writing any code."
            " Do not start implementing until you understand the requirements."
        ),
        messages=[{"role": "user", "content": vague_request}],
    )
    questions = next((b.text for b in resp.content if hasattr(b, "text")), "")
    print("Claude's clarifying questions:")
    print(questions)
    print()
    print("  -> Claude asks BEFORE coding → avoids rewriting after wrong assumptions.")
    print("  -> Use when: requirements unclear, multiple valid approaches exist.")


# ---------------------------------------------------------------------------
# Technique selection guide
# ---------------------------------------------------------------------------
def show_technique_selection() -> None:
    sep = "-" * 50
    print(sep)
    print("TECHNIQUE SELECTION GUIDE")
    print()
    techniques = [
        {
            "name": "Input/Output Examples",
            "use_when": [
                "The transformation is visual/structural",
                "Hard to describe the format in words",
                "Multiple examples clarify edge cases",
            ],
            "avoid_when": "Requirements are already unambiguous from text description",
        },
        {
            "name": "Test-Driven Iteration",
            "use_when": [
                "Correctness is critical (financial calculations, data integrity)",
                "Tests already exist or can be written before coding",
                "Bug is hard to describe but easy to demonstrate via test",
            ],
            "avoid_when": "No tests and writing tests would take longer than the fix",
        },
        {
            "name": "Interview Pattern",
            "use_when": [
                "Requirements are vague ('make it faster', 'add caching')",
                "Multiple valid approaches with different trade-offs",
                "Risk of writing code that needs to be thrown away is high",
            ],
            "avoid_when": "Requirements are already specific and detailed",
        },
    ]
    for t in techniques:
        print(f"  {t['name']}:")
        print(f"    Use when: {t['use_when'][0]}")
        print(f"    Avoid when: {t['avoid_when']}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Input/Output Examples technique")
    print(sep)
    technique_io_examples()

    print()
    print(sep)
    print("DEMO 2: Test-Driven Iteration technique")
    print(sep)
    technique_tdd_iteration()

    print()
    print(sep)
    print("DEMO 3: Interview Pattern technique")
    print(sep)
    technique_interview_pattern()

    print()
    print(sep)
    print("DEMO 4: Technique selection guide")
    print(sep)
    show_technique_selection()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Input/Output examples: show exact transformations instead of describing them.")
    print("     2 concrete examples often beats 2 paragraphs of description.")
    print("  2. Test-driven iteration: share failing tests as the next prompt.")
    print("     Test failures are unambiguous; Claude makes targeted, correct fixes.")
    print("  3. Interview pattern: Claude asks clarifying questions BEFORE coding.")
    print("     Use when requirements are vague or multiple approaches are valid.")
    print("  4. Single-message: provide all context upfront (examples + constraints).")
    print("     Sequential: start basic, refine in follow-up turns.")
    print("  5. Choosing wrong technique wastes time: asking 10 questions for a typo fix")
    print("     is as inefficient as diving into code for an underspecified architecture task.")
