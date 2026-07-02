"""
Domain 1 - Task 1.2: Multi-Agent Systems with Coordinator-Subagent Patterns

EXAM CONCEPTS:
  1. Hub-and-spoke: coordinator manages ALL inter-subagent communication,
     error handling, and information routing.

  2. Subagents operate with ISOLATED context -- they do NOT inherit the
     coordinator's conversation history automatically.

  3. Coordinator responsibilities: task decomposition, delegation, result
     aggregation, deciding WHICH subagents to invoke based on complexity.

  4. RISK: Overly narrow task decomposition → incomplete topic coverage.
     E.g., decomposing "creative industries" into only visual arts subtasks
     completely misses music, writing, and film.

  5. Iterative refinement: coordinator evaluates synthesis output for gaps,
     re-delegates to search/analysis subagents, re-invokes synthesis.

  Mnemonic: DARE
    Decompose (analyze query, identify required domains)
    Assign (delegate to specialized subagents with isolated context)
    Refine (evaluate coverage gaps, re-delegate as needed)
    Emit (route all output through coordinator for observability)

Run: uv run python 02_multi_agent_coordinator.py
"""

import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Simulated subagent: runs a separate isolated API call (no shared context)
# ---------------------------------------------------------------------------
def run_subagent(agent_name: str, system_prompt: str, task_prompt: str) -> str:
    """
    Each subagent is a FRESH API call with EXPLICIT context in its prompt.
    Subagents do NOT inherit the coordinator's history.
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": task_prompt}],
    )
    result = response.content[0].text.strip()
    print(f"  [{agent_name}] -> {result[:120]}...")
    return result


# ---------------------------------------------------------------------------
# ANTI-PATTERN: narrow task decomposition
# ---------------------------------------------------------------------------
def narrow_decomposition_coordinator(topic: str) -> str:
    """
    Coordinator decomposes into only 3 narrow subtasks (all visual arts),
    completely missing music, writing, and film.
    """
    print("COORDINATOR: Decomposing task (NARROW -- ANTI-PATTERN)")

    # Bug: coordinator only thinks of visual art subtopics
    subtasks = [
        "AI in digital art creation",
        "AI in graphic design",
        "AI in photography",
    ]
    print("  Subtasks assigned:", subtasks)

    findings = []
    for subtask in subtasks:
        result = run_subagent(
            "SearchAgent",
            "You are a research agent. Summarize key findings in 2-3 sentences.",
            f"Research: {subtask}" + NL + "Topic context: Impact of AI on creative industries.",
        )
        findings.append(f"[{subtask}]: {result}")

    # Synthesize
    synthesis = run_subagent(
        "SynthesisAgent",
        "You are a synthesis agent. Combine findings into a coherent summary.",
        "Combine these research findings:" + NL + NL.join(findings),
    )
    return synthesis


# ---------------------------------------------------------------------------
# CORRECT: broad decomposition with iterative gap-checking
# ---------------------------------------------------------------------------
def broad_decomposition_coordinator(topic: str) -> str:
    """
    Correct coordinator:
    1. Analyzes the full scope of the topic
    2. Decomposes into broad, non-overlapping subtasks
    3. Evaluates synthesis for gaps
    4. Re-delegates if coverage is insufficient
    """
    print("COORDINATOR: Decomposing task (BROAD -- CORRECT)")

    # Step 1: Use coordinator LLM to plan subtasks
    plan_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": (
                f"You are planning research on: '{topic}'" + NL
                + "List 4-5 distinct subtopics that together give COMPLETE coverage." + NL
                + "Output one subtopic per line, nothing else."
            ),
        }],
    )
    subtasks = [
        line.strip().lstrip("-•123456789. ")
        for line in plan_response.content[0].text.strip().split(NL)
        if line.strip()
    ][:5]
    print("  Subtasks assigned:", subtasks)

    # Step 2: Delegate to search subagents (pass topic context explicitly)
    findings = []
    for subtask in subtasks:
        result = run_subagent(
            "SearchAgent",
            "You are a research agent. Summarize key findings in 2-3 sentences.",
            # EXAM KEY: explicit context injected -- subagent cannot see coordinator history
            f"Research subtopic: {subtask}" + NL
            + f"Overall research topic: {topic}" + NL
            + "Focus only on your assigned subtopic.",
        )
        findings.append({"subtopic": subtask, "findings": result})

    # Step 3: Synthesize
    findings_text = NL.join(f"[{f['subtopic']}]: {f['findings']}" for f in findings)
    synthesis = run_subagent(
        "SynthesisAgent",
        "You are a synthesis agent. Combine findings into a comprehensive summary.",
        # EXAM KEY: findings passed explicitly to synthesis subagent
        f"Research topic: {topic}" + NL + NL + "Research findings:" + NL + findings_text,
    )

    # Step 4: Gap check (iterative refinement)
    gap_check = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=128,
        messages=[{
            "role": "user",
            "content": (
                f"Does this summary fully cover: '{topic}'?" + NL
                + "Summary: " + synthesis[:300] + NL
                + "List any missing major areas, or say 'COMPLETE' if coverage is sufficient."
            ),
        }],
    )
    gap_text = gap_check.content[0].text.strip()
    print(f"  [GapCheck] -> {gap_text[:120]}")

    if "COMPLETE" not in gap_text.upper():
        print("  COORDINATOR: Gaps detected -- re-delegating for missing areas...")
        gap_result = run_subagent(
            "SearchAgent",
            "You are a research agent. Summarize key findings in 2-3 sentences.",
            f"Research gaps for topic '{topic}':" + NL + gap_text,
        )
        synthesis = run_subagent(
            "SynthesisAgent",
            "You are a synthesis agent. Combine all findings.",
            f"Original synthesis: {synthesis}" + NL + NL
            + f"Additional findings on gaps: {gap_result}" + NL
            + "Produce a final comprehensive summary.",
        )

    return synthesis


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60
    topic = "impact of AI on creative industries"

    print(sep)
    print("DEMO 1: ANTI-PATTERN -- narrow task decomposition")
    print("(Only visual arts subtasks -- misses music, writing, film)")
    print(sep)
    narrow_result = narrow_decomposition_coordinator(topic)
    print()
    print("Final synthesis (NARROW):")
    print(narrow_result[:400])

    print()
    print(sep)
    print("DEMO 2: CORRECT -- broad decomposition with iterative gap check")
    print(sep)
    broad_result = broad_decomposition_coordinator(topic)
    print()
    print("Final synthesis (BROAD):")
    print(broad_result[:400])

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Coordinator MANAGES all routing -- subagents never talk to each other.")
    print("  2. Subagents have ISOLATED context -- inject all needed info explicitly.")
    print("  3. Decompose BROADLY to avoid missing entire topic domains.")
    print("  4. Evaluate for coverage gaps -- re-delegate if synthesis is incomplete.")
    print("  5. Route ALL output through coordinator for observability.")
    print("  Mnemonic DARE: Decompose, Assign, Refine, Emit.")
