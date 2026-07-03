---
name: summarize-diff
description: Read the current git diff and produce a one-paragraph summary for a PR description. Read-only — no writes, no network.
context: fork
allowed-tools:
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git status:*)
  - Read
argument-hint: (no args needed; runs on the current unstaged + staged diff)
---

# summarize-diff (Step 8 — project-scoped skill)

Invoke with `/summarize-diff` in this project.

## Why `context: fork` matters (EXAM KEY)

- Runs in an ISOLATED forked context — the skill's messages never
  pollute the main conversation.
- The skill returns ONLY its final summary string; intermediate `git diff`
  output and reasoning stay in the fork.
- Fork isolation is the ONLY way to run a tool-heavy analysis without
  bloating the parent context window.

## Why `allowed-tools` matters (EXAM KEY)

- Restricts the skill to READ-ONLY git introspection + Read.
- Even though the skill is invoked from the main session that has
  full tool access, the allowlist here is what runs. Prevents an
  accidental `git commit` or file write from a summarization skill.

## Instructions

You are inside a forked context. Do this:

1. Run `git diff --stat` to get the file-level summary.
2. Run `git diff` (unstaged) and `git diff --cached` (staged).
3. Return ONE paragraph (max 80 words) covering:
   - What changed (surfaces, not implementations)
   - Why the reader should care (behavior change vs cleanup)
   - Any migrations / breaking changes

Do NOT include line counts, file lists, or "I ran git diff" narration.

## Verify this skill runs isolated

1. In the main session, `/summarize-diff`.
2. After it returns, ask "what was in the diff you just read?" in the
   main session. Claude should NOT recall the specific diff content —
   the fork's context is gone. Only the returned summary survives.
