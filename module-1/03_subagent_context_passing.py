"""
Domain 1 - Task 1.3: Configure Subagent Invocation, Context Passing, and Spawning

EXAM CONCEPTS:
  1. Task tool: mechanism for spawning subagents. coordinator's allowedTools
     MUST include "Task" to invoke subagents.

  2. Subagents do NOT automatically inherit parent context or share memory.
     Context MUST be explicitly provided in each subagent's prompt.

  3. AgentDefinition: includes descriptions, system prompts, and tool
     restrictions for each subagent type.

  4. Parallel spawning: emit MULTIPLE Task tool calls in a SINGLE coordinator
     response -- not across separate turns.

  5. Structured data formats: separate content from metadata (source URLs,
     document names, page numbers) when passing context between agents to
     preserve attribution.

  6. Coordinator prompts specify GOALS and QUALITY CRITERIA -- not step-by-step
     instructions -- to enable subagent adaptability.

Run: uv run python 03_subagent_context_passing.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Simulated subagent runner
# ---------------------------------------------------------------------------
def spawn_subagent(
    name: str,
    system_prompt: str,
    task_with_context: str,
    max_tokens: int = 512,
) -> str:
    """Fresh API call -- isolated context -- no inherited history."""
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": task_with_context}],
    )
    return resp.content[0].text.strip()


# ---------------------------------------------------------------------------
# ANTI-PATTERN: no context injection (subagent knows nothing)
# ---------------------------------------------------------------------------
def antipattern_no_context_injection() -> str:
    print("ANTI-PATTERN: Synthesis subagent given NO prior findings")
    result = spawn_subagent(
        "SynthesisAgent",
        "You are a synthesis agent. Combine research findings.",
        # No findings passed -- subagent has no context!
        "Please synthesize the research findings and write a comprehensive summary.",
    )
    return result


# ---------------------------------------------------------------------------
# CORRECT: explicit context injection
# ---------------------------------------------------------------------------
def correct_explicit_context_injection() -> dict:
    """
    Step 1: Run search and analysis subagents (simulated results).
    Step 2: Pass ALL findings explicitly to synthesis subagent.
    """
    print("CORRECT: Explicit context injection into synthesis subagent")

    # Simulated outputs from prior subagents
    web_search_findings = [
        {
            "claim": "AI tools have reduced illustration time by 40% in game development",
            "source_url": "https://example.com/game-ai-2024",
            "excerpt": "Studios report significant productivity gains...",
            "date": "2024-03-15",
        },
        {
            "claim": "70% of graphic designers report using AI tools weekly",
            "source_url": "https://example.com/design-survey-2024",
            "excerpt": "Survey of 500 professional designers shows...",
            "date": "2024-05-01",
        },
    ]

    doc_analysis_findings = [
        {
            "claim": "AI music generation raises copyright attribution questions",
            "source_doc": "IP_Law_Review_2024.pdf",
            "page": 12,
            "excerpt": "Courts have yet to establish clear precedent...",
            "date": "2024-01-20",
        },
    ]

    # KEY EXAM POINT: pass complete findings explicitly in subagent prompt
    # Separate content from metadata (source URLs, doc names, page numbers)
    synthesis_prompt = (
        "Synthesize these research findings into a comprehensive report." + NL
        + "IMPORTANT: Preserve source attribution for every claim." + NL + NL
        + "=== WEB SEARCH FINDINGS ===" + NL
        + json.dumps(web_search_findings, indent=2) + NL + NL
        + "=== DOCUMENT ANALYSIS FINDINGS ===" + NL
        + json.dumps(doc_analysis_findings, indent=2) + NL + NL
        + "For each claim in your synthesis, cite the source_url or source_doc."
    )

    synthesis = spawn_subagent(
        "SynthesisAgent",
        "You are a synthesis agent. Produce a cited research summary.",
        synthesis_prompt,
    )

    return {
        "synthesis": synthesis,
        "web_findings_count": len(web_search_findings),
        "doc_findings_count": len(doc_analysis_findings),
    }


# ---------------------------------------------------------------------------
# Parallel subagent spawning demo
# ---------------------------------------------------------------------------
def demonstrate_parallel_spawning() -> dict:
    """
    EXAM KEY: Parallel subagents are spawned by emitting MULTIPLE Task tool
    calls in a SINGLE coordinator response (not across separate turns).

    Here we simulate this: coordinator issues multiple tasks simultaneously.
    In practice with the Agent SDK, the coordinator returns multiple Task
    tool calls in one response block.
    """
    print("CORRECT: Parallel subagent execution (multiple tasks in single response)")

    import concurrent.futures

    # These would be Task tool calls in a single coordinator response
    parallel_tasks = [
        {
            "agent": "WebSearchAgent",
            "system": "You are a web search specialist. Find recent statistics.",
            "task": "Find statistics on AI adoption in the music industry (2023-2024).",
        },
        {
            "agent": "DocAnalysisAgent",
            "system": "You are a document analysis specialist. Extract key claims.",
            "task": "Analyze: what are the main challenges AI faces in creative writing?",
        },
        {
            "agent": "TrendAgent",
            "system": "You are a trend analyst. Identify emerging patterns.",
            "task": "What emerging AI tools are disrupting film production workflows?",
        },
    ]

    results = {}
    # Simulate parallel execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                spawn_subagent,
                t["agent"], t["system"], t["task"]
            ): t["agent"]
            for t in parallel_tasks
        }
        for future in concurrent.futures.as_completed(futures):
            agent_name = futures[future]
            results[agent_name] = future.result()
            print(f"  [{agent_name}] completed")

    return results


# ---------------------------------------------------------------------------
# Coordinator goal vs procedural prompt comparison
# ---------------------------------------------------------------------------
def demonstrate_goal_vs_procedural_prompts() -> None:
    sep = "-" * 50
    print(sep)
    print("GOAL-BASED coordinator prompt (CORRECT):")
    goal_prompt = (
        "Research goal: 'How is AI changing the music industry?'" + NL
        + "Quality criteria:" + NL
        + "  - Cover at least 3 distinct aspects (creation, distribution, licensing)" + NL
        + "  - Include statistics from 2023 or later" + NL
        + "  - Cite at least 2 sources" + NL
        + "Return a structured JSON with claims and sources."
    )
    print(goal_prompt)

    print(sep)
    print("PROCEDURAL coordinator prompt (ANTI-PATTERN):")
    proc_prompt = (
        "Step 1: Search Google for 'AI music industry'." + NL
        + "Step 2: Click the first 3 links." + NL
        + "Step 3: Copy statistics from each page." + NL
        + "Step 4: Paste them into a document." + NL
        + "(This is fragile -- steps break when the web page structure changes.)"
    )
    print(proc_prompt)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: ANTI-PATTERN -- no context injection")
    print(sep)
    bad = antipattern_no_context_injection()
    print("Synthesis output (no context):", bad[:200])

    print()
    print(sep)
    print("DEMO 2: CORRECT -- explicit context injection with metadata")
    print(sep)
    good = correct_explicit_context_injection()
    print("Synthesis (with injected findings):")
    print(good["synthesis"][:400])
    print(f"  (Used {good['web_findings_count']} web + {good['doc_findings_count']} doc findings)")

    print()
    print(sep)
    print("DEMO 3: Parallel subagent spawning")
    print(sep)
    parallel_results = demonstrate_parallel_spawning()
    for agent, result in parallel_results.items():
        print(f"  {agent}: {result[:100]}...")

    print()
    print(sep)
    print("DEMO 4: Goal-based vs Procedural coordinator prompts")
    print(sep)
    demonstrate_goal_vs_procedural_prompts()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Subagents have ISOLATED context -- inject ALL needed info explicitly.")
    print("  2. Separate content from metadata (source URLs, page numbers) in handoffs.")
    print("  3. Parallel spawning = multiple Task calls in ONE coordinator response.")
    print("  4. Coordinator specifies GOALS + QUALITY CRITERIA, not step-by-step steps.")
    print("  5. allowedTools MUST include 'Task' for a coordinator to spawn subagents.")
