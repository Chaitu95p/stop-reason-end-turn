"""
Domain 5 - Task 5.3: Error Propagation in Multi-Step Workflows

EXAM CONCEPTS:
  1. Anti-patterns:
     Suppress errors → mark failed step as success (hides failures from agent)
     Terminate whole workflow → one failure kills all unrelated sub-tasks

  2. Correct: propagate structured error context:
     - failure_type: what kind of failure (transient, validation, permission)
     - failed_step: which step in the workflow failed
     - partial_results: what DID succeed before the failure
     - alternatives: other ways to resolve (escalate, skip, retry)

  3. Local recovery: subagents handle transient failures internally
     (retry with backoff). Only propagate if the subagent cannot resolve.

  4. Access failure vs valid empty result (same as Domain 2 concept):
     Access failure  = the query COULD NOT COMPLETE (propagate as error)
     Empty result    = query completed, no records match (success, not an error)

  5. Workflow checkpoint pattern: save partial results after each step so
     a failure in step N doesn't require re-running steps 1 to N-1.

Run: uv run python 03_error_propagation.py
"""

import json
import time
import anthropic

client = anthropic.Anthropic()
NL = chr(10)


# ---------------------------------------------------------------------------
# Structured error propagation helpers
# ---------------------------------------------------------------------------
def make_workflow_error(
    failed_step: str,
    failure_type: str,
    developer_message: str,
    human_message: str,
    partial_results: dict = None,
    alternatives: list = None,
) -> dict:
    """
    Structured error that propagates up from a failed workflow step.
    Includes partial results so the coordinator can still use them.
    """
    error = {
        "success": False,
        "failed_step": failed_step,
        "failure_type": failure_type,  # transient | validation | permission | not_found
        "is_retryable": failure_type == "transient",
        "developer_message": developer_message,
        "human_message": human_message,
    }
    if partial_results:
        error["partial_results"] = partial_results
    if alternatives:
        error["alternatives"] = alternatives
    return error


def make_workflow_success(step: str, data: dict) -> dict:
    return {"success": True, "step": step, "data": data}


# ---------------------------------------------------------------------------
# Mock workflow steps
# ---------------------------------------------------------------------------
_transient_attempt = 0

def step_verify_customer(customer_id: str) -> dict:
    if customer_id == "RESTRICTED":
        return make_workflow_error(
            failed_step="verify_customer",
            failure_type="permission",
            developer_message=f"Account {customer_id} requires elevated access",
            human_message="I don't have access to this account.",
            alternatives=["escalate_to_supervisor"],
        )
    return make_workflow_success("verify_customer", {"customer_id": customer_id, "tier": "premium", "name": "Alice"})


def step_get_orders(customer_id: str) -> dict:
    return make_workflow_success("get_orders", {"orders": [{"id": "ORD-100", "total": 129.99, "status": "delivered"}]})


def step_check_policy(order_id: str, refund_amount: float) -> dict:
    if refund_amount > 500:
        return make_workflow_error(
            failed_step="check_policy",
            failure_type="validation",
            developer_message=f"Amount ${refund_amount} exceeds $500 limit",
            human_message=f"Refunds over $500 require manager approval.",
            alternatives=["escalate_to_manager", "split_refund"],
        )
    return make_workflow_success("check_policy", {"approved": True, "max_allowed": 500})


def step_process_refund(order_id: str, amount: float) -> dict:
    global _transient_attempt
    _transient_attempt += 1
    # Simulate: fails first time (transient), succeeds on retry
    if _transient_attempt == 1:
        return make_workflow_error(
            failed_step="process_refund",
            failure_type="transient",
            developer_message="Payment gateway timeout after 5000ms",
            human_message="Brief delay processing payment.",
        )
    return make_workflow_success("process_refund", {"refund_id": f"REF-{order_id}", "amount": amount})


def step_send_confirmation(customer_id: str, refund_id: str) -> dict:
    return make_workflow_success("send_confirmation", {"email_sent": True, "message_id": "MSG-001"})


# ---------------------------------------------------------------------------
# Anti-pattern 1: suppress errors (mark failed steps as success)
# ---------------------------------------------------------------------------
def antipattern_suppress_errors(customer_id: str, order_id: str, amount: float) -> dict:
    """
    WRONG: if any step fails, mark it as success and continue.
    Agent never knows failures occurred — makes decisions on bad data.
    """
    results = {}

    r_verify = step_verify_customer(customer_id)
    results["verify"] = r_verify if r_verify["success"] else {"success": True, "data": {}}  # SUPPRESS

    r_orders = step_get_orders(customer_id)
    results["orders"] = r_orders if r_orders["success"] else {"success": True, "data": {}}  # SUPPRESS

    r_policy = step_check_policy(order_id, amount)
    results["policy"] = r_policy if r_policy["success"] else {"success": True, "data": {}}  # SUPPRESS

    r_refund = step_process_refund(order_id, amount)
    results["refund"] = r_refund if r_refund["success"] else {"success": True, "data": {}}  # SUPPRESS

    return {"completed": True, "results": results}


# ---------------------------------------------------------------------------
# Anti-pattern 2: terminate whole workflow on any error
# ---------------------------------------------------------------------------
def antipattern_terminate_all(customer_id: str, order_id: str, amount: float) -> dict:
    """
    WRONG: one step failure terminates the entire workflow.
    Even successful earlier steps are discarded — can't proceed at all.
    """
    r_verify = step_verify_customer(customer_id)
    if not r_verify["success"]:
        return {"completed": False, "error": "Workflow terminated", "reason": r_verify}

    r_orders = step_get_orders(customer_id)
    if not r_orders["success"]:
        return {"completed": False, "error": "Workflow terminated", "reason": r_orders}

    r_policy = step_check_policy(order_id, amount)
    if not r_policy["success"]:
        return {"completed": False, "error": "Workflow terminated", "reason": r_policy}  # TERMINATE on policy

    r_refund = step_process_refund(order_id, amount)
    if not r_refund["success"]:
        return {"completed": False, "error": "Workflow terminated", "reason": r_refund}

    return {"completed": True}


# ---------------------------------------------------------------------------
# Correct: structured error propagation with partial results
# ---------------------------------------------------------------------------
def run_refund_workflow(customer_id: str, order_id: str, amount: float) -> dict:
    """
    CORRECT: propagate structured errors with partial results.
    - Transient errors: retry once locally before propagating
    - Non-retryable: propagate with alternatives so coordinator can decide
    - Partial results: preserved even when later steps fail
    """
    checkpoint = {}

    # Step 1: Verify customer
    r_verify = step_verify_customer(customer_id)
    if not r_verify["success"]:
        return make_workflow_error(
            failed_step="verify_customer",
            failure_type=r_verify["failure_type"],
            developer_message=r_verify["developer_message"],
            human_message=r_verify["human_message"],
            partial_results=checkpoint,
            alternatives=r_verify.get("alternatives", []),
        )
    checkpoint["customer"] = r_verify["data"]
    print(f"  [Step 1] verify_customer: OK")

    # Step 2: Get orders
    r_orders = step_get_orders(customer_id)
    if not r_orders["success"]:
        return make_workflow_error(
            failed_step="get_orders",
            failure_type=r_orders["failure_type"],
            developer_message=r_orders["developer_message"],
            human_message=r_orders["human_message"],
            partial_results=checkpoint,
        )
    checkpoint["orders"] = r_orders["data"]
    print(f"  [Step 2] get_orders: OK — {len(r_orders['data']['orders'])} orders found")

    # Step 3: Check policy
    r_policy = step_check_policy(order_id, amount)
    if not r_policy["success"]:
        # Policy violation — propagate with partial results and alternatives
        return make_workflow_error(
            failed_step="check_policy",
            failure_type=r_policy["failure_type"],
            developer_message=r_policy["developer_message"],
            human_message=r_policy["human_message"],
            partial_results=checkpoint,  # customer and orders data preserved
            alternatives=r_policy.get("alternatives", []),
        )
    checkpoint["policy_approved"] = True
    print(f"  [Step 3] check_policy: OK")

    # Step 4: Process refund — with local transient retry
    print(f"  [Step 4] process_refund: attempting...")
    r_refund = step_process_refund(order_id, amount)
    if not r_refund["success"] and r_refund["is_retryable"]:
        print(f"  [Step 4] process_refund: transient error — retrying once...")
        time.sleep(0.1)  # small backoff
        r_refund = step_process_refund(order_id, amount)
    if not r_refund["success"]:
        return make_workflow_error(
            failed_step="process_refund",
            failure_type=r_refund["failure_type"],
            developer_message=r_refund["developer_message"],
            human_message=r_refund["human_message"],
            partial_results=checkpoint,
        )
    checkpoint["refund"] = r_refund["data"]
    print(f"  [Step 4] process_refund: OK — {r_refund['data']['refund_id']}")

    # Step 5: Send confirmation
    r_confirm = step_send_confirmation(customer_id, r_refund["data"]["refund_id"])
    if not r_confirm["success"]:
        # Confirmation failure is non-critical — include as warning, don't fail
        checkpoint["confirmation_warning"] = "Email confirmation could not be sent"
        print(f"  [Step 5] send_confirmation: WARN (non-critical, continuing)")
    else:
        checkpoint["confirmation"] = r_confirm["data"]
        print(f"  [Step 5] send_confirmation: OK")

    return {"success": True, "completed_steps": list(checkpoint.keys()), "results": checkpoint}


# ---------------------------------------------------------------------------
# Agent interprets structured errors
# ---------------------------------------------------------------------------
def agent_handles_error(error_result: dict) -> str:
    """Use Claude to interpret a structured workflow error and determine next action."""
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=(
            "You are a workflow coordinator. A workflow step returned an error."
            " Decide: retry, escalate to human, or use an alternative action."
            " Give a concise 1-2 sentence recommendation."
        ),
        messages=[{
            "role": "user",
            "content": "Workflow error result:\n" + json.dumps(error_result, indent=2),
        }],
    )
    return next((b.text for b in resp.content if hasattr(b, "text")), "")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sep = "=" * 60

    print(sep)
    print("DEMO 1: Anti-pattern — suppress errors (mark failures as success)")
    print(sep)
    result = antipattern_suppress_errors("RESTRICTED", "ORD-100", 650.0)
    print(json.dumps(result, indent=2))
    print("-> Agent sees all steps as 'success' — acts on missing/empty data")

    print()
    print(sep)
    print("DEMO 2: Anti-pattern — terminate whole workflow on any error")
    print(sep)
    result = antipattern_terminate_all("C001", "ORD-100", 650.0)
    print(json.dumps(result, indent=2))
    print("-> Steps 1-2 succeeded but results are discarded — can't partially resolve")

    print()
    print(sep)
    print("DEMO 3: Correct — structured error propagation (policy violation)")
    print(sep)
    result = run_refund_workflow("C001", "ORD-100", 650.0)
    print(json.dumps(result, indent=2))
    if not result.get("success"):
        print()
        print("Agent decision based on structured error:")
        recommendation = agent_handles_error(result)
        print(f"  {recommendation}")

    print()
    print(sep)
    print("DEMO 4: Correct — transient error with local retry (then success)")
    print(sep)
    # Reset transient counter
    global _transient_attempt
    _transient_attempt = 0
    result = run_refund_workflow("C001", "ORD-100", 129.99)
    print(json.dumps(result, indent=2))

    print()
    print(sep)
    print("KEY TAKEAWAYS:")
    print("  1. NEVER suppress errors by marking failed steps as success.")
    print("     Agent makes wrong decisions when it can't see failures.")
    print("  2. NEVER terminate whole workflow on non-critical step failure.")
    print("     Preserve partial results — coordinator decides what to do next.")
    print("  3. CORRECT error structure: failed_step, failure_type, is_retryable,")
    print("     developer_message, human_message, partial_results, alternatives.")
    print("  4. Local recovery: subagent retries transient errors once before propagating.")
    print("  5. Access failure != empty result: query-succeeded-no-records is success.")
