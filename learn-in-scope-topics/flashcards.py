"""
Domain 0 - CCA-F In-Scope Topics: Terminal Flashcard Trainer

EXAM CONCEPTS:
  1. Every in-scope topic (18 total, guide page 35-36) becomes a flashcard.
  2. Flip through them at random; grade yourself; the ones you flunk resurface.
  3. Pure Python. No API calls, no dependencies beyond stdlib.

  This script is a study aid — it does NOT talk to Claude. All content is
  local. Run it during a coffee break.

  Mnemonic: DRILL
    Draw a random card
    Reveal the answer on Enter
    Indicate self-grade (y/n)
    Loop until the deck is empty of unknowns
    Log final accuracy

Run: uv run python flashcards.py
"""

import random
import sys

NL = chr(10)


# ---------------------------------------------------------------------------
# The deck — one card per in-scope topic, plus a few high-yield gotchas
# ---------------------------------------------------------------------------
DECK = [
    {
        "topic": "T1 Agentic loop",
        "q": "What is the ONLY correct signal to terminate an agentic loop?",
        "a": "response.stop_reason == 'end_turn'. NEVER parse natural language "
             "text ('DONE'), and never use a fixed iteration cap as the PRIMARY "
             "stopping mechanism.",
    },
    {
        "topic": "T1 Agentic loop",
        "q": "Between agentic-loop iterations, what MUST you append to messages?",
        "a": "The assistant response (with tool_use blocks) AND a user message "
             "containing tool_result blocks with matching tool_use_id.",
    },
    {
        "topic": "T2 Multi-agent",
        "q": "Coordinator decomposes 'creative industries' into 3 visual-art "
             "subtasks. Subagents complete successfully but music, writing, "
             "film are missing. Root cause?",
        "a": "Coordinator decomposition too narrow. Subagents worked correctly "
             "within their scope — the assignment was incomplete. Blame the "
             "decomposition, not the subagents.",
    },
    {
        "topic": "T2 Multi-agent",
        "q": "Do subagents inherit the coordinator's conversation history?",
        "a": "No. Subagent context is isolated. Coordinator must pass context "
             "EXPLICITLY in the invocation prompt.",
    },
    {
        "topic": "T3 Subagent context",
        "q": "How do you make a subagent survive a crash?",
        "a": "Persist a structured manifest of completed steps to disk. On "
             "restart, replay from manifest instead of restarting from scratch.",
    },
    {
        "topic": "T4 Tool design",
        "q": "Ideal number of tools per agent?",
        "a": "4-5. 18 tools measurably degrades tool selection reliability. "
             "Restrict each subagent to tools relevant to its role.",
    },
    {
        "topic": "T4 tool_choice",
        "q": "Three tool_choice values and their behaviour?",
        "a": "'auto' = model decides (may return text, may skip tool). "
             "'any' = model MUST call some tool. "
             "{'type':'tool','name':'X'} = force a specific tool.",
    },
    {
        "topic": "T5 MCP resources vs tools",
        "q": "When do you expose data as an MCP RESOURCE vs a TOOL?",
        "a": "Resource = read-only content catalog (doc trees, schemas, issue "
             "lists) that reduces exploratory tool calls. Tool = an ACTION with "
             "side effects.",
    },
    {
        "topic": "T6 MCP config",
        "q": "Where do you put a TEAM-SHARED MCP server config?",
        "a": ".mcp.json at the project root (version-controlled). Personal / "
             "experimental servers go in ~/.claude.json.",
    },
    {
        "topic": "T6 MCP config",
        "q": "How do you keep secrets out of .mcp.json?",
        "a": "Environment variable expansion: 'env': {'TOKEN': '${GITHUB_TOKEN}'} "
             "— Claude Code expands ${VAR} at connection time from your local env.",
    },
    {
        "topic": "T7 Error handling",
        "q": "What are the four error categories (TVBP)?",
        "a": "Transient (retryable — timeout), Validation (fix input format), "
             "Business (policy limit — explain via humanMessage), Permission "
             "(access denied — escalate to human).",
    },
    {
        "topic": "T7 Empty result",
        "q": "Is 'no matches found' an error?",
        "a": "No. Return isError: false with querySuccessful: true and an empty "
             "results list. Distinguish empty result from access failure.",
    },
    {
        "topic": "T8 Escalation",
        "q": "Agent misclassifies which cases to escalate. Best first fix?",
        "a": "Add explicit escalation criteria + few-shot examples to the system "
             "prompt. LLM self-confidence is unreliable, so don't rely on it. "
             "Don't over-engineer with a classifier model.",
    },
    {
        "topic": "T9 CLAUDE.md hierarchy",
        "q": "A teammate is missing an instruction you added. Most likely cause?",
        "a": "You put it in ~/.claude/CLAUDE.md (user-scoped, personal-only). "
             "Move it to .claude/CLAUDE.md or root CLAUDE.md for team-sharing "
             "via version control.",
    },
    {
        "topic": "T9 Path-scoped rules",
        "q": "Test files are spread across many directories. Best way to apply "
             "a testing convention?",
        "a": ".claude/rules/tests.md with YAML frontmatter: paths: "
             "['**/*.test.tsx']. Loads ONLY when editing matching files.",
    },
    {
        "topic": "T10 Skills",
        "q": "Which skill frontmatter option isolates verbose output from the "
             "main conversation?",
        "a": "context: fork — runs the skill in an isolated sub-agent context.",
    },
    {
        "topic": "T10 Skills",
        "q": "How do you restrict a skill's tool access?",
        "a": "allowed-tools: [ ... ] frontmatter — e.g. allowed-tools: [Read, "
             "Grep] to make a read-only skill.",
    },
    {
        "topic": "T11 Plan mode",
        "q": "When do you enter plan mode vs. execute directly?",
        "a": "Plan mode: architectural, multi-file, multiple valid approaches, "
             "unfamiliar. Direct: single-file bug with clear repro, obvious "
             "localised edit.",
    },
    {
        "topic": "T12 Iterative refinement",
        "q": "Prose spec produces inconsistent output. What works better?",
        "a": "Provide 2-3 concrete input/output examples. Examples beat prose "
             "when prose is being interpreted inconsistently.",
    },
    {
        "topic": "T12 Iterative refinement",
        "q": "You have multiple interacting bugs. Report them how?",
        "a": "All in ONE message (Claude sees the interaction). Independent "
             "bugs → sequence them across messages.",
    },
    {
        "topic": "T13 Structured output",
        "q": "How do you force Claude to return valid JSON matching a schema?",
        "a": "Define a tool with the schema in input_schema, then set "
             "tool_choice: {'type': 'tool', 'name': 'your_tool'}.",
    },
    {
        "topic": "T13 Nullable fields",
        "q": "A field is often unknown. Best schema design?",
        "a": "Make it nullable (accept null). Prevents Claude from hallucinating "
             "a value when the source is silent.",
    },
    {
        "topic": "T14 Few-shot",
        "q": "You have 3 few-shot examples. Which cases should they cover?",
        "a": "Ambiguous / edge cases, not easy ones. Include at least one "
             "false-positive example with the correct rejection.",
    },
    {
        "topic": "T15 Batch processing",
        "q": "Cost and latency of Message Batches API?",
        "a": "50% discount vs sync. Up to 24h latency. Single-turn only — no "
             "multi-turn tool loops. Correlate responses via custom_id.",
    },
    {
        "topic": "T15 Batch failure handling",
        "q": "In a 10k-item batch, 50 items fail transient errors. What do you do?",
        "a": "Retry ONLY the failed items with a new custom_id (e.g. "
             "'id__retry'). Do not resubmit the whole batch — the 9,950 "
             "successful items are already done.",
    },
    {
        "topic": "T16 Context window",
        "q": "Where should critical facts go in a long prompt?",
        "a": "At the START and END. Middle-of-context recall is measurably "
             "weaker — 'lost in the middle'.",
    },
    {
        "topic": "T17 Human review",
        "q": "How do you set the confidence threshold for human review?",
        "a": "Calibrate the model's confidence against a labeled validation set, "
             "then set threshold from the MEASURED error rate. LLM "
             "self-reported confidence is poorly calibrated.",
    },
    {
        "topic": "T18 Provenance",
        "q": "Two sources give different numbers for the same fact. What do you do?",
        "a": "Annotate the conflict explicitly. Cite both sources with as-of "
             "dates. Mark the claim CONTESTED (vs WELL_ESTABLISHED / UNVERIFIED).",
    },
    {
        "topic": "T18 Provenance",
        "q": "What should you report about coverage gaps?",
        "a": "Explicitly. Say what you DID NOT find, not just what you did. "
             "Silent gaps mislead the user into thinking the answer is complete.",
    },
    {
        "topic": "Out-of-scope",
        "q": "Which is explicitly OUT of scope on the exam: (a) TVBP error "
             "categories (b) prompt caching implementation details (c) plan mode",
        "a": "(b) Prompt caching implementation details. Knowing prompt caching "
             "EXISTS is fine — the token accounting mechanics are not tested.",
    },
]


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------
def run_flashcards() -> None:
    unknowns = DECK.copy()
    random.shuffle(unknowns)
    correct = 0
    wrong = 0
    seen = 0

    sep = "=" * 60
    intro = (
        NL
        + sep + NL
        + "CCA-F Flashcard Trainer  (" + str(len(DECK)) + " cards)" + NL
        + sep + NL
        + "Answer in your head, press Enter to reveal, grade yourself." + NL
        + "  y = knew it   n = missed it   q = quit" + NL
    )
    print(intro)

    while unknowns:
        card = unknowns.pop(0)
        seen += 1
        print(sep)
        print(f"[{seen}/{len(DECK)}]  Topic: {card['topic']}")
        print(sep)
        print("Q:", card["q"])
        try:
            input(NL + "(press Enter to see answer)")
        except EOFError:
            break
        print(NL + "A: " + card["a"])
        try:
            grade = input(NL + "Grade (y/n/q): ").strip().lower()
        except EOFError:
            break
        if grade == "q":
            break
        elif grade == "y":
            correct += 1
        else:
            wrong += 1
            # missed cards return to the deck at a random later position
            insert_at = random.randint(0, len(unknowns))
            unknowns.insert(insert_at, card)
        print()

    total = correct + wrong
    accuracy = (correct / total * 100) if total else 0.0

    print(sep)
    print("Session summary")
    print(sep)
    print(f"Cards seen: {total}")
    print(f"Correct:    {correct}")
    print(f"Missed:     {wrong}")
    print(f"Accuracy:   {accuracy:.1f}%")

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Every card maps to an in-scope topic on the CCA-F exam.")
    print("  2. Missed cards resurface — you don't finish until you've beaten them.")
    print("  3. This is pure local Python; no API calls, no dependencies.")
    print("  4. For deeper study, read study-guide.html and cheatsheet.md.")


if __name__ == "__main__":
    try:
        run_flashcards()
    except KeyboardInterrupt:
        print(NL + "Exited early. Come back when you have another 10 minutes.")
        sys.exit(0)
