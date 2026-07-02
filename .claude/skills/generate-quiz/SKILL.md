---
description: Generate 10 CCA-F exam-style multiple-choice questions from a module's demo scripts
argument-hint: "[module number 1-5, e.g. 3]"
allowed-tools: Glob, Read
context: fork
---

# Skill: generate-quiz
# Usage: /generate-quiz 3  (generates 10 MCQs from module-3)

Read a module's demo scripts and generate realistic CCA-F exam-style
multiple-choice questions with answers and explanations.

## Steps

1. Resolve the module directory from the argument (number or path).
   If no argument given, ask which module.

2. Use Glob to find all demo scripts: `Glob('module-N/0*.py')`

3. Read each script's header docstring and KEY TAKEAWAYS section.
   Focus on: exam concepts, mnemonics, anti-patterns, and named distinctions.

4. Generate exactly 10 MCQ questions following this format:

---
## Module N Quiz — <Domain Name>

**Q1.** <Question text>

A) <Option A>
B) <Option B>
C) <Option C>
D) <Option D>

**Answer: B**
**Explanation:** <1-2 sentences explaining why B is correct and why the others are wrong.>
**Script reference:** `0N_name.py` — <exam concept this tests>

---

## Question design rules
- Mix question types: definition, anti-pattern identification, scenario-based
- Anti-pattern options should be plausible (not obviously wrong)
- At least 2 questions should test mnemonic knowledge
- At least 2 questions should present a scenario and ask "which is correct?"
- At least 1 question should test the "empty result vs access failure" or
  similar distinctions that appear in multiple modules
- Distribute questions across all scripts in the module (not just the first)
- Do NOT make up concepts — every question must be traceable to script content

## Notes
- Runs in a forked session (context: fork)
- Read-only (allowed-tools: Glob, Read — no API calls to Anthropic)
- After generating, offer: "Type /generate-quiz N again for a different set of questions"
