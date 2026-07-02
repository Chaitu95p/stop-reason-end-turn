# Code Review — 2026-07-02

**Scope:** `git diff f485364..HEAD` — all 5 commits from repo inception.
**Effort:** high (8-angle finders, 1-vote recall-biased verify, ≤10 findings).
**Reviewer:** Claude Opus 4.7 via `/code-review high`.

Cap at 10 findings, ranked most-severe first. Correctness bugs first, then convention violations, then altitude/cleanup.

Not shown here: 6 reuse findings dropped as intentional pedagogical independence, plus a few subsumed cleanup items. See session transcript for the full candidate list if needed.

---

## Correctness bugs (fix first)

### [ ] 1. `exercise-3-extraction-pipeline/03_batch_and_confidence.py:113` — empty `params: {}` in retry branch

`resubmit_failed()` emits `{custom_id: "DOC-...__retry", params: {}}` on `retry_later`. The Batches API rejects a request with empty params (missing model/messages/tools). Teaches a broken pattern.

**Failure scenario:** Anyone copying this pattern into real code hits an opaque API rejection on their first retried request.

**Suggested fix:** carry the original request forward (or re-build it from `original_docs[cid]`) instead of emitting an empty params dict.

```python
if action == "retry_later":
    print(f"  {cid}: {f['error_type']} -> requeue as-is")
    original = build_batch_requests([{"id": cid, "text": original_docs[cid]}])[0]
    new_requests.append({"custom_id": cid + "__retry", "params": original["params"]})
    continue
```

---

### [ ] 2. `exercise-4-multi-agent-research/02_structured_findings.py:86` — `tool_choice={"type":"auto"}` lets subagent skip the tool entirely

`collect_findings()` uses `tool_choice={"type": "auto"}` inside its loop. The system prompt asks the model to call `record_finding`, but `auto` does not force it. If the model replies with text and no tool call, `stop_reason == "end_turn"` triggers an early return with `findings = []`. Downstream `synthesize_with_provenance()` then has nothing to cite.

**Failure scenario:** On any run where the model chooses to narrate rather than tool-call (perfectly legal under `auto`), the demo silently produces an empty findings set — misleading anyone learning the pattern.

**Suggested fix:** use `tool_choice={"type": "any"}` so at least one tool call per turn is guaranteed. Then the model can only exit the loop by NOT calling any tool → the `stop_reason != "tool_use"` branch handles cleanly.

---

## Convention violations (CLAUDE.md rules)

These predate this session — they're in the original modules 1-5, not the exercises. Fixing them brings the reference material back in line with the stated contract.

### [ ] 3. `module-3/01_explain_hierarchy.py:97` — inline `\n` in f-string

**Rule (CLAUDE.md):** *"`NL = chr(10)` is used for all multi-line string concatenation throughout every script — never `\n` inline."*

Uses `f"\n{level['level']}"` instead of NL concatenation.

---

### [ ] 4. `module-3/05_iterative_refinement.py:130` — inline `\n` in f-string

Same rule. Uses `f"These tests are failing:\n{failing_tests}\n\nFix the code"`.

---

### [ ] 5. `module-4/06_multi_pass_review.py:26` — inline `\n` (multiple sites, lines 26-50)

Same rule. `FILE_A` and `FILE_B` constants use inline `\n` across ~25 lines. Highest-density violation site.

---

### [ ] 6. `module-5/06_information_provenance.py:168` — inline `\n` in f-strings (lines 168, 181, 196)

Same rule. Three separate f-strings.

---

### [ ] 7. `module-4/02_few_shot_prompting.py` — final print uses `"KEY TAKEAWAY:"` (singular)

**Rule (CLAUDE.md):** *"KEY TAKEAWAYS: printed bullet list (≥3 points)"* — plural.

Both a spec violation and a grep hazard: any tool searching the repo for `KEY TAKEAWAYS:` as a section marker will silently skip this file.

---

### [ ] 8. `module-4/03_structured_output_tool_use.py` — same singular `"KEY TAKEAWAY:"` violation

Two files in the same module share this drift — likely copied from a common template with the typo.

---

## Altitude / cleanup

### [ ] 9. `exercise-3-extraction-pipeline/02_validation_retry.py:156` — `is_resolvable()` couples to a Pydantic error-message string

```python
if e.get("loc") == ("category_detail",) and "required when category=='other'" in str(e.get("msg", "")):
```

The predicate matches the exact wording of the `field_validator` at line ~59. If that message is edited by one character, `is_resolvable()` silently flips to True and unresolvable errors get retried — burning tokens.

**Suggested fix:** raise a typed custom exception from the validator, then match on `isinstance()` or an error-code marker instead of the human message.

---

### [ ] 10. `exercise-3-extraction-pipeline/03_batch_and_confidence.py:78` — dead `request` parameter in `classify_batch_failure()`

Signature declares `request: dict` but the function body only inspects `error_type`. Caller at line 106 passes `f` (the failure dict). Dead parameter masks that classification is purely error-driven; a future contributor may assume `request` is already used when adding request-shape rules.

**Suggested fix:** drop the `request` parameter. If a future rule DOES need request shape, add it explicitly with a real dependency.

---

## Quick-fix batch order

If you fix in one sitting, do them in this order to minimise diff churn:

1. **Findings 1 + 2** in one commit — real correctness bugs in exercise scripts.
2. **Findings 3-6** in one commit — bulk `NL = chr(10)` substitution across modules 3/4/5.
3. **Findings 7 + 8** in one commit — `KEY TAKEAWAY` → `KEY TAKEAWAYS` (2-char edit each).
4. **Findings 9 + 10** in one commit — exercise-3 cleanup.

That's 4 commits, each self-contained and easy to review.
