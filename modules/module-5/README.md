# Module 5 — Context Management & Reliability

**Exam domain weight: 15%**

Covers how to preserve critical facts across context compression, route to human review, propagate errors in multi-step workflows, manage codebase context, score confidence for escalation, and track information provenance.

## Scripts

| Script | Task | Key concept |
|--------|------|-------------|
| `01_context_preservation.py` | 5.1 Context Preservation | Case facts block; verbose trimming; lost-in-middle; upstream-compact |
| `02_escalation_patterns.py` | 5.2 Escalation Patterns | Decision criteria for human handoff; confidence thresholds |
| `03_error_propagation.py` | 5.3 Error Propagation | Partial results; unresolvable vs local-retry errors |
| `04_codebase_context.py` | 5.4 Codebase Context | Explore subagent; file scoping; avoiding context bloat |
| `05_human_review_confidence.py` | 5.5 Human Review Routing | Per-finding confidence scores; routing thresholds |
| `06_information_provenance.py` | 5.6 Information Provenance | Source attribution; citation tracking; audit trail |

## Run

```bash
# All scripts in order
cd modules/module-5 && for f in 0*.py; do echo "=== $f ===" && uv run python "$f"; done

# Single script
uv run python 01_context_preservation.py
```

## Key exam facts

- **Progressive summarization risk:** each compression round loses precise numbers. Fix: extract a structured case facts block and inject it at the top of every prompt.
- **Lost-in-the-middle:** Claude's attention degrades for content buried in long contexts — place critical facts at the START or END.
- **Verbose tool output:** trim 40+ field API responses to 5-8 relevant fields before storing (~85% context reduction).
- **Upstream agent modification:** when a downstream synthesis agent has a limited context budget, change what the UPSTREAM subagents return (compact key facts + citations + relevance scores) — not just how the downstream agent filters.
- **Explore subagent:** use `context: fork` for verbose discovery tasks to protect the main session context window.
- **`/compact` ordering:** always write key findings to a scratchpad BEFORE running `/compact`, or they will be lost.
- **Mnemonic FACT-U:** Facts-block, Aggregate-trim, Cite-positions, Track, Upstream-compact.
