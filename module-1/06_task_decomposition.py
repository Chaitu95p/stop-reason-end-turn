"""
Domain 1 - Task 1.6: Task Decomposition Strategies for Complex Workflows

EXAM CONCEPTS:
  1. PROMPT CHAINING (fixed sequential pipeline):
     Break tasks into predetermined sequential steps.
     Best for: predictable multi-aspect reviews, known structure.
     Example: analyze each file individually → cross-file integration pass.

  2. DYNAMIC ADAPTIVE DECOMPOSITION:
     Generate subtasks based on intermediate findings.
     Best for: open-ended investigation tasks where scope is unknown.
     Example: map codebase → identify high-impact areas → adapt plan.

  3. SPLITTING LARGE REVIEWS:
     Per-file local analysis passes PLUS separate cross-file integration pass.
     Why: prevents attention dilution when processing many files at once.

  4. OPEN-ENDED TASK DECOMPOSITION:
     First MAP structure → IDENTIFY high-impact areas → CREATE prioritized plan
     that ADAPTS as dependencies are discovered.

  KEY TRADEOFF:
    Prompt chaining: deterministic, easy to debug, but inflexible.
    Dynamic: adaptive, handles unknowns, but harder to predict/debug.

Run: uv run python 06_task_decomposition.py
"""

import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Sample "files" to review
# ---------------------------------------------------------------------------
FILES = {
    "auth.py": """\
def login(username, password):
    # Returns True if credentials match
    if username == "admin" and password == "admin123":
        return True
    return False
""",
    "api.py": """\
def get_user_data(user_id):
    # Fetch user from database
    query = "SELECT * FROM users WHERE id=" + user_id  # potential injection
    return db.execute(query)

def process_request(req):
    token = req.headers.get("auth_token")
    # Missing: call auth.verify_token(token) before proceeding
    return handle(req)
""",
    "utils.py": """\
import hashlib

def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()  # weak hash

def format_date(ts):
    # Format Unix timestamp to readable date
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
""",
}


def call_claude(system: str, user: str, max_tokens: int = 512) -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text.strip()


# ---------------------------------------------------------------------------
# PATTERN A: Prompt Chaining (fixed sequential pipeline)
# ---------------------------------------------------------------------------
def prompt_chaining_review(files: dict) -> dict:
    """
    Fixed pipeline:
    Step 1: Analyze each file locally for per-file issues.
    Step 2: Cross-file integration pass (data flow, dependency issues).
    Step 3: Severity summary.

    Advantages: predictable, parallelizable per file, depth per file.
    Use when: code review with known aspects to check (security, logic, style).
    """
    print("=== PROMPT CHAINING: Fixed sequential pipeline ===")

    # Step 1: Per-file analysis (could be parallelized)
    per_file_findings = {}
    for filename, content in files.items():
        print(f"  Step 1a: Analyzing {filename}...")
        findings = call_claude(
            "You are a security code reviewer. Find bugs and security issues.",
            f"Review this file for LOCAL issues only (bugs within this file):" + NL
            + f"File: {filename}" + NL + "```python" + NL + content + NL + "```" + NL
            + "List issues as: LINE | ISSUE | SEVERITY(critical/high/medium/low)",
        )
        per_file_findings[filename] = findings
        print(f"    Found: {findings[:80]}...")

    # Step 2: Cross-file integration pass
    print("  Step 2: Cross-file integration pass...")
    all_findings_text = NL.join(
        f"=== {fn} ===" + NL + findings
        for fn, findings in per_file_findings.items()
    )
    files_text = NL.join(
        f"=== {fn} ===" + NL + "```python" + NL + content + NL + "```"
        for fn, content in files.items()
    )
    cross_file = call_claude(
        "You are a code reviewer focused on CROSS-FILE dependencies and data flow.",
        "Identify issues that SPAN multiple files (e.g., missing auth checks, "
        "data flowing insecurely between modules)." + NL + NL
        + "Files:" + NL + files_text + NL + NL
        + "Per-file findings:" + NL + all_findings_text,
        max_tokens=400,
    )
    print(f"  Cross-file: {cross_file[:80]}...")

    # Step 3: Summary
    print("  Step 3: Severity summary...")
    summary = call_claude(
        "You are a technical lead. Summarize code review findings.",
        "Summarize these findings by severity:" + NL + all_findings_text + NL + NL + cross_file,
        max_tokens=300,
    )

    return {
        "per_file_findings": per_file_findings,
        "cross_file_findings": cross_file,
        "summary": summary,
        "pattern": "prompt_chaining",
    }


# ---------------------------------------------------------------------------
# PATTERN B: Dynamic Adaptive Decomposition
# ---------------------------------------------------------------------------
def dynamic_decomposition(task: str, context: str) -> dict:
    """
    Adaptive plan: LLM decides what subtasks to generate based on context.
    Each step's output informs the next step's plan.

    Use when: open-ended investigation, unknown scope, adapts to discoveries.
    """
    print("=== DYNAMIC DECOMPOSITION: Adaptive investigation ===")

    # Step 1: Map structure and identify investigation areas
    print("  Phase 1: Map codebase structure and identify high-impact areas...")
    mapping = call_claude(
        "You are a senior engineer planning a code investigation.",
        f"Task: {task}" + NL + NL
        + f"Codebase overview:" + NL + context + NL + NL
        + "Generate 3-5 specific investigation subtasks, prioritized by impact." + NL
        + "Output format: PRIORITY | SUBTASK | REASON" + NL
        + "Order from highest to lowest priority.",
        max_tokens=300,
    )
    print(f"  Investigation plan:" + NL + "    " + mapping[:200].replace(NL, NL + "    "))

    # Step 2: Execute top-priority subtask (adaptive -- based on phase 1 output)
    print("  Phase 2: Execute highest-priority subtask...")
    execution = call_claude(
        "You are a code reviewer executing an investigation plan.",
        f"Execute the FIRST subtask from this plan:" + NL + mapping + NL + NL
        + "Codebase:" + NL + context + NL + NL
        + "Report findings, and note any unexpected dependencies discovered.",
        max_tokens=400,
    )
    print(f"  Findings: {execution[:100]}...")

    # Step 3: Adapt plan based on discoveries
    print("  Phase 3: Adapt remaining plan based on findings...")
    adapted = call_claude(
        "You are updating an investigation plan based on discoveries.",
        f"Original plan:" + NL + mapping + NL + NL
        + f"New findings:" + NL + execution + NL + NL
        + "What additional subtasks should be added based on these discoveries? "
        + "Output: NEW_SUBTASK | TRIGGERED_BY",
        max_tokens=200,
    )
    print(f"  Adapted plan additions: {adapted[:100]}...")

    return {
        "initial_plan": mapping,
        "execution_findings": execution,
        "adapted_plan": adapted,
        "pattern": "dynamic_decomposition",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Prompt Chaining (fixed sequential pipeline)")
    print("Use case: predictable multi-file code review")
    print(sep)
    chain_result = prompt_chaining_review(FILES)
    print()
    print("SUMMARY:")
    print(chain_result["summary"][:400])

    print()
    print(sep)
    print("DEMO 2: Dynamic Adaptive Decomposition")
    print("Use case: open-ended investigation ('add comprehensive tests')")
    print(sep)
    codebase_summary = "auth.py: authentication module | api.py: API endpoints | utils.py: utilities"
    dynamic_result = dynamic_decomposition(
        task="Add comprehensive tests to this legacy codebase",
        context=codebase_summary,
    )

    print()
    print(sep)
    print("COMPARISON:")
    print("  Prompt Chaining:")
    print("    + Predictable, parallelizable, easy to debug")
    print("    + Each file gets FULL attention (no dilution)")
    print("    - Inflexible if scope changes mid-review")
    print("    Best for: known structure, multi-aspect reviews")
    print()
    print("  Dynamic Decomposition:")
    print("    + Adapts to unknown scope and discoveries")
    print("    + Handles open-ended tasks ('add tests', 'investigate bug')")
    print("    - Less predictable, harder to reproduce")
    print("    Best for: exploration, open-ended investigations")

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Prompt chaining: per-file LOCAL pass + separate CROSS-FILE pass.")
    print("  2. Per-file analysis prevents ATTENTION DILUTION on large reviews.")
    print("  3. Dynamic decomposition: MAP → IDENTIFY → PLAN → ADAPT on discoveries.")
    print("  4. Choose based on task predictability: fixed pipeline vs adaptive plan.")
