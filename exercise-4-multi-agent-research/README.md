# Exercise 4: Design and Debug a Multi-Agent Research Pipeline

**Source:** CCA-F Exam Guide, Preparation Exercise 4
**Domains reinforced:** Domain 1 (Agentic Architecture), Domain 2 (Tool Design & MCP), Domain 5 (Context & Reliability)

## Steps covered

| Step | Script | Concept |
|------|--------|---------|
| 16. Coordinator + 2 subagents via Task tool; explicit context passing | `01_coordinator_parallel.py` | No inherited context; pass findings in-prompt |
| 17. Parallel Task tool calls in one response; latency measurement | `01_coordinator_parallel.py` | Wall-clock speedup |
| 18. Structured findings: claim / evidence / source / date | `02_structured_findings.py` | Attribution preserved through synthesis |
| 19. Timeout error propagation to coordinator; partial results proceed | `03_errors_and_conflicts.py` | Coverage-gap annotation |
| 20. Conflicting sources preserved, well-established vs contested | `03_errors_and_conflicts.py` | Synthesis with disagreement |

## Simulation note

Real Claude Code subagents use the `Task` tool. To keep these scripts
runnable in a single-process demo without spawning real subagents, each
script SIMULATES the Task tool: a fake `spawn_subagent()` function makes
its own `client.messages.create()` call with an isolated `messages` list.
The pattern -- explicit context in each subagent's prompt, structured
return schema, coordinator synthesis over the returned dicts -- is
identical to a real Task-tool orchestration.

## Run

```bash
cd exercise-4-multi-agent-research
uv sync
export ANTHROPIC_API_KEY=sk-ant-...
uv run python 01_coordinator_parallel.py
uv run python 02_structured_findings.py
uv run python 03_errors_and_conflicts.py
```

## Mnemonic — TASK

- **T**ransfer context EXPLICITLY into each subagent prompt (no inheritance)
- **A**llowedTools includes "Task" on the coordinator only
- **S**ynthesize AFTER all subagents return; preserve provenance
- **K**eep partial results on subagent failure; annotate coverage gaps
