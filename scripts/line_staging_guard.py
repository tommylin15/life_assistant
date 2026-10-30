"""Fail-closed guard for LINE-enabled fixed Staging during auto releases.

The endpoint is public but returns only LIFF ID and configured origin.
The guard has no GCP credentials and never changes resources or reads secrets.
Auto releases are allowed ONLY when this endpoint explicitly reports the
application-level disabled/unconfigured response, twice.
"""
from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

STAGING_LINE_URL = "https://life-assistant-v3-stage-tl15.web.app/api/v1/line/config"
DISABLED_RESPONSE = "LINE integration is not configured"
MAX_BODY_BYTES = 512


def fetch_config() -> tuple[int, bytes]:
    request = Request(
        STAGING_LINE_URL,
        headers={"Cache-Control": "no-cache", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=12) as response:
            return response.status, response.read(MAX_BODY_BYTES)
    except HTTPError as error:
        return error.code, error.read(MAX_BODY_BYTES)
    except (URLError, TimeoutError, OSError):
        return 0, b""


def explicitly_disabled(status: int, body: bytes) -> bool:
    """503 alone is NOT permission to overwrite; require exact app response."""
    if status != 503:
        return False
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError, TypeError):
        return False
    return isinstance(data, dict) and data.get("detail") == DISABLED_RESPONSE


def should_protect(*, fetch=None, sleep=None) -> tuple[bool, str]:
    """Return (protect, safe_reason); unknown network/CDN response is protected."""
    get = fetch or fetch_config
    pause = sleep or time.sleep
    for attempt in range(2):
        try:
            status, body = get()
        except Exception:
            return True, "unknown_config_response"
        if status == 200:
            return True, "line_config_enabled"
        if not explicitly_disabled(status, body):
            return True, "unknown_config_response"
        if attempt == 0:
            pause(2)
    return False, "line_explicitly_disabled"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--github-output", help="GitHub Actions GITHUB_OUTPUT path")
    args = parser.parse_args()
    protect, reason = should_protect()
    print(f"line_staging_guard={'HOLD' if protect else 'ALLOW'} reason={reason}", flush=True)
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"protect={'true' if protect else 'false'}\n")
            handle.write(f"reason={reason}\n")
    # A HOLD is an expected automatic skip. The calling workflow controls
    # whether it skips dispatch or fails the already-enqueued V3 backstop.


if __name__ == "__main__":
    main()
