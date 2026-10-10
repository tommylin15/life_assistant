#!/usr/bin/env python3
"""Bounded, fail-closed Firebase Preview propagation/readiness verification.

A just-created Firebase Hosting channel may return HTTP 404 while its edge
configuration propagates. This is never a PASS: retry for a bounded duration,
then require the exact release SHA and an unauthenticated API 401.
"""
from __future__ import annotations

import os
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TRANSIENT = {0, 404, 429, 502, 503, 504}


def _fetch(url: str) -> tuple[int, str]:
    try:
        req = Request(url, headers={"Cache-Control": "no-cache"})
        with urlopen(req, timeout=15) as reply:
            return int(reply.status), reply.read(256).decode("utf-8", "replace")
    except HTTPError as error:
        return int(error.code), ""
    except (URLError, TimeoutError):
        return 0, ""


def verify(
    preview_url: str,
    release_sha: str,
    *,
    attempts: int = 24,
    delay: float = 5,
    fetch=None,
    sleep=None,
) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", release_sha):
        raise ValueError("invalid release SHA")
    # Never verify or fetch arbitrary hosts from CLI output.
    host_pattern = (
        r"https://life-assistant-v3-stage-tl15--v3-"
        + re.escape(release_sha[:10])
        + r"-[a-z0-9]+[.]web[.]app/?"
    )
    if not re.fullmatch(host_pattern, preview_url):
        raise ValueError("preview URL is not the exact release channel/site")
    if not 1 <= attempts <= 36 or not 0 <= delay <= 10:
        raise ValueError("invalid bounded retry parameters")

    get = fetch or _fetch
    pause = sleep or time.sleep
    base = preview_url.rstrip("/")
    for iteration in range(1, attempts + 1):
        sha_status, sha_value = get(f"{base}/release.txt")
        if sha_status == 200:
            if sha_value.strip() != release_sha:
                raise RuntimeError("preview release SHA mismatch")
            api_status, _ = get(f"{base}/api/v1/tasks")
            if api_status == 401:
                print(f"preview=PASS release_sha={release_sha} api_unauthenticated=401", flush=True)
                return
            if api_status not in TRANSIENT:
                raise RuntimeError(f"preview API unauthorized access gate FAIL status={api_status}")
            print(f"preview_api=RETRY iteration={iteration} status={api_status}", flush=True)
        elif sha_status in TRANSIENT:
            print(f"preview_static=RETRY iteration={iteration} status={sha_status}", flush=True)
        else:
            raise RuntimeError(f"preview static failed non-transient HTTP={sha_status}")
        if iteration < attempts:
            pause(delay)

    raise RuntimeError(f"preview readiness FAIL: bounded {attempts} checks exhausted")


def main() -> None:
    try:
        verify(os.environ["PREVIEW_URL"], os.environ["RELEASE_SHA"])
    except (KeyError, ValueError, RuntimeError) as exc:
        print(f"preview_readiness=FAIL reason={exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
