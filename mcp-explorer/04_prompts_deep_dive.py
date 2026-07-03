"""
04 — Prompts Deep Dive
=======================
What this covers:
  - Simple string prompt (single user message)
  - Multi-turn prompts using Message objects (user + assistant roles)
  - Typed parameters with Annotated + Field descriptions
  - System-style setup prompts (multi-turn conversation starter)
  - Dynamic prompts based on data
  - Accessing prompt messages on the client side
  - When to use prompts vs just hardcoding the system message

Run: uv run python 04_prompts_deep_dive.py
"""

import asyncio
import json
from typing import Annotated
from pydantic import Field
from fastmcp import FastMCP, Client
from fastmcp.prompts.base import Message

mcp = FastMCP("prompts-demo")


# ── 1. Simple string prompt — becomes a single user message ───────────────
@mcp.prompt
def summarize(text: str, max_words: int = 100) -> str:
    """Prompt asking Claude to summarize text."""
    return f"Please summarize the following text in at most {max_words} words:\n\n{text}"


# ── 2. Multi-turn prompt — list[Message] ──────────────────────────────────
#
# Message(content, role="user")  — default role is "user"
# Message(content, role="assistant")
#
# Multi-turn prompts pre-load a conversation history so Claude picks up
# in the right context (e.g., already in "expert mode").

@mcp.prompt
def expert_chat(domain: str) -> list[Message]:
    """Prime Claude as a domain expert ready to answer questions."""
    return [
        Message(f"You are a world-class expert in {domain}. "
                f"Answer all questions with precision, citing specifics.", role="user"),
        Message(f"Understood. I'm ready to discuss {domain} at an expert level. "
                f"What would you like to know?", role="assistant"),
    ]


# ── 3. System + user setup prompt ────────────────────────────────────────
@mcp.prompt
def code_review_setup(
    language: Annotated[str, Field(description="Programming language to review")],
    focus: Annotated[str, Field(description="Focus area: 'security', 'performance', or 'style'")] = "style",
) -> list[Message]:
    """Set up a code review session with specific language and focus."""
    return [
        Message(
            f"You are a senior {language} engineer specializing in {focus}. "
            f"Review code snippets with these priorities:\n"
            f"  1. Correctness\n  2. {focus.capitalize()} considerations\n  3. Readability",
            role="user",
        ),
        Message(
            f"Ready to review {language} code with a focus on {focus}. "
            f"Please share the code snippet.",
            role="assistant",
        ),
    ]


# ── 4. Data-driven prompt ─────────────────────────────────────────────────
@mcp.prompt
def customer_support_context(customer_id: str, issue_type: str) -> list[Message]:
    """Build a support prompt pre-loaded with customer context."""
    # Simulate fetching customer data (in real use, this would read a resource)
    customers = {
        "C001": {"name": "Alice Smith",  "tier": "premium",  "open_tickets": 2},
        "C002": {"name": "Bob Jones",    "tier": "standard", "open_tickets": 0},
    }
    customer = customers.get(customer_id, {"name": "Unknown", "tier": "unknown", "open_tickets": 0})

    context = json.dumps({
        "customer_name": customer["name"],
        "tier": customer["tier"],
        "open_tickets": customer["open_tickets"],
        "current_issue": issue_type,
    }, indent=2)

    return [
        Message(
            f"You are a customer support agent. Customer context:\n{context}\n\n"
            f"Priority: Premium customers get faster resolutions. "
            f"Always verify identity before modifying account.",
            role="user",
        ),
        Message(
            f"Hello {customer['name']}! I can see you're reaching out about {issue_type}. "
            f"How can I help you today?",
            role="assistant",
        ),
    ]


# ── 5. Extraction prompt — structured output guide ────────────────────────
@mcp.prompt
def extract_entities(
    document_type: Annotated[str, Field(description="Type of document: 'invoice', 'contract', or 'email'")],
) -> str:
    """Prompt for entity extraction from a specific document type."""
    field_guide = {
        "invoice":  "Extract: vendor_name, invoice_date, total_amount, line_items",
        "contract": "Extract: parties, effective_date, term_months, jurisdiction",
        "email":    "Extract: sender, recipients, subject, key_action_items",
    }
    guide = field_guide.get(document_type, "Extract all relevant entities with their values.")
    return (
        f"Extract structured information from the {document_type} below.\n"
        f"{guide}\n\n"
        f"Return ONLY a JSON object. Use null for any field not found in the document."
    )


# ── Demo runner ────────────────────────────────────────────────────────────
async def main() -> None:
    sep = "=" * 60
    print(sep)
    print("04 — Prompts Deep Dive")
    print(sep)

    async with Client(mcp) as client:
        prompts = await client.list_prompts()
        print(f"\nRegistered prompts ({len(prompts)}):")
        for p in prompts:
            args = [f"{a.name}({'required' if a.required else 'optional'})" for a in (p.arguments or [])]
            print(f"  {p.name:<30} args: {args}")

        # ── 1. Simple string prompt ─────────────────────────────────────
        print("\n── 1. Simple string prompt ──")
        result = await client.get_prompt("summarize", {
            "text": "The quick brown fox jumps over the lazy dog. "
                    "This sentence contains every letter of the alphabet.",
            "max_words": 15,
        })
        print(f"  messages count : {len(result.messages)}")
        print(f"  role           : {result.messages[0].role}")
        print(f"  content        : {result.messages[0].content.text!r}")

        # ── 2. Multi-turn prompt ────────────────────────────────────────
        print("\n── 2. Multi-turn prompt (expert_chat) ──")
        result = await client.get_prompt("expert_chat", {"domain": "distributed systems"})
        print(f"  messages count : {len(result.messages)}")
        for msg in result.messages:
            preview = msg.content.text[:70].replace("\n", " ")
            print(f"  [{msg.role:<10}] {preview!r}")

        # ── 3. Typed parameter prompt ────────────────────────────────────
        print("\n── 3. Typed parameter prompt (code_review_setup) ──")
        result = await client.get_prompt("code_review_setup", {
            "language": "Python",
            "focus": "security",
        })
        print(f"  messages count : {len(result.messages)}")
        for msg in result.messages:
            preview = msg.content.text[:80].replace("\n", " ")
            print(f"  [{msg.role:<10}] {preview!r}")

        # ── 4. Data-driven prompt ────────────────────────────────────────
        print("\n── 4. Data-driven prompt (customer_support_context) ──")
        result = await client.get_prompt("customer_support_context", {
            "customer_id": "C001",
            "issue_type": "billing discrepancy",
        })
        print(f"  messages count : {len(result.messages)}")
        for msg in result.messages:
            preview = msg.content.text[:90].replace("\n", " ")
            print(f"  [{msg.role:<10}] {preview!r}")

        # ── 5. Extraction prompt ─────────────────────────────────────────
        print("\n── 5. Extraction prompt ──")
        result = await client.get_prompt("extract_entities", {"document_type": "invoice"})
        print(f"  prompt text:\n{result.messages[0].content.text}")

    print()
    print("KEY TAKEAWAYS:")
    print("  1. Return str → single user Message.")
    print("  2. Return list[Message] → multi-turn conversation with role control.")
    print("  3. Message(content, role='user'/'assistant') — from fastmcp.prompts.base.")
    print("  4. get_prompt() returns GetPromptResult with .messages list.")
    print("  5. Access text via: result.messages[i].content.text")
    print("  6. Prompts are reusable, parameterized conversation starters — not one-off strings.")
    print("  7. Use prompts for: expert-mode setup, document-type-specific extraction, support context.")


if __name__ == "__main__":
    asyncio.run(main())
