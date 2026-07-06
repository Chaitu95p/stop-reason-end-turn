"""
Exercise 6 - Step 3: Multi-Pass Review Architecture

EXAM CONCEPTS:
  1. Attention dilution problem:
       Reviewing 14 files in a single pass causes:
       - Inconsistent depth (some files get detailed feedback, others superficial)
       - Missed bugs in middle files ("lost-in-the-middle" effect)
       - Contradictory findings (pattern flagged in file A, approved in file B)

  2. Multi-pass review architecture:
       PASS 1 (per-file local):   analyze each file individually for local issues
                                  (null dereferences, error handling, security)
       PASS 2 (cross-file integration): separate pass examining cross-file data flow,
                                  shared state, API contract mismatches

  3. Why NOT a bigger context window:
       Larger context windows do NOT solve attention quality issues.
       The model still dilutes attention across many files.
       Focused per-file passes are better than one big pass.

  4. Self-review limitations:
       A model retains reasoning from its own generation.
       Multi-pass with an INDEPENDENT instance (no prior context) catches
       subtle issues better than self-review or extended-thinking instructions.

  5. Confidence alongside findings:
       Having the model self-report confidence per finding enables
       calibrated review routing: high-confidence findings posted directly,
       low-confidence findings routed to human review.

  Mnemonic: FOCUS
    File-by-file local pass first
    Only one concern per pass
    Cross-file integration pass second
    Use independent instances, not self-review
    Split before aggregating -- never all-at-once

Run: uv run python 02_multipass_review.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)

# ---------------------------------------------------------------------------
# Simulated PR files (3 files changed)
# ---------------------------------------------------------------------------
PR_FILES = {
    "src/payments/processor.py": (
        "def process_payment(order_id: str, amount: float) -> dict:" + NL
        + "    customer = get_customer(order_id)  # may return None" + NL
        + "    charge_card(customer['card'], amount)  # KeyError if None" + NL
        + "    return {'success': True, 'order': order_id}" + NL
    ),
    "src/orders/lookup.py": (
        "def get_order(order_id: str) -> dict:" + NL
        + "    result = db.query(f\"SELECT * FROM orders WHERE id='{order_id}'\")" + NL
        + "    return result[0] if result else {}" + NL
    ),
    "src/notifications/email.py": (
        "def send_receipt(customer_email: str, order: dict) -> None:" + NL
        + "    amount = order['amount']  # may KeyError if order is empty" + NL
        + "    smtp.send(customer_email, f'Your receipt: ${amount}')" + NL
    ),
}

# Cross-file integration issue: process_payment passes customer['card'] to charge_card,
# but get_customer returns None on lookup failure -> cross-file None propagation bug.


LOCAL_REVIEW_TOOL = [
    {
        "name": "report_local_findings",
        "description": "Report local (within-file) code quality findings for the current file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file": {"type": "string"},
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "line":       {"type": ["integer", "null"]},
                            "issue":      {"type": "string"},
                            "severity":   {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1,
                                           "description": "Model confidence 0.0-1.0"},
                        },
                        "required": ["issue", "severity", "confidence"],
                    },
                },
            },
            "required": ["file", "findings"],
        },
    }
]

INTEGRATION_REVIEW_TOOL = [
    {
        "name": "report_integration_findings",
        "description": "Report cross-file integration issues after analyzing data flow across all files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "files_involved": {"type": "array", "items": {"type": "string"}},
                            "issue":          {"type": "string"},
                            "severity":       {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                            "confidence":     {"type": "number", "minimum": 0, "maximum": 1},
                        },
                        "required": ["files_involved", "issue", "severity", "confidence"],
                    },
                },
            },
            "required": ["findings"],
        },
    }
]


def review_file_local(file_path: str, content: str) -> dict:
    """PASS 1: Review a single file for local issues."""
    messages = [{
        "role": "user",
        "content": (
            f"Review this file for local code quality issues (bugs, null dereferences, "
            f"error handling, security). Report findings via report_local_findings." + NL
            + f"FILE: {file_path}" + NL + content
        ),
    }]
    system = (
        "You are a code reviewer. Focus ONLY on local issues within this single file. "
        "Include confidence scores (0.0-1.0) for each finding. "
        "Report via report_local_findings tool."
    )
    for _ in range(5):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=system,
            tools=LOCAL_REVIEW_TOOL,
            tool_choice={"type": "tool", "name": "report_local_findings"},
            messages=messages,
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "report_local_findings":
                return block.input
        if resp.stop_reason == "end_turn":
            return {"file": file_path, "findings": []}
        messages.append({"role": "assistant", "content": resp.content})
    return {"file": file_path, "findings": []}


def review_integration(all_files: dict, local_findings: list) -> dict:
    """PASS 2: Cross-file integration review."""
    files_section = NL.join(
        f"=== {path} ===" + NL + content
        for path, content in all_files.items()
    )
    local_section = json.dumps(local_findings, indent=2)
    messages = [{
        "role": "user",
        "content": (
            "Analyze CROSS-FILE data flow issues: None propagation, "
            "API contract mismatches, shared state bugs." + NL
            + "Local findings already reported (do not duplicate):" + NL
            + local_section + NL
            + "ALL FILES:" + NL + files_section + NL
            + "Report via report_integration_findings tool."
        ),
    }]
    system = (
        "You are a code reviewer focused ONLY on cross-file integration issues. "
        "Look for data flow problems between modules. "
        "Include confidence scores. Report via report_integration_findings."
    )
    for _ in range(5):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=system,
            tools=INTEGRATION_REVIEW_TOOL,
            tool_choice={"type": "tool", "name": "report_integration_findings"},
            messages=messages,
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "report_integration_findings":
                return block.input
        if resp.stop_reason == "end_turn":
            return {"findings": []}
        messages.append({"role": "assistant", "content": resp.content})
    return {"findings": []}


# ---------------------------------------------------------------------------
# DEMO 1: Multi-pass review architecture
# ---------------------------------------------------------------------------
def demo_multipass_review() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 1: Multi-pass review (per-file local + cross-file integration)")
    print()
    all_local = []
    print("PASS 1: Per-file local analysis")
    for path, content in PR_FILES.items():
        print(f"  Reviewing {path}...")
        result = review_file_local(path, content)
        findings = result.get("findings", [])
        all_local.extend(findings)
        print(f"    -> {len(findings)} local finding(s)")
        for f in findings:
            conf = f.get("confidence", 0)
            print(f"       [{f['severity'].upper()} conf={conf:.1f}] {f['issue'][:70]}")

    print()
    print("PASS 2: Cross-file integration analysis")
    integration_result = review_integration(PR_FILES, all_local)
    integration_findings = integration_result.get("findings", [])
    print(f"  -> {len(integration_findings)} cross-file finding(s)")
    for f in integration_findings:
        files = ", ".join(f.get("files_involved", []))
        conf = f.get("confidence", 0)
        print(f"    [{f['severity'].upper()} conf={conf:.1f}] [{files}] {f['issue'][:80]}")

    print()
    print(f"Total: {len(all_local)} local + {len(integration_findings)} integration findings")


# ---------------------------------------------------------------------------
# DEMO 2: Single-pass vs multi-pass architecture comparison
# ---------------------------------------------------------------------------
def demo_architecture_comparison() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 2: Architecture comparison")
    print()
    scenarios = [
        ("Single-pass (14 files at once)",
         ["Attention dilution: 14 files compete for model attention",
          "Lost-in-the-middle: files 5-9 get less attention",
          "Contradictory: same pattern flagged in file A, approved in file B",
          "Missed: cross-file None propagation is hard to spot in bulk"]),
        ("Multi-pass (this demo -- per-file + integration)",
         ["Consistent depth: each file reviewed in full isolation",
          "No middle dilution: every file is the ONLY file in its pass",
          "No contradictions: local issues per file, integration issues separate",
          "Catches cross-file bugs: dedicated integration pass"]),
    ]
    for arch, notes in scenarios:
        print(f"  {arch}:")
        for n in notes:
            print(f"    - {n}")
        print()
    print("EXAM TRAP: 'Use a higher-tier model with larger context window'")
    print("  WRONG: larger context windows do NOT solve attention quality issues.")
    print("  CORRECT: focused per-file passes are better than one big pass.")


if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("DEMO 1: Multi-pass review architecture")
    print(sep)
    demo_multipass_review()

    print()
    print(sep)
    print("DEMO 2: Architecture comparison")
    print(sep)
    demo_architecture_comparison()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Single-pass review of many files causes attention dilution and")
    print("     contradictory findings -- split into per-file local passes.")
    print("  2. Run a SEPARATE integration pass for cross-file data flow analysis.")
    print("  3. A larger context window does NOT fix attention quality -- use focused passes.")
    print("  4. Include confidence scores per finding to route low-confidence ones")
    print("     to human review, preserving limited reviewer capacity.")
    print("  5. Independent instances (no generation context) catch subtle issues")
    print("     better than self-review even with 'review critically' prompts.")
    print("  Mnemonic FOCUS: File-by-file/Only one concern/Cross-file second/Use independent/Split first.")
