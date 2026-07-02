"""
Exercise 3 - Steps 12-13: Pydantic Validation-Retry Loop + Few-Shot Examples

EXAM CONCEPTS:
  1. Two failure modes -- distinguish before retrying:
       RESOLVABLE via retry: format mismatch, wrong type, missing required
         field that IS present in source under a different name.
       NOT RESOLVABLE via retry: information genuinely absent from source.

  2. Retry loop feeds the specific validation error back:
       messages = [original_user_msg,
                   assistant_bad_extraction,
                   user_with_ValidationError_text]
     The model then corrects THAT specific field, not the whole extraction.

  3. Cap retries (e.g. 2) -- unresolvable errors won't be fixed by more
     tries, so unbounded loops waste tokens.

  4. Few-shot examples solve STRUCTURAL variety, not FACTUAL variety.
     Show 2-3 differently-formatted source docs and their extractions;
     the model generalizes the mapping to novel layouts.

  Mnemonic: RETRY
    Resolvable errors get a second pass
    Error message quoted verbatim to the model
    Two attempts max before human review
    Retain original document in the retry context
    Yield null when info absent -- don't loop trying to invent it

Run: uv run python 02_validation_retry.py
"""

import json
import anthropic
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Literal

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Pydantic schema mirrors the tool_use input_schema (kept in sync manually)
# ---------------------------------------------------------------------------
class Extraction(BaseModel):
    document_id: str
    title: str
    author: str | None
    published_year: int | None
    category: Literal["research", "policy", "opinion", "news", "other"]
    category_detail: str | None
    key_findings: list[str]

    @field_validator("category_detail")
    @classmethod
    def _detail_required_when_other(cls, v, info):
        cat = info.data.get("category")
        if cat == "other" and not v:
            raise ValueError("category_detail is required when category=='other'")
        return v

    @field_validator("published_year")
    @classmethod
    def _sane_year(cls, v):
        if v is not None and not (1800 <= v <= 2100):
            raise ValueError(f"published_year {v} outside plausible range 1800-2100")
        return v


TOOL = {
    "name": "record_extraction",
    "description": "Record extracted fields.",
    "input_schema": {
        "type": "object",
        "properties": {
            "document_id":     {"type": "string"},
            "title":           {"type": "string"},
            "author":          {"type": ["string", "null"]},
            "published_year":  {"type": ["integer", "null"]},
            "category":        {"type": "string",
                                "enum": ["research", "policy", "opinion", "news", "other"]},
            "category_detail": {"type": ["string", "null"]},
            "key_findings":    {"type": "array", "items": {"type": "string"}},
        },
        "required": ["document_id", "title", "author", "published_year",
                     "category", "category_detail", "key_findings"],
    },
}


# ---------------------------------------------------------------------------
# Few-shot examples (Step 13) -- structurally different source layouts
# ---------------------------------------------------------------------------
FEW_SHOT_EXAMPLES = NL.join([
    "EXAMPLE 1 -- narrative prose:",
    'Written by Prof. K. Ito in 2019, "Urban Cycling Trends" reports a 22% ',
    "rise in bike commuting across five Japanese cities. It is a research paper.",
    "  Extracted -> author='Prof. K. Ito', year=2019, category='research',",
    "               key_findings=['22% rise in bike commuting across five Japanese cities']",
    "",
    "EXAMPLE 2 -- structured header (labeled fields):",
    "Title: Zoning Reform Impact",
    "By: City Planning Office",
    "Year: 2021",
    "Findings: 8% housing supply increase; 3% median rent decrease.",
    "  Extracted -> author='City Planning Office', year=2021, category='policy',",
    "               key_findings=['8% housing supply increase','3% median rent decrease']",
    "",
    "EXAMPLE 3 -- inline citations (author embedded in text):",
    "Recent work (Chen et al., 2024) suggests that transformer scaling laws ",
    "hold up to 400B parameters. This is a research summary.",
    "  Extracted -> author='Chen et al.', year=2024, category='research',",
    "               key_findings=['Transformer scaling laws hold up to 400B parameters']",
])

SYSTEM = (
    "You extract structured records from documents." + NL
    + "Documents vary widely in format -- header-labeled, narrative prose, or " + NL
    + "inline citation styles. Learn from these examples:" + NL + NL
    + FEW_SHOT_EXAMPLES + NL + NL
    + "Rules:" + NL
    + "  - Emit null for any REQUIRED field whose value is not present in the source." + NL
    + "  - NEVER fabricate. If the year is not stated, published_year=null." + NL
    + "  - Use category='other' + fill category_detail when no listed category fits."
)


def extract_once(document_id: str, text: str, prior_messages: list = None) -> tuple[dict, list]:
    """One extraction attempt. Return (raw_input, updated_messages)."""
    messages = list(prior_messages) if prior_messages else [
        {"role": "user", "content": f"document_id={document_id}" + NL + NL + text}
    ]
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "record_extraction"},
        messages=messages,
    )
    messages.append({"role": "assistant", "content": resp.content})
    for b in resp.content:
        if b.type == "tool_use":
            return b.input, messages
    raise RuntimeError("no tool_use block")


def is_resolvable(err: ValidationError) -> bool:
    """
    Heuristic: format/type errors are resolvable; 'value absent from source'
    reported via a specific sentinel is not.
    Here we treat all Pydantic errors as resolvable EXCEPT category_detail
    missing on category=='other' (source may genuinely lack detail).
    """
    for e in err.errors():
        if e.get("loc") == ("category_detail",) and "required when category=='other'" in str(e.get("msg", "")):
            return False
    return True


def extract_with_retry(document_id: str, text: str, max_retries: int = 2) -> dict | None:
    prior = None
    for attempt in range(max_retries + 1):
        raw, prior = extract_once(document_id, text, prior)
        try:
            valid = Extraction(**raw)
            print(f"  attempt {attempt+1}: VALID")
            return valid.model_dump()
        except ValidationError as e:
            print(f"  attempt {attempt+1}: ValidationError -- {e.error_count()} issue(s)")
            if not is_resolvable(e):
                print(f"    UNRESOLVABLE -- routing to human review, no more retries.")
                return None
            if attempt == max_retries:
                print(f"    Retry budget exhausted -- routing to human review.")
                return None
            # Feed the specific error back to the model
            feedback = (
                "Your last extraction failed validation:" + NL
                + str(e) + NL
                + "Please call record_extraction AGAIN with corrected values. "
                "Only change the fields called out above; keep the rest."
            )
            prior.append({"role": "user", "content": feedback})


# ---------------------------------------------------------------------------
# Test documents that will trip validation in specific ways
# ---------------------------------------------------------------------------
DOC_STRUCTURED = """
Title: Zoning Reform Impact
By: City Planning Office
Year: 2021
Findings: 8% housing supply increase; 3% median rent decrease.
"""

DOC_INLINE_CITATION = """
Recent work (Chen et al., 2024) shows that transformer scaling laws hold
up to 400B parameters, with quality gains flattening beyond that scale.
This report is a research summary.
"""

# This one has no year mentioned -- forces model to emit null.
DOC_NO_YEAR = """
Title: Backyard Bird Census
Author: Volunteers Anonymous

Sparrow populations declined 8% relative to prior counts. Robins held steady.
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Structured-header layout (few-shot learned)")
    print(sep)
    result = extract_with_retry("DOC-101", DOC_STRUCTURED)
    print(json.dumps(result, indent=2) if result else "-> HUMAN REVIEW")

    print()
    print(sep)
    print("DEMO 2: Inline-citation layout (harder -- author embedded in prose)")
    print(sep)
    result = extract_with_retry("DOC-102", DOC_INLINE_CITATION)
    print(json.dumps(result, indent=2) if result else "-> HUMAN REVIEW")

    print()
    print(sep)
    print("DEMO 3: Missing year -- model must emit null, no retry needed")
    print(sep)
    result = extract_with_retry("DOC-103", DOC_NO_YEAR)
    print(json.dumps(result, indent=2) if result else "-> HUMAN REVIEW")

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. Feed the SPECIFIC ValidationError back to the model on retry --")
    print("     it corrects the named field without redoing the whole extraction.")
    print("  2. Cap retries: 2 attempts is typical. Errors that persist are")
    print("     usually 'info not in source' -- retrying wastes tokens.")
    print("  3. Distinguish resolvable (type/format) vs unresolvable (info absent)")
    print("     errors BEFORE retrying, and route the latter to human review.")
    print("  4. Few-shot examples solve STRUCTURAL variety (different layouts),")
    print("     not FACTUAL variety -- one example per layout type is usually enough.")
    print("  Mnemonic RETRY: Resolvable retries, Error text quoted, Two max,")
    print("     Retain doc in context, Yield null when info absent.")
