"""Emit validated NUL-delimited gcloud flags; no credential values in CLI flags."""
import os
import re
import sys

BUNDLE = "life-assistant-bundle"


def build_flags(env):
    values = {key: env.get("LINE_" + key, "").strip()
              for key in ("NAMESPACE", "ORIGIN", "LIFF_ID", "LOGIN_CHANNEL_ID", "BUNDLE_REF")}
    # Even a LINE-disabled release must pin the existing Life bundle to avoid
    # unrelated secrets silently changing when new containers start.
    bundle_ref = values["BUNDLE_REF"]
    if not re.fullmatch(r"life-assistant-bundle:[1-9][0-9]*", bundle_ref):
        raise ValueError("Missing or invalid LINE_BUNDLE_REF")
    if env.get("LINE_ENABLED") != "true":
        return [
            "--update-env-vars=LIFE_LINE_ENABLED=false",
            "--update-secrets=LIFE_ASSISTANT_BUNDLE=" + bundle_ref,
        ]
    patterns = {
        "NAMESPACE": r"[a-zA-Z0-9_-]{1,80}",
        "ORIGIN": r"https://[a-zA-Z0-9.-]+",
        "LIFF_ID": r"[0-9]+-[a-zA-Z0-9]+",
        "LOGIN_CHANNEL_ID": r"[0-9]+",
    }
    for key, pattern in patterns.items():
        if not re.fullmatch(pattern, values[key]):
            raise ValueError("Missing or invalid LINE_" + key)
    config = ",".join(["LIFE_LINE_ENABLED=true"] + [
        "LIFE_LINE_" + key + "=" + values[key]
        for key in ("NAMESPACE", "ORIGIN", "LIFF_ID", "LOGIN_CHANNEL_ID")
    ])
    return [
        "--update-env-vars=" + config,
        "--update-secrets=LIFE_ASSISTANT_BUNDLE=" + bundle_ref,
    ]


if __name__ == "__main__":
    try:
        for flag in build_flags(os.environ):
            sys.stdout.buffer.write(flag.encode() + b"\0")
    except ValueError as exc:
        sys.exit(str(exc))
