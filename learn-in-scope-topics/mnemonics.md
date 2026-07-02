# Mnemonics for CCA-F Topics

Drill these until each mnemonic instantly expands to its full meaning. Every one maps to an in-scope topic — knowing the mnemonic recovers the whole answer under exam pressure.

---

## Domain 1 — Agentic Architecture

### `STOP` — Agentic loop lifecycle (Topic 1)
- **S**end request to `messages.create`
- **T**est `stop_reason` on the response
- **O**perate tools (execute all `tool_use` blocks in this response)
- **P**roceed to next iteration (append tool results, loop) **or Terminate** on `end_turn`

**Anti-mnemonic: DON'T CAP** — never let a fixed iteration `Cap`, natural-language `A`ssistant text parse, or `P`hrase-based `DONE`/`complete` marker be your PRIMARY stopping mechanism.

### `HUB` — Coordinator-subagent pattern (Topic 2)
- **H**ub-and-spoke: all communication passes through the coordinator
- **U**nique context: subagents don't inherit the coordinator's history — you must pass context explicitly
- **B**readth check: coordinator must decompose broadly enough (the classic exam trap is over-narrow decomposition, e.g. "creative industries" → only visual arts)

### `PIC` — Subagent context management (Topic 3)
- **P**ass context explicitly in the subagent invocation prompt
- **I**solate: each subagent has its own context window
- **C**rash recovery via manifest files — persist structured state, replay from manifest on failure

---

## Domain 2 — Tool Design & MCP

### `SLAT` — Tool interface design (Topic 4)
- **S**plit tools when the operations are semantically distinct (e.g. `get_customer` + `process_refund`, not one `handle_customer`)
- **L**imit total tool count (4-5 per agent, not 18) — too many tools degrades selection reliability
- **A**ction naming: verbs for actions, nouns for resources; disambiguate similar-sounding names
- **T**ell the model what the tool returns — description quality drives adoption over built-in tools

### `TVBP` — Error categories (Topic 7)
- **T**ransient (timeout, service unavailable) → `isRetryable: true`
- **V**alidation (bad input format) → `isRetryable: false`, ask user to fix
- **B**usiness (policy limit exceeded) → `isRetryable: false`, explain policy via `humanMessage`
- **P**ermission (access denied) → `isRetryable: false`, escalate to human

### `ERR` — Structured error response fields (Topic 7)
- **E**rrorCategory (transient/validation/business/permission)
- **R**etryable (isRetryable boolean)
- **R**eason messages: `developerMessage` (technical) + `humanMessage` (customer-facing)

### `CHOOSE` — tool_choice values (Topic 4, 13)
- `auto` — model decides (default; may return text instead of calling a tool)
- `any` — model MUST call some tool (use this for structured output when you don't care which of several tools)
- `{"type": "tool", "name": "X"}` — force a specific tool (use for first-step pinning, e.g. `extract_metadata` before enrichment)

### `MCP-PES` — MCP server config (Topic 6)
- **P**roject scope (`.mcp.json` at repo root — version-controlled, team-shared)
- **E**nvironment variable expansion via `${VAR}` in `.mcp.json` — never commit secrets
- **S**imultaneous access: all configured servers' tools are discovered at connect time and available concurrently

### `RvT` — MCP resources vs tools (Topic 5)
- **R**esources = static content catalogs (docs, schemas, issue lists) — read-only, exposed for browsing
- **T**ools = actions with side effects — invoked by the agent to DO something
- Use resources to reduce exploratory tool calls — give the agent a directory listing before it has to grep

### `EES` — Escalation decision-making (Topic 8)
- **E**xplicit criteria in the system prompt (few-shot examples of "when to escalate")
- **E**mpirical customer preference (if the customer says "get me a human", escalate immediately regardless of criteria)
- **S**urface policy gaps back to the team — don't just escalate, log the pattern so policy can be updated

---

## Domain 3 — Claude Code Config

### `UPD` — CLAUDE.md hierarchy (Topic 9)
- **U**ser level (`~/.claude/CLAUDE.md`) — personal, NOT shared with team
- **P**roject level (`.claude/CLAUDE.md` or root `CLAUDE.md`) — team-wide via version control
- **D**irectory level (subfolder `CLAUDE.md`) — applies only in that subtree

Common exam trap: team member missing an instruction because it was placed at the user level.

### `RULES` — .claude/rules/ path-scoped rules (Topic 9)
- YAML frontmatter with `paths:` glob pattern (e.g. `paths: ["**/*.test.tsx"]`)
- Loads ONLY when editing matching files → saves tokens
- Prefer this over subdirectory `CLAUDE.md` when the convention spans multiple directories (e.g. all test files repo-wide)

### `SKILL` — Skill frontmatter fields (Topic 10)
- `context: fork` — run in isolated sub-agent context (keeps verbose output out of main convo)
- `allowed-tools:` — restrict tool access (e.g. read-only for a doc-generator)
- `argument-hint:` — prompt developer for required args when invoked without them
- Project-scoped in `.claude/skills/`, user-scoped in `~/.claude/skills/`

### `PLAN` — When to use plan mode (Topic 11)
- **P**arallel valid approaches exist (multiple ways to solve)
- **L**arge-scale change (many files, architectural implications)
- **A**mbiguous requirements needing exploration
- **N**ovel domain the user hasn't decided on

Direct execution = single-file bug with clear stack trace, adding a validation, obvious localised edit.

### `TIC` — Iterative refinement techniques (Topic 12)
- **T**ests first: write test suite, share failures to guide iteration
- **I**nput/output examples (2-3 concrete pairs) beat prose descriptions
- **C**onversation interview: have Claude ask questions before implementing

### `TvI` — When to bundle vs sequence fixes (Topic 12)
- **T**ogether if issues interact (fix them in one message so Claude sees the full picture)
- **I**ndividually if independent (sequence them to avoid confusing changes)

---

## Domain 4 — Prompt Engineering

### `SNT` — Structured output via tool_use schema design (Topic 13)
- **S**chema first — JSON schema is the contract; Claude conforms
- **N**ullable fields for uncertain data (prevents hallucination — model returns `null` instead of inventing)
- **T**ool_choice pin (`{"type": "tool", "name": "extract_X"}`) to force schema conformance every time

### `FEW` — Few-shot prompting (Topic 14)
- **F**ormat consistency — same shape across examples (labels, punctuation, casing)
- **E**dge cases first — target ambiguous scenarios, not easy ones (few-shot for ambiguity reduction)
- **W**rong-answer examples — include false-positive cases with the correct rejection

### `BATCH` — Message Batches API (Topic 15)
- **B**est for high-volume, non-urgent (up to 24h latency window)
- **A**mount: 50% cost discount vs sync API
- **T**ool use limitation: batches don't support multi-turn tool loops (single-turn only)
- **C**ustom_id correlation — each request has a unique id; correlate responses back
- **H**andle failures per-item: some batch requests can succeed while others fail — retry only failed items

---

## Domain 5 — Context & Reliability

### `TRIM` — Context window optimization (Topic 16)
- **T**rim verbose tool outputs (summarise before adding to context)
- **R**eorder inputs — position-aware (place critical facts at start and end; middle gets "lost")
- **I**mportant facts extract into structured summaries
- **M**iddle-of-context is where recall drops → don't put critical info there

### `CALIBRATE` — Human review / confidence calibration (Topic 17)
- **C**onfidence scores must be calibrated against labeled validation sets
- **A**ccuracy segmentation by document type AND by field
- **L**abeled ground truth is required — self-reported confidence is unreliable
- **I**mplementation: stratified sampling for error rate measurement
- **B**oundary threshold routing: below threshold → human review

### `CLASP` — Information provenance (Topic 18)
- **C**laim — the statement being made
- **L**inked source — URL or document reference
- **A**s of date — temporal validity of the claim
- **S**tatus — WELL_ESTABLISHED / CONTESTED / UNVERIFIED
- **P**artial coverage — explicitly note which subtopics have gaps

---

## Rapid-recall drill sheet

Cover the right column with your hand, expand each mnemonic aloud:

```
STOP     → Send · Test stop_reason · Operate tools · Proceed/Terminate
HUB      → Hub-and-spoke · Unique context · Breadth check
PIC      → Pass · Isolate · Crash-recover
SLAT     → Split · Limit count · Action-name · Tell what it returns
TVBP     → Transient · Validation · Business · Permission
CHOOSE   → auto · any · forced
MCP-PES  → Project · Env-var · Simultaneous
RvT      → Resources = content · Tools = actions
EES      → Explicit criteria · Empirical preference · Surface gaps
UPD      → User · Project · Directory
RULES    → YAML paths glob, path-scoped, prefer over subdir CLAUDE.md
SKILL    → context:fork · allowed-tools · argument-hint
PLAN     → Parallel approaches · Large · Ambiguous · Novel
TIC      → Tests first · I/O examples · Conversation-interview
SNT      → Schema first · Nullable fields · Tool_choice pin
FEW      → Format consistency · Edge cases · Wrong-answer examples
BATCH    → 24h · 50% cost · single-turn · custom_id · per-item failure
TRIM     → Trim outputs · Reorder · Important extract · Middle-of-context loss
CALIBRATE → Calibrate · Accuracy segment · Labeled truth · Sampling · Boundary route
CLASP    → Claim · Linked source · As-of date · Status · Partial coverage
```
