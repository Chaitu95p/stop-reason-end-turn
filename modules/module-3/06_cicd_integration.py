"""
Domain 3 - Task 3.6: CI/CD Integration with Claude Code

EXAM CONCEPTS:
  1. Non-interactive mode (-p flag):
     claude -p "Review this PR for security issues" --output-format json
     Runs Claude Code without user interaction — suitable for CI pipelines.
     Returns structured output that CI scripts can parse.

  2. Structured output for CI: use tool_use with a schema to force
     machine-readable output (severity, location, description).
     Unstructured prose output is hard to parse in CI scripts.

  3. Including prior findings: pass previous review results as context
     to avoid flagging the same issues in every CI run.
     "Previously flagged: [X, Y] — only report NEW issues."

  4. Session isolation: each CI run should start a fresh session.
     Do NOT resume sessions between CI runs — stale context causes
     missed findings or incorrect assessments.

  5. Output-format json: when using the CLI flag, Claude Code returns
     a JSON object with: cost, duration, result (the text or tool output).
     Scripts should parse this JSON rather than the raw text.

Run: uv run python 06_cicd_integration.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Structured CI finding schema
# ---------------------------------------------------------------------------
CI_REVIEW_TOOL = {
    "name": "report_ci_findings",
    "description": (
        "Report security and quality findings from a code review. "
        "Only report NEW findings not already listed in previously_flagged."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low", "info"],
                        },
                        "category": {
                            "type": "string",
                            "enum": [
                                "security",
                                "auth",
                                "input_validation",
                                "error_handling",
                                "performance",
                                "test_coverage",
                            ],
                        },
                        "file": {"type": "string"},
                        "line": {"type": ["integer", "null"]},
                        "description": {"type": "string"},
                        "suggestion": {"type": "string"},
                        "is_new": {"type": "boolean", "description": "True if not in previously_flagged"},
                    },
                    "required": ["severity", "category", "file", "description", "suggestion", "is_new"],
                },
            },
            "summary": {
                "type": "object",
                "properties": {
                    "total_new": {"type": "integer"},
                    "critical_count": {"type": "integer"},
                    "high_count": {"type": "integer"},
                    "should_block_merge": {"type": "boolean"},
                    "block_reason": {"type": ["string", "null"]},
                },
                "required": ["total_new", "critical_count", "high_count", "should_block_merge"],
            },
        },
        "required": ["findings", "summary"],
    },
}


# ---------------------------------------------------------------------------
# Simulated code changes (PR diff)
# ---------------------------------------------------------------------------
SAMPLE_PR_DIFF = """
--- a/src/api/routes/refunds.py
+++ b/src/api/routes/refunds.py
@@ -1,8 +1,15 @@
+import subprocess
+import os
+
 @router.post("/refunds")
-async def create_refund(request: RefundRequest, auth: Auth = Depends(get_auth)):
+async def create_refund(request: RefundRequest):
+    # REMOVED auth dependency for testing
     processor = RefundProcessor()
-    return processor.process(request.order_id, request.amount)
+    # Log to file for debugging
+    os.system(f"echo 'Refund: {request.order_id}' >> /tmp/debug.log")
+    result = processor.process(request.order_id, request.amount)
+    return result

--- a/src/billing/refunds.py
+++ b/src/billing/refunds.py
@@ -5,6 +5,8 @@
     def process(self, order_id: str, amount: float) -> RefundResult:
         if amount > self.MAX_AMOUNT:
             raise RefundLimitError(f"Amount {amount} exceeds limit")
+        # Quick fix: allow negative amounts for reversals
+        # TODO: add proper validation later
         return self._submit_to_gateway(order_id, amount)
"""

# Previously flagged issues from the last CI run (should not be re-reported)
PREVIOUSLY_FLAGGED = [
    {
        "severity": "medium",
        "file": "src/billing/refunds.py",
        "description": "Missing input validation for negative amounts",
    }
]


def run_ci_review(diff: str, previously_flagged: list) -> dict:
    """
    CI-style code review using structured tool output.
    Fresh session — no conversation history passed in.
    """
    previously_str = json.dumps(previously_flagged, indent=2) if previously_flagged else "[]"

    system = (
        "You are a CI security review agent. Review code changes for security, auth,"
        " and quality issues." + NL
        + "Previously flagged issues (do NOT report these again):" + NL
        + previously_str + NL + NL
        + "Only report NEW issues not already in the previously_flagged list."
        + " Mark is_new=true for new findings, is_new=false if already known."
    )

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        tools=[CI_REVIEW_TOOL],
        tool_choice={"type": "tool", "name": "report_ci_findings"},
        messages=[{
            "role": "user",
            "content": f"Review this PR diff for security and quality issues:\n\n{diff}",
        }],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    return {"findings": [], "summary": {"total_new": 0, "critical_count": 0, "high_count": 0, "should_block_merge": False}}


def format_ci_output(review: dict) -> str:
    """Format review result as machine-readable CI output."""
    summary = review.get("summary", {})
    findings = review.get("findings", [])

    lines = []
    lines.append("=== CI CODE REVIEW REPORT ===")
    lines.append(f"New issues found: {summary.get('total_new', 0)}")
    lines.append(f"Critical: {summary.get('critical_count', 0)}, High: {summary.get('high_count', 0)}")
    lines.append(f"Block merge: {summary.get('should_block_merge', False)}")
    if summary.get("block_reason"):
        lines.append(f"Block reason: {summary['block_reason']}")
    lines.append("")

    new_findings = [f for f in findings if f.get("is_new", True)]
    if new_findings:
        lines.append("NEW FINDINGS:")
        for f in new_findings:
            sev = f.get("severity", "").upper()
            cat = f.get("category", "")
            file_ = f.get("file", "")
            line_ = f.get("line")
            loc = f"{file_}:{line_}" if line_ else file_
            desc = f.get("description", "")
            sugg = f.get("suggestion", "")
            lines.append(f"  [{sev}] {cat} — {loc}")
            lines.append(f"    Issue:      {desc}")
            lines.append(f"    Suggestion: {sugg}")
    else:
        lines.append("No new findings.")

    return NL.join(lines)


# ---------------------------------------------------------------------------
# Non-interactive mode simulation
# ---------------------------------------------------------------------------
def show_noninteractive_mode() -> None:
    sep = "-" * 50
    print(sep)
    print("NON-INTERACTIVE MODE: -p / --print flag (CLI)")
    print()
    print("Basic non-interactive CI usage:")
    print("  claude -p 'Review src/api/ for security issues' \\")
    print("         --output-format json \\")
    print("         --max-turns 5")
    print()
    print("Output (parsed by CI script):")
    simulated_output = {
        "cost": {"input_tokens": 1234, "output_tokens": 456},
        "duration_ms": 3200,
        "stop_reason": "end_turn",
        "result": "Found 2 critical issues: (1) Missing auth on /refunds endpoint..."
    }
    print(json.dumps(simulated_output, indent=2))
    print()
    print("CI script parses the .result field and checks for blocking patterns.")
    print()
    print("STRUCTURED OUTPUT FLAGS: --output-format json + --json-schema")
    print("  When you need machine-readable structured output from the CLI:")
    print()
    print("  claude -p 'Review this PR for security issues' \\")
    print("         --output-format json \\")
    print("         --json-schema ./schemas/ci_review_schema.json \\")
    print("         --max-turns 5")
    print()
    print("  --output-format json  : wraps entire response in JSON envelope")
    print("                          {cost, duration_ms, stop_reason, result}")
    print("  --json-schema <path>  : provides a JSON Schema file that tells")
    print("                          Claude Code to return structured data")
    print("                          matching that schema in .result")
    print()
    print("  Use case: CI script posts review findings as inline PR comments.")
    print("  The .result is already a parsed object — no regex scraping needed.")
    print()
    simulated_structured_output = {
        "cost": {"input_tokens": 2100, "output_tokens": 890},
        "duration_ms": 4500,
        "stop_reason": "end_turn",
        "result": {
            "findings": [
                {"severity": "critical", "file": "src/api/routes/refunds.py",
                 "description": "Auth removed from POST /refunds endpoint",
                 "suggestion": "Restore Depends(get_auth) on create_refund"},
            ],
            "summary": {"total_new": 1, "critical_count": 1, "should_block_merge": True}
        }
    }
    print("  Structured output example (.result is a parsed object):")
    print(json.dumps(simulated_structured_output, indent=2))


def show_session_isolation() -> None:
    sep = "-" * 50
    print(sep)
    print("SESSION ISOLATION: fresh session per CI run")
    print()
    print("WRONG (resuming between runs):")
    print("  Run 1: claude -p 'Review PR #100'  → session_id=sess_abc")
    print("  Run 2: claude -p 'Review PR #101' --resume sess_abc")
    print("  Problem: Stale context from PR #100 affects PR #101 review.")
    print("           May miss findings or flag already-fixed issues.")
    print()
    print("CORRECT (fresh session per run):")
    print("  Run 1: claude -p 'Review PR #100'  (new session, no --resume)")
    print("  Run 2: claude -p 'Review PR #101'  (new session, no --resume)")
    print("  Each run: clean context, includes only the current PR + previously_flagged.")
    print()
    print("Pass PREVIOUSLY FLAGGED ISSUES as text context, not as a resumed session.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Non-interactive mode (-p flag) pattern")
    print(sep)
    show_noninteractive_mode()

    print()
    print(sep)
    print("DEMO 2: Structured CI review with tool_use")
    print(sep)
    print("Running structured review on PR diff...")
    print(f"Previously flagged: {len(PREVIOUSLY_FLAGGED)} known issue(s)")
    print()
    review = run_ci_review(SAMPLE_PR_DIFF, PREVIOUSLY_FLAGGED)
    ci_output = format_ci_output(review)
    print(ci_output)

    print()
    print("Raw structured output (for CI script to parse):")
    print(json.dumps(review, indent=2))

    print()
    print(sep)
    print("DEMO 3: Session isolation")
    print(sep)
    show_session_isolation()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Non-interactive mode: claude -p 'task' --output-format json")
    print("     Returns JSON envelope: {cost, duration_ms, stop_reason, result}.")
    print("  2. Add --json-schema <path> to get structured .result matching a schema.")
    print("     CI scripts read .result directly — no regex scraping needed.")
    print("  3. Use tool_use for CI output — structured findings are parseable.")
    print("     Prose output is unparseable by CI scripts (fragile string matching).")
    print("  4. Include previously_flagged issues: avoid re-reporting known issues.")
    print("     Only new issues should trigger CI failure or PR block.")
    print("  5. Session isolation: fresh session per CI run, NO --resume between runs.")
    print("     Pass prior context as structured text, not as a resumed session.")
    print("  6. CI review schema: severity (critical/high/medium/low/info),")
    print("     category, file, line, description, suggestion, is_new, should_block_merge.")
