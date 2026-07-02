# CCA-F In-Scope Topics — Learning Companion

This folder unpacks every **In-Scope Topic** listed in the CCA-F Exam Guide (page 35-36) so you can read, memorise, and self-quiz your way to the exam. It complements — not replaces — the runnable demos in `../module-1/` through `../module-5/`.

## How to use this folder

| If you want to... | Open |
|---|---|
| Read the whole thing in a friendly UI | `study-guide.html` (double-click in your browser) |
| Quick review the day before the exam | `cheatsheet.md` |
| Drill mnemonics until they stick | `mnemonics.md` |
| Test yourself with exam-style questions | `quiz.md` |
| Do terminal flashcards | `uv run python flashcards.py` |
| Run code that shows the concept live | `../module-N/` (see cross-reference below) |

## The 18 In-Scope Topics

Numbered exactly as they appear in the guide. Each one links to its section in `study-guide.html` and to the runnable demo(s) that show it in action.

| # | Topic | Runnable demo |
|---|---|---|
| 1 | Agentic loop implementation | `module-1/01_agentic_loop.py` |
| 2 | Multi-agent orchestration | `module-1/02_multi_agent_hub_spoke.py`, `exercise-4-multi-agent-research/01_coordinator_parallel.py` |
| 3 | Subagent context management | `module-1/03_subagent_context.py`, `module-5/04_state_persistence.py` |
| 4 | Tool interface design | `module-2/01_tool_design.py` |
| 5 | MCP tool and resource design | `module-2/03_mcp_resources.py`, `module-2/04_tool_descriptions.py` |
| 6 | MCP server configuration | `module-2/05_mcp_config.py`, `exercise-2-team-workflow/.mcp.json` |
| 7 | Error handling and propagation | `module-2/02_structured_error_responses.py`, `exercise-4-multi-agent-research/03_errors_and_conflicts.py` |
| 8 | Escalation decision-making | `module-1/04_escalation.py`, `exercise-1-multi-tool-agent/02_hooks_and_multiconcern.py` |
| 9 | CLAUDE.md configuration | `module-3/01_explain_hierarchy.py`, `module-3/01_claude_md_hierarchy/` |
| 10 | Custom commands and skills | `module-3/02_custom_commands_skills/`, `../.claude/commands/`, `../.claude/skills/` |
| 11 | Plan mode vs direct execution | `module-3/04_plan_vs_direct.py`, `exercise-2-team-workflow/PLAN_MODE_vs_DIRECT.md` |
| 12 | Iterative refinement | `module-3/05_iterative_refinement.py` |
| 13 | Structured output via tool_use | `module-4/03_structured_output_tool_use.py`, `exercise-3-extraction-pipeline/01_schema_and_extract.py` |
| 14 | Few-shot prompting | `module-4/02_few_shot_prompting.py` |
| 15 | Batch processing | `module-4/05_batch_processing.py`, `exercise-3-extraction-pipeline/03_batch_and_confidence.py` |
| 16 | Context window optimization | `module-5/01_context_window.py`, `module-5/02_progressive_summarization.py` |
| 17 | Human review workflows | `module-5/05_human_review.py`, `exercise-3-extraction-pipeline/02_validation_retry.py` |
| 18 | Information provenance | `module-5/06_information_provenance.py`, `exercise-4-multi-agent-research/02_structured_findings.py` |

## Exam domain weightings

Understanding which topics carry the most weight helps you prioritise revision.

| Domain | Weight | Topics in this domain |
|---|---|---|
| 1. Agentic Architecture & Orchestration | 27% | 1, 2, 3 |
| 2. Tool Design & MCP Integration | 18% | 4, 5, 6, 7, 8 |
| 3. Claude Code Configuration & Workflows | 20% | 9, 10, 11, 12 |
| 4. Prompt Engineering & Structured Output | 20% | 13, 14, 15 |
| 5. Context Management & Reliability | 15% | 16, 17, 18 |

Domain 1 has the highest weight but only 3 topics — so each of those 3 topics carries roughly **9% of the whole exam**. Prioritise them.

## Out-of-scope reminders

Do NOT waste study time on these — they are explicitly excluded (guide page 36):

- Fine-tuning, RLHF, Constitutional AI
- API authentication/billing/rate limits/pricing
- MCP server hosting, container orchestration
- Vision, computer use, streaming API internals
- Prompt caching *implementation* details (knowing it exists is fine)
- Token counting algorithms, embedding/vector DB internals
- Specific cloud provider config (AWS/GCP/Azure)
