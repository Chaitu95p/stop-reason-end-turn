#!/usr/bin/env bash
# .claude/hooks/pre-tool-use.sh
#
# PreToolUse hook — called by Claude Code BEFORE every Bash tool execution.
#
# Environment variables provided by Claude Code:
#   CLAUDE_TOOL_NAME   : name of the tool being called (e.g. "Bash")
#   CLAUDE_TOOL_INPUT  : JSON string of the tool's input parameters
#
# Exit codes:
#   0  → allow the tool call to proceed
#   2  → block the tool call and show the output as an error to Claude
#
# Claude Code docs: hooks run as shell commands; stdout/stderr are shown
# to Claude as feedback when exit code is non-zero.

set -euo pipefail

# Only intercept Bash tool calls
if [ "${CLAUDE_TOOL_NAME:-}" != "Bash" ]; then
  exit 0
fi

# Extract the command string from the JSON input
# CLAUDE_TOOL_INPUT is a JSON object like: {"command": "rm -rf /tmp/foo"}
COMMAND=$(echo "${CLAUDE_TOOL_INPUT:-{}}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('command', ''))
except Exception:
    print('')
" 2>/dev/null || true)

# ── Dangerous pattern checks ───────────────────────────────────────────────

# Block: recursive force-delete
if echo "$COMMAND" | grep -qE 'rm\s+-[a-z]*r[a-z]*f|rm\s+-[a-z]*f[a-z]*r'; then
  echo "BLOCKED by pre-tool-use hook: 'rm -rf' detected."
  echo "Command: $COMMAND"
  echo "This operation is blocked to prevent accidental data loss."
  echo "If you genuinely need to delete files, do it manually."
  exit 2
fi

# Block: force push
if echo "$COMMAND" | grep -qE 'git\s+push.*--force|git\s+push.*-f\b'; then
  echo "BLOCKED by pre-tool-use hook: 'git push --force' detected."
  echo "Command: $COMMAND"
  echo "Force-pushing can destroy remote history. Do this manually after review."
  exit 2
fi

# Block: pip (use uv instead)
if echo "$COMMAND" | grep -qE '^\s*(pip|pip3)\s+install'; then
  echo "BLOCKED by pre-tool-use hook: 'pip install' detected."
  echo "This project uses 'uv' for package management."
  echo "Use: uv add <package>  (inside the correct module directory)"
  exit 2
fi

# Block: curl/wget piped to bash (supply chain risk)
if echo "$COMMAND" | grep -qE 'curl\s+.*\|\s*(bash|sh)|wget\s+.*\|\s*(bash|sh)'; then
  echo "BLOCKED by pre-tool-use hook: curl/wget piped to shell detected."
  echo "Command: $COMMAND"
  echo "Downloading and executing scripts directly is a supply-chain risk."
  exit 2
fi

# ── All checks passed ──────────────────────────────────────────────────────
exit 0
