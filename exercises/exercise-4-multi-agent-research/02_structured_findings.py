"""
Exercise 4 - Step 18: Structured Findings with Provenance

EXAM CONCEPTS:
  1. Every finding is a STRUCTURED record separating:
       claim      -- what is asserted
       evidence   -- verbatim excerpt supporting the claim
       source     -- URL / document name / identifier
       date       -- publication date of the source
       subagent   -- which subagent produced this finding

  2. Synthesis MUST preserve provenance:
     Bad:  "APIs typically use JWT."
     Good: "APIs typically use JWT [web_search: rfc7519.txt, 2015]"

  3. Structured findings enable downstream operations:
     - Filtering by source freshness (drop findings from >2y old sources)
     - Deduplication across subagents (two subagents reporting same claim)
     - Confidence weighting by source authority
     - Audit trail for compliance / hallucination checks

  Mnemonic: CESD
    Claim (the assertion)
    Evidence (verbatim quote)
    Source (URL or doc id)
    Date (publication timestamp)

Run: uv run python 02_structured_findings.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Structured finding tool
# ---------------------------------------------------------------------------
FINDING_TOOL = {
    "name": "record_finding",
    "description": "Record ONE research finding with full provenance. "
                   "Call this tool once per distinct claim you want to submit.",
    "input_schema": {
        "type": "object",
        "properties": {
            "claim":    {"type": "string",
                         "description": "The assertion, in one sentence."},
            "evidence": {"type": "string",
                         "description": "Verbatim excerpt from the source supporting the claim."},
            "source":   {"type": "string",
                         "description": "URL, document name, or citation."},
            "date":     {"type": ["string", "null"],
                         "description": "Publication date (ISO YYYY-MM-DD) or null if unknown."},
        },
        "required": ["claim", "evidence", "source", "date"],
    },
}


SUBAGENT_SYSTEM = (
    "You are a research subagent." + NL
    + "For each distinct claim, call record_finding ONCE. Do not repeat claims." + NL
    + "Evidence MUST be a verbatim quote from the source you cite." + NL
    + "If you cannot verify a source, DO NOT report the finding."
)


def collect_findings(role_context: str, question: str) -> list[dict]:
    """
    Subagent that MUST use record_finding for its outputs.
    tool_choice='any' lets it call multiple times; end_turn signals it is done.
    """
    messages = [{"role": "user",
                 "content": f"Role: {role_context}" + NL
                            + f"Question: {question}" + NL
                            + "Emit 2-3 findings via record_finding, then end."}]
    findings = []
    while True:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SUBAGENT_SYSTEM,
            tools=[FINDING_TOOL],
            tool_choice={"type": "auto"},
            messages=messages,
        )
        if resp.stop_reason == "end_turn":
            return findings
        if resp.stop_reason != "tool_use":
            return findings
        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for b in resp.content:
            if b.type == "tool_use" and b.name == "record_finding":
                findings.append(b.input)
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": b.id,
                    "content":     "recorded",
                })
        messages.append({"role": "user", "content": tool_results})


def synthesize_with_provenance(question: str, all_findings: list[dict]) -> str:
    """
    Coordinator synthesis that MUST cite [source, date] inline.
    """
    lines = []
    for f in all_findings:
        lines.append(f"- CLAIM: {f['claim']}" + NL
                     + f"  EVIDENCE: {f['evidence']}" + NL
                     + f"  SOURCE: {f['source']} (date: {f['date']})" + NL
                     + f"  SUBAGENT: {f.get('_subagent','?')}")
    prompt = (
        f"Research question: {question}" + NL + NL
        + "Findings collected (with provenance):" + NL
        + NL.join(lines) + NL + NL
        + "Write a 3-4 sentence synthesis. EVERY factual claim must be immediately "
        + "followed by an inline citation of the form [source, date]. "
        + "If two findings agree, cite both. Do not introduce new facts."
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system="You synthesize research findings and preserve every citation.",
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(getattr(b, "text", "") for b in resp.content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60
    question = "When did the OAuth 2.0 authorization framework standard get published, and what does it cover?"

    print(sep)
    print("DEMO 1: Web-search subagent collects structured findings")
    print(sep)
    web_findings = collect_findings("web-search researcher (public sources)", question)
    for f in web_findings:
        f["_subagent"] = "web_search"
        print(f"  claim:   {f['claim'][:80]}")
        print(f"  source:  {f['source']}  date: {f['date']}")

    print()
    print(sep)
    print("DEMO 2: Doc-analysis subagent collects structured findings")
    print(sep)
    doc_findings = collect_findings("internal-document analyst", question)
    for f in doc_findings:
        f["_subagent"] = "doc_analysis"
        print(f"  claim:   {f['claim'][:80]}")
        print(f"  source:  {f['source']}  date: {f['date']}")

    print()
    print(sep)
    print("DEMO 3: Coordinator synthesis with preserved citations")
    print(sep)
    synthesis = synthesize_with_provenance(question, web_findings + doc_findings)
    print(synthesis[:1200])

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Every finding = {claim, evidence, source, date}. Enforce via")
    print("     a required-fields JSON schema on the record_finding tool.")
    print("  2. Ask synthesis to cite INLINE ([source, date]). This is testable:")
    print("     grep the synthesis for citation markers; count vs # findings.")
    print("  3. Structured provenance enables downstream ops: freshness filter,")
    print("     cross-subagent dedup, source-authority weighting, audit trail.")
    print("  4. If a subagent CANNOT cite a source, it MUST NOT report --")
    print("     enforced by SUBAGENT_SYSTEM rule + verbatim-evidence requirement.")
    print("  Mnemonic CESD: Claim, Evidence, Source, Date.")
