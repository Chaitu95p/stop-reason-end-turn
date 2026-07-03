# Exam Preparation Recommendations (Pages 36-37)

> Source: CCA-F Exam Guide v0.2, section "Exam Preparation Recommendations" (items 21-27)

These 7 recommendations are the official study actions prescribed by Anthropic.
Each one is annotated with how to fulfill it using this repo.

---

## Recommendation 21 — Build an Agent with the Claude Agent SDK

**What the guide says:**
> Implement a complete agentic loop with tool calling, error handling, and session management.
> Practice spawning subagents and passing context between them.

**Why this matters on the exam:**
Domain 1 is 27% of the exam. Every multi-step scenario (customer support, research pipeline, CI/CD agent) tests whether you instinctively check `stop_reason` to control the loop — not text parsing, not fixed counters.

**How to do it in this repo:**
```bash
cd modules/module-1 && uv run python 01_agentic_loop.py
```
Key things to internalize from that script:
- The `while True` loop with `if stop_reason == "end_turn": return` pattern
- Tool results appended as `{"role": "user", "content": [{"type": "tool_result", ...}]}`
- ALL tool_use blocks in one response must be executed before the next request

**Exam trap to avoid:**
The anti-pattern functions in `01_agentic_loop.py` (`antipattern_nl_parsing`, `antipattern_fixed_cap`) are exactly what wrong answers look like. Know them cold.

---

## Recommendation 22 — Configure Claude Code for a Real Project

**What the guide says:**
> Set up CLAUDE.md with a configuration hierarchy, create path-specific rules in `.claude/rules/`,
> build custom skills with frontmatter options (`context: fork`, `allowed-tools`), and integrate
> at least one MCP server.

**Why this matters on the exam:**
Domain 3 is 20% of the exam. Configuration hierarchy questions often have subtle wrong answers where the level of override is incorrect.

**How to do it in this repo:**
```bash
# Study the three pedagogical examples in module-3:
ls modules/module-3/01_claude_md_hierarchy/
ls modules/module-3/02_custom_commands_skills/
ls modules/module-3/03_path_specific_rules/

# Then study the real config for this project:
cat .claude/settings.json
cat .claude/rules/demo-scripts.md
```

**Key facts for the exam:**

| Level | File | Scope |
|-------|------|-------|
| User | `~/.claude/CLAUDE.md` | All projects |
| Project | `<repo>/CLAUDE.md` | All sessions in this repo |
| Directory | `<dir>/CLAUDE.md` | Sessions in that subdirectory |
| Path rules | `.claude/rules/*.md` (with `paths:` frontmatter) | Only matching glob patterns |

**Skill frontmatter:**
- `context: fork` — skill runs in isolated fork, doesn't pollute main conversation
- `allowed-tools: [Read, Bash]` — restricts tools available inside the skill
- `argument-hint: "<module-number>"` — shown in autocomplete UI

---

## Recommendation 23 — Design and Test MCP Tools

**What the guide says:**
> Write tool descriptions that clearly differentiate similar tools. Implement structured error
> responses with error categories and retryable flags. Test tool selection reliability with
> ambiguous requests.

**Why this matters on the exam:**
Domain 2 is 18%. The exam tests whether you know the difference between uniform vs. structured errors, and can identify which error category maps to which recovery action.

**How to do it in this repo:**
```bash
cd modules/module-2 && uv run python 02_structured_error_responses.py
```

**Memorize TVBP:**
| Category | isRetryable | Agent Action |
|----------|-------------|-------------|
| **T**ransient | `true` | Retry once; escalate if still fails |
| **V**alidation | `false` | Ask customer for corrected input |
| **B**usiness | `false` | Explain policy using `humanMessage` |
| **P**ermission | `false` | Escalate to human agent immediately |

**MCP Resources vs Tools:**
- **Resources** = read-only content catalogs (e.g., knowledge bases, product lists)
- **Tools** = stateful actions (e.g., create order, process refund)
- Rule of thumb: if it has side effects → tool; if it's a lookup → resource

---

## Recommendation 24 — Build a Structured Data Extraction Pipeline

**What the guide says:**
> Use `tool_use` with JSON schemas, implement validation-retry loops, design schemas with
> optional/nullable fields, and practice batch processing with the Message Batches API.

**Why this matters on the exam:**
Domain 4 (20%) has heavy focus on schema design trade-offs. The exam will test nullable vs optional field handling and when the Batches API is appropriate.

**How to do it in this repo:**
```bash
cd modules/module-4 && for f in 0*.py; do echo "=== $f ===" && uv run python "$f"; done
```

**Critical schema design rules:**
- Use `nullable` fields for information that may be absent (prevents fabrication)
- Use `enum` + an `"other"` + detail string for open-ended categorization
- `tool_choice: "any"` forces the model to call a tool (required for structured output)
- `tool_choice: {"type": "tool", "name": "..."}` forces a *specific* tool

**Batch API facts (memorize exactly):**
- 50% cost reduction
- Up to 24-hour processing window
- Use `custom_id` to correlate requests with responses
- **Does NOT support multi-turn tool calling** — single-turn only
- Poll for completion (no webhooks)

**Validation-retry pattern:**
```
attempt → validate (Pydantic/JSON schema)
  fail  → send follow-up with: document + failed extraction + specific error
  pass  → accept result
```

---

## Recommendation 25 — Practice Prompt Engineering Techniques

**What the guide says:**
> Write few-shot examples for ambiguous scenarios. Define explicit review criteria to reduce
> false positives. Design multi-pass review architectures for large code reviews.

**Why this matters on the exam:**
Domain 4 tests both prompting technique selection and the reasoning behind it. Wrong answers often use the right technique in the wrong context.

**Few-shot targeting rules:**
- Use few-shot for **ambiguous** cases, not just format demos
- Examples should show the **edge cases** Claude struggles with, not the easy ones
- Format consistency: few-shot examples must match the exact output format you expect

**Multi-pass vs single-pass:**
| Use multi-pass when... | Use single-pass when... |
|------------------------|-------------------------|
| Document too large for one context | Simple extraction, small document |
| First pass: categorize; second pass: extract | Format is uniform across all documents |
| Parallel: different reviewers per dimension | One concern, one reviewer |

**False positive reduction technique:**
Add explicit review criteria in the system prompt:
```
"Only flag a bug if you can identify: (1) the specific line, (2) the specific failure mode,
(3) a concrete example input that triggers it. Do not flag speculative issues."
```

---

## Recommendation 26 — Study Context Management Patterns

**What the guide says:**
> Practice extracting structured facts from verbose tool outputs, implementing scratchpad files
> for long sessions, and designing subagent delegation to manage context limits.

**Why this matters on the exam:**
Domain 5 (15%) tests architectural judgment. Questions will present a scenario where the context window is a constraint and ask which pattern best solves it.

**How to do it in this repo:**
```bash
cd modules/module-5 && for f in 0*.py; do echo "=== $f ===" && uv run python "$f"; done
```

**Three key patterns:**
1. **Structured fact extraction** — replace verbose tool output with a compact JSON summary before appending to history
2. **Scratchpad files** — write structured state to disk; subagents read the file rather than needing conversation history
3. **Subagent delegation** — offload tasks to subagents; only the *summary* returns to the coordinator's context

**Lost-in-the-middle effect:**
- Models attend best to content at the START and END of context
- Put critical instructions and constraints at the BEGINNING of the system prompt
- Put the most relevant document/context snippet at the END, just before the user message

**Token budget strategy:**
```
Total available tokens = context window - max_tokens (reserved for output)
Priority order: system prompt > recent messages > tool results > older history
Trim older tool results first (they're already reflected in subsequent messages)
```

---

## Recommendation 27 — Review Escalation and Human-in-the-Loop Patterns

**What the guide says:**
> Understand when to escalate (policy gaps, customer requests, inability to progress) versus
> resolve autonomously. Practice designing human review workflows with confidence-based routing.

**Why this matters on the exam:**
Escalation logic appears in both Domain 1 and Domain 5. The exam distinguishes between agents that escalate too eagerly (bad UX) and too rarely (bad safety posture).

**Escalate when:**
1. The request exceeds defined policy limits (the agent cannot authorize it)
2. The customer explicitly requests a human
3. The agent has been unable to resolve after a defined number of attempts
4. The action is irreversible and above a risk threshold

**Do NOT escalate when:**
- The error is transient (retry first)
- The validation error can be fixed by asking for corrected input
- The resolution falls within the agent's defined authority

**Confidence-based routing:**
```
field_confidence >= 0.95  →  auto-accept
0.70 <= field_confidence < 0.95  →  human spot-check (stratified sample)
field_confidence < 0.70  →  mandatory human review
```

**Stratified sampling:** Don't sample uniformly. Oversample low-confidence, new document types, and fields with historically poor accuracy. This gives you better error rate measurement per segment.
