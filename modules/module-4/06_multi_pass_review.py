"""
Domain 4 - Task 4.6: Multi-Instance & Multi-Pass Review

EXAM CONCEPT:
  Self-review limitation: the model retains its generation reasoning context,
  making it less likely to question its own decisions.

  Better approaches:
    1. Independent review instance: second Claude WITHOUT the generator context.
       Catches subtle issues more effectively than self-review.
    2. Multi-pass for large PRs:
         Pass 1: per-file local analysis (avoids attention dilution)
         Pass 2: cross-file integration analysis
       Separate passes prevent contradictory findings.
    3. Confidence self-reporting: model reports confidence per finding
       to enable calibrated review routing.

Run: uv run python 06_multi_pass_review.py
"""

import anthropic

client = anthropic.Anthropic()

FILE_A = (
    "# auth.py\n"
    "import hashlib\n\n"
    'SECRET_KEY = "hardcoded_secret_abc123"  # BUG: hardcoded secret\n\n'
    "def authenticate(user, password):\n"
    "    # Returns True if password hash matches stored hash\n"
    "    stored = get_stored_hash(user)\n"
    "    return hashlib.md5(password).hexdigest() == stored  # BUG: MD5 insecure; missing .encode()\n"
)

FILE_B = (
    "# api.py\n"
    "from auth import authenticate, SECRET_KEY\n\n"
    "def login_endpoint(request):\n"
    '    user = request.get("username")\n'
    '    pw = request.get("password")\n'
    "    if authenticate(user, pw):\n"
    "        # Issue a token signed with SECRET_KEY\n"
    "        token = sign_token(user, SECRET_KEY)\n"
    '        return {"token": token}\n'
    '    return {"error": "unauthorized"}\n'
)


def single_pass_review(files: dict) -> str:
    combined = "\n\n".join("File: {}\n{}".format(name, code) for name, code in files.items())
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="You are a security code reviewer. List all security issues found.",
        messages=[{"role": "user", "content": "Review these files:\n\n" + combined}],
    )
    return resp.content[0].text


def multi_pass_review(files: dict) -> dict:
    local_findings = {}

    # Pass 1: per-file (independent context, no attention dilution)
    for filename, code in files.items():
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=(
                "You are a security code reviewer analyzing a SINGLE file.\n"
                "Report issues with format:\n"
                "  FINDING | <severity: critical|high|medium|low> | <confidence: high|medium|low> | <description>"
            ),
            messages=[{"role": "user", "content": "Review {}:\n```python\n{}\n```".format(filename, code)}],
        )
        local_findings[filename] = resp.content[0].text

    # Pass 2: cross-file integration
    findings_summary = "\n\n".join("=== {} ===\n{}".format(f, v) for f, v in local_findings.items())
    resp_integration = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=(
            "You are a security architect reviewing cross-file interactions.\n"
            "Given per-file findings, identify:\n"
            "  1. Issues spanning multiple files (e.g., secret defined in file A, used insecurely in file B).\n"
            "  2. Contradictions between file-level findings.\n"
            "  3. Severity upgrades when local issues combine into a larger threat.\n"
            "Format: CROSS-FILE FINDING | <files affected> | <combined severity> | <description>"
        ),
        messages=[{"role": "user", "content": "Cross-file analysis:\n\n" + findings_summary}],
    )

    return {"local": local_findings, "integration": resp_integration.content[0].text}


def independent_reviewer_demo(original_output: str) -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=(
            "You are an independent security auditor.\n"
            "You are reviewing findings written by another analyst.\n"
            "Critically evaluate each finding:\n"
            "  - Flag any finding that seems overstated or incorrect.\n"
            "  - Identify HIGH/CRITICAL issues the original review may have missed.\n"
            "  - Mark confidence: AGREE | DISAGREE | UNCERTAIN for each finding."
        ),
        messages=[{"role": "user", "content": "Review these security findings:\n\n" + original_output}],
    )
    return resp.content[0].text


if __name__ == "__main__":
    files = {"auth.py": FILE_A, "api.py": FILE_B}
    sep = "=" * 60

    print(sep)
    print("APPROACH 1: Single-pass (all files, one prompt)")
    print(sep)
    single_result = single_pass_review(files)
    print(single_result)

    print("\n" + sep)
    print("APPROACH 2: Multi-pass (per-file local + cross-file integration)")
    print(sep)
    multi_result = multi_pass_review(files)
    for fname, findings in multi_result["local"].items():
        print("\n--- Local: {} ---".format(fname))
        print(findings)
    print("\n--- Cross-file Integration ---")
    print(multi_result["integration"])

    print("\n" + sep)
    print("APPROACH 3: Independent reviewer (no generation context)")
    print(sep)
    review_critique = independent_reviewer_demo(single_result)
    print(review_critique)

    print("\n\nKEY TAKEAWAY:")
    print("  Self-review: worst (retains generation context).")
    print("  Independent instance: best for catching subtle issues.")
    print("  Multi-pass: best for large PRs (avoids attention dilution).")
    print("  Report confidence per finding for calibrated routing.")
