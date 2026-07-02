"""
Domain 5 - Task 5.4: Codebase Context Management

EXAM CONCEPTS:
  1. Context degradation: in extended sessions, early context gets compressed.
     Generic answers replace specific ones. "Use appropriate error handling"
     instead of "catch RefundLimitError and log to /var/log/billing.log".

  2. Scratchpad file pattern: agent writes key findings to a file as it works.
     Re-reads the file at the start of each reasoning step.
     Survives context window compression unlike in-memory conversation history.

  3. Subagent delegation for verbose exploration: delegate large file reads
     to subagents to protect the main coordinator's context window.

  4. Crash recovery: export key findings to a manifest file during long tasks.
     On restart, read the manifest to resume without full re-exploration.

  5. /compact concept (Claude Code): when context fills, use /compact to
     summarize old context. Key findings should be in scratchpad BEFORE
     compaction, not just in conversation history.

Run: uv run python 04_codebase_context.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Simulated codebase (in-memory, representing what file reads would return)
# ---------------------------------------------------------------------------
MOCK_CODEBASE = {
    "src/billing/refunds.py": """
class RefundProcessor:
    MAX_AMOUNT = 500.0  # USD policy limit
    LOG_PATH = "/var/log/billing/refunds.log"

    def process(self, order_id: str, amount: float) -> RefundResult:
        if amount > self.MAX_AMOUNT:
            raise RefundLimitError(f"Amount {amount} exceeds limit {self.MAX_AMOUNT}")
        return self._submit_to_gateway(order_id, amount)

    def _submit_to_gateway(self, order_id: str, amount: float) -> RefundResult:
        # Calls payment-gateway v3 API at https://pay.internal/v3/refunds
        pass
""",
    "src/billing/credits.py": """
class CreditManager:
    GOODWILL_CAP = 50.0   # Max goodwill credit per customer per year
    PROMO_CODES = {"SORRY10": 10.0, "VIP20": 20.0}

    def issue_goodwill(self, customer_id: str, amount: float) -> Credit:
        if amount > self.GOODWILL_CAP:
            raise CreditLimitError("Exceeds annual goodwill cap")
        return Credit(customer_id=customer_id, amount=amount, type="goodwill")
""",
    "src/api/routes.py": """
@router.post("/refunds")
async def create_refund(request: RefundRequest, auth: Auth = Depends(get_auth)):
    # Requires: billing:write scope
    processor = RefundProcessor()
    return processor.process(request.order_id, request.amount)

@router.post("/credits")
async def issue_credit(request: CreditRequest, auth: Auth = Depends(get_auth)):
    # Requires: billing:admin scope
    mgr = CreditManager()
    return mgr.issue_goodwill(request.customer_id, request.amount)
""",
    "tests/test_refunds.py": """
def test_refund_within_limit():
    p = RefundProcessor()
    result = p.process("ORD-100", 100.0)
    assert result.status == "approved"

def test_refund_exceeds_limit():
    p = RefundProcessor()
    with pytest.raises(RefundLimitError):
        p.process("ORD-100", 999.0)
""",
}


# ---------------------------------------------------------------------------
# Context degradation demonstration
# ---------------------------------------------------------------------------
def show_context_degradation() -> None:
    sep = "-" * 50
    print(sep)
    print("CONTEXT DEGRADATION over extended sessions")
    print()
    print("Early session — specific and accurate:")
    print("  Q: How should errors be handled in the refund processor?")
    print("  A: Catch RefundLimitError when amount exceeds $500.")
    print("     Log the error to /var/log/billing/refunds.log")
    print("     Return HTTP 422 to the caller with the limit message.")
    print()
    print("Late session (after context compression):")
    print("  Q: How should errors be handled in the refund processor?")
    print("  A: Use appropriate error handling for refund operations.")
    print("     Ensure errors are logged and the user is notified.")
    print()
    print("CAUSE: Early conversation (where RefundLimitError, $500, /var/log/ appeared)")
    print("was compressed into a summary that lost specific details.")
    print("SOLUTION: Scratchpad file with key findings, re-read before each step.")


# ---------------------------------------------------------------------------
# Scratchpad file pattern (simulated)
# ---------------------------------------------------------------------------
SCRATCHPAD = {}   # simulates an in-memory scratchpad (would be a file in real Claude Code)


def write_to_scratchpad(key: str, value) -> None:
    """Agent writes findings to scratchpad as it explores."""
    SCRATCHPAD[key] = value
    print(f"  [Scratchpad] Wrote: {key} = {str(value)[:80]}")


def read_scratchpad() -> dict:
    """Agent re-reads scratchpad at the start of each reasoning step."""
    return SCRATCHPAD.copy()


def explore_codebase_with_scratchpad(task: str) -> str:
    """
    Agent explores codebase, writing key findings to scratchpad as it goes.
    Then reads scratchpad before generating final answer.
    """
    # Step 1: Read key files (simulated)
    refund_content = MOCK_CODEBASE["src/billing/refunds.py"]
    write_to_scratchpad("refund_limit_usd", 500.0)
    write_to_scratchpad("refund_log_path", "/var/log/billing/refunds.log")
    write_to_scratchpad("refund_error_class", "RefundLimitError")
    write_to_scratchpad("gateway_api", "https://pay.internal/v3/refunds")

    credit_content = MOCK_CODEBASE["src/billing/credits.py"]
    write_to_scratchpad("goodwill_cap_usd", 50.0)
    write_to_scratchpad("promo_codes", {"SORRY10": 10.0, "VIP20": 20.0})

    route_content = MOCK_CODEBASE["src/api/routes.py"]
    write_to_scratchpad("refund_auth_scope", "billing:write")
    write_to_scratchpad("credit_auth_scope", "billing:admin")

    # Step 2: Re-read scratchpad before generating answer
    facts = read_scratchpad()
    print()
    print(f"  [Scratchpad] Re-reading before final answer: {list(facts.keys())}")

    # Use Claude with scratchpad facts injected
    system = (
        "You are a code analysis agent. Use ONLY the facts in the scratchpad to answer." + NL
        + "Scratchpad contents:" + NL
        + json.dumps(facts, indent=2)
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": task}],
    )
    return next((b.text for b in resp.content if hasattr(b, "text")), "")


# ---------------------------------------------------------------------------
# Subagent delegation pattern
# ---------------------------------------------------------------------------
def demo_subagent_delegation() -> None:
    """
    Coordinator delegates large file reads to a subagent.
    Subagent returns a summary, not the full content.
    This protects the coordinator's context window.
    """
    sep = "-" * 50
    print(sep)
    print("SUBAGENT DELEGATION: coordinator delegates verbose reads")
    print()

    # Coordinator prompt
    coordinator_task = "Summarize the billing module: what limits exist and what auth scopes are needed?"

    # Subagent processes all file content (would be delegated via Task tool in real Claude Code)
    all_content = NL.join(f"=== {path} ==={NL}{content}"
                          for path, content in MOCK_CODEBASE.items()
                          if "billing" in path or "api" in path)

    subagent_resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system="You are a code summarization subagent. Extract key limits, thresholds, and auth requirements.",
        messages=[{"role": "user", "content": f"Summarize this code:\n{all_content}"}],
    )
    subagent_summary = next((b.text for b in subagent_resp.content if hasattr(b, "text")), "")

    print(f"  Raw code sent to subagent: {len(all_content)} chars")
    print(f"  Summary returned to coordinator: {len(subagent_summary)} chars")
    print(f"  Context saved: {(1 - len(subagent_summary)/len(all_content))*100:.0f}%")
    print()
    print(f"  Subagent summary:\n  {subagent_summary[:400]}")


# ---------------------------------------------------------------------------
# Crash recovery manifest pattern
# ---------------------------------------------------------------------------
def demo_crash_recovery() -> None:
    sep = "-" * 50
    print(sep)
    print("CRASH RECOVERY: manifest export pattern")
    print()

    # Simulate work done before crash
    manifest = {
        "task": "Audit billing module for security issues",
        "completed_files": [
            "src/billing/refunds.py",
            "src/billing/credits.py",
        ],
        "pending_files": [
            "src/api/routes.py",
            "tests/test_refunds.py",
        ],
        "findings_so_far": [
            {"file": "refunds.py", "issue": "Gateway URL hardcoded, should use env var", "severity": "medium"},
            {"file": "credits.py", "issue": "No rate limiting on goodwill credits", "severity": "high"},
        ],
        "session_id": "sess_audit_2024",
        "checkpoint_at": "2024-01-15T10:45:00Z",
    }

    print("  Manifest saved before crash:")
    print(json.dumps(manifest, indent=2))
    print()
    print("  After crash/restart, agent reads manifest and resumes:")
    print(f"  -> Skip already-processed: {manifest['completed_files']}")
    print(f"  -> Continue with: {manifest['pending_files']}")
    print(f"  -> Existing findings preserved: {len(manifest['findings_so_far'])} issues")
    print()
    print("  Without manifest: full re-exploration required (expensive)")
    print("  With manifest: resume from checkpoint (efficient)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Context degradation in extended sessions")
    print(sep)
    show_context_degradation()

    print()
    print(sep)
    print("DEMO 2: Scratchpad file pattern")
    print(sep)
    print("Exploring codebase with scratchpad pattern...")
    answer = explore_codebase_with_scratchpad(
        "How should errors be handled in the refund processor, and what log path should be used?"
    )
    print()
    print(f"Final answer (using scratchpad facts):")
    print(f"  {answer}")

    print()
    print(sep)
    print("DEMO 3: Subagent delegation for verbose reads")
    print(sep)
    demo_subagent_delegation()

    print()
    print(sep)
    print("DEMO 4: Crash recovery via manifest export")
    print(sep)
    demo_crash_recovery()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Context degradation: long sessions → compressed history → vague answers.")
    print("     Scratchpad file preserves specific findings across compressions.")
    print("  2. Agent writes findings to scratchpad AS IT EXPLORES, not after.")
    print("     Re-reads scratchpad at the START of each reasoning step.")
    print("  3. Delegate verbose file reads to subagents — they summarize and return")
    print("     a compact result, protecting the coordinator's context window.")
    print("  4. Crash recovery: export manifest after each file processed.")
    print("     On restart, read manifest to skip completed work.")
    print("  5. /compact in Claude Code: run BEFORE context fills, not after.")
    print("     Key findings must be in scratchpad BEFORE compaction.")
