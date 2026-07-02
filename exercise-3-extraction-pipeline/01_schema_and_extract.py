"""
Exercise 3 - Step 11: Extraction Schema with Nullable + Enum-with-Other Patterns

EXAM CONCEPTS:
  1. Structured output via tool_use: force the model to call an
     "extraction tool" whose input_schema IS the desired output shape.
     Use tool_choice={"type": "tool", "name": "..."} to guarantee it.

  2. NULLABLE fields prevent fabrication:
       "author": {"type": ["string", "null"]}
     tells the model to emit null when the source is silent -- not to
     invent a plausible-sounding author.

  3. ENUM WITH "OTHER" + detail escape hatch:
       "category": enum [A, B, C, other]
       "categoryDetail": nullable string, required when category=="other"
     lets the model classify cleanly on known values without pretending
     an unknown case fits one of them.

  4. REQUIRED vs OPTIONAL fields:
       required = must always be present in output (may be null)
       optional = model may omit entirely
     Being explicit avoids "schema drift" where the same document
     yields differently-shaped outputs across runs.

  Mnemonic: SCHEMA
    Strict tool_choice pins the output shape
    Categorical enum + "other" for unknown cases
    Handling null lets model refuse to fabricate
    Every required field present (even if null)
    Match Pydantic model to input_schema 1:1
    Attribution: keep document_id in the shape

Run: uv run python 01_schema_and_extract.py
"""

import json
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# The extraction schema -- notice every pattern the exam calls out
# ---------------------------------------------------------------------------
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "document_id": {"type": "string", "description": "Verbatim id from source"},

        "title": {"type": "string"},

        # NULLABLE -- absent in some documents, must emit null (not "Unknown")
        "author": {"type": ["string", "null"],
                   "description": "Emit null if the document does not explicitly state an author."},

        # NULLABLE + typed
        "published_year": {"type": ["integer", "null"]},

        # ENUM + "other" escape hatch
        "category": {"type": "string",
                     "enum": ["research", "policy", "opinion", "news", "other"]},
        "category_detail": {"type": ["string", "null"],
                            "description": "REQUIRED when category=='other'; free text describing the actual category. Null otherwise."},

        # Required list (may be empty)
        "key_findings": {"type": "array", "items": {"type": "string"},
                         "description": "One line per finding. Empty list if none."},

        # Optional field -- may be omitted entirely
        "notes": {"type": "string"},
    },
    "required": ["document_id", "title", "author", "published_year",
                 "category", "category_detail", "key_findings"],
}

EXTRACTION_TOOL = {
    "name": "record_extraction",
    "description": "Record the fields extracted from the source document.",
    "input_schema": EXTRACTION_SCHEMA,
}


SYSTEM = (
    "You extract structured records from documents." + NL
    + "Rules:" + NL
    + "  - If a REQUIRED field's value is not present in the source, emit null." + NL
    + "  - NEVER fabricate authors, dates, or findings not in the source." + NL
    + "  - Use category='other' + fill category_detail when no listed category fits." + NL
    + "  - Emit key_findings as separate lines, verbatim or lightly paraphrased."
)


def extract(document_id: str, text: str) -> dict:
    """Force structured output via tool_choice pinning."""
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM,
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "record_extraction"},  # EXAM: guaranteed call
        messages=[{"role": "user",
                   "content": f"document_id={document_id}" + NL + NL + text}],
    )
    for b in resp.content:
        if b.type == "tool_use" and b.name == "record_extraction":
            return b.input
    raise RuntimeError("extraction tool was not called")


# ---------------------------------------------------------------------------
# Sample documents chosen to exercise EACH schema pattern
# ---------------------------------------------------------------------------
DOC_COMPLETE = """
Title: Effects of Sleep on Working Memory
Author: Dr. Jane Rivera
Published: 2023

We found that adults sleeping less than 6 hours nightly showed a 17%
decrement in n-back task accuracy. Effect held after controlling for age.
"""

DOC_MISSING_AUTHOR = """
Title: Community Broadband Adoption 2024
Published: 2024

Municipal fiber deployments grew 12% year-over-year. Rural counties saw
the largest gains. Cost per household dropped below $60.
"""

DOC_UNKNOWN_CATEGORY = """
Title: Poems from the Coastal Winter
Author: M. Okafor
Published: 2022

A collection of eighteen short poems reflecting on tidal patterns and
grief. No empirical claims.
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    for label, doc_id, text in [
        ("COMPLETE (all fields present)",           "DOC-001", DOC_COMPLETE),
        ("MISSING AUTHOR (must emit null)",         "DOC-002", DOC_MISSING_AUTHOR),
        ("UNKNOWN CATEGORY (must use 'other')",     "DOC-003", DOC_UNKNOWN_CATEGORY),
    ]:
        print(sep)
        print(f"DEMO: {label}")
        print(sep)
        result = extract(doc_id, text)
        print(json.dumps(result, indent=2))
        print()
        # Verify the anti-fabrication contract
        if doc_id == "DOC-002":
            assert result["author"] is None, "MODEL FABRICATED an author!"
            print("  OK -- author is null (no fabrication).")
        if doc_id == "DOC-003":
            assert result["category"] == "other"
            assert result["category_detail"], "category_detail required when other"
            print(f"  OK -- category=other, detail='{result['category_detail']}'.")
        print()

    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. tool_choice={'type':'tool','name':...} GUARANTEES the extraction tool")
    print("     is called -- no free-text response leaks out.")
    print("  2. Nullable fields (type: [T, 'null']) prevent fabrication when the")
    print("     source is silent -- the model emits null instead of inventing.")
    print("  3. Enum + 'other' + companion detail field lets unknown cases be")
    print("     classified honestly without forcing them into wrong buckets.")
    print("  4. Required-with-null > optional: forces the field to always appear,")
    print("     eliminates schema drift between runs on similar documents.")
    print("  Mnemonic SCHEMA: Strict tool_choice, Categorical+other, Handle null,")
    print("     Every required present, Match Pydantic 1:1, Attribution kept.")
