# Official Preparation Exercises

> Source: CCA-F Exam Guide v0.2, section "Preparation Exercises" (steps 1-20)

These 4 exercises are the official hands-on tasks from the exam guide.
Each is annotated with what to focus on and how to connect it to this repo.

---

## Exercise 1: Build a Multi-Tool Agent with Escalation Logic

**Domains reinforced:** Domain 1 (Agentic Architecture), Domain 2 (Tool Design), Domain 5 (Context & Reliability)

**Objective:** Design an agentic loop with tool integration, structured error handling, and escalation patterns.

### Steps

**Step 1** — Define 3-4 MCP tools with detailed descriptions that clearly differentiate each tool's purpose, expected inputs, and boundary conditions. Include at least two tools with similar functionality that require careful description to avoid selection confusion.

> **Exam focus:** Tool descriptions are one of the most-tested topics. Two tools that sound similar but have different scopes (e.g., `get_customer` vs `lookup_account`) must have descriptions that make the decision boundary unmistakable.

**Step 2** — Implement an agentic loop that checks `stop_reason` to determine whether to continue tool execution or present the final response. Handle both `"tool_use"` and `"end_turn"` stop reasons correctly.

> **Repo reference:** `modules/module-1/01_agentic_loop.py` — `run_agentic_loop()` is the canonical correct implementation.

**Step 3** — Add structured error responses to your tools: include `errorCategory` (transient/validation/permission), `isRetryable` boolean, and human-readable descriptions. Test that the agent handles each error type appropriately.

> **Repo reference:** `modules/module-2/02_structured_error_responses.py` — `make_error()` is the canonical pattern.

**Step 4** — Implement a programmatic hook that intercepts tool calls to enforce a business rule (e.g., blocking operations above a threshold amount), redirecting to an escalation workflow when triggered.

> **Exam focus:** Hooks are a Domain 3 topic. `PreToolUse` hooks run before the tool executes; `PostToolUse` hooks run after. Blocking via a hook is different from the model deciding not to call a tool.

**Step 5** — Test with multi-concern messages (e.g., requests involving multiple issues) and verify the agent decomposes the request, handles each concern, and synthesizes a unified response.

> **Exam focus:** Multi-concern decomposition is the reason coordinators spawn subagents. Each concern maps to one subagent; the coordinator synthesizes results.

---

## Exercise 2: Configure Claude Code for a Team Development Workflow

**Domains reinforced:** Domain 3 (Claude Code Configuration), Domain 2 (MCP Integration)

**Objective:** Configure CLAUDE.md hierarchies, custom slash commands, path-specific rules, and MCP server integration for a multi-developer project.

### Steps

**Step 6** — Create a project-level CLAUDE.md with universal coding standards and testing conventions. Verify that instructions placed at the project level are consistently applied across all team members.

> **Repo reference:** This repo's root `CLAUDE.md` is the example. Note how it uses `@` imports to pull in specific script files.

**Step 7** — Create `.claude/rules/` files with YAML frontmatter glob patterns for different code areas.

```yaml
---
paths:
  - "src/api/**/*"
---
# API conventions here — only loaded when editing API files
```

> **Exam focus:** Path rules use YAML frontmatter with `paths:` key containing glob patterns. Rules in `.claude/rules/` are additive; they do not override CLAUDE.md.

**Step 8** — Create a project-scoped skill in `.claude/skills/` with `context: fork` and `allowed-tools` restrictions. Verify the skill runs in isolation without polluting the main conversation context.

```yaml
---
context: fork
allowed-tools:
  - Read
  - Bash
argument-hint: "<target-directory>"
---
```

> **Exam focus:** `context: fork` is the isolation mechanism. Without it, skill execution shares and modifies main context. Know this distinction cold.

**Step 9** — Configure an MCP server in `.mcp.json` with environment variable expansion for credentials. Add a personal experimental MCP server in `~/.claude.json` and verify both are available simultaneously.

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["server.js"],
      "env": {
        "API_KEY": "${MY_API_KEY}"
      }
    }
  }
}
```

> **Exam focus:** `.mcp.json` = project scope (checked into repo); `~/.claude.json` = user scope (personal only). Both can be active simultaneously. Environment variable expansion uses `${VAR_NAME}` syntax.

**Step 10** — Test plan mode versus direct execution on tasks of varying complexity: a single-file bug fix, a multi-file library migration, and a new feature with multiple valid implementation approaches.

> **Plan mode triggers:** architectural decisions, multi-file changes, multiple valid implementation approaches, high-risk/irreversible operations. **Skip plan mode:** single-file edits, obvious implementations, simple CRUD.

---

## Exercise 3: Build a Structured Data Extraction Pipeline

**Domains reinforced:** Domain 4 (Prompt Engineering & Structured Output), Domain 5 (Context Management)

**Objective:** Design JSON schemas, use tool_use for structured output, implement validation-retry loops, and design batch processing strategies.

### Steps

**Step 11** — Define an extraction tool with a JSON schema containing required and optional fields, an enum with an "other" + detail string pattern, and nullable fields for information that may not exist in source documents.

```json
{
  "type": "object",
  "properties": {
    "order_type": {
      "type": "string",
      "enum": ["refund", "exchange", "complaint", "other"]
    },
    "order_type_detail": {
      "type": ["string", "null"],
      "description": "Required when order_type is 'other'"
    },
    "refund_amount": {
      "type": ["number", "null"],
      "description": "null if not mentioned in document"
    }
  },
  "required": ["order_type"]
}
```

> **Exam focus:** `nullable` fields (`"type": ["string", "null"]`) prevent the model from hallucinating values when information is absent. This is the correct pattern — not omitting the field from the schema.

**Step 12** — Implement a validation-retry loop: when Pydantic or JSON schema validation fails, send a follow-up request including the document, the failed extraction, and the specific validation error.

```python
for attempt in range(max_retries):
    result = call_claude(document, tool_schema)
    try:
        validated = MySchema.model_validate(result)
        return validated
    except ValidationError as e:
        # Send the error back to Claude with the original document
        retry_prompt = f"Previous extraction failed validation: {e}\nRetry with document: {document}"
```

> **Exam focus:** Include the specific validation error in the retry prompt — not just "try again." The model needs to know what went wrong to fix it.

**Step 13** — Add few-shot examples demonstrating extraction from documents with varied formats (inline citations vs bibliographies, narrative descriptions vs structured tables).

> **Exam focus:** Few-shot examples for extraction should demonstrate the *ambiguous* format variations, not just the happy-path format. Target the specific structural patterns that cause failures.

**Step 14** — Design a batch processing strategy: submit a batch of 100 documents using the Message Batches API, handle failures by `custom_id`, resubmit failed documents with modifications.

> **Batch API rules:**
> - Set `custom_id` to your document ID so you can match responses to inputs
> - Poll for batch completion (no push notifications)
> - Resubmit failures after diagnosing: chunk oversized documents, fix format issues
> - 24-hour window means batch processing is for latency-tolerant workflows only

**Step 15** — Implement a human review routing strategy: output field-level confidence scores, route low-confidence extractions to human review, analyze accuracy by document type and field.

> **Exam focus:** Confidence calibration is the key concept. Verify calibration with a labeled validation set: if the model says 0.9 confidence, ~90% of those extractions should actually be correct. If not, adjust thresholds.

---

## Exercise 4: Design and Debug a Multi-Agent Research Pipeline

**Domains reinforced:** Domain 1 (Agentic Architecture), Domain 2 (MCP), Domain 5 (Context Management)

**Objective:** Orchestrate subagents, manage context passing, implement error propagation, and handle synthesis with provenance tracking.

### Steps

**Step 16** — Build a coordinator agent that delegates to at least two subagents. Ensure the coordinator's `allowedTools` includes `"Task"` and that each subagent receives its research findings directly in its prompt.

> **Critical exam fact:** Subagents do NOT inherit the coordinator's conversation history. The coordinator must explicitly pass all relevant context in the Task tool's `prompt` parameter.

```python
# CORRECT: pass context explicitly
task_prompt = f"""
Research the following claim: {claim}
Use these prior findings as context: {json.dumps(prior_findings)}
"""

# WRONG: assume subagent has access to parent context
task_prompt = f"Research claim #{claim_id}"  # subagent has no idea what claim_id refers to
```

**Step 17** — Implement parallel subagent execution by having the coordinator emit multiple Task tool calls in a single response. Measure the latency improvement compared to sequential execution.

> **Exam focus:** Parallel spawning happens when the model emits multiple `tool_use` blocks in ONE response. If it emits them in separate responses, they run sequentially. The agentic loop framework handles parallel execution when multiple tool calls appear together.

**Step 18** — Design structured output for subagents that separates content from metadata: each finding should include a claim, evidence excerpt, source URL/document name, and publication date.

> **Provenance tracking pattern:**
```json
{
  "claim": "X causes Y",
  "evidence_excerpt": "...direct quote from source...",
  "source_url": "https://...",
  "publication_date": "2024-03-15",
  "confidence": 0.87
}
```

**Step 19** — Implement error propagation: simulate a subagent timeout and verify the coordinator receives structured error context (failure type, attempted query, partial results).

> **Exam focus:** Subagents should NOT silently fail. The structured error should include:
> - `failure_type`: what went wrong
> - `attempted_query`: what was being searched
> - `partial_results`: whatever was found before failure (don't discard)
> The coordinator proceeds with partial results and annotates the output with coverage gaps.

**Step 20** — Test with conflicting source data and verify the synthesis output preserves both values with source attribution rather than arbitrarily selecting one.

> **Provenance conflict rule:** When two credible sources conflict, the correct output is:
> ```
> Source A (2023) reports X = 42%; Source B (2024) reports X = 38%. Sources disagree.
> ```
> **Not:** silently picking one value. The exam will test this specific behavior.
