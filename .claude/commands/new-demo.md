# /new-demo
# Usage: /new-demo $ARGUMENTS  (e.g. /new-demo module-1 1.8)
# Scaffolds a new numbered demo script following project conventions.

The argument format is: `<module-dir> <domain>.<task>`
Example: `/new-demo module-1 1.8` creates `module-1/08_<name>.py`

Steps:
1. Parse $ARGUMENTS:
   - First token: module directory (e.g. `module-1`)
   - Second token: domain.task number (e.g. `1.8`)
   If missing, ask the user which module and task number to use.

2. Ask the user:
   - What is the task name? (e.g. "Checkpoint Patterns")
   - What exam concepts should the script demonstrate? (list them)
   - What mnemonic should it use? (or leave blank to suggest one)

3. Determine the next available script number in the module directory.
   Use Glob to list existing scripts: `Glob('<module-dir>/0*.py')`

4. Create the script file at `<module-dir>/0N_<snake_case_name>.py`
   using the EXACT template below (fill in from user answers):

```python
"""
Domain N - Task N.M: <Task Name>

EXAM CONCEPTS:
  1. <Concept 1>
  2. <Concept 2>
  3. <Concept 3>

  Mnemonic: <WORD>
    <Letter> → <meaning>
    <Letter> → <meaning>
    <Letter> → <meaning>
    <Letter> → <meaning>

Run: uv run python 0N_<name>.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# TODO: Add mock tool implementations here
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# DEMO 1: <description>
# ---------------------------------------------------------------------------
def demo_one() -> None:
    pass  # TODO: implement


# ---------------------------------------------------------------------------
# DEMO 2: <description>
# ---------------------------------------------------------------------------
def demo_two() -> None:
    pass  # TODO: implement


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: <description>")
    print(sep)
    demo_one()

    print()
    print(sep)
    print("DEMO 2: <description>")
    print(sep)
    demo_two()

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. <takeaway 1>")
    print("  2. <takeaway 2>")
    print("  3. <takeaway 3>")
    print("  Mnemonic <WORD>: <Letter>→<meaning>, <Letter>→<meaning>, ...")
```

5. After creating the file, print:
   - The full path of the created file
   - A reminder to fill in the TODOs and run `uv run python <filename>` to verify
