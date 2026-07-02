# Step 10: Plan Mode vs Direct Execution — When Each Wins

The exam step says: "Test plan mode versus direct execution on tasks of
varying complexity: a single-file bug fix, a multi-file library migration,
and a new feature with multiple valid implementation approaches. Observe
when plan mode provides value."

Below is the observation matrix from running each in this repo.

## Task A — Single-file bug fix

**Example prompt:** "Fix the off-by-one in `paginate()` inside `src/api/orders/routes.py:47`."

| Mode   | Behavior | Cost |
|--------|----------|------|
| Direct | Reads the file, edits the one line, done. | ~1 tool call, ~3s |
| Plan   | Reads the file, writes a plan describing "I will change line 47 from `<=` to `<`", asks approval, then edits. | ~4 tool calls, ~15s |

**Verdict:** DIRECT wins. The fix is deterministic and localized; plan mode
adds ceremony without insight. Rule of thumb: if there's only one obviously
correct change, skip plan mode.

## Task B — Multi-file library migration

**Example prompt:** "Migrate our HTTP client from `requests` to `httpx` across the whole repo."

| Mode   | Behavior | Cost |
|--------|----------|------|
| Direct | Starts changing files one at a time; may miss call sites; may introduce inconsistency between sync/async usage. | High risk of half-done state |
| Plan   | Greps for all call sites; enumerates them; distinguishes sync vs async patterns; asks whether to use `AsyncClient` in tests; produces a checklist. | Higher upfront cost, lower rework |

**Verdict:** PLAN wins. Multi-file changes benefit from an explicit inventory
before edits begin. Without a plan you often discover on file 8 that the
approach chosen for files 1-7 doesn't fit — expensive to unwind.

## Task C — New feature with multiple valid approaches

**Example prompt:** "Add rate limiting to the API. It's currently unlimited."

| Mode   | Behavior | Cost |
|--------|----------|------|
| Direct | Picks the first plausible approach (e.g. in-memory dict) and builds it. Locks in a choice you might not want. | Rework probable |
| Plan   | Surfaces the choice: token bucket vs sliding window? Per-user vs per-IP? Redis vs in-memory? User picks BEFORE code is written. | Alignment before implementation |

**Verdict:** PLAN wins decisively. When multiple valid approaches exist,
the model's default choice may not match your architecture, security
posture, or ops setup. Plan mode is the alignment mechanism.

## Decision heuristic (EXAM-READY)

Use PLAN mode when ANY of these hold:
- More than 2-3 files will change
- Architectural choice is present (which library, which pattern)
- Change is hard to reverse (schema, public API, dependency)
- You'd want to review a PR description before merging

Use DIRECT mode when ALL of these hold:
- Single file, small scope
- Only one correct answer (typo, off-by-one, obvious refactor)
- No ripple effects downstream
