"""
Domain 3 - Task 3.4: Plan Mode vs Direct Execution

EXAM CONCEPTS:
  1. Plan mode: Claude explores the codebase and proposes an implementation
     plan for USER APPROVAL before making any changes. Triggered by:
     - Multi-file changes (touching 3+ files)
     - Architectural decisions (which pattern to use)
     - Unknown scope (need to explore to understand impact)
     - User preference ("always plan before touching billing code")

  2. Direct execution: Claude makes the change immediately. Appropriate for:
     - Single-file, obvious changes (fix a typo, rename a variable)
     - Changes where the user gave specific, detailed instructions
     - Low-risk, easily reversible modifications

  3. EnterPlanMode signal: When Claude identifies a task as requiring planning,
     it should use EnterPlanMode to switch to plan mode and write a plan
     before implementing anything.

  4. Anti-pattern: starting implementation before understanding scope.
     Multi-file changes discovered mid-implementation cause partial,
     inconsistent states that are hard to roll back.

  5. Plan content: numbered steps, files affected, architectural decisions,
     trade-offs considered. Plan is approved by the user before coding begins.

  6. Explore subagent: for open-ended discovery tasks (find all callers of X,
     map the full module structure), spawn an Explore subagent to do the
     verbose reading WITHOUT filling the main session's context window.
     Use during the plan-mode investigation phase, before writing the plan.
     Explore runs read-only and returns a compact summary.

Run: uv run python 04_plan_vs_direct.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Classification tool
# ---------------------------------------------------------------------------
CLASSIFY_TOOL = {
    "name": "classify_task",
    "description": (
        "Classify a development task as requiring 'plan_mode' or 'direct_execution'. "
        "plan_mode: multi-file, architectural choice, unknown scope, or user-specified. "
        "direct_execution: single-file, obvious fix, specific detailed instructions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "classification": {
                "type": "string",
                "enum": ["plan_mode", "direct_execution"],
            },
            "primary_reason": {
                "type": "string",
                "enum": [
                    "multi_file_change",      # touches 3+ files
                    "architectural_decision",  # choice between patterns/approaches
                    "unknown_scope",           # need exploration to understand impact
                    "user_specified",          # user said "plan first"
                    "single_file_obvious",     # clear single-file change
                    "detailed_instructions",   # user gave specific step-by-step instructions
                ],
            },
            "reasoning": {
                "type": "string",
                "description": "One sentence explaining why this classification is correct.",
            },
            "files_likely_affected": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of files likely touched (estimate if unknown).",
            },
        },
        "required": ["classification", "primary_reason", "reasoning", "files_likely_affected"],
    },
}


# ---------------------------------------------------------------------------
# Test task descriptions
# ---------------------------------------------------------------------------
TASKS = [
    {
        "id": 1,
        "description": "Fix the typo 'refund_id' → 'refund_id' (misspelled as 'refun_id') in src/billing/refunds.py line 45.",
        "expected": "direct_execution",
        "reason": "Single-file, exact location given, trivial fix",
    },
    {
        "id": 2,
        "description": "Add user authentication to the billing API. We need JWT tokens, middleware, and the routes should check permissions.",
        "expected": "plan_mode",
        "reason": "Multi-file, architectural decision (JWT vs session), unknown scope",
    },
    {
        "id": 3,
        "description": "Change the refund limit from $500 to $750 in src/billing/refunds.py:MAX_AMOUNT.",
        "expected": "direct_execution",
        "reason": "Single-file, specific location, obvious change",
    },
    {
        "id": 4,
        "description": "Refactor the billing module to use a repository pattern instead of direct database calls.",
        "expected": "plan_mode",
        "reason": "Architectural decision, multi-file, significant scope",
    },
    {
        "id": 5,
        "description": "Can you make our API faster? Users are complaining it's slow.",
        "expected": "plan_mode",
        "reason": "Unknown scope — need to profile and explore to understand bottlenecks",
    },
    {
        "id": 6,
        "description": "Add a docstring to the process_refund method in src/billing/refunds.py.",
        "expected": "direct_execution",
        "reason": "Single-file, low-risk, trivial addition",
    },
    {
        "id": 7,
        "description": "Please plan first, then add rate limiting to all API endpoints.",
        "expected": "plan_mode",
        "reason": "User explicitly said 'plan first' + multi-file change",
    },
]


def classify_task(description: str) -> dict:
    """Use Claude to classify a task as plan_mode or direct_execution."""
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=(
            "You are a Claude Code expert. Classify development tasks as requiring"
            " 'plan_mode' or 'direct_execution'." + NL
            + "plan_mode: multi-file, architectural decision, unknown scope, or user requested planning." + NL
            + "direct_execution: single-file obvious fix, specific instructions, low risk."
        ),
        tools=[CLASSIFY_TOOL],
        tool_choice={"type": "tool", "name": "classify_task"},
        messages=[{"role": "user", "content": f"Task: {description}"}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    return {}


# ---------------------------------------------------------------------------
# Show plan example
# ---------------------------------------------------------------------------
def show_plan_example() -> None:
    sep = "-" * 50
    print(sep)
    print("EXAMPLE PLAN (what Claude produces in plan mode)")
    print(sep)
    plan = """
Task: Add JWT authentication to the billing API

## Plan

### Files to create
1. src/auth/jwt.py — JWT token creation and validation
2. src/auth/middleware.py — FastAPI middleware to check Authorization header
3. src/auth/dependencies.py — get_current_user() Depends() function

### Files to modify
4. src/api/routes/refunds.py — add Depends(get_current_user) to all handlers
5. src/api/routes/credits.py — same
6. pyproject.toml — add python-jose, passlib dependencies

### Test files to create
7. tests/test_auth.py — unit tests for JWT functions and middleware

### Architectural decisions
- JWT (stateless) vs session (stateful): chose JWT for horizontal scaling
- Token expiry: 15 minutes for access token, 7 days for refresh token
- Scope model: billing:read, billing:write, billing:admin (matches existing routes)

### Steps
1. Install python-jose, passlib
2. Create src/auth/jwt.py with create_token(), decode_token()
3. Create src/auth/middleware.py
4. Create src/auth/dependencies.py
5. Modify route files (2 files)
6. Write tests

Shall I proceed with this plan?
"""
    print(plan)


# ---------------------------------------------------------------------------
# DEMO 3: Explore subagent pattern (simulated)
# ---------------------------------------------------------------------------
def demo_explore_subagent() -> None:
    sep = "-" * 50
    print(sep)
    print("DEMO 3: Explore subagent for plan-mode investigation")
    print()
    print("SCENARIO: Plan 'Add rate limiting to all API endpoints'")
    print()
    print("Without Explore subagent (fills main session context):")
    print("  Main session reads every route file, middleware, config file...")
    print("  All file content accumulates in context window.")
    print("  By the time the plan is written, context is 60% full.")
    print()
    print("With Explore subagent (protects main session):")
    print("  Main session: spawn Explore subagent with goal:")
    print('  "Find all API route files and count endpoints in each."')
    print()

    # Simulate the Explore subagent doing the discovery work
    explore_task = (
        "Given a project with FastAPI routes, list all endpoint files "
        "and estimate how many routes each contains. "
        "Return a compact summary only."
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=(
            "You are an Explore subagent. Your goal is codebase discovery — "
            "read files and return a COMPACT structured summary. "
            "Never return raw file content. Synthesize into a short list." + NL
            + "Simulated project structure:" + NL
            + "  src/api/routes/refunds.py    (3 endpoints: POST /refunds, GET /refunds/{id}, DELETE /refunds/{id})" + NL
            + "  src/api/routes/credits.py    (2 endpoints: POST /credits, GET /credits/{customer_id})" + NL
            + "  src/api/routes/customers.py  (4 endpoints: CRUD + GET /customers/{id}/orders)" + NL
            + "  src/api/middleware.py        (auth middleware, no routes)"
        ),
        messages=[{"role": "user", "content": explore_task}],
    )
    summary = next((b.text for b in resp.content if hasattr(b, "text")), "")

    print("  Explore subagent returns compact summary:")
    print(f"  {summary[:400]}")
    print()
    print("  Main session receives summary (not raw file content).")
    print("  Main session context window: largely unaffected.")
    print("  Plan can now be written with full context budget available.")
    print()
    print("KEY DISTINCTION: Explore vs direct reading")
    uses = [
        ("Direct Read in main session", "Use for 1-3 specific files with known paths"),
        ("Explore subagent", "Use for open-ended discovery: 'find all X', 'map module Y'"),
    ]
    for approach, when in uses:
        print(f"  {approach:35s} — {when}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60
    print(sep)
    print("DEMO 1: Task classification — plan mode vs direct execution")
    print(sep)
    print()

    correct = 0
    for task in TASKS:
        result = classify_task(task["description"])
        classification = result.get("classification", "unknown")
        reason = result.get("primary_reason", "")
        reasoning = result.get("reasoning", "")
        files = result.get("files_likely_affected", [])
        is_correct = classification == task["expected"]
        if is_correct:
            correct += 1
        status = "CORRECT" if is_correct else "WRONG"

        print(f"Task {task['id']}: [{status}]")
        print(f"  Description: {task['description'][:80]}")
        print(f"  Classification: {classification} (reason: {reason})")
        print(f"  Reasoning: {reasoning}")
        print(f"  Files likely affected: {files}")
        if not is_correct:
            print(f"  Expected: {task['expected']} — {task['reason']}")
        print()

    print(f"Score: {correct}/{len(TASKS)} correct")

    print()
    print(sep)
    print("DEMO 2: What a plan looks like")
    print(sep)
    show_plan_example()

    print()
    print(sep)
    print("DEMO 3: Explore subagent for verbose codebase discovery")
    print(sep)
    demo_explore_subagent()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Plan mode triggers: multi-file, architectural decision,")
    print("     unknown scope, or user says 'plan first'.")
    print("  2. Direct execution: single-file, obvious fix, specific instructions.")
    print("  3. Anti-pattern: starting multi-file changes without a plan.")
    print("     Partial implementations are hard to roll back.")
    print("  4. Plan content: numbered steps, files affected, decisions, trade-offs.")
    print("     User reviews and approves BEFORE any code is written.")
    print("  5. In Claude Code: Enter plan mode → explore → write plan → ExitPlanMode.")
    print("     User sees the plan and must approve before implementation begins.")
    print("  6. Explore subagent: spawn for open-ended discovery to protect the main")
    print("     session's context window. Returns compact summary, not raw file content.")
