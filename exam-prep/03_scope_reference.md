# In-Scope and Out-of-Scope Topics

> Source: CCA-F Exam Guide v0.2 Appendix — "In-Scope Topics" and "Out-of-Scope Topics"

Use this as a filter when studying. If a topic is out-of-scope, skip it completely and use that time on in-scope material.

---

## IN-SCOPE — Will Appear on Exam

### Domain 1 — Agentic Architecture & Orchestration (27%)
- Agentic loop implementation: control flow based on `stop_reason`, tool result handling, loop termination
- Multi-agent orchestration: coordinator-subagent patterns, task decomposition, parallel subagent execution, iterative refinement loops
- Subagent context management: explicit context passing, structured state persistence, crash recovery using manifests

### Domain 2 — Tool Design & MCP Integration (18%)
- Tool interface design: effective tool descriptions, splitting vs consolidating tools, naming to reduce ambiguity
- MCP tool and resource design: resources for content catalogs, tools for actions, description quality
- MCP server configuration: project vs user scope, environment variable expansion, multi-server simultaneous access
- Error handling and propagation: structured error responses, transient vs business vs permission errors, local recovery before escalation
- Escalation decision-making: explicit criteria, honoring customer preferences, policy gap identification

### Domain 3 — Claude Code Configuration & Workflows (20%)
- CLAUDE.md configuration: hierarchy (user/project/directory), `@import` patterns, `.claude/rules/` with glob patterns
- Custom commands and skills: project vs user scope, `context: fork`, `allowed-tools`, `argument-hint` frontmatter
- Plan mode vs direct execution: complexity assessment, architectural decisions, single-file changes

### Domain 4 — Prompt Engineering & Structured Output (20%)
- Iterative refinement: input/output examples, test-driven iteration, interview pattern, sequential vs parallel issue resolution
- Structured output via `tool_use`: schema design, `tool_choice` configuration, nullable fields to prevent hallucination
- Few-shot prompting: ambiguous scenario targeting, format consistency, false positive reduction
- Batch processing: Message Batches API appropriateness, latency tolerance assessment, failure handling by `custom_id`

### Domain 5 — Context Management & Reliability (15%)
- Context window optimization: trimming verbose tool outputs, structured fact extraction, position-aware input ordering
- Human review workflows: confidence calibration, stratified sampling, accuracy segmentation by document type and field
- Information provenance: claim-source mappings, temporal data handling, conflict annotation, coverage gap reporting

---

## Technologies and Concepts — Full Exam Coverage List

These are the exact technologies from the appendix that may appear on exam questions:

**Claude Agent SDK**
- Agent definitions, agentic loops, `stop_reason` handling
- Hooks (`PostToolUse`, tool call interception)
- Subagent spawning via Task tool, `allowedTools` configuration

**Model Context Protocol (MCP)**
- MCP servers, MCP tools, MCP resources
- `isError` flag, tool descriptions, tool distribution
- `.mcp.json` configuration, environment variable expansion

**Claude Code**
- CLAUDE.md configuration hierarchy (user/project/directory)
- `.claude/rules/` with YAML frontmatter path-scoping
- `.claude/commands/` for slash commands
- `.claude/skills/` with SKILL.md frontmatter (`context: fork`, `allowed-tools`, `argument-hint`)
- Plan mode, direct execution, `/memory` command, `/compact`, `--resume`, `fork_session`, Explore subagent

**Claude Code CLI**
- `-p` / `--print` flag for non-interactive mode
- `--output-format json`
- `--json-schema` for structured CI output

**Claude API**
- `tool_use` with JSON schemas
- `tool_choice` options: `"auto"`, `"any"`, forced tool selection
- `stop_reason` values: `"tool_use"`, `"end_turn"`
- `max_tokens`, system prompts

**Message Batches API**
- 50% cost savings
- Up to 24-hour processing window
- `custom_id` for request/response correlation
- Polling for completion
- No multi-turn tool calling support

**JSON Schema**
- Required vs optional fields
- Enum types, nullable fields
- "Other" + detail string patterns
- Strict mode for syntax error elimination

**Pydantic**
- Schema validation, semantic validation errors, validation-retry loops

**Built-in Tools**
- Read, Write, Edit, Bash, Grep, Glob — their purposes and selection criteria

**Few-shot Prompting**
- Targeted examples for ambiguous scenarios
- Format demonstration, generalization to novel patterns

**Prompt Chaining**
- Sequential task decomposition into focused passes

**Context Window Management**
- Token budgets, progressive summarization
- Lost-in-the-middle effects, context extraction, scratchpad files

**Session Management**
- Session resumption, `fork_session`, named sessions, session context isolation

**Confidence Scoring**
- Field-level confidence, calibration with labeled validation sets
- Stratified sampling for error rate measurement

---

## OUT-OF-SCOPE — Will NOT Appear on Exam

Skip these entirely. Do not study them for this exam.

| Topic | Why Out of Scope |
|-------|-----------------|
| Fine-tuning / custom model training | Not relevant to using Claude API |
| Claude API authentication, billing, account management | Administrative, not architectural |
| Specific programming languages or frameworks | Exam is language-agnostic |
| Deploying/hosting MCP servers (infra, networking, containers) | Infrastructure layer |
| Claude's internal architecture, training, model weights | Internal — not exposed |
| Constitutional AI, RLHF, safety training methodologies | Training methodology |
| Embedding models or vector database implementation | Different domain |
| Computer use (browser automation, desktop interaction) | Different capability |
| Vision/image analysis capabilities | Different capability |
| Streaming API / server-sent events | API surface, not architecture |
| Rate limiting, quotas, API pricing calculations | Billing/ops concern |
| OAuth, API key rotation, auth protocols | Security/ops concern |
| Specific cloud provider configs (AWS, GCP, Azure) | Infrastructure layer |
| Performance benchmarking or model comparison metrics | Evaluation, not architecture |
| Prompt caching implementation details | "Beyond knowing it exists" |
| Token counting algorithms / tokenization specifics | Internal implementation |

**Study tip:** If a practice question drifts into any of these topics, it is either a bad practice question or you are overthinking the scope of a legitimate question. Refocus on the in-scope concept being tested.
