# /run-module
# Usage: /run-module $ARGUMENTS  (e.g. /run-module 2)
# Runs all numbered demo scripts in the specified module in order.

The argument is a module number between 1 and 5.

Steps:
1. Validate that $ARGUMENTS is a number between 1 and 5.
   If not, list the available modules:
     - 1: Agentic Architecture & Orchestration
     - 2: Tool Design & MCP Integration
     - 3: Claude Code Configuration & Workflows
     - 4: Prompt Engineering & Structured Output
     - 5: Context Management & Reliability

2. Use Bash to run each script in `modules/module-$ARGUMENTS/` that matches `0*.py`, in order:
   ```
   cd modules/module-$ARGUMENTS && for f in $(ls 0*.py | sort); do
     echo ""; echo "========== $f =========="; uv run python "$f"
   done
   ```

3. After all scripts complete, print a summary:
   - How many scripts ran
   - Any that produced errors (non-zero exit code)
   - The exam domain and weight this module covers

4. If any script fails, show the error output and suggest:
   - Check that ANTHROPIC_API_KEY is set in the environment
   - Verify uv dependencies: `uv sync`
