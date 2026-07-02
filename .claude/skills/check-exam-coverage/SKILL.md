---
description: Cross-check all demo scripts against the CCA-F exam domain and task list, identify uncovered or thin topics
argument-hint: "[optional: specific domain number 1-5, or leave blank for all]"
allowed-tools: Glob, Grep, Read
context: fork
---

# Skill: check-exam-coverage
# Usage: /check-exam-coverage        (checks all 5 domains)
#        /check-exam-coverage 3      (checks only Domain 3)

Read all demo scripts and cross-reference their coverage against the complete
CCA-F exam domain and task list. Identify gaps, thin coverage, and uncovered topics.

## Authoritative exam domain/task list

### Domain 1 — Agentic Architecture & Orchestration (27%)
- 1.1 Agentic loop lifecycle (stop_reason, tool execution, history)
- 1.2 Multi-agent coordination (hub-and-spoke, decomposition, DARE)
- 1.3 Subagent context passing (explicit injection, parallel spawning)
- 1.4 Workflow enforcement (programmatic gates vs prompt-based ordering)
- 1.5 SDK hooks (PostToolUse normalization, PreToolCall policy enforcement)
- 1.6 Task decomposition (prompt chaining vs dynamic adaptive)
- 1.7 Session management (resumption, fork_session, stale context)

### Domain 2 — Tool Design & MCP Integration (18%)
- 2.1 Tool interface design (SEEB: scope, examples, edge-cases, boundaries)
- 2.2 Structured error responses (TVBP: transient/validation/business/permission)
- 2.3 Tool distribution & scoping (overload anti-pattern, scoped subagents, tool_choice)
- 2.4 MCP server configuration (.mcp.json, project vs user scope, env-var expansion)
- 2.5 Built-in tool selection (GRREW: Grep/Read/Read+Write/Edit/Write)

### Domain 3 — Claude Code Configuration & Workflows (20%)
- 3.1 CLAUDE.md hierarchy (user/project/subdirectory, @import, merging)
- 3.2 Custom commands & skills ($ARGUMENTS, frontmatter, context:fork, allowed-tools)
- 3.3 Path-specific rules (.claude/rules/, YAML frontmatter, glob patterns)
- 3.4 Plan mode vs direct execution (triggers, EnterPlanMode, approval flow)
- 3.5 Iterative refinement (I/O examples, TDD iteration, interview pattern)
- 3.6 CI/CD integration (-p flag, structured output, session isolation, prior findings)

### Domain 4 — Prompt Engineering & Structured Output (20%)
- 4.1 Explicit criteria (PRECISE mnemonic, disable high-FP categories)
- 4.2 Few-shot prompting (FADE mnemonic, tool selection, extraction)
- 4.3 Structured output via tool_use (SANE reliability ladder, tool_choice modes)
- 4.4 Validation & retry loop (semantic validation, retry on failure)
- 4.5 Batch processing (parallel vs sequential, rate limiting)
- 4.6 Multi-pass review (first pass broad, second pass targeted)
- 4.7 Prefill technique (assistant turn prefill, temperature settings, XML system prompts)

### Domain 5 — Context Management & Reliability (15%)
- 5.1 Context preservation (FACT mnemonic, progressive summarization risk, trimming)
- 5.2 Escalation patterns (objective triggers, acknowledge-first, few-shot criteria)
- 5.3 Error propagation (suppress anti-pattern, terminate anti-pattern, partial results)
- 5.4 Codebase context (degradation, scratchpad pattern, crash recovery manifest)
- 5.5 Human review & confidence (field-level scores, stratified sampling, routing thresholds)
- 5.6 Information provenance (claim-source mapping, conflict annotation, temporal data)

## Steps

1. Use Glob to enumerate all demo scripts: `Glob('module-*/0*.py')`

2. For each script, Read the header docstring and extract the task number (Domain N - Task N.M).

3. Build a coverage matrix: which tasks from the list above have a corresponding script?

4. Identify:
   - **Covered tasks**: task has a dedicated script, mnemonic present, KEY TAKEAWAYS complete
   - **Thinly covered**: task is mentioned in a script but not as the primary focus
   - **Gap tasks**: task appears in the exam list but no script covers it

5. Output the coverage report:

---
## CCA-F Coverage Report

### Summary
- Total exam tasks: 31
- Fully covered: N
- Thinly covered: N
- Gap (no script): N
- Coverage: N%

### Domain-by-Domain Breakdown

#### Domain 1 (27%) — Agentic Architecture & Orchestration
| Task | Script | Status |
|------|--------|--------|
| 1.1 Agentic loop | module-1/01_agentic_loop.py | ✅ Covered |
...

#### Domain 2 (18%) — Tool Design & MCP Integration
...

### Gaps & Recommendations
For each gap or thin coverage area:
- Task N.M: <description>
  - Suggested script: `module-N/0N_<name>.py`
  - Key concepts to cover: ...
  - Use `/new-demo module-N N.M` to scaffold it

---

## Notes
- READ-ONLY (allowed-tools: Glob, Grep, Read — no writes)
- Runs in a forked session (context: fork)
- No Anthropic API calls — pure file analysis
