# Exercise 1: Build a Multi-Tool Agent with Escalation Logic

**Source:** CCA-F Exam Guide, Preparation Exercise 1
**Domains reinforced:** Domain 1 (Agentic Architecture), Domain 2 (Tool Design & MCP), Domain 5 (Context & Reliability)

## Steps covered

| Step | Script | Concept |
|------|--------|---------|
| 1. Define 3-4 tools with disambiguating descriptions (incl. two similar tools) | `01_tools_and_loop.py` | Tool naming & description quality |
| 2. Agentic loop driven by `stop_reason` | `01_tools_and_loop.py` | `tool_use` vs `end_turn` |
| 3. Structured error responses (`errorCategory`, `isRetryable`, `humanMessage`) | `01_tools_and_loop.py` | TVBP recovery |
| 4. PreToolUse hook enforces business rule → escalation | `02_hooks_and_multiconcern.py` | Deterministic policy layer |
| 5. Multi-concern request decomposition + synthesis | `02_hooks_and_multiconcern.py` | Context accumulation across turns |

## Run

```bash
cd exercise-1-multi-tool-agent
uv sync
export ANTHROPIC_API_KEY=sk-ant-...
uv run python 01_tools_and_loop.py
uv run python 02_hooks_and_multiconcern.py
```

## Mnemonic — LOOP

- **L**ist stop_reason cases (tool_use → continue, end_turn → done)
- **O**perate each tool_use block, append result
- **O**verride via PreToolUse hook when policy triggers
- **P**ropagate structured error + escalate when non-recoverable
