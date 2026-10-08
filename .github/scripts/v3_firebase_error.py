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
    # Emit only a bounded, fixed vocabulary: never disclose arbitrary messages.
    safe_dictionary = (
        "unable failed failure error unexpected occurred authenticate authentication",
        "login project site target hosting channel deploy preview previewchannel",
        "firebase cloud run revision pintag permission forbidden denied required",
        "config configuration configs missing unknown exists found invalid",
        "not found credentials account credential expired disabled enable",
        "service backend functions function API directory root file firebasejson",
        "unsupported install setup select selectonly must include either both",
        "please update upgrade api scope scopes region create release",
        "invalid credentials quota billing upgrade resources cannot can",
    )
    allowed = set(" ".join(safe_dictionary).lower().split())
    if isinstance(obj, dict):
        error_payload = obj.get("error")
        source = error_payload if isinstance(error_payload, str) else json.dumps(error_payload)
        detected = {t.lower() for t in re.findall(r"[A-Za-z]{3,18}", source)}
        vocabulary = sorted(detected & allowed)
        result_error_length = len(source)
    else:
        vocabulary, result_error_length = [], 0
    # For diagnosis, preserve sentence structure but replace EVERY non-whitelisted
    # word, identifier and number. Arbitrary provider strings never reach logs.
    grammar = set(
        "a an and are as at be been but by can cannot could did do does each either "
        "for from has have if in into is it its must no not of on only or other "
        "please should that the their there these this to was were when which "
        "will with without would you your already any exists existing set supply "
        "specify single default deploy deployment preview channel site sites project "
        "hosting target targets firebase cloud run revision function functions "
        "configured configuration required need needs enabled active available "
        "using use invalid cannot failed fail error could please not found"
        .split()
    )
    if isinstance(obj, dict):
        raw = obj.get("error")
        raw = raw if isinstance(raw, str) else json.dumps(raw)
        scanned = re.findall(r"[A-Za-z]{1,32}|[0-9]+|[.,:;!?()\-]", raw)
        skeleton = " ".join(
            word.lower() if word.lower() in grammar else "*"
            for word in scanned[:65])
    else:
        skeleton = ""
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
        "error_payload_length": result_error_length,
        "safe_error_vocabulary": vocabulary,
        "safe_error_skeleton": skeleton,
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
