# /run-script
# Usage: /run-script $ARGUMENTS  (e.g. /run-script module-1/01_agentic_loop.py)
# Runs a single demo script and summarizes what it demonstrated.

The argument is a relative path to a demo script (e.g. `module-2/03_tool_distribution.py`).

Steps:
1. Verify the file exists. If $ARGUMENTS is empty or the file is not found:
   - List all available scripts with: Glob('modules/module-*/0*.py')
   - Ask the user which one to run.

2. Read the script's header docstring to understand:
   - Which exam domain and task it covers
   - The key concepts and mnemonic it demonstrates

3. Determine the module directory (e.g. `module-2` from `module-2/03_tool_distribution.py`).

4. Run the script:
   ```bash
   cd <module-dir> && uv run python <script-filename>
   ```

5. After it completes, output:
   - **Domain**: which exam domain this covers
   - **Concepts demonstrated**: bullet list of key exam concepts from the header docstring
   - **Mnemonic**: the mnemonic from the docstring (e.g. STOP, DARE, SEEB)
   - **Output summary**: brief summary of what the demo showed

6. If the script errors, show the traceback and common fixes:
   - Missing ANTHROPIC_API_KEY → `export ANTHROPIC_API_KEY=sk-...`
   - Missing deps → `cd <module-dir> && uv sync`
