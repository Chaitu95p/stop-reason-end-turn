# .claude/commands/commit.md
# Custom slash command: /commit
# Invoked as: /commit (no arguments needed)

1. Run `git diff --staged` to see what is staged.
2. Run `git status` to see untracked files that should be included.
3. Analyze the changes and draft a commit message following this format:
   - First line: imperative mood, ≤72 chars, no period (e.g., "Add refund limit validation")
   - Blank line
   - Body: explain WHY, not what (the diff already shows what)
   - Footer: Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
4. Show me the proposed commit message and ask for approval BEFORE committing.
5. After I approve, run: git commit -m "<message>"
6. Do NOT push. Do NOT amend previous commits.

IMPORTANT: Never commit if tests are failing. Always check with: uv run pytest -q
