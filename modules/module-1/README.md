# Module 1 — Agentic Architecture & Orchestration

**Exam domain weight: 27%** (highest weight domain)

Covers how Claude-based agents loop, coordinate, spawn subagents, enforce workflows, intercept tool calls, decompose tasks, and manage session state.

## Scripts

| Script | Task | Key concept |
|--------|------|-------------|
| `01_agentic_loop.py` | 1.1 Agentic Loops | Loop on `stop_reason == "tool_use"`, terminate on `"end_turn"` |
| `02_multi_agent_coordinator.py` | 1.2 Multi-Agent Systems | Coordinator-subagent pattern; result aggregation |
| `03_subagent_context_passing.py` | 1.3 Subagent Context Passing | Scoped context; avoid passing full history to subagents |
| `04_workflow_enforcement.py` | 1.4 Workflow Enforcement | Gate patterns; required step ordering; handoff schemas |
| `05_sdk_hooks.py` | 1.5 SDK Hooks | `PreToolUse` / `PostToolUse`; interception and normalization |
| `06_task_decomposition.py` | 1.6 Task Decomposition | Parallel vs sequential splits; dependency mapping |
| `07_session_management.py` | 1.7 Session Management | State resumption; session forking; checkpoint patterns |

## Run

```bash
# All scripts in order
cd modules/module-1 && for f in 0*.py; do echo "=== $f ===" && uv run python "$f"; done

# Single script
uv run python 01_agentic_loop.py
```

## Key exam facts

- **Agentic loop stop condition:** `stop_reason == "tool_use"` → execute tools and loop; `stop_reason == "end_turn"` → done. Never parse natural language text or use a fixed iteration cap as the primary stop.
- **Tool results must be appended** to conversation history before the next API call, as a `{"role": "user", "content": [{"type": "tool_result", ...}]}` message.
- **SDK hook names:** `PreToolUse` and `PostToolUse` (not `PreToolCall`).
- **Mnemonic STOP:** Send request → Test `stop_reason` → Operate tools → Proceed or Terminate.
