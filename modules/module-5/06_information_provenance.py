"""
Domain 5 - Task 5.6: Information Provenance & Source Attribution

EXAM CONCEPTS:
  1. Claim-source mappings: every factual claim in a synthesis should be
     traceable back to a source document with a specific citation.
     Synthesis that drops provenance becomes unverifiable.

  2. Conflicting statistics: when two sources give different numbers,
     ANNOTATE BOTH with their source — do not silently pick one.
     The human reader or downstream system decides which to trust.

  3. Temporal data: publication dates are required metadata.
     "User growth is 40%" from a 2019 report is misleading without the date.

  4. Coverage annotations: distinguish well-supported claims (3+ sources)
     from weakly-supported claims (1 source) and gap areas (no sources).

  5. Anti-pattern: fabricating citations, or citing a source for a claim
     that does not appear in that source (hallucinated attribution).

Run: uv run python 06_information_provenance.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Extraction tool with provenance
# ---------------------------------------------------------------------------
EXTRACT_WITH_PROVENANCE_TOOL = {
    "name": "extract_claims_with_provenance",
    "description": (
        "Extract factual claims from a research document. "
        "For EACH claim, cite the exact source document and the verbatim quote "
        "that supports it. If two sources conflict, return both annotated. "
        "Mark claims with coverage: 'well_supported' (3+ sources), "
        "'single_source' (1 source), 'gap' (inferred, no direct source)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string", "description": "The factual claim being made."},
                        "sources": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "document": {"type": "string"},
                                    "publication_date": {"type": "string", "description": "ISO date or year of publication."},
                                    "verbatim_quote": {"type": "string", "description": "Exact text from the source supporting this claim."},
                                },
                                "required": ["document", "publication_date", "verbatim_quote"],
                            },
                        },
                        "coverage": {
                            "type": "string",
                            "enum": ["well_supported", "single_source", "gap"],
                        },
                        "conflict_note": {
                            "type": ["string", "null"],
                            "description": "If sources conflict, note the conflict and both values here.",
                        },
                    },
                    "required": ["claim", "sources", "coverage"],
                },
            },
            "gap_areas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topics mentioned in the query that have no source coverage.",
            },
        },
        "required": ["claims", "gap_areas"],
    },
}


# ---------------------------------------------------------------------------
# Sample research documents with conflicting statistics
# ---------------------------------------------------------------------------
RESEARCH_DOCS = [
    {
        "document": "Annual Market Report 2023",
        "publication_date": "2023-06",
        "content": (
            "The cloud services market grew by 23% in 2022, reaching $580B globally. "
            "Enterprise adoption of AI tools reached 34% of Fortune 500 companies. "
            "Remote work adoption stabilized at 28% of workforce permanently working remotely."
        ),
    },
    {
        "document": "Gartner Technology Forecast 2023",
        "publication_date": "2023-03",
        "content": (
            "Cloud market growth is estimated at 19% for 2022, with total market size of $545B. "
            "AI tool adoption among enterprises is approximately 31%, based on survey of 1,200 CIOs. "
            "The hybrid work model has been adopted by 67% of organizations."
        ),
    },
    {
        "document": "McKinsey Digital Transformation Study 2019",
        "publication_date": "2019-11",
        "content": (
            "AI adoption in enterprises has reached 47% based on our global survey. "
            "Digital transformation budgets increased by 15% year-over-year. "
            "Note: This report predates COVID-19 and remote work shifts."
        ),
    },
]


def synthesize_with_provenance(query: str) -> dict:
    """Extract claims from multiple sources, preserving provenance."""
    # Combine all documents with clear source labeling
    combined = NL.join(
        f"--- SOURCE: {doc['document']} (published: {doc['publication_date']}) ---{NL}{doc['content']}"
        for doc in RESEARCH_DOCS
    )

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=(
            "You are a research synthesis agent. Extract claims with full provenance." + NL
            + "CRITICAL: When sources conflict, annotate BOTH values with their sources." + NL
            + "NEVER silently pick one conflicting statistic over another." + NL
            + "NEVER fabricate citations or attribute claims to documents that don't contain them."
        ),
        tools=[EXTRACT_WITH_PROVENANCE_TOOL],
        tool_choice={"type": "tool", "name": "extract_claims_with_provenance"},
        messages=[{
            "role": "user",
            "content": f"Query: {query}{NL}{NL}Sources:{NL}{combined}",
        }],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    return {}


# ---------------------------------------------------------------------------
# Provenance report formatter
# ---------------------------------------------------------------------------
def format_provenance_report(synthesis: dict) -> str:
    """Format the synthesis result as a human-readable provenance report."""
    lines = []
    claims = synthesis.get("claims", [])
    gaps = synthesis.get("gap_areas", [])

    for i, claim_data in enumerate(claims, 1):
        claim = claim_data.get("claim", "")
        coverage = claim_data.get("coverage", "")
        sources = claim_data.get("sources", [])
        conflict = claim_data.get("conflict_note")

        coverage_icon = {"well_supported": "[WELL]", "single_source": "[SINGLE]", "gap": "[GAP]"}.get(coverage, "")
        lines.append(f"\nClaim {i} {coverage_icon}: {claim}")

        if conflict:
            lines.append(f"  CONFLICT: {conflict}")

        for src in sources:
            doc = src.get("document", "")
            date = src.get("publication_date", "")
            quote = src.get("verbatim_quote", "")[:100]
            lines.append(f"  Source: {doc} ({date})")
            lines.append(f"  Quote:  \"{quote}\"")

    if gaps:
        lines.append(f"\nGap areas (no source coverage): {gaps}")

    return NL.join(lines)


# ---------------------------------------------------------------------------
# Anti-pattern: provenance-free synthesis
# ---------------------------------------------------------------------------
def antipattern_no_provenance(query: str) -> str:
    """WRONG: synthesize without provenance — unverifiable claims."""
    all_content = " ".join(doc["content"] for doc in RESEARCH_DOCS)
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system="Summarize the key statistics from the provided research.",
        messages=[{"role": "user", "content": f"Query: {query}\n\nResearch:\n{all_content}"}],
    )
    return next((b.text for b in resp.content if hasattr(b, "text")), "")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60
    query = "What is the current state of cloud market growth and AI enterprise adoption?"

    print(sep)
    print("DEMO 1: Anti-pattern — synthesis without provenance")
    print(sep)
    no_prov = antipattern_no_provenance(query)
    print("Summary (NO provenance):")
    print(no_prov)
    print()
    print("Problems with this output:")
    print("  - Which source is the 23% growth from? Or 19%? We don't know.")
    print("  - Is AI adoption 31%, 34%, or 47%? All three appeared in sources.")
    print("  - The 47% figure is from 2019 — outdated, but not flagged.")
    print("  - Gaps (topics with no source coverage) are not identified.")

    print()
    print(sep)
    print("DEMO 2: Correct — synthesis with full provenance")
    print(sep)
    synthesis = synthesize_with_provenance(query)
    report = format_provenance_report(synthesis)
    print("Synthesis WITH provenance:")
    print(report)

    print()
    print(sep)
    print("DEMO 3: Raw provenance data (structured)")
    print(sep)
    print(json.dumps(synthesis, indent=2))

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Every claim needs a source: document name + publication date + quote.")
    print("  2. Conflicting statistics: annotate BOTH with their source.")
    print("     Never silently pick one — let the human or downstream system decide.")
    print("  3. Temporal data: a 2019 stat on AI adoption is misleading in 2024.")
    print("     Always include publication dates alongside statistics.")
    print("  4. Coverage annotations: well_supported (3+ sources), single_source,")
    print("     gap (no source coverage). Aggregate claims hide which are unsupported.")
    print("  5. Anti-pattern: fabricated citations or attributed claims not in the source.")
    print("     Use verbatim quotes to prove the claim is actually in the source.")
