#!/usr/bin/env python3
"""Bounded, secret-safe Firebase CLI failure categories for public Actions logs."""
import hashlib
import json
import re
import sys
from pathlib import Path

RULES = {
    "PERMISSION_OR_IAM": r"permission|permission_denied|not authorized|forbidden|403",
    "AUTHENTICATION": r"unauthorized|credential|login required|invalid token|authentication",
    "PIN_TAG_OR_REVISION": r"pintag|pin.tag|revision|cloud run|run\.services",
    "PROJECT_OR_SITE": r"hosting site|site.*not found|firebase project|project id|no project",
    "INVALID_CONFIGURATION": r"invalid|unsupported|malformed|configuration",
    "BILLING": r"billing|payment",
    "QUOTA": r"quota|rate.limit|too many requests|429",
    "NOT_FOUND": r"not found|404",
    "HOSTING_API": r"firebasehosting|hosting api|hosting",
    "NETWORK": r"timeout|connection reset|dns",
}


def summarize(stdout: str, stderr: str, returncode: int) -> dict:
    # Do not publish any arbitrary provider messages, URLs, tokens or credentials.
    combined = stdout + "\n" + stderr
    categories = sorted(
        k for k, pattern in RULES.items()
        if re.search(pattern, combined, flags=re.IGNORECASE))
    matches = re.findall(r"(?<!\d)(?:400|401|403|404|409|429|500|502|503)(?!\d)",
                         combined)
    obj = None
    try:
        obj = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        pass
    # Exact API status/code fields are included only if independently scalar/safe.
    api_status = None
    if isinstance(obj, dict) and isinstance(obj.get("status"), str):
        if obj["status"] in ("success", "error"):
            api_status = obj["status"]
    return {
        "result": "FAIL",
        "exit_code": returncode,
        "categories": categories or ["UNKNOWN_REDACTED"],
        "http_codes": sorted(set(matches)),
        "json_status": api_status,
        "log_fingerprint": hashlib.sha256(combined.encode()).hexdigest()[:16],
        "message_redacted": True,
    }


def main():
    out, err = Path(sys.argv[1]), Path(sys.argv[2])
    code = int(sys.argv[3])
    print(json.dumps(summarize(
        out.read_text(errors="replace") if out.exists() else "",
        err.read_text(errors="replace") if err.exists() else "",
        code), sort_keys=True))


if __name__ == "__main__":
    main()
