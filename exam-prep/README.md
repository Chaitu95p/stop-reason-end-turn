# CCA-F Exam Prep — Master Study Guide

**Goal:** Pass the Claude Certified Architect – Foundations (CCA-F) exam with confidence.

---

## Exam at a Glance

| Domain | Topic | Weight |
|--------|-------|--------|
| 1 | Agentic Architecture & Orchestration | 27% |
| 2 | Tool Design & MCP Integration | 18% |
| 3 | Claude Code Configuration & Workflows | 20% |
| 4 | Prompt Engineering & Structured Output | 20% |
| 5 | Context Management & Reliability | 15% |

**Pass mindset:** Every question tests *practical judgment* under realistic trade-offs — not trivia recall. The exam uses scenario-based questions, so always ask "which answer reflects correct production behavior?"

---

## Files in This Directory

| File | What It Covers |
|------|---------------|
| `01_preparation_recommendations.md` | The 7 official recommendations from exam guide pages 36-37 (with how each maps to this repo) |
| `02_exercises.md` | The 4 official hands-on exercises (steps 1-20) |
| `03_scope_reference.md` | Complete in-scope and out-of-scope topic lists |
| `04_tips_and_tricks.md` | Anti-patterns, exam traps, mnemonics, and quick-win strategies |
| `05_quick_reference_card.md` | Single-page cheat sheet — review the morning of the exam |

---

## Recommended Study Path (10-day plan)

### Days 1-2 — Agentic Architecture (Domain 1, 27%)
- Run `modules/module-1/` scripts in order
- Study stop_reason loop lifecycle end-to-end
- Memorize the STOP mnemonic (Send → Test → Operate → Proceed/Terminate)
- Key anti-patterns: NL parsing, fixed iteration caps, missing tool result history

### Days 3-4 — Tool Design & MCP (Domain 2, 18%)
- Run `modules/module-2/` scripts
- Memorize TVBP error categories (Transient, Validation, Business, Permission)
- Practice: empty result ≠ access failure (use `querySuccessful` field)
- Key: isRetryable flag drives agent decision-making, not the error message text

### Days 5 — Claude Code Config (Domain 3, 20%)
- Run `modules/module-3/` scripts + explore the three example subdirectories
- Hierarchy: user CLAUDE.md < project CLAUDE.md < directory CLAUDE.md < .claude/rules/
- Skill frontmatter: `context: fork` = isolation; `allowed-tools` restricts tool access
- Plan mode triggers: complexity, multi-file changes, ambiguous approaches

### Days 6-7 — Prompt Engineering & Structured Output (Domain 4, 20%)
- Run `modules/module-4/` scripts
- Structured output: always use `tool_use` + JSON schema, not freeform parsing
- Few-shot: targeted at ambiguous cases, not just format demos
- Batch API: 50% cost, ≤24h window, no multi-turn tool calling, custom_id for correlation

### Days 8 — Context Management & Reliability (Domain 5, 15%)
- Run `modules/module-5/` scripts
- Lost-in-the-middle: important items at START or END of context, not middle
- Scratchpad files: externalize structured state for sessions exceeding context limits
- Confidence scoring: field-level scores → stratified sampling → human review routing

### Days 9 — Official Exercises
- Work through `02_exercises.md` — all 4 exercises reinforce cross-domain judgment
- Focus on exercise 4 (multi-agent research pipeline) — highest complexity scenario

### Day 10 — Final Review
- Review `05_quick_reference_card.md` cover-to-cover
- Read through `04_tips_and_tricks.md` anti-patterns section
- Run `/check-exam-coverage` to verify all topics are reinforced by scripts

---

## The Most-Tested Exam Pattern

Almost every hard question on this exam tests ONE of these three judgment calls:

1. **Stop reason discipline** — `stop_reason == "tool_use"` → loop; `"end_turn"` → done. Never parse text.
2. **Error category routing** — transient → retry; validation → fix input; business → explain; permission → escalate.
3. **Context passing in multi-agent** — subagents do NOT inherit parent context automatically; you must pass it explicitly in the Task tool prompt.
