---
description: Deep-analyze a module's exam concepts and produce a structured study summary with all mnemonics
argument-hint: "[module number, e.g. 1 or module-2]"
allowed-tools: Glob, Grep, Read
context: fork
---

# Skill: explore-module
# Usage: /explore-module 2  (or /explore-module module-2)

Perform a thorough read-only analysis of the specified module and produce a
structured study summary for CCA-F exam preparation.

## Steps

1. Resolve the module directory:
   - If argument is a number (e.g. `2`), use `module-2/`
   - If argument is a path (e.g. `module-2`), use it directly
   - If no argument given, list all modules and ask

2. Use Glob to find all demo scripts:
   `Glob('module-N/0*.py')`

3. For each script (in order), Read the full file and extract:
   - Task number and name (from header docstring first line)
   - All items under "EXAM CONCEPTS:"
   - The mnemonic (word + letter meanings)
   - The KEY TAKEAWAYS bullet points

4. Produce the structured study summary in this format:

---
## Module N — <Domain Name> (<Weight>%)

### Scripts in this module
| Script | Task | Mnemonic |
|--------|------|---------|
| 01_name.py | 1.1: Description | STOP |
| 02_name.py | 1.2: Description | DARE |
...

### Exam Concepts by Task

#### Task 1.1: <Name>  (script: 01_name.py)
- Concept 1
- Concept 2
- Concept 3
- **Mnemonic STOP**: Send → ..., Test → ..., Operate → ..., Proceed → ...

#### Task 1.2: <Name>  (script: 02_name.py)
...

### All Mnemonics (quick reference)
| Mnemonic | Script | Meaning |
|----------|--------|---------|
| STOP | 01_agentic_loop.py | Send, Test stop_reason, Operate tools, Proceed/Terminate |
...

### Key Anti-Patterns to Avoid
(extracted from "ANTI-PATTERN" labeled sections across all scripts)
...

---

5. End with: "Run `/run-module N` to execute all demos in this module."

## Notes
- This skill is READ-ONLY (allowed-tools: Glob, Grep, Read — no Write or Edit)
- Runs in a forked session (context: fork) so it doesn't pollute main context
- Does not make any API calls to Anthropic — pure file analysis
