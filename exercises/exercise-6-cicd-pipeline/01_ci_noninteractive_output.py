"""
Exercise 6 - Steps 1-2: Non-Interactive CI Mode and Structured Output

EXAM CONCEPTS:
  1. -p / --print flag for non-interactive CI mode:
       claude -p "Analyze this PR for security issues"
       Processes the prompt, prints result to stdout, and EXITS.
       Without -p, Claude Code waits for interactive input -- CI jobs hang.

  2. --output-format json with --json-schema for structured CI output:
       claude -p "..." --output-format json --json-schema schema.json
       Produces machine-parseable output for automated comment posting.

  3. CLAUDE.md provides CI context:
       Testing standards, review criteria, fixture conventions.
       CI-invoked Claude Code reads the project CLAUDE.md automatically.
       This is how you configure review behavior without passing it on the CLI.

  4. Session context isolation:
       The SAME Claude session that generated code is less effective at
       reviewing its own changes -- it retains the generation reasoning context.
       CORRECT: use an independent Claude instance for review.
       ANTI-PATTERN: asking the same session to "review what you just wrote."

  5. Avoiding duplicate comments on re-runs:
       Include prior review findings in context on re-run.
       Instruct Claude to report ONLY new or still-unaddressed issues.
       Otherwise re-running after a commit floods the PR with duplicate comments.

  Mnemonic: PRIDE
    Print flag (-p) prevents interactive hang
    Review in an independent session -- not the generator's
    Include prior findings on re-run to avoid duplicates
    Document criteria in CLAUDE.md (not on CLI)
    Exit after output -- CI needs a clean process exit

Run: uv run python 01_ci_noninteractive_output.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)

# ---------------------------------------------------------------------------
# Mock PR diff (in-memory -- no real git I/O)
# ---------------------------------------------------------------------------
PR_DIFF = """
--- a/src/payments/processor.py
+++ b/src/payments/processor.py
@@ -10,6 +10,12 @@
 def process_payment(order_id: str, amount: float) -> dict:
     customer = get_customer(order_id)
+    # TODO: remove debug logging before merge
+    print(f"DEBUG: processing {order_id} amount={amount} customer={customer}")
+    query = f"SELECT * FROM orders WHERE id = '{order_id}'"  # noqa
+    if amount > 0:
+        charge_card(customer, amount)
+        send_receipt(customer["email"])
     return {"success": True}
"""

# ---------------------------------------------------------------------------
# Structured output schema for CI review findings
# ---------------------------------------------------------------------------
CI_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file":     {"type": "string"},
                    "line":     {"type": ["integer", "null"]},
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "category": {"type": "string", "enum": ["security", "bug", "style", "other"]},
                    "message":  {"type": "string"},
                    "suggestion": {"type": ["string", "null"]},
                },
                "required": ["file", "severity", "category", "message"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["findings", "summary"],
}

REVIEW_TOOL = [
    {
        "name": "submit_review",
        "description": (
            "Submit the structured code review findings. "
            "Call this ONCE when analysis is complete."
        ),
        "input_schema": CI_REVIEW_SCHEMA,
    }
]


def run_ci_review(diff: str, prior_findings: list = None, label: str = "RUN") -> dict:
    """
    Simulate Claude Code running in CI mode (-p flag behavior).
    Uses tool_use to produce structured JSON output.
    Includes prior findings when present (avoid duplicate comments).
    """
    prior_section = ""
    if prior_findings:
        prior_section = (
            NL + "PRIOR REVIEW FINDINGS (already posted as PR comments):" + NL
            + json.dumps(prior_findings, indent=2) + NL
            + "Report ONLY findings NOT in the list above. "
            + "Do not re-report already-addressed issues." + NL
        )

    prompt = (
        "Analyze this PR diff for code quality issues." + NL
        + prior_section + NL
        + "PR DIFF:" + NL + diff + NL
        + "Report findings using the submit_review tool. "
        + "Focus on: security vulnerabilities, bugs, NOT style issues."
    )
    messages = [{"role": "user", "content": prompt}]
    system = (
        "You are a CI code review agent running in non-interactive mode. " + NL
        + "Review criteria (from CLAUDE.md):" + NL
        + "  - REPORT: SQL injection, debug prints in production, exception handling bugs" + NL
        + "  - SKIP: formatting, minor style, local naming conventions" + NL
        + "Submit findings via submit_review tool. One call only."
    )
    for _ in range(5):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=REVIEW_TOOL,
            tool_choice={"type": "tool", "name": "submit_review"},
            messages=messages,
        )
        if resp.stop_reason in ("end_turn", "tool_use"):
            for block in resp.content:
                if block.type == "tool_use" and block.name == "submit_review":
                    print(f"  [{label}] submit_review called with {len(block.input.get('findings', []))} findings")
                    return block.input
            if resp.stop_reason == "end_turn":
                return {"findings": [], "summary": "No structured output produced"}
        messages.append({"role": "assistant", "content": resp.content})
    return {"findings": [], "summary": "(loop limit)"}


# ---------------------------------------------------------------------------
# DEMO 1: CI mode flag concepts
# ---------------------------------------------------------------------------
def demo_ci_flag_concepts() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 1: CLI flags for CI/CD mode")
    print()
    commands = [
        (
            "HANGS in CI (interactive mode):",
            "claude \"Analyze this PR for security issues\"",
            "Waits for stdin -- CI job hangs indefinitely.",
        ),
        (
            "CORRECT for CI (-p flag):",
            "claude -p \"Analyze this PR for security issues\"",
            "Processes prompt, prints to stdout, exits cleanly.",
        ),
        (
            "STRUCTURED output for automation:",
            "claude -p \"...\" --output-format json --json-schema schema.json",
            "Machine-parseable JSON; post as inline PR comments programmatically.",
        ),
    ]
    for label, cmd, note in commands:
        print(f"  {label}")
        print(f"    $ {cmd}")
        print(f"    -> {note}")
        print()


# ---------------------------------------------------------------------------
# DEMO 2: Independent review instance vs same-session review
# ---------------------------------------------------------------------------
def demo_session_isolation() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 2: Session context isolation -- independent review vs self-review")
    print()
    print("ANTI-PATTERN: asking the same session that generated code to review it.")
    print("  The model retains reasoning context from generation.")
    print("  It is less likely to question its own design decisions.")
    print("  Even with 'review critically' instructions, bias remains.")
    print()
    print("CORRECT: Use an independent Claude instance for review.")
    print("  Fresh session = no generation context retained.")
    print("  More likely to catch subtle issues the generator rationalized away.")
    print()
    print("Running independent review on PR diff...")
    result = run_ci_review(PR_DIFF, label="INDEPENDENT")
    print()
    print("Structured findings:")
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# DEMO 3: Re-run with prior findings (avoid duplicate comments)
# ---------------------------------------------------------------------------
def demo_dedup_on_rerun() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 3: Including prior findings to avoid duplicate PR comments")
    print()

    # First run
    print("First run (no prior findings)...")
    first_result = run_ci_review(PR_DIFF, label="RUN-1")
    first_findings = first_result.get("findings", [])
    print(f"  First run: {len(first_findings)} findings")

    # Simulate developer addressing the SQL injection finding
    prior_reported = [f for f in first_findings if f.get("category") == "security"]
    print(f"  Developer addressed security findings. Prior findings to exclude: {len(prior_reported)}")
    print()

    # Second run after new commit
    print("Second run (passing prior findings to deduplicate)...")
    second_result = run_ci_review(PR_DIFF, prior_findings=prior_reported, label="RUN-2")
    second_findings = second_result.get("findings", [])
    print(f"  Second run: {len(second_findings)} new/unaddressed findings")
    print()
    if second_findings:
        print("  New findings:")
        for f in second_findings:
            print(f"    [{f['severity'].upper()}] {f.get('file','?')} - {f['message'][:80]}")
    else:
        print("  No new findings beyond what was already reported.")


if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("DEMO 1: CI/CD flag concepts (-p, --output-format json)")
    print(sep)
    demo_ci_flag_concepts()

    print()
    print(sep)
    print("DEMO 2: Session context isolation for independent review")
    print(sep)
    demo_session_isolation()

    print()
    print(sep)
    print("DEMO 3: Deduplication on re-run with prior findings")
    print(sep)
    demo_dedup_on_rerun()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. -p (--print) flag is REQUIRED for CI -- without it Claude waits for input.")
    print("  2. --output-format json + --json-schema produces machine-parseable PR comments.")
    print("  3. CLAUDE.md provides review criteria to CI-invoked Claude Code.")
    print("  4. Always use an INDEPENDENT Claude instance for review -- same-session")
    print("     review retains generation bias and misses subtle issues.")
    print("  5. Include prior findings on re-run and instruct 'report only NEW issues'")
    print("     to prevent duplicate PR comments after each commit.")
    print("  Mnemonic PRIDE: Print flag/-p/Review independently/Include prior/Document in CLAUDE.md/Exit clean.")
