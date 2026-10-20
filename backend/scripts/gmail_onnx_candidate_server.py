"""Isolated *private* ONNX deployment canary, not the Life user API.

No Gmail API, database, OAuth, user messages, outside AI, or user payloads.
Only public synthetic fixtures, health and model readiness are served.
"""
from __future__ import annotations

import asyncio
import os
import resource
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.services.gmail_local_classifier import (
    active_classifier_version, classify_local,
)

_MODEL_READY = False
_MODEL_VERSION = "unknown"


def _smoke() -> dict[str, object]:
    fixtures = (
        ("本期水費還沒繳清，請於指定日期前付款", "您的帳單需要確認", "billing"),
        ("郵局有您的待領包裹", "請至窗口出示證件", "pickup"),
        ("陌生裝置存取您的帳戶", "請自行核對安全紀錄", "security"),
        ("信用卡本期費用已繳清", "款項已成功入帳", None),
        ("週末購物優惠快報", "推薦您最新的商品", None),
    )
    start = time.perf_counter()
    outcomes = [classify_local(a, b, None).category for a, b, _ in fixtures]
    ok = all(actual == expected for actual, (_, _, expected) in zip(outcomes, fixtures))
    rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return {
        "pass": ok,
        "cases": len(fixtures),
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        "max_rss_mib": round(rss_mib, 1),
        # Return no subject, snippet, or sender even on failure.
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _MODEL_READY, _MODEL_VERSION
    if not os.environ.get("GMAIL_RADAR_LOCAL_MODEL_PATH"):
        raise RuntimeError("gmail_candidate_local_checkpoint_missing")
    # Require full local ONNX initialization before Cloud Run considers
    # the revision ready; no runtime download or external inference.
    _MODEL_VERSION = await asyncio.to_thread(active_classifier_version)
    if not _MODEL_VERSION.endswith("-sem"):
        raise RuntimeError("gmail_candidate_offline_model_not_ready")
    report = await asyncio.to_thread(_smoke)
    if not report["pass"] or report["max_rss_mib"] > 1536:
        raise RuntimeError("gmail_candidate_startup_smoke_failed")
    _MODEL_READY = True
    print(
        f"gmail_onnx_candidate_startup=PASS "
        f"model={_MODEL_VERSION} synthetic={report['cases']} "
        f"rss_mib={report['max_rss_mib']}",
        flush=True,
    )
    try:
        yield
    finally:
        _MODEL_READY = False


app = FastAPI(
    title="Life isolated Gmail ONNX canary",
    description="Internal synthetic and readiness checks only",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"service": "gmail-onnx-candidate", "status": "ok"}


@app.get("/ready")
async def ready():
    if not _MODEL_READY:
        raise HTTPException(503, "local model not ready")
    return {
        "service": "gmail-onnx-candidate",
        "status": "ready",
        "classifier_version": _MODEL_VERSION,
        "max_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
    }


@app.post("/synthetic-smoke")
async def synthetic_smoke():
    if not _MODEL_READY:
        raise HTTPException(503, "local model not ready")
    result = await asyncio.to_thread(_smoke)
    if not result["pass"]:
        raise HTTPException(503, "synthetic test failed")
    return {"status": "pass", **result}
