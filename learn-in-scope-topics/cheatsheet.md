# CCA-F One-Page Cheatsheet

Rapid-review sheet for the day before the exam. Every in-scope topic in one glance.

---

## D1 Agentic Architecture (27%)

**T1 Agentic loop** — Loop on `stop_reason == "tool_use"`, exit on `"end_turn"`. **Never** stop on: NL text parsing (`if "DONE" in text`), fixed iteration cap (as PRIMARY stop), assistant text presence. Always append tool_result to messages before next call.

**T2 Multi-agent orchestration** — Hub-and-spoke: coordinator owns ALL routing, error handling, and info flow. Subagents don't inherit coordinator history — pass context explicitly. Common failure: over-narrow decomposition (topic "creative industries" → only "visual arts" subtasks). Coordinator must dynamically select subagents based on query, not always run the full pipeline.

**T3 Subagent context management** — Explicit context passing in the invocation prompt. Structured state persistence (manifest files) for crash recovery. Isolated per-subagent context prevents pollution.

---

## D2 Tool Design & MCP (18%)

**T4 Tool interface design** — 4-5 tools per agent, not 18. Split by semantic purpose. Constrained > generic (e.g. `load_document` that validates URLs > `fetch_url`). Description quality determines whether Claude adopts your tool over built-ins like Grep.

**T5 MCP tools vs resources** — Resources = content catalogs (read-only browse: schemas, doc trees, issue lists) → reduces exploratory tool calls. Tools = actions with side effects.

**T6 MCP server config** — Project scope `.mcp.json` (team, VCS-shared). User scope `~/.claude.json` (personal). Env vars via `${VAR}` — never commit secrets. All configured servers' tools available simultaneously. Prefer community MCP servers over custom for standard integrations (Jira, GitHub).

**T7 Error handling — TVBP** — **T**ransient/retry, **V**alidation/fix-input, **B**usiness/explain-policy, **P**ermission/escalate. Structured fields: `isError`, `errorCategory`, `isRetryable`, `errorCode`, `developerMessage`, `humanMessage`. **Empty result ≠ access failure**: use `querySuccessful` flag to distinguish. Uniform `{"error": "failed"}` blocks intelligent recovery.

**T8 Escalation decisions** — Explicit criteria in system prompt + few-shot examples (LLM self-confidence is unreliable). Honor customer preferences ("get me a human") over criteria. Log escalations to surface policy gaps back to the team.

**T4b tool_choice** — `auto` (may not tool-call), `any` (forces some tool), `{"type":"tool","name":"X"}` (force specific tool, useful for pinning first step).

---

## D3 Claude Code Config (20%)

**T9 CLAUDE.md hierarchy** — User (`~/.claude/`) is personal-only. Project (`.claude/CLAUDE.md` or root `CLAUDE.md`) is team-shared via VCS. Directory (subfolder `CLAUDE.md`) applies to that subtree. `@import` for modularity. Split large files into `.claude/rules/*.md` with YAML `paths:` frontmatter.

**T10 Custom commands + skills** — Project-scoped in `.claude/commands/` and `.claude/skills/` (team-shared). Skill frontmatter: `context: fork` (isolate output), `allowed-tools:` (restrict), `argument-hint:` (prompt for args). Personal variants in `~/.claude/skills/` with different names.

**T9b Path-scoped rules** — `.claude/rules/*.md` with YAML `paths: ["**/*.test.tsx"]` — loads only when editing matching files. Prefer over subdirectory `CLAUDE.md` when the rule spans files across directories.

**T11 Plan mode vs direct** — Plan mode: architectural, multi-file, multiple valid approaches, unfamiliar area. Direct: single-file bug with clear repro, obvious localised edit. Use Explore subagent to isolate verbose discovery from main context.

**T12 Iterative refinement** — 2-3 concrete I/O examples beat prose. Write tests first, iterate on failures. Interview pattern: have Claude ask questions before implementing. Interacting issues → single message; independent issues → sequence them.

---

## D4 Prompt Engineering (20%)

**T13 Structured output via tool_use** — Define JSON schema in a tool's `input_schema`. Force with `tool_choice: {"type": "tool", "name": "extract_X"}`. Nullable fields for uncertain data prevent hallucination. Enum + "other" pattern with dependent-field validation.

**T14 Few-shot** — Target ambiguous cases, not easy ones. Consistent format across examples. Include false-positive examples with correct rejection. 3-5 examples usually enough.

**T15 Batch processing (Message Batches API)** — 50% cost discount, up to 24h latency. Single-turn only (no multi-turn tool loops). Correlate via `custom_id`. Handle per-item failures — retry only the failed items with `custom_id + "__retry"`. Appropriate when latency is tolerated (nightly extraction) — inappropriate for interactive support agents.

---

## D5 Context & Reliability (15%)

**T16 Context window optimization** — Trim verbose tool outputs before appending. Position-aware ordering: critical facts at start AND end (middle is "lost"). Extract structured summaries. Scratchpad files for state that outgrows the window.

**T17 Human review workflows** — Confidence scores must be calibrated with labeled validation sets. Self-reported LLM confidence is poorly calibrated (a wrong-but-confident model still returns high confidence). Stratified sampling to measure error rates by document type + field. Route below-threshold to human review.

**T18 Information provenance** — Every claim links to source + as-of date. Classify: WELL_ESTABLISHED / CONTESTED / UNVERIFIED. Explicit conflict annotation when sources disagree. Coverage gap reporting — say what you DIDN'T find, not just what you did.

---

## The high-yield gotchas

1. **`stop_reason` is the only correct loop control.** Any answer that says "check assistant text" or "cap iterations" is wrong.
2. **`auto` may not tool-call.** If your prompt says "always use tool X", you still need `tool_choice: "any"` or forced.
3. **Empty result ≠ error.** `{isError: false, results: [], querySuccessful: true}` is the right shape.
4. **User-level CLAUDE.md is NOT shared.** If a teammate is missing an instruction, it's probably at user level.
5. **`context: fork`** keeps skill output out of the main convo — used for verbose exploratory tasks.
6. **Batches API is single-turn.** Cannot loop tools inside a batch request.
7. **Middle of a long prompt is "lost".** Put critical stuff at start AND end.
8. **Coordinator decomposition scope is the exam trap.** If subagents completed successfully but coverage is missing, blame the decomposition, not the subagents.
9. **Self-reported confidence is unreliable.** Calibrate against labeled data, not against the model's own score.
10. **Prompt caching internals are OUT OF SCOPE.** Knowing "it exists" is enough.
