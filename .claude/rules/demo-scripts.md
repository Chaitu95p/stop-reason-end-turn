---
paths:
  - "module-*/0*.py"
---

# Demo Script Conventions

These rules apply whenever you are reading, editing, or creating a Python demo
script (`0N_name.py`) inside any `module-*/` directory.

## Required header docstring

Every script MUST start with a docstring in this exact structure:

```python
"""
Domain N - Task N.M: <Task Name>

EXAM CONCEPTS:
  1. <Concept 1>
  2. <Concept 2>
  3. <Concept 3>

  Mnemonic: <WORD>
    <Letter> → <meaning>
    ...

Run: uv run python 0N_name.py
"""
```

- The first line of the docstring must be `Domain N - Task N.M: <description>`.
- `EXAM CONCEPTS:` section must list at least 3 numbered points.
- A mnemonic must be present (word + letter-by-letter expansion).
- `Run:` line must show the exact command to execute this script.

## Code conventions

- **Model**: always `model="claude-sonnet-4-6"` — never substitute another model.
- **Newlines**: use `NL = chr(10)` at module level and reference `NL` in strings.
  Never use `\n` inside f-strings or multi-line string concatenation.
- **Mock tools**: all tool functions must be pure Python (dicts/callables).
  No real HTTP calls, no real database connections, no real file system writes.
- **API key**: never set or reference `ANTHROPIC_API_KEY` in code.
  Assume it is already in the environment. Use `client = anthropic.Anthropic()`.
- **No hardcoded secrets**: no tokens, passwords, or real credentials anywhere.

## Structure requirements

- Demo sections labeled `# DEMO N: <description>` with matching print headers.
- Anti-pattern sections labeled `# ANTI-PATTERN N: <description>`.
- Every script must have `if __name__ == "__main__":` block.
- Every `__main__` block must end with `KEY TAKEAWAYS:` print section (≥3 bullets).
- Scripts must be standalone: `uv run python <filename>` from the module directory.

## Before editing a demo script

1. Read the full script first.
2. Run it to confirm current behavior.
3. Do not add external dependencies — keep all tools as mock implementations.
4. Preserve the KEY TAKEAWAYS section content and structure.
5. If adding a new DEMO section, label it and add a corresponding entry in `__main__`.
