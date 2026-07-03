"""
Exercise 4 - Steps 19-20: Error Propagation + Conflicting Source Synthesis

EXAM CONCEPTS:
  1. Subagent errors MUST be structured for the coordinator:
       {
         "isError": True,
         "failureType": "timeout" | "rate_limit" | "no_results" | "auth",
         "attemptedQuery": "...",
         "partialResult": {...} or None,
       }
     Uniform failure strings block the coordinator from proceeding intelligently.

  2. Coordinator MUST be able to proceed with partial results:
     - Never block the whole report on one failed subagent.
     - Annotate the final report with COVERAGE GAPS ("web-search unavailable
       for the 2023 subquery; findings below reflect doc-analysis only").

  3. Conflicting-source handling:
     - Do NOT silently pick one value when two credible sources disagree.
     - Preserve BOTH values with attribution.
     - Structure the report to distinguish:
         WELL-ESTABLISHED: all sources agree, no contradiction
         CONTESTED:        sources disagree; report both
         UNVERIFIED:       only one weak source

  Mnemonic: CONFLICT
    Cite BOTH values with sources when they disagree
    Only synthesize a single value when sources agree
    No arbitrary tie-breaking without transparent criteria
    Flag CONTESTED explicitly in the report
    Log the disagreement for later human review
    Include source dates -- newer disagreeing sources may supersede
    Coverage gaps annotated when subagents fail
    Trust boundary: single unverified source != established fact

Run: uv run python 03_errors_and_conflicts.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Simulated subagent that may FAIL with structured error
# ---------------------------------------------------------------------------
def subagent_call(name: str, query: str, force_fail: str | None = None) -> dict:
    if force_fail == "timeout":
        return {
            "isError": True,
            "failureType": "timeout",
            "attemptedQuery": query,
            "partialResult": {
                "findings_completed": 1,
                "findings": [{"claim": "Partial hit: X was reported in mid-2023",
                              "source": "cached-index-snippet", "date": "2023-06-01"}],
            },
            "humanMessage": f"{name} exceeded its 10s budget; returning partial results.",
        }
    if force_fail == "no_results":
        return {"isError": False, "querySuccessful": True, "findings": [],
                "message": f"{name}: no matches for '{query}'"}
    # Normal-path: hand-crafted for the conflict demo
    findings_by_agent = {
        "web_search": [
            {"claim": "Global widget shipments in 2023 were 4.2 billion units",
             "evidence": "Widget Analytics Q4 report: 4.2B units shipped",
             "source": "widgetanalytics.com/q4-2023", "date": "2024-02-15"},
            {"claim": "Top exporting country was Country A with 38% share",
             "evidence": "By country: A=38%, B=22%, C=17%, other=23%",
             "source": "widgetanalytics.com/q4-2023", "date": "2024-02-15"},
        ],
        "doc_analysis": [
            # NOTE: this DISAGREES with web_search on total shipments
            {"claim": "Global widget shipments in 2023 were 3.9 billion units",
             "evidence": "Industry consortium reports 3.9B units shipped in 2023",
             "source": "internal://consortium-report-2024.pdf", "date": "2024-03-20"},
            {"claim": "Top exporting country was Country A with 38% share",
             "evidence": "consortium share table: A=38%",
             "source": "internal://consortium-report-2024.pdf", "date": "2024-03-20"},
        ],
    }
    return {"isError": False, "findings": findings_by_agent.get(name, []),
            "attemptedQuery": query}


# ---------------------------------------------------------------------------
# Reliability classification (Step 20)
#       ^^ LEARNING-MODE contribution point below
# ---------------------------------------------------------------------------
def classify_finding_reliability(claim_key: str, findings: list[dict]) -> dict:
    """
    Given all findings that address the same claim_key (a normalized topic),
    classify as WELL_ESTABLISHED / CONTESTED / UNVERIFIED.

    ---------------------------------------------------------------------------
    LEARNING-MODE TODO -- your reliability policy goes here.

    Exam step 20 says: "verify the synthesis output preserves both values
    with source attribution rather than arbitrarily selecting one, and
    structures the report to distinguish well-established from contested findings."

    Fill in 5-10 lines that:
      1. If findings has length >= 2 AND all findings' `claim` strings match
         (case/whitespace-insensitive) -> WELL_ESTABLISHED
      2. If findings has length >= 2 AND claims DIFFER on the same key ->
         CONTESTED (return all differing values + sources)
      3. If findings has length 1 -> UNVERIFIED
      4. If findings is empty -> return {"status": "MISSING"}

    Design choices worth thinking about:
      - Numeric near-equality: if two sources say "4.2B" and "4.15B", is that
        agreement or disagreement? (define a tolerance)
      - Source authority weighting: does one recognized industry body outweigh
        two anonymous blogs? (add a source_weights map)
      - Recency preference: does a 2024 source supersede a 2020 source?
    ---------------------------------------------------------------------------
    """
    if not findings:
        return {"status": "MISSING", "claim_key": claim_key}
    unique_claims = list({f["claim"].strip().lower(): f for f in findings}.values())
    if len(findings) == 1:
        return {"status": "UNVERIFIED", "claim_key": claim_key,
                "value": findings[0]["claim"], "source": findings[0]["source"]}
    if len(unique_claims) == 1:
        return {"status": "WELL_ESTABLISHED", "claim_key": claim_key,
                "value": findings[0]["claim"],
                "sources": [f["source"] for f in findings]}
    return {"status": "CONTESTED", "claim_key": claim_key,
            "values": [{"value": f["claim"], "source": f["source"], "date": f["date"]}
                       for f in unique_claims]}


def group_findings_by_topic(findings_flat: list[dict]) -> dict[str, list[dict]]:
    """
    Naive grouping by the first 4 significant words of the claim.
    A real pipeline would use embeddings or explicit topic tags.
    """
    groups: dict[str, list[dict]] = {}
    for f in findings_flat:
        key_words = [w for w in f["claim"].lower().split() if len(w) > 3][:4]
        key = " ".join(key_words)
        groups.setdefault(key, []).append(f)
    return groups


def synthesize_with_reliability(question: str, classifications: list[dict]) -> str:
    lines = []
    for c in classifications:
        lines.append(json.dumps(c))
    prompt = (
        f"Research question: {question}" + NL + NL
        + "Findings classified by reliability:" + NL
        + NL.join(lines) + NL + NL
        + "Write a report with THREE sections:" + NL
        + "  ## Well-established" + NL
        + "  ## Contested (show ALL values with sources)" + NL
        + "  ## Unverified / coverage gaps" + NL
        + "Every claim must retain its source. Do NOT pick a single value for CONTESTED."
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system="You are a research synthesizer. Faithfully report every reliability class.",
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(getattr(b, "text", "") for b in resp.content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60
    question = "What was global widget shipment volume in 2023 and which country led exports?"

    # ---- DEMO 1: subagent timeout with partial results ----
    print(sep)
    print("DEMO 1: Structured error from a timing-out subagent")
    print(sep)
    err_result = subagent_call("web_search", "widget shipments 2023", force_fail="timeout")
    print(json.dumps(err_result, indent=2))
    print("  -> Coordinator can proceed using partialResult + annotate a coverage gap.")

    # ---- DEMO 2: coordinator merges partial + full ----
    print()
    print(sep)
    print("DEMO 2: Coordinator merges partial (from timeout) + doc_analysis (full)")
    print(sep)
    web = subagent_call("web_search", "widget shipments 2023", force_fail="timeout")
    doc = subagent_call("doc_analysis", "widget shipments 2023")
    web_findings = web.get("partialResult", {}).get("findings", []) if web["isError"] else web["findings"]
    doc_findings = doc.get("findings", [])
    combined = web_findings + doc_findings
    coverage_gap = None
    if web["isError"]:
        coverage_gap = f"web_search timed out; partial coverage only."
        print(f"  COVERAGE GAP: {coverage_gap}")
    print(f"  Combined findings: {len(combined)}")

    # ---- DEMO 3: conflict detection between full runs ----
    print()
    print(sep)
    print("DEMO 3: Conflict detection (web_search vs doc_analysis disagree on total)")
    print(sep)
    web = subagent_call("web_search", "widget shipments 2023")
    doc = subagent_call("doc_analysis", "widget shipments 2023")
    all_findings = web["findings"] + doc["findings"]
    groups = group_findings_by_topic(all_findings)
    classifications = [classify_finding_reliability(k, v) for k, v in groups.items()]
    for c in classifications:
        print(f"  [{c['status']}] {c.get('claim_key','')}")

    # ---- DEMO 4: full synthesis with reliability sections ----
    print()
    print(sep)
    print("DEMO 4: Final synthesis with Well-established / Contested / Unverified")
    print(sep)
    synthesis = synthesize_with_reliability(question, classifications)
    print(synthesis[:1500])

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Subagent errors are STRUCTURED: failureType + attemptedQuery +")
    print("     partialResult. Coordinator can proceed intelligently.")
    print("  2. Partial results are USED, not discarded -- and coverage gaps are")
    print("     annotated in the final report so the reader knows what's missing.")
    print("  3. Conflicting sources are PRESERVED with attribution -- classifier")
    print("     labels WELL_ESTABLISHED / CONTESTED / UNVERIFIED before synthesis.")
    print("  4. Synthesis MUST NOT arbitrarily pick one value for contested claims --")
    print("     it reports both with sources so the reader decides.")
    print("  Mnemonic CONFLICT: Cite both, Only single value when agreed,")
    print("     No tie-breaking without criteria, Flag contested, Log for review,")
    print("     Include dates, Coverage gaps annotated, Trust boundary respected.")
