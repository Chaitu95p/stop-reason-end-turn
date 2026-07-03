# Tips, Tricks & Exam Strategy

---

## How to Read Exam Questions

The CCA-F uses scenario-based, multiple-choice questions. Every hard question follows one of these patterns:

### Pattern 1: "Which is the CORRECT implementation?"
The answer choices contain one canonical-correct pattern and 2-3 plausible-but-wrong variants.

**Strategy:** Identify the anti-pattern in each wrong answer:
- Does it parse text to decide when to stop? → Anti-pattern (use `stop_reason`)
- Does it skip appending tool results? → Missing context for next iteration
- Does it use a fixed iteration cap as the PRIMARY stop? → Anti-pattern

### Pattern 2: "What SHOULD the agent do when...?"
Tests error recovery behavior. The correct answer always matches the error category → action mapping.

**Strategy:** Map error → category → action in one step:
- "Service unavailable after 5s" → transient → retry once
- "Amount exceeds $500 limit" → business → explain policy, do NOT retry
- "Customer ID format is wrong" → validation → ask for correct ID
- "Requires elevated permissions" → permission → escalate to human immediately

### Pattern 3: "Which configuration achieves...?"
Tests CLAUDE.md hierarchy, MCP config, and skill frontmatter knowledge.

**Strategy:** Determine the SCOPE being described (user/project/directory/path) and pick the configuration level that matches.

### Pattern 4: "What is the MOST LIKELY reason for this behavior?"
Describes unexpected agent behavior (hallucination, wrong tool called, context loss) and asks you to diagnose.

**Strategy:** Work backwards from the symptom:
- Two similar tools chosen incorrectly → tool description ambiguity
- Agent loops forever → not checking `stop_reason` or missing `end_turn` handling
- Subagent returns irrelevant results → coordinator didn't pass context explicitly
- Model fabricates a field value → schema is missing `nullable` on that field

---

## High-Value Mnemonics (Memorize These)

### STOP — Agentic Loop Lifecycle
```
S — Send request to Claude
T — Test stop_reason
O — Operate tools (if "tool_use")
P — Proceed (loop back) or Terminate (if "end_turn")
```

### TVBP — Error Categories
```
T — Transient  (isRetryable=true):  Retry → escalate
V — Validation (isRetryable=false): Fix input
B — Business   (isRetryable=false): Explain policy
P — Permission (isRetryable=false): Escalate immediately
```

### CPDS — MCP Config File Scope
```
C — .mcp.json    → Current project (checked in)
P — ~/.claude.json → Personal user-level
D — Both can be   → Dual-active simultaneously
S — Secrets expand via ${VAR_NAME}
```

### FANE — Skill Frontmatter Options
```
F — Fork context (context: fork) = isolated, doesn't pollute main
A — Allowed-tools: restricts tools inside skill
N — N/a to main conversation = fork runs separately
E — Enhances reusability without side effects on context
```

### LAME — Context Window Priority (what to preserve)
```
L — Latest user message (always keep)
A — Active system instructions (never trim)
M — Most recent tool results (keep N most recent)
E — Earliest history (trim first)
```

---

## Anti-Patterns That Appear as Wrong Answers

These anti-patterns show up explicitly as wrong answer choices. Know them so you can eliminate them instantly.

### Domain 1 Anti-patterns

**AP-1: Text parsing for loop termination**
```python
# WRONG
if "DONE" in response_text.upper():
    break
```
→ Correct: `if response.stop_reason == "end_turn": return`

**AP-2: Fixed iteration cap as primary stop**
```python
# WRONG as primary mechanism
for i in range(5):
    ...
```
→ Correct: `while True:` with `stop_reason` as the only exit

**AP-3: Missing tool result append**
```python
# WRONG: calling API again without appending tool results
messages.append({"role": "assistant", "content": response.content})
# forgot: messages.append({"role": "user", "content": tool_results})
response = client.messages.create(...)
```

**AP-4: Assuming subagents inherit parent context**
```python
# WRONG
task_prompt = f"Continue analyzing issue #{issue_id}"
# CORRECT
task_prompt = f"Analyze this issue: {issue_details}. Context: {relevant_history}"
```

### Domain 2 Anti-patterns

**AP-5: Uniform error responses**
```json
// WRONG
{"error": "Operation failed"}

// CORRECT
{"isError": true, "errorCategory": "transient", "isRetryable": true, ...}
```

**AP-6: Empty result treated as error**
```python
# WRONG: raising exception when query succeeds but finds nothing
if not results:
    return {"isError": True, "error": "Not found"}

# CORRECT
return {"isError": False, "results": [], "querySuccessful": True}
```

### Domain 3 Anti-patterns

**AP-7: Skill without context: fork polluting main context**
> A skill that modifies or extends the main conversation context when it should be isolated.
> Fix: add `context: fork` to SKILL.md frontmatter.

**AP-8: Putting secrets directly in .mcp.json**
```json
// WRONG
{"env": {"API_KEY": "sk-abc123"}}

// CORRECT
{"env": {"API_KEY": "${MY_SECRET_KEY}"}}
```

### Domain 4 Anti-patterns

**AP-9: Schema without nullable fields**
```json
// WRONG: refund_amount must always have a value, model hallucinates
"refund_amount": {"type": "number"}

// CORRECT: allow null when value isn't in the document
"refund_amount": {"type": ["number", "null"]}
```

**AP-10: Validation retry without error details**
```python
# WRONG: sending generic retry
messages.append({"role": "user", "content": "Please try again."})

# CORRECT: include the specific validation error
retry_msg = f"Validation failed: {validation_error}. Original document: {document}"
messages.append({"role": "user", "content": retry_msg})
```

---

## Domain-Specific Quick Wins

### Domain 1 (27%) — Highest ROI

The loop pattern is the most-tested concept in the entire exam. You need to be able to:
1. Write the correct `while True:` loop from memory
2. Identify which of 4 loop variants is correct
3. Know that ALL tool_use blocks in one response are executed together before the next API call

**Easy 3 points:** Know that `stop_reason` can be `"tool_use"`, `"end_turn"`, `"max_tokens"`, or `"stop_sequence"`. Only `"tool_use"` should loop; all others are terminal.

### Domain 3 (20%) — Configuration Hierarchy

The hierarchy question always describes a scenario where the answer depends on which level takes precedence. The override order is:

```
directory CLAUDE.md  >  project CLAUDE.md  >  user CLAUDE.md
.claude/rules/*.md (additive, path-scoped)
```

**Easy 2 points:** `.claude/rules/` files are ADDITIVE to CLAUDE.md, not overrides. They activate only for matching file paths.

### Domain 4 (20%) — When to Use Batch API

The exam will present a scenario and ask if the Batches API is appropriate. Apply this decision tree:

```
Latency-tolerant (can wait up to 24h)?    → YES required
Single-turn only (no tool calling loop)?  → Batches fits
Cost reduction is priority?               → Batches (50% savings)

Needs real-time response?                 → NO, use standard API
Needs multi-turn tool calling?            → NO, use standard API
```

### Domain 2 (18%) — Tool Description Quality

Tool selection failures in exams are always caused by ambiguous tool descriptions. The exam tests whether you can identify the RIGHT fix:

- Two tools with overlapping scope → fix: add explicit boundary conditions ("Use THIS tool when X; use OTHER tool when Y")
- Tool called with wrong input format → fix: add input schema constraints + examples in description
- Tool called when it shouldn't be → fix: add negative examples ("Do NOT use this for...")

### Domain 5 (15%) — Context Position Effects

**Lost-in-the-middle:** Models attend best to content at the START and END of their input. In multiple-choice questions about why critical instructions were ignored, the answer is almost always "the instruction was placed in the middle of a long context."

---

## Day-of-Exam Strategy

1. **Flag and skip hard questions** — don't spend more than 90 seconds on any single question; flag it and return after completing the rest
2. **Eliminate anti-patterns first** — most wrong answers contain an identifiable anti-pattern (text parsing, missing tool results, fixed caps); eliminating these narrows most questions to 2 choices
3. **For "MOST appropriate" questions** — the correct answer is usually the one that mentions `stop_reason`, `errorCategory`, or explicit context passing; answers that describe heuristics or natural language parsing are almost always wrong
4. **For architecture questions** — prefer the answer that adds the least coupling between components; the exam values clean separation between orchestrator, subagents, and tools
5. **Trust the exam guide language** — when an answer uses exact terminology from the guide (TVBP, `context: fork`, `querySuccessful`), it is usually correct; when an answer uses vague language ("best effort," "as appropriate"), it is usually wrong
