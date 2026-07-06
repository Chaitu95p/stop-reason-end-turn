"""
Domain 4 - Bonus (OUT OF SCOPE): Prefill Technique & Temperature Settings

WARNING: This script covers techniques NOT listed in the CCA-F in-scope topics.
  Prefill technique, temperature settings, and XML system prompt architecture do
  NOT appear in the 27 exam task statements or the official in-scope topics list.
  Study this ONLY after you have fully covered the 27 in-scope task statements.
  Do not spend exam prep time on this at the expense of in-scope material.

EXAM CONCEPTS:

  PREFILL TECHNIQUE:
    Start the assistant turn with partial content to force output format.
    Prefill with "{" forces Claude to produce JSON.
    Combine with stop_sequences to control where output ends.

    messages = [
      {"role": "user",      "content": "Extract entities..."},
      {"role": "assistant", "content": "{"}   <-- prefill forces JSON start
    ]

  TEMPERATURE:
    0:       Deterministic -- classification, extraction, code gen, factual Q&A
    0.3-0.7: Balanced -- general writing, some creativity
    0.8-1.0: Creative -- brainstorming, diverse idea generation

  SYSTEM PROMPT ARCHITECTURE (XML tags):
    <role>...</role>
    <instructions>...</instructions>
    <constraints>...</constraints>
    <output_format>...</output_format>
    <examples>...</examples>

Run: uv run python 07_prefill_technique.py
"""

import json
import anthropic

client = anthropic.Anthropic()

TEXT = "On Jan 5 2024, Alice Smith met with Bob Jones at Acme Corp in San Francisco."

SYSTEM_WITH_XML = """<role>
You are a named-entity extraction engine.
</role>

<instructions>
Extract all named entities from the user text.
</instructions>

<constraints>
- Only extract what is explicitly stated; do not infer.
- Dates must be in ISO 8601 format.
</constraints>

<output_format>
Return ONLY a JSON object with these keys:
  persons   : list of person names
  orgs      : list of organization names
  locations : list of location names
  dates     : list of ISO dates
No prose, no markdown fences -- raw JSON only.
</output_format>"""


def extract_without_prefill() -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        temperature=0,
        system=SYSTEM_WITH_XML,
        messages=[{"role": "user", "content": TEXT}],
    )
    return resp.content[0].text


def extract_with_prefill() -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        temperature=0,
        system=SYSTEM_WITH_XML,
        messages=[
            {"role": "user", "content": TEXT},
            {"role": "assistant", "content": "{"},  # PREFILL: force JSON output
        ],
    )
    # Claude continues from the prefill; prepend the { we gave it
    raw = "{" + resp.content[0].text
    return raw


def show_temperature_effects():
    sep = "=" * 60
    print("\n" + sep)
    print("Temperature effects on output diversity")
    print(sep)
    prompt = "Suggest a one-sentence tagline for a cloud storage product."
    for temp in [0.0, 0.5, 1.0]:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=64,
            temperature=temp,
            messages=[{"role": "user", "content": prompt}],
        )
        print("  temp={}: {}".format(temp, resp.content[0].text.strip()))


if __name__ == "__main__":
    sep = "=" * 60
    print("Demonstrating: Prefill Technique + Temperature + XML System Prompts")
    print(sep)

    print("\n--- Without prefill ---")
    out_no_prefill = extract_without_prefill()
    print("Raw output:\n" + out_no_prefill)
    try:
        json.loads(out_no_prefill)
        print("  -> Parsed as JSON: OK")
    except json.JSONDecodeError as e:
        print("  -> JSON parse FAILED: {} (prose/fences in output)".format(e))

    print("\n--- With prefill (assistant starts with {) ---")
    out_prefill = extract_with_prefill()
    print("Raw output:\n" + out_prefill)
    try:
        parsed = json.loads(out_prefill)
        print("  -> Parsed as JSON: OK")
        print("  -> persons  : " + str(parsed.get("persons")))
        print("  -> orgs     : " + str(parsed.get("orgs")))
        print("  -> locations: " + str(parsed.get("locations")))
        print("  -> dates    : " + str(parsed.get("dates")))
    except json.JSONDecodeError as e:
        print("  -> JSON parse FAILED: {}".format(e))

    show_temperature_effects()

    print("\n\nKEY TAKEAWAYS:")
    print("  Prefill + stop_sequences = lightweight JSON forcing without tool_use.")
    print("  XML tags in system prompts reduce instruction-following errors.")
    print("  Temperature 0 for extraction/classification; 1.0 for creativity.")
    print("  Reliability ladder: text < prefill < natural schema < tool_use (SANE).")
