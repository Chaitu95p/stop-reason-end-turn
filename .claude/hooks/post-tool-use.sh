#!/usr/bin/env bash
# .claude/hooks/post-tool-use.sh
#
# PostToolUse hook — called by Claude Code AFTER every tool execution.
#
# Environment variables provided by Claude Code:
#   CLAUDE_TOOL_NAME    : name of the tool that was called (e.g. "Bash", "Read", "Edit")
#   CLAUDE_TOOL_INPUT   : JSON string of the tool's input parameters
#   CLAUDE_TOOL_OUTPUT  : JSON string of the tool's output/result
#
# This hook appends a log entry to .claude/tool-usage.log for audit/debug purposes.
# Exit code 0 always — this hook never blocks tool execution.

set -uo pipefail

LOG_FILE=".claude/tool-usage.log"
TOOL="${CLAUDE_TOOL_NAME:-unknown}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

# Build a short summary of the tool input (first 120 chars, single line)
INPUT_SUMMARY=$(echo "${CLAUDE_TOOL_INPUT:-{}}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # Pick the most descriptive field depending on tool type
    for key in ['command', 'file_path', 'pattern', 'path', 'query']:
        if key in data:
            val = str(data[key])[:120].replace('\n', ' ')
            print(f'{key}={val}')
            sys.exit(0)
    # Fallback: first key
    if data:
        k, v = next(iter(data.items()))
        print(f'{k}={str(v)[:120]}')
except Exception:
    pass
" 2>/dev/null || true)

# Append log entry (create file and parent dir if absent)
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
echo "${TIMESTAMP} | ${TOOL} | ${INPUT_SUMMARY}" >> "$LOG_FILE" 2>/dev/null || true

# Always exit 0 — this hook never blocks
exit 0
