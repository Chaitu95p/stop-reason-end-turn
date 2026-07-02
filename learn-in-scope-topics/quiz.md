# CCA-F Practice Quiz — 20 Questions

Exam-style multiple-choice questions covering all 18 in-scope topics. Answers + explanations at the bottom. **Do the full 20 before looking**.

---

**Q1.** An agentic loop should terminate when:

A) The response text contains "DONE"
B) A fixed iteration count is reached
C) `response.stop_reason == "end_turn"`
D) The response contains no tool_use blocks

---

**Q2.** A coordinator agent decomposes "impact of AI on creative industries" into three subtasks: "AI in digital art", "AI in graphic design", "AI in photography". Each subagent completes successfully but the final report misses music, writing, and film. The root cause is:

A) Synthesis agent lacks gap-detection instructions
B) Coordinator decomposition is too narrow
C) Search subagent queries need broadening
D) Document analysis filters were too restrictive

---

**Q3.** You want a subagent to survive a crash and resume from where it stopped. The correct approach is:

A) Rely on the coordinator to re-invoke it with the same prompt
B) Persist a structured manifest of completed steps; replay from manifest on restart
C) Increase the retry count in the coordinator's error handler
D) Use context: fork to isolate the subagent

---

**Q4.** An agent has 18 tools available and frequently picks wrong ones. The best first fix is:

A) Improve tool descriptions
B) Add `tool_choice: "any"` to force a call
C) Restrict the agent to 4-5 tools relevant to its role
D) Add few-shot examples of correct tool sequences

---

**Q5.** In `.mcp.json` you have `"env": {"TOKEN": "${GITHUB_TOKEN}"}`. What happens?

A) The literal string `${GITHUB_TOKEN}` is sent to the MCP server
B) Claude Code expands the env var at connection time
C) The MCP server itself resolves the placeholder
D) An error — env-var expansion is not supported in `.mcp.json`

---

**Q6.** A tool returns `{"isError": true, "errorCategory": "business", "isRetryable": false, "humanMessage": "Refunds over $500 require manager approval"}`. The correct agent behaviour is:

A) Retry the operation once
B) Return the humanMessage to the customer and stop retrying
C) Escalate to a human agent immediately
D) Ask the customer to reformat the request

---

**Q7.** Which is TRUE about empty results vs access failures?

A) Both should return `isError: true`
B) Empty results should be `isError: false` with `querySuccessful: true`
C) Access failures should be silently ignored
D) There is no meaningful distinction — both are failures

---

**Q8.** You want a customer support agent to sometimes call the tool `escalate_to_human` and sometimes reply directly. The best `tool_choice` setting is:

A) `"auto"`
B) `"any"`
C) `{"type": "tool", "name": "escalate_to_human"}`
D) None — remove `tool_choice` entirely

---

**Q9.** A teammate reports that `CLAUDE.md` instructions you added aren't taking effect for them. Most likely cause:

A) You placed the file in `~/.claude/CLAUDE.md` (user-scoped, not shared)
B) The file needs a YAML frontmatter block
C) They need to run `/reload`
D) `CLAUDE.md` doesn't affect Claude Code — only the API

---

**Q10.** You want a rule that applies whenever anyone edits `**/*.test.tsx`, regardless of which directory the test file lives in. Best place:

A) `.claude/CLAUDE.md` at the root
B) A subdirectory `CLAUDE.md` in `tests/`
C) `.claude/rules/tests.md` with YAML `paths: ["**/*.test.tsx"]`
D) `~/.claude/CLAUDE.md` on each teammate's machine

---

**Q11.** A skill that produces verbose codebase-analysis output should use which frontmatter option to keep the main conversation clean?

A) `allowed-tools:`
B) `context: fork`
C) `argument-hint:`
D) `verbose: false`

---

**Q12.** You need to restructure a monolith into microservices — dozens of files, unclear service boundaries. Best approach:

A) Direct execution — start editing and iterate
B) Enter plan mode to explore, understand dependencies, and design first
C) Use `context: fork` on a skill
D) Configure a new MCP server for the migration

---

**Q13.** You've described a data transformation in prose but Claude's output is inconsistent across runs. Best fix:

A) Increase max_tokens
B) Switch to a larger model
C) Provide 2-3 concrete input/output examples
D) Add "please be consistent" to the prompt

---

**Q14.** You want Claude to always return JSON matching a specific schema. Best approach:

A) Ask nicely in the system prompt
B) Define a tool with that schema in `input_schema` and use `tool_choice: {"type": "tool", "name": "..."}`
C) Use `response_format: "json"` (doesn't exist in Anthropic API)
D) Parse the assistant text with a regex

---

**Q15.** A field in your extraction schema is often unknown from the source document. Best schema design:

A) Set a required default like `"unknown"`
B) Make the field nullable — allow `null` to be returned
C) Omit the field from the schema
D) Add a follow-up tool call to look it up

---

**Q16.** You need to extract structured data from 10,000 documents overnight. You do NOT need multi-turn tool loops. Best approach:

A) Loop the sync API 10,000 times sequentially
B) Use the Message Batches API — 50% cost, up to 24h latency
C) Fine-tune a small model
D) Use the sync API with `stream: true`

---

**Q17.** In a long prompt where you dump a 200KB document into the middle, which sentence is TRUE?

A) Long documents help Claude reason better — more context always helps
B) Middle-of-context recall is measurably weaker than start-or-end — critical facts should be at the boundaries
C) The middle of the context is treated identically to start/end positions
D) Order doesn't matter with modern models

---

**Q18.** Your extraction pipeline emits confidence scores. Which is the RIGHT way to route to human review?

A) Send every document above 0.9 to human review
B) Trust the model's self-reported confidence and use a fixed threshold
C) Calibrate confidence against a labeled validation set, then set a threshold based on measured error rate
D) Send every document to a human — LLM extraction can't be trusted

---

**Q19.** Two sources report different revenue numbers for the same company. Your synthesis agent should:

A) Pick the higher number (more optimistic)
B) Pick the more recent source silently
C) Explicitly annotate the conflict, cite both sources with dates, mark the claim CONTESTED
D) Skip the fact entirely

---

**Q20.** Which of these is EXPLICITLY out of scope for the CCA-F exam?

A) Structured error responses and TVBP categories
B) `.mcp.json` env-var expansion
C) Prompt caching implementation details
D) Path-scoped rules with YAML frontmatter

---

# Answers

<details>
<summary>Click after answering all 20</summary>

**Q1: C.** `stop_reason == "end_turn"` is the only correct loop terminator. `A` (NL parsing) and `B` (fixed cap as primary) are explicit anti-patterns in the guide. `D` is close but wrong — `end_turn` is the definitive signal; a response could contain non-tool_use content and still not be terminal (rare, but the spec is unambiguous about the stop_reason field).

**Q2: B.** The subagents completed correctly — the failure is upstream in decomposition scope. This is the canonical exam trap.

**Q3: B.** Structured manifests + replay is the crash-recovery pattern. A doesn't help if the coordinator itself crashes; C treats recovery as retry (wrong); D is unrelated (context: fork is for skills output isolation).

**Q4: C.** 18 tools degrades tool selection reliability — the guide says 4-5 tools per agent. Improving descriptions (A) helps, but the primary lever is restriction.

**Q5: B.** `${VAR}` is expanded by Claude Code at connection time using the local environment — this is the pattern that keeps secrets out of version control.

**Q6: B.** Business errors are not retryable — the correct behaviour is to explain the policy via `humanMessage`. Not escalation (C) — that's for permission errors.

**Q7: B.** Empty result is a successful query with zero matches; use `querySuccessful: true` to distinguish it from access failure. Both being errors (A) prevents intelligent handling.

**Q8: A.** Model needs discretion — `auto` lets it choose. `any` (B) would force some tool call even when a direct reply is correct. `C` is over-constrained.

**Q9: A.** User-scoped config is personal — never shared via VCS. This is the classic diagnosis question in the guide.

**Q10: C.** Path-scoped rule with glob frontmatter is the right choice when the convention applies to files across directories. Subdirectory `CLAUDE.md` (B) only covers one subtree.

**Q11: B.** `context: fork` runs the skill in an isolated subagent context so its verbose output doesn't pollute the main conversation.

**Q12: B.** Multi-file, architectural, multiple valid approaches → plan mode.

**Q13: C.** Concrete I/O examples are more effective than prose when prose is being interpreted inconsistently.

**Q14: B.** Structured output via tool_use with forced `tool_choice` is the canonical pattern. `C` is a distractor — that field is OpenAI's, not Anthropic's.

**Q15: B.** Nullable fields let Claude return `null` for unknown data instead of hallucinating a value.

**Q16: B.** Overnight, no multi-turn tool loops → Batches API is the fit (50% cheaper, 24h SLA).

**Q17: B.** "Lost in the middle" — critical facts should go at the boundaries.

**Q18: C.** LLM self-confidence is poorly calibrated. Calibrate against labeled data and set threshold from measured error rate.

**Q19: C.** Explicit conflict annotation, source citation, temporal validity, CONTESTED status — that's the provenance pattern.

**Q20: C.** Prompt caching *implementation details* are explicitly out of scope (guide page 36). Knowing prompt caching exists is fine; the token accounting mechanics are not tested.

</details>

## Scoring

- **18-20 correct** — Ready for the exam. Focus on the topics you missed.
- **14-17 correct** — Solid but review the missed domains. Do the topic READMEs in `study-guide.html`.
- **10-13 correct** — Study more. Re-read the modules for the domains you're weak in.
- **Below 10** — Go back to the runnable demos and work through them one at a time.
