"""
Module 3 - Task 4.5: Batch Processing Strategies

EXAM CONCEPTS:
  Message Batches API facts (memorize all):
    - 50% cost savings vs synchronous
    - Up to 24-hour processing window
    - NO guaranteed latency SLA
    - NO multi-turn tool calling
    - Use custom_id to correlate request/response pairs

  Mnemonic BATCH = Big Async Tasks, Cheap and Hourly

  SLA calculation (exam tests this):
    submission_window = SLA_hours - max_batch_duration_hours
    Example: SLA=30h, batch=24h -> submit at most every 6h.

  Failure handling (exam tests this):
    - Identify failed requests by custom_id
    - Resubmit ONLY failed ones (not the whole batch)
    - For context-limit failures: chunk the document and resubmit

  Prompt refinement before large batch:
    - Test on 5-10 document sample FIRST
    - Fix prompt issues before spending on the full batch
    - Reduces iterative resubmission costs

Run: uv run python 05_batch_processing.py
"""

import time
import anthropic

client = anthropic.Anthropic()

NL = chr(10)

DOCUMENTS = [
    {"id": "doc-001", "text": "Quarterly revenue increased 15% YoY. Net margin improved to 22%."},
    {"id": "doc-002", "text": "Critical security vulnerability discovered in authentication module."},
    {"id": "doc-003", "text": "New employee onboarding checklist updated for remote workers."},
    {"id": "doc-004", "text": "Server outage at 2am caused 3 hours of downtime. Root cause: disk full."},
    {"id": "doc-005", "text": "Team offsite scheduled for Q3. Budget approved for 2-day retreat."},
]

CLASSIFY_SYSTEM = (
    "Classify the document into exactly one category:" + NL
    + "financial | security | hr | incident | other" + NL + NL
    + "Respond with ONLY the category word. No explanation."
)


def calculate_sla_window(sla_hours: float, max_batch_duration_hours: float = 24) -> float:
    """
    Calculate max time between batch submissions to guarantee an SLA.

    Exam concept: if batch takes UP TO 24 hours, submit with enough lead time.

    Example:
      SLA = 30 hours, max batch = 24 hours
      -> Must submit every 30-24 = 6 hours at most
      -> Submit at T=0, get results by T=24 (within 30h SLA)
      -> Next submission at T=6, results by T=30 (within SLA)
    """
    window = sla_hours - max_batch_duration_hours
    if window <= 0:
        raise ValueError(
            f"SLA of {sla_hours}h cannot be guaranteed: batch can take up to {max_batch_duration_hours}h"
        )
    return window


def run_batch_processing():
    """Step 1: Prompt refinement on sample, then full batch submission."""
    print("Step 1: Prompt refinement on sample set BEFORE large batch")
    print("  -> In practice: test on 5-10 docs, fix issues, then submit full batch.")
    print("  -> This reduces iterative resubmission costs significantly.")
    print()

    requests = [
        {
            "custom_id": doc["id"],  # correlates response to request
            "params": {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 16,
                "system": CLASSIFY_SYSTEM,
                "messages": [{"role": "user", "content": doc["text"]}],
            },
        }
        for doc in DOCUMENTS
    ]

    print("Submitting batch with {} requests...".format(len(requests)))
    batch = client.messages.batches.create(requests=requests)
    print("Batch ID: " + batch.id)

    print("Polling for completion (real batches can take up to 24h)...")
    max_polls = 30
    for poll_num in range(max_polls):
        time.sleep(3)
        batch = client.messages.batches.retrieve(batch.id)
        print("  Poll {}: status={} counts={}".format(
            poll_num + 1, batch.processing_status, batch.request_counts
        ))
        if batch.processing_status == "ended":
            break
    else:
        print("  Batch still processing. In production, store batch.id and check later.")
        return None, None

    successes = {}
    failures = {}
    doc_lookup = {d["id"]: d["text"] for d in DOCUMENTS}

    print()
    print("Results:")
    for result in client.messages.batches.results(batch.id):
        cid = result.custom_id
        if result.result.type == "succeeded":
            classification = result.result.message.content[0].text.strip()
            successes[cid] = classification
            print("  {} | {:10} | {}...".format(cid, classification, doc_lookup.get(cid, "")[:40]))
        elif result.result.type == "errored":
            failures[cid] = result.result.error.type
            print("  {} | ERROR: {}".format(cid, result.result.error.type))
        elif result.result.type == "canceled":
            failures[cid] = "canceled"
            print("  {} | CANCELED".format(cid))

    return successes, failures


def resubmit_failures(failures: dict):
    """
    Handle failures: resubmit only failed docs identified by custom_id.
    For context-limit failures, chunk the document before resubmitting.
    """
    if not failures:
        print("  No failures to resubmit.")
        return

    print()
    print("=" * 60)
    print("Failure handling: resubmitting {} failed documents".format(len(failures)))
    print("=" * 60)
    doc_lookup = {d["id"]: d["text"] for d in DOCUMENTS}

    retry_requests = []
    for cid, error_type in failures.items():
        text = doc_lookup.get(cid, "")
        if error_type in ("overloaded_error", "request_too_large"):
            # Chunk long documents for context-limit failures
            chunk_size = len(text) // 2
            for i, chunk in enumerate([text[:chunk_size], text[chunk_size:]]):
                retry_requests.append({
                    "custom_id": f"{cid}_chunk{i}",
                    "params": {
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 16,
                        "system": CLASSIFY_SYSTEM,
                        "messages": [{"role": "user", "content": chunk}],
                    },
                })
            print("  {} -> chunked into 2 parts (was: {})".format(cid, error_type))
        else:
            retry_requests.append({
                "custom_id": cid + "_retry",
                "params": {
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 16,
                    "system": CLASSIFY_SYSTEM,
                    "messages": [{"role": "user", "content": text}],
                },
            })
            print("  {} -> simple retry (was: {})".format(cid, error_type))

    print("  Would submit {} retry requests".format(len(retry_requests)))


def explain_batch_decisions():
    sep = "=" * 60
    print()
    print(sep)
    print("BATCH vs SYNCHRONOUS decision framework")
    print(sep)
    scenarios = [
        ("Pre-merge code review (developer waiting)",   "SYNCHRONOUS", "blocking, needs real-time"),
        ("Nightly security scan of all repos",           "BATCH",       "latency-tolerant, cost savings"),
        ("User asks chatbot a question",                 "SYNCHRONOUS", "real-time interaction"),
        ("Weekly summarization of 10K support tickets",  "BATCH",       "non-blocking, large volume"),
        ("CI/CD pipeline check blocking deployment",     "SYNCHRONOUS", "blocking, no latency slack"),
        ("Monthly compliance report generation",         "BATCH",       "overnight job, 50% savings"),
    ]
    for scenario, decision, reason in scenarios:
        print("  {:12} | {}".format(decision, scenario))
        print("               Reason: " + reason)
        print()

    print(sep)
    print("SLA Calculation: submission_window = SLA - max_batch_duration")
    print(sep)
    for sla in [25, 30, 48]:
        try:
            window = calculate_sla_window(sla)
            print("  SLA={}h -> submit every {}h max (batch takes up to 24h)".format(sla, window))
        except ValueError as e:
            print("  SLA={}h -> IMPOSSIBLE: {}".format(sla, e))


if __name__ == "__main__":
    print("Demonstrating: Message Batches API")
    print("Key facts: 50% cost savings, 24h window, no latency SLA, no multi-turn tools")
    print("Mnemonic BATCH = Big Async Tasks, Cheap and Hourly")
    print("=" * 60)

    successes, failures = run_batch_processing()

    if failures is not None:
        resubmit_failures(failures)

    explain_batch_decisions()

    print()
    print("KEY TAKEAWAY:")
    print("  Batch = cheap, async, latency-tolerant workloads ONLY.")
    print("  Never batch blocking workflows like pre-merge checks.")
    print("  SLA window = SLA_hours - 24 (max batch duration).")
    print("  On failure: resubmit only failed docs (by custom_id); chunk context-limit fails.")
    print("  Always do sample-set prompt refinement before submitting full batch.")
