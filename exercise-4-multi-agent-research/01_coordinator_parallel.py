"""
Exercise 4 - Steps 16-17: Coordinator + Parallel Subagents via Task Tool

EXAM CONCEPTS:
  1. Coordinator-subagent pattern:
     - Coordinator has allowedTools including "Task"
     - Each subagent receives its FULL research context in its prompt --
       NEVER assume automatic context inheritance across subagents.

  2. Parallel subagent execution:
     - Coordinator emits MULTIPLE Task tool_use blocks in a SINGLE response
     - Each subagent runs concurrently
     - Coordinator waits for all before synthesizing

  3. Explicit context passing prevents:
     - Subagent hallucinating shared background it never saw
     - Silent version skew between subagents' assumptions
     - "Lost-in-the-middle" issues when the parent context is too big

  4. Sequential vs parallel wall-clock:
     Sequential: T_total = sum(T_subagent_i)
     Parallel:   T_total = max(T_subagent_i)  + coordinator overhead

  Mnemonic: PARALLEL
    Pack multiple Task calls in one coordinator response
    Assumptions passed explicitly, never inherited
    Return schemas identical across subagents to simplify synthesis
    All findings await before synthesis
    Latency = MAX(subagent_time), not SUM
    Log which subagent produced which finding
    Every subagent gets ONLY the context it needs, not the whole chat
    Latency win is bounded by the slowest subagent

Run: uv run python 01_coordinator_parallel.py
"""

import json
import time
import concurrent.futures
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Simulated Task-tool subagent spawning
# ---------------------------------------------------------------------------
def spawn_subagent(role_prompt: str, task_prompt: str, tools: list = None) -> dict:
    """
    Simulate a Task-tool subagent:
    - Fresh messages list (no inherited context from coordinator)
    - Own system prompt (the subagent's role)
    - Returns final assistant text as its report
    """
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=role_prompt,
        tools=tools or [],
        messages=[{"role": "user", "content": task_prompt}],
    )
    text = "".join(getattr(b, "text", "") for b in resp.content)
    return {"role_prompt_head": role_prompt[:60], "report": text}


WEB_SEARCH_ROLE = (
    "You are a web-search research subagent." + NL
    + "You are given a SPECIFIC research question. Produce a concise briefing "
    "of what a search for that question would surface, based on your training data." + NL
    + "Return bullet-point findings only. Do not ask for tools -- do your best from memory."
)

DOC_ANALYSIS_ROLE = (
    "You are a document-analysis research subagent." + NL
    + "You are given a SPECIFIC research question. Produce a concise summary "
    "of how internal documents WOULD address that question, drawing on general knowledge "
    "as a stand-in." + NL
    + "Return bullet-point findings only."
)


def run_sequential(question: str) -> tuple[dict, float]:
    """Baseline: run subagents one after another."""
    t0 = time.time()
    web = spawn_subagent(
        WEB_SEARCH_ROLE,
        f"Research question: {question}" + NL + "Focus on public web knowledge.",
    )
    doc = spawn_subagent(
        DOC_ANALYSIS_ROLE,
        f"Research question: {question}" + NL + "Focus on internal-document perspective.",
    )
    return {"web": web, "doc": doc}, time.time() - t0


def run_parallel(question: str) -> tuple[dict, float]:
    """Parallel: both subagents run at once via ThreadPoolExecutor."""
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f_web = ex.submit(spawn_subagent, WEB_SEARCH_ROLE,
                          f"Research question: {question}" + NL
                          + "Focus on public web knowledge.")
        f_doc = ex.submit(spawn_subagent, DOC_ANALYSIS_ROLE,
                          f"Research question: {question}" + NL
                          + "Focus on internal-document perspective.")
        return {"web": f_web.result(), "doc": f_doc.result()}, time.time() - t0


# ---------------------------------------------------------------------------
# Coordinator synthesis
# ---------------------------------------------------------------------------
def coordinator_synthesize(question: str, findings: dict) -> str:
    """Coordinator combines subagent reports -- explicit context, NOT inherited."""
    prompt = (
        f"Research question: {question}" + NL + NL
        + "Findings from web_search subagent:" + NL
        + findings["web"]["report"] + NL + NL
        + "Findings from doc_analysis subagent:" + NL
        + findings["doc"]["report"] + NL + NL
        + "Synthesize a 3-4 bullet unified answer. Preserve which subagent found what."
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system="You are the research coordinator. Synthesize findings faithfully.",
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(getattr(b, "text", "") for b in resp.content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60
    question = "What are the trade-offs between token bucket and sliding window rate limiting for public APIs?"

    print(sep)
    print("DEMO 1: Sequential subagent execution (baseline)")
    print(sep)
    findings_seq, t_seq = run_sequential(question)
    print(f"Sequential wall-clock: {t_seq:.2f}s")

    print()
    print(sep)
    print("DEMO 2: Parallel subagent execution (Task tool style)")
    print(sep)
    findings_par, t_par = run_parallel(question)
    print(f"Parallel   wall-clock: {t_par:.2f}s")
    print(f"Speedup: {t_seq / max(t_par, 0.01):.2f}x")
    print(f"Theoretical max speedup with 2 subagents: 2.00x")

    print()
    print(sep)
    print("DEMO 3: Coordinator synthesis over parallel findings")
    print(sep)
    synthesis = coordinator_synthesize(question, findings_par)
    print(synthesis[:1000])

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Each subagent gets its OWN prompt with FULL context needed --")
    print("     never rely on coordinator context being inherited automatically.")
    print("  2. Parallel latency = MAX(subagent_time), sequential = SUM.")
    print("     Speedup is bounded by the slowest subagent, not linear in count.")
    print("  3. The coordinator's job is DECOMPOSITION and SYNTHESIS -- not")
    print("     research itself. Delegate research to subagents with narrow scope.")
    print("  4. Explicit context passing keeps subagent context windows small,")
    print("     which improves reasoning quality (avoids lost-in-the-middle).")
    print("  Mnemonic PARALLEL: Pack Task calls, Assumptions explicit,")
    print("     Return schemas uniform, All await, Latency=max, Log source,")
    print("     Every subagent minimal context, Latency bounded by slowest.")
