# Quick Reference Card — Review Morning of Exam

---

## The Canonical Agentic Loop (write from memory)

```python
messages = [{"role": "user", "content": user_message}]
while True:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM,
        tools=TOOLS,
        messages=messages,
    )
    if response.stop_reason == "end_turn":
        return next(b.text for b in response.content if hasattr(b, "text"))
    if response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = TOOL_REGISTRY[block.name](**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})
    # "max_tokens", "stop_sequence" → also terminal, handle like end_turn
```

---

## TVBP Error Categories

| Category | isRetryable | Agent Does |
|----------|-------------|-----------|
| Transient | `true` | Retry once; escalate if still failing |
| Validation | `false` | Ask user for corrected input |
| Business | `false` | Explain policy using `humanMessage` |
| Permission | `false` | Escalate to human immediately |

**Empty result ≠ Error.** Use `{"isError": false, "results": [], "querySuccessful": true}`

---

## CLAUDE.md Hierarchy

```
~/.claude/CLAUDE.md          → user-level (all projects)
<repo>/CLAUDE.md             → project-level (all sessions in repo)
<repo>/<dir>/CLAUDE.md       → directory-level (sessions in that dir)
.claude/rules/*.md           → path-scoped (additive, YAML paths: frontmatter)
```

Override direction: **directory > project > user** (more specific wins)

---

## Skill Frontmatter

```yaml
---
context: fork          # ISOLATED — doesn't affect main conversation
allowed-tools:
  - Read
  - Bash
argument-hint: "<target>"
---
```

Without `context: fork` → skill runs in main context (contaminates it).

---

## MCP Server Config

```json
// .mcp.json = project scope (checked in)
// ~/.claude.json = user scope (personal)
// Both active simultaneously

{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["server.js"],
      "env": { "API_KEY": "${MY_API_KEY}" }  // ← env var expansion
    }
  }
}
```

- **Tools** = actions with side effects
- **Resources** = read-only content catalogs

---

## Structured Output Pattern

```python
response = client.messages.create(
    tools=[extraction_tool],
    tool_choice={"type": "tool", "name": "extract_data"},  # force specific tool
    messages=[{"role": "user", "content": document}],
)
```

- `tool_choice: "auto"` — model decides whether to use a tool
- `tool_choice: "any"` — must call SOME tool
- `tool_choice: {"type": "tool", "name": "X"}` — must call tool X

**Nullable fields** prevent hallucination: `"type": ["string", "null"]`

---

## Message Batches API

| Property | Value |
|----------|-------|
| Cost | 50% reduction |
| Latency | Up to 24 hours |
| Multi-turn tool calling | NOT supported |
| Correlation | `custom_id` field |
| Completion check | Poll (no webhooks) |

Use when: latency-tolerant, single-turn, cost-sensitive.
Do NOT use when: real-time required, or needs agentic tool calling loop.

---

## Multi-Agent Context Passing

```python
# CORRECT: explicit context passing
task_prompt = f"""
Research: {question}
Prior context: {json.dumps(coordinator_findings)}
Output format: {json.dumps(output_schema)}
"""

# WRONG: subagents do NOT inherit parent history
task_prompt = f"Continue the research from earlier."
```

**Parallel subagents:** emit multiple `tool_use` blocks in ONE response.
**Sequential subagents:** emit one tool_use block per response.

---

## Plan Mode Decision Rule

| Situation | Mode |
|-----------|------|
| Multi-file changes | Plan mode |
| Architectural decision with multiple valid approaches | Plan mode |
| High-risk / irreversible operations | Plan mode |
| Single-file bug fix | Direct |
| Simple CRUD / obvious implementation | Direct |

---

## Context Window Optimization

1. **Trim verbose tool outputs** — extract only the relevant fields into a compact JSON summary
2. **Scratchpad files** — write structured state to disk for sessions exceeding context limits
3. **Position matters** — critical info at START or END (lost-in-the-middle effect)
4. **Subagent delegation** — only the *summary* returns to coordinator, not the full subagent transcript

---

## Escalation Decision Tree

```
Can I resolve this within my defined authority?
  YES → resolve autonomously
  NO  → escalate

Did the customer explicitly ask for a human?
  YES → escalate immediately (regardless of whether I could resolve it)

Is this a transient error?
  YES → retry first; escalate only if retry fails

Is this a permission/business error?
  YES → permission = escalate immediately
       business   = explain policy (do NOT escalate unless customer requests)
```

---

## stop_reason Values

| Value | Meaning | Loop action |
|-------|---------|-------------|
| `"tool_use"` | Model wants to call tools | Execute tools, loop |
| `"end_turn"` | Model finished | Terminate, return response |
| `"max_tokens"` | Hit token limit | Terminate (handle gracefully) |
| `"stop_sequence"` | Hit stop sequence | Terminate |

---

## Key Numbers

| Fact | Value |
|------|-------|
| Batches API cost saving | 50% |
| Batches API max processing time | 24 hours |
| Batches supports multi-turn tool calling | NO |
| Domain 1 exam weight | 27% |
| Domain 3 exam weight | 20% |
| Domain 4 exam weight | 20% |
| Domain 2 exam weight | 18% |
| Domain 5 exam weight | 15% |
