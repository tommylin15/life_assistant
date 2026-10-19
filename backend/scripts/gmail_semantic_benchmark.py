"""Bounded offline-only Gmail V2 synthetic acceptance benchmark.

No OAuth, Gmail, external AI, real messages or stored private data.
Run with GMAIL_RADAR_LOCAL_MODEL_PATH pointing to an immutable local ONNX folder.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import socket
import statistics
import time
from contextlib import contextmanager

from app.api.gmail_radar import classify_message
from app.services.gmail_local_classifier import active_classifier_version, classify_local

# Independent synthetic positive / negative test cases, not reference examples.
CASES = [
    ("10月手機費尚未付款，請盡速完成", "請查明本月的應付費用", "billing"),
    ("本期保費請儘速繳納", "保障續保請確認款項", "billing"),
    ("您的應付帳款尚未結清", "請查看正式帳單", "billing"),
    ("Your monthly invoice requires payment", "Please settle the outstanding invoice", "billing"),
    ("快遞已送達管理室", "請在三天內領取包裹", "pickup"),
    ("宅配寄放超商自取櫃", "記得前往領件", "pickup"),
    ("Your parcel is waiting at the collection point", "", "pickup"),
    ("明天預定的診所看診時段已保留", "請準時到場", "booking"),
    ("Your appointment details for Thursday", "Review your reservation", "booking"),
    ("行程更新，列車班次時間調整", "請查看最新交通資訊", "travel"),
    ("Your departure time has moved", "Please review your itinerary", "travel"),
    ("審查資料尚缺一件證明", "請於指定期限補齊", "administrative"),
    ("學校校外教學同意表需家長簽回", "班導師提醒", "administrative"),
    ("Your application needs additional documents", "Submit before the deadline", "deadline"),
    ("Unfamiliar device accessed your account", "Please review your recent activity", "security"),
    ("疑似有人使用其他裝置操作您的帳號", "請自行核查", "security"),
    ("Third-party app was given new permissions", "Review access from your account settings", "authorization"),
    ("您使用的服務將因扣款問題中止", "請檢查訂閱資料", "account"),
    ("Your return request could not be processed", "Please contact the seller", "refund"),
    ("退貨要求未通過商家審核", "需進一步聯絡處理", "refund"),
    ("您的繳款已成功完成", "交易已入帳", None),
    ("廣告促銷：信用卡專屬週末折扣", "好康優惠券", None),
    ("網路銀行提供新功能介紹", "電子報文章更新", None),
    ("We received your payment and no action is required", "", None),
    ("一般商店購物收據", "本次交易已完成", None),
    ("健康講座資訊分享", "歡迎參與線上活動", None),
    ("秋冬購物趨勢報告", "本月推薦商品", None),
    ("Your account monthly activity summary", "Review activity from your bank app", None),
    ("請查看最新的服務條款", "此通知不需要回覆", None),
    ("旅遊攻略推薦", "自由行景點與交通整理", None),
    ("Your order has shipped", "Track your parcel in the merchant app", None),
    ("開戶流程已完成", "無需任何後續操作", None),
    ("專案月報", "附上最新產業分析文章", None),
    ("明日天氣晴朗", "週末溫度預報", None),
    ("歡迎加入社群", "已成功建立您的帳號", None),
    ("上週活動照片分享", "感謝您的參加", None),
]


@contextmanager
def network_forbidden():
    connect = socket.socket.connect

    def blocked(*_args, **_kwargs):
        raise RuntimeError("OFFLINE_BENCHMARK_NETWORK_ATTEMPT")

    socket.socket.connect = blocked
    try:
        yield
    finally:
        socket.socket.connect = connect


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def benchmark() -> dict:
    from scripts.gmail_semantic_artifact import verify_checkpoint
    from pathlib import Path
    model_path = os.environ.get("GMAIL_RADAR_LOCAL_MODEL_PATH", "")
    verify_checkpoint(Path(model_path))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    started = time.perf_counter()
    with network_forbidden():
        model_version = active_classifier_version()
        if not model_version.endswith("-sem"):
            raise RuntimeError("local_semantic_model_not_ready")
        cold_seconds = time.perf_counter() - started
        preds = []
        timings = []
        for subject, snippet, expected in CASES:
            tick = time.perf_counter()
            outcome = classify_local(subject, snippet, classify_message(subject, snippet))
            timings.append((time.perf_counter() - tick) * 1000)
            preds.append((outcome.category, expected))
    tp = sum(gold is not None and actual == gold for actual, gold in preds)
    wrong_category = sum(gold is not None and actual is not None and actual != gold for actual, gold in preds)
    fp = sum(gold is None and actual is not None for actual, gold in preds)
    fn = sum(gold is not None and actual is None for actual, gold in preds)
    tn = sum(gold is None and actual is None for actual, gold in preds)
    precision = tp / max(1, tp + wrong_category + fp)
    recall = tp / max(1, tp + wrong_category + fn)
    specificity = tn / max(1, tn + fp)
    return {
        "model_revision": model_version,
        "synthetic_samples": len(CASES),
        "correct_positive": tp, "wrong_category": wrong_category,
        "false_positive": fp, "false_negative": fn, "true_negative": tn,
        "precision_exact_category": round(precision, 4),
        "recall_exact_category": round(recall, 4),
        "negative_specificity": round(specificity, 4),
        "cold_load_seconds": round(cold_seconds, 3),
        "median_message_ms": round(statistics.median(timings), 2),
        "p95_message_ms": round(percentile(timings, .95), 2),
        "max_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--enforce-gates", action="store_true")
    args = parser.parse_args()
    result = benchmark()
    from pathlib import Path
    Path(args.report).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.enforce_gates:
        # Prototype quality gate only. Real owner mailbox holdout is a separate
        # acceptance gate and these scores cannot substitute for it.
        if (result["precision_exact_category"] < 0.80
                or result["recall_exact_category"] < 0.65
                or result["negative_specificity"] < 0.90
                or result["p95_message_ms"] > 2500
                or result["max_rss_mib"] > 1200):
            raise SystemExit("gmail_semantic_benchmark=FAIL quality_or_resource_guard")
        print("gmail_semantic_benchmark=PASS synthetic_quality_and_resource")


if __name__ == "__main__":
    main()
