"""
Domain 1 - Task 1.7: Manage Session State, Resumption, and Forking

EXAM CONCEPTS:
  1. Named session resumption: --resume <session-name> continues a specific
     prior conversation (Claude Code CLI feature).

  2. fork_session: creates INDEPENDENT branches from a shared analysis baseline
     to explore divergent approaches without cross-contamination.

  3. When resuming after code modifications: inform the agent about SPECIFIC
     file changes for targeted re-analysis (not full re-exploration).

  4. Starting fresh with injected summaries is MORE RELIABLE than resuming
     with stale tool results.

  KEY DECISION:
    Resume session  → prior context is MOSTLY VALID (same codebase, minor changes)
    Fresh + summary → prior tool results are STALE (significant code changes)

  EXAM NOTE: --resume and fork_session are Claude Code CLI/SDK features.
  This demo illustrates the CONCEPTS via API patterns that mirror the behavior.

Run: uv run python 07_session_management.py
"""

import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Simulate a "prior session" -- these are stale tool results from a past run
# ---------------------------------------------------------------------------
STALE_SESSION_HISTORY = [
    {"role": "user", "content": "Analyze the authentication module in auth.py"},
    {
        "role": "assistant",
        "content": (
            "I've analyzed auth.py. The login function uses hardcoded admin credentials "
            "(admin/admin123). The password is compared in plain text with no hashing. "
            "The file has 45 lines and imports nothing from external libraries."
        ),
    },
    # Stale tool results -- auth.py was refactored since this session
    {"role": "user", "content": "What about the token validation?"},
    {
        "role": "assistant",
        "content": (
            "Based on my earlier analysis, auth.py does not implement token validation. "
            "It only has the login() function. (NOTE: This may be stale if file changed.)"
        ),
    },
]

FRESH_SUMMARY = """
PRIOR ANALYSIS SUMMARY (from session 2024-06-15):
  - auth.py originally had: plain-text password comparison, hardcoded admin credentials
  - auth.py was REFACTORED on 2024-06-16:
    * Added bcrypt password hashing
    * Removed hardcoded credentials (now reads from env vars)
    * Added JWT token validation (new function: verify_token())
  - api.py: still has SQL injection risk in get_user_data() (unchanged)
  - utils.py: MD5 hashing for passwords (still present, needs fix)

TARGETED RE-ANALYSIS NEEDED:
  - Verify new bcrypt implementation in auth.py is correct
  - Check if verify_token() has proper error handling
  - SQL injection in api.py still unresolved
"""


# ---------------------------------------------------------------------------
# PATTERN 1: Resume with stale tool results (PROBLEMATIC)
# ---------------------------------------------------------------------------
def resume_with_stale_context(new_question: str) -> str:
    """
    PROBLEMATIC: resuming a session after code changed.
    The agent still references the old auth.py analysis even though the file
    has been completely refactored.
    """
    print("PATTERN 1: Resume with stale context (PROBLEMATIC)")
    messages = list(STALE_SESSION_HISTORY)
    messages.append({"role": "user", "content": new_question})

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system="You are a security code reviewer analyzing a Python codebase.",
        messages=messages,
    )
    return resp.content[0].text.strip()


# ---------------------------------------------------------------------------
# PATTERN 2: Fresh session with injected summary (RELIABLE)
# ---------------------------------------------------------------------------
def fresh_session_with_summary(new_question: str) -> str:
    """
    RELIABLE: start fresh but inject a structured summary of prior findings.
    The agent uses the summary + specific change info for targeted re-analysis.
    """
    print("PATTERN 2: Fresh session with injected summary (RELIABLE)")
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=(
            "You are a security code reviewer." + NL
            + "The following is a SUMMARY of prior analysis. "
            + "Use it as context but note that code may have changed."
        ),
        messages=[{
            "role": "user",
            "content": FRESH_SUMMARY + NL + NL + "Question: " + new_question,
        }],
    )
    return resp.content[0].text.strip()


# ---------------------------------------------------------------------------
# PATTERN 3: fork_session concept -- branching from shared baseline
# ---------------------------------------------------------------------------
def demonstrate_fork_session_concept() -> dict:
    """
    fork_session: create INDEPENDENT branches from a shared analysis baseline.
    Use when: exploring divergent approaches (e.g., two refactoring strategies)
    without cross-contaminating the analysis.

    Branch A: Explore "add bcrypt hashing" approach
    Branch B: Explore "use external auth service (Auth0)" approach
    Both branches start from the same codebase analysis.
    """
    print("PATTERN 3: fork_session -- two independent branches from shared baseline")

    # Shared baseline (both branches start here)
    shared_baseline = (
        "CODEBASE ANALYSIS BASELINE:" + NL
        + "  - auth.py: plain-text password storage, security risk" + NL
        + "  - utils.py: MD5 hashing (weak)" + NL
        + "  - api.py: SQL injection risk" + NL
        + "  - No token validation exists" + NL
        + "TASK: Evaluate two competing approaches to fix authentication security."
    )

    # Branch A: bcrypt approach
    branch_a = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system="You are a security architect. Evaluate approach A.",
        messages=[{
            "role": "user",
            "content": shared_baseline + NL + NL
            + "Evaluate APPROACH A: Add bcrypt + JWT tokens to the existing codebase." + NL
            + "Assess: effort, risk, time to production, security improvement.",
        }],
    )

    # Branch B: external auth service approach (independent -- no A context)
    branch_b = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system="You are a security architect. Evaluate approach B.",
        messages=[{
            "role": "user",
            "content": shared_baseline + NL + NL
            + "Evaluate APPROACH B: Replace auth module with Auth0 (external service)." + NL
            + "Assess: effort, risk, time to production, security improvement.",
        }],
    )

    return {
        "baseline": shared_baseline,
        "branch_a_bcrypt": branch_a.content[0].text.strip(),
        "branch_b_auth0": branch_b.content[0].text.strip(),
    }


# ---------------------------------------------------------------------------
# PATTERN 4: Targeted re-analysis (inform about specific file changes)
# ---------------------------------------------------------------------------
def targeted_reanalysis(changed_files: list, change_summary: str) -> str:
    """
    EXAM KEY: When resuming after code modifications, inform the agent about
    SPECIFIC file changes for targeted re-analysis, rather than full re-exploration.
    """
    print("PATTERN 4: Targeted re-analysis with specific change information")

    targeted_prompt = (
        "PRIOR CONTEXT: I previously analyzed this codebase and found security issues." + NL
        + "SPECIFIC CHANGES since last analysis:" + NL
        + change_summary + NL + NL
        + f"Changed files: {', '.join(changed_files)}" + NL + NL
        + "TARGETED RE-ANALYSIS NEEDED:" + NL
        + "Focus ONLY on the changed files. Check if changes resolved prior issues." + NL
        + "Do NOT re-analyze unchanged files (api.py, utils.py)."
    )

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system="You are a security code reviewer doing targeted re-analysis.",
        messages=[{"role": "user", "content": targeted_prompt}],
    )
    return resp.content[0].text.strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60
    question = "Is the authentication module now secure? What still needs fixing?"

    print(sep)
    print("DEMO 1: Resume with stale tool results (PROBLEMATIC after code changes)")
    print(sep)
    stale = resume_with_stale_context(question)
    print("Response (stale):", stale[:300])
    print("^ Problem: references old auth.py that no longer exists as described")

    print()
    print(sep)
    print("DEMO 2: Fresh session with structured summary (RELIABLE)")
    print(sep)
    fresh = fresh_session_with_summary(question)
    print("Response (fresh + summary):", fresh[:300])

    print()
    print(sep)
    print("DEMO 3: fork_session -- parallel branches from shared baseline")
    print(sep)
    forks = demonstrate_fork_session_concept()
    print("Branch A (bcrypt):", forks["branch_a_bcrypt"][:200])
    print()
    print("Branch B (Auth0):", forks["branch_b_auth0"][:200])
    print("^ Branches are INDEPENDENT -- no cross-contamination of reasoning")

    print()
    print(sep)
    print("DEMO 4: Targeted re-analysis (specific file change notification)")
    print(sep)
    targeted = targeted_reanalysis(
        changed_files=["auth.py"],
        change_summary="auth.py refactored: added bcrypt, added JWT verify_token(), removed hardcoded credentials",
    )
    print("Targeted response:", targeted[:300])

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. RESUME when prior context is mostly valid (minor changes).")
    print("  2. FRESH + SUMMARY when prior tool results are stale (major refactor).")
    print("  3. fork_session = independent branches from shared baseline.")
    print("  4. Targeted re-analysis: tell agent WHAT changed, not to re-explore all.")
    print("  5. --resume <session-name> continues named Claude Code sessions.")
