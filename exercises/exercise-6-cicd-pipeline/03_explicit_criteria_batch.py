"""
Exercise 6 - Steps 4-5: Explicit Review Criteria and Batch Processing

EXAM CONCEPTS:
  1. Explicit criteria vs vague instructions:
       VAGUE:    "be conservative" / "only report high-confidence findings"
       EXPLICIT: "flag SQL injection and unhandled nulls; skip style and naming"
       Vague confidence-based filtering does NOT reduce false positives.
       Explicit categorical criteria DO.

  2. False positive impact on developer trust:
       High false-positive categories undermine confidence in accurate categories.
       If 30% of style findings are false positives, developers start ignoring ALL findings.
       Solution: disable high-FP categories while improving prompts, not blanket "be conservative."

  3. Few-shot examples for consistent output:
       Showing 2-4 examples of (code snippet, correct finding) trains the model
       on boundary cases -- acceptable vs genuine issue.
       More effective than detailed prose descriptions for edge cases.

  4. Message Batches API characteristics:
       50% cost savings vs synchronous API
       Up to 24-hour processing window
       NO guaranteed latency SLA
       NO multi-turn tool calling support (single request/response)
       custom_id field for correlating request/response pairs

  5. API selection by latency requirements:
       BLOCKING workflows (pre-merge checks): use synchronous API
       NON-BLOCKING workflows (overnight reports, weekly audits): use batch API
       The 50% savings only applies when latency tolerance exists.

  Mnemonic: BATCH
    Blocking = synchronous API only
    Async/overnight = batch API (50% savings)
    Twenty-four hour max window (no SLA guarantee)
    Correlate via custom_id
    Half the cost but no multi-turn tool use

Run: uv run python 03_explicit_criteria_batch.py
"""

import json
import time
import anthropic

client = anthropic.Anthropic()
NL = chr(10)

# ---------------------------------------------------------------------------
# Mock code snippets for review
# ---------------------------------------------------------------------------
CODE_SAMPLES = [
    {
        "id": "sample-001",
        "file": "src/auth/login.py",
        "snippet": (
            "def login(username, password):" + NL
            + "    query = f\"SELECT * FROM users WHERE username='{username}'\"" + NL
            + "    user = db.execute(query)" + NL
            + "    if user and user.password == password:" + NL
            + "        return generate_token(user.id)" + NL
        ),
    },
    {
        "id": "sample-002",
        "file": "src/orders/handler.py",
        "snippet": (
            "def get_user_orders(user_id: str) -> list:" + NL
            + "    result = db.query('SELECT * FROM orders WHERE user_id = ?', [user_id])" + NL
            + "    return result or []" + NL
        ),
    },
    {
        "id": "sample-003",
        "file": "src/utils/formatter.py",
        "snippet": (
            "def format_price(amount: float) -> str:" + NL
            + "    return f'${amount:.2f}'" + NL
            + "# using f-string formatting instead of format()" + NL
        ),
    },
]

REVIEW_TOOL = [
    {
        "name": "submit_findings",
        "description": "Submit code review findings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code_id":  {"type": "string"},
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string",
                                         "enum": ["security", "bug", "performance", "style"]},
                            "severity": {"type": "string",
                                         "enum": ["critical", "high", "medium", "low"]},
                            "message":  {"type": "string"},
                        },
                        "required": ["category", "severity", "message"],
                    },
                },
            },
            "required": ["code_id", "findings"],
        },
    }
]


def run_review(code_id: str, snippet: str, system_prompt: str) -> dict:
    """Run a synchronous code review with the given system prompt."""
    messages = [{
        "role": "user",
        "content": f"Review this code snippet (id: {code_id}):" + NL + snippet,
    }]
    for _ in range(5):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=system_prompt,
            tools=REVIEW_TOOL,
            tool_choice={"type": "tool", "name": "submit_findings"},
            messages=messages,
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "submit_findings":
                return block.input
        if resp.stop_reason == "end_turn":
            return {"code_id": code_id, "findings": []}
        messages.append({"role": "assistant", "content": resp.content})
    return {"code_id": code_id, "findings": []}


# ---------------------------------------------------------------------------
# System prompts: vague vs explicit criteria
# ---------------------------------------------------------------------------
SYSTEM_VAGUE = (
    "You are a code reviewer. "
    "Be conservative and only report high-confidence findings. "
    "Review for code quality issues."
)

SYSTEM_EXPLICIT = (
    "You are a code reviewer for a Python codebase." + NL
    + "REPORT these categories:" + NL
    + "  security: SQL injection, hardcoded credentials, injection vulnerabilities" + NL
    + "  bug: unhandled None dereference, uncaught exceptions on external calls" + NL
    + "SKIP these categories (do NOT report):" + NL
    + "  style: formatting, f-string vs format(), variable naming conventions" + NL
    + "  performance: micro-optimizations unless they are O(n^2) or worse" + NL
    + "FEW-SHOT EXAMPLES:" + NL
    + "  GENUINE SECURITY: query = f\"SELECT * FROM users WHERE id='{user_id}'\"" + NL
    + "    -> SQL injection: user input directly interpolated into SQL string." + NL
    + "  NOT AN ISSUE: return result or []" + NL
    + "    -> Defensive default return; not a bug." + NL
    + "  NOT AN ISSUE: f'${amount:.2f}'" + NL
    + "    -> Style preference only; do NOT report." + NL
)


# ---------------------------------------------------------------------------
# DEMO 1: Vague vs explicit criteria comparison
# ---------------------------------------------------------------------------
def demo_explicit_vs_vague_criteria() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 1: Vague vs explicit review criteria")
    print()
    for sample in CODE_SAMPLES:
        sid, sfile, snippet = sample["id"], sample["file"], sample["snippet"]
        print(f"--- {sfile} ({sid}) ---")

        result_vague = run_review(sid + "-vague", snippet, SYSTEM_VAGUE)
        findings_vague = result_vague.get("findings", [])

        result_explicit = run_review(sid + "-explicit", snippet, SYSTEM_EXPLICIT)
        findings_explicit = result_explicit.get("findings", [])

        print(f"  VAGUE criteria:    {len(findings_vague)} finding(s): "
              + ", ".join(f"[{f['category']}]" for f in findings_vague) if findings_vague else "  VAGUE criteria:    0 findings")
        print(f"  EXPLICIT criteria: {len(findings_explicit)} finding(s): "
              + ", ".join(f"[{f['category']}]" for f in findings_explicit) if findings_explicit else "  EXPLICIT criteria: 0 findings")
        print()


# ---------------------------------------------------------------------------
# DEMO 2: Batch API selection logic
# ---------------------------------------------------------------------------
def demo_batch_api_selection() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 2: Message Batches API -- when to use vs synchronous API")
    print()
    workflows = [
        {
            "name": "Pre-merge check",
            "blocking": True,
            "latency_tolerance": "seconds",
            "api": "SYNCHRONOUS",
            "reason": "Developer waits for result before merging. Batch 24h window unacceptable.",
        },
        {
            "name": "Nightly technical debt report",
            "blocking": False,
            "latency_tolerance": "hours",
            "api": "BATCH (50% savings)",
            "reason": "Overnight job. Results reviewed next morning. 24h window acceptable.",
        },
        {
            "name": "Weekly security audit",
            "blocking": False,
            "latency_tolerance": "hours",
            "api": "BATCH (50% savings)",
            "reason": "Non-blocking. Batch submits hundreds of files at 50% lower cost.",
        },
        {
            "name": "Real-time chat assistant",
            "blocking": True,
            "latency_tolerance": "milliseconds",
            "api": "SYNCHRONOUS",
            "reason": "User interaction requires immediate response.",
        },
    ]
    for wf in workflows:
        tag = "BATCH" if "BATCH" in wf["api"] else "SYNC "
        print(f"  [{tag}] {wf['name']}")
        print(f"         API: {wf['api']}")
        print(f"         Why: {wf['reason']}")
        print()

    print("BATCH API constraints (EXAM: must know all of these):")
    constraints = [
        "50% cost savings vs synchronous API",
        "Up to 24-hour processing window",
        "NO guaranteed latency SLA",
        "NO multi-turn tool calling (single request/response only)",
        "custom_id field used to correlate requests with responses",
        "Poll for completion; resubmit failed requests by custom_id",
    ]
    for c in constraints:
        print(f"  - {c}")


# ---------------------------------------------------------------------------
# DEMO 3: Simulated batch processing workflow with custom_id
# ---------------------------------------------------------------------------
def demo_batch_workflow_simulation() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 3: Batch processing workflow (custom_id correlation)")
    print()
    # Simulate what a batch submission would look like
    batch_requests = [
        {
            "custom_id": f"review-{s['id']}",
            "model": "claude-sonnet-4-6",
            "max_tokens": 512,
            "messages": [{"role": "user", "content": f"Review: {s['snippet'][:80]}..."}],
        }
        for s in CODE_SAMPLES
    ]
    print(f"Batch submission: {len(batch_requests)} requests")
    for req in batch_requests:
        print(f"  custom_id={req['custom_id']!r}")
    print()
    print("After batch completes (~24h), correlate results by custom_id:")
    for req in batch_requests:
        print(f"  {req['custom_id']} -> look up response, post as PR comment if findings found")
    print()
    print("Handling batch failures:")
    print("  1. Identify failed requests by custom_id in batch results")
    print("  2. If failure reason = context limit exceeded -> chunk the document and resubmit")
    print("  3. If failure reason = timeout -> resubmit with same custom_id")
    print("  4. NEVER resubmit all requests -- only the failed ones (cost efficiency)")
    print()
    print("Prompt refinement before large batch:")
    print("  Test on 10-20 samples BEFORE submitting 10,000 documents.")
    print("  Iterate prompt until first-pass success rate is high.")
    print("  Reduces iterative resubmission costs for the full batch.")


if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("DEMO 1: Vague vs explicit review criteria")
    print(sep)
    demo_explicit_vs_vague_criteria()

    print()
    print(sep)
    print("DEMO 2: Batch API selection by latency tolerance")
    print(sep)
    demo_batch_api_selection()

    print()
    print(sep)
    print("DEMO 3: Batch workflow with custom_id correlation")
    print(sep)
    demo_batch_workflow_simulation()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Vague criteria ('be conservative') do NOT reduce false positives.")
    print("     Explicit categorical criteria (REPORT security/bug; SKIP style) DO.")
    print("  2. High false-positive categories erode trust in ALL findings -- disable")
    print("     them while improving prompts, rather than blanket confidence filters.")
    print("  3. Batch API: 50% savings, 24h window, no latency SLA, no multi-turn tool use.")
    print("  4. Synchronous API for blocking workflows (pre-merge); batch for overnight/weekly.")
    print("  5. Use custom_id to correlate batch results; resubmit only failed requests.")
    print("  6. Refine prompts on a sample set before batch-processing large volumes.")
    print("  Mnemonic BATCH: Blocking=sync/Async=batch/Twenty-four hours/Correlate by custom_id/Half cost.")
