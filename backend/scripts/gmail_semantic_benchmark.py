"""Bounded offline-only Gmail V2 synthetic acceptance benchmark.

No OAuth, Gmail, external AI, real messages or stored private data.
Run with GMAIL_RADAR_LOCAL_MODEL_PATH pointing to an immutable local ONNX folder.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import resource
import socket
import statistics
import time
from contextlib import contextmanager

from app.api.gmail_radar import classify_message
from app.services.gmail_local_classifier import active_classifier_version, classify_local, _examples_embeddings

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


# Independent post-calibration holdout; never used to choose similarity limits.
HOLDOUT_CASES = [
    ("尚未入帳的水費請儘速處理", "逾期費用需補繳", "billing"),
    ("本月分期款尚待支付", "請檢查付款帳戶", "billing"),
    ("Your electricity bill is outstanding", "Service may be interrupted", "billing"),
    ("宅配員將物品放在郵局領件窗口", "持證件前往領取", "pickup"),
    ("門診已安排至下週二上午", "請確認您的就診行程", "booking"),
    ("The airline moved your departure time", "Please check updated flight details", "travel"),
    ("審核需要您補交相關證明文件", "資料尚未齊全", "administrative"),
    ("主管正在等候文件簽核", "請至公司系統查看", "administrative"),
    ("Your profile was accessed from an unfamiliar location", "Review account access", "security"),
    ("有人未經您允許使用您的卡片", "請核對交易活動", "security"),
    ("An application obtained additional mailbox permissions", "Review account access", "authorization"),
    ("因為扣款資訊有問題，服務續約可能停止", "需查看繳款設定", "account"),
    ("您的退費申請未獲准", "需要進一步處理", "refund"),
    ("截止時間之前請回覆審核要求", "附加資料仍待提供", "deadline"),
    ("本期卡費昨日已繳清", "本次付款完成", None),
    ("服務條款更新供參考", "此次更新不需回覆", None),
    ("個人購物清單已儲存", "資料同步成功", None),
    ("網路商店包裹已寄出", "訂單已出貨，無需其他操作", None),
    ("您已順利登入會員帳戶", "沒有異常情況", None),
    ("上個月的帳戶使用月報", "供您自行參考", None),
    ("交通安全知識文章", "航班旅遊新聞", None),
    ("Payment received successfully", "Your balance is settled", None),
    ("Newsletter: welcome to this month", "Read our newest articles", None),
    ("上週活動圓滿結束", "歡迎查看活動照片", None),
    ("週末美食推薦", "餐廳排名及菜單", None),
    ("購物點數已入帳", "優惠回饋已完成", None),
    ("Online order receipt", "Your order was delivered and paid", None),
    ("本週路況新聞回顧", "沒有個人行程變更", None),
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
        diagnostics = []
        reference_model, reference_examples, reference_vectors = _examples_embeddings(model_path)
        candidate_vectors = reference_model.encode(
            [(subject + ' ' + snippet)[:800] for subject, snippet, _ in CASES],
            normalize_embeddings=True,
        )
        for i, (query, (_, _, expected)) in enumerate(zip(candidate_vectors, CASES)):
            scores = {}
            for (category, _), vector in zip(reference_examples, reference_vectors):
                similarity = sum(float(a) * float(b) for a, b in zip(query, vector))
                if math.isfinite(similarity):
                    scores[category] = max(scores.get(category, -1.0), similarity)
            ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
            diagnostics.append({
                'id': i, 'expected': expected or 'none',
                'top_category': ranked[0][0],
                'top_similarity': round(ranked[0][1], 4),
                'margin': round(ranked[0][1] - ranked[1][1], 4),
            })
        for subject, snippet, expected in CASES + HOLDOUT_CASES:
            tick = time.perf_counter()
            outcome = classify_local(subject, snippet, classify_message(subject, snippet))
            timings.append((time.perf_counter() - tick) * 1000)
            preds.append((outcome.category, expected))
    def rates(rows):
        tp = sum(gold is not None and actual == gold for actual, gold in rows)
        wrong = sum(gold is not None and actual is not None and actual != gold for actual, gold in rows)
        fp = sum(gold is None and actual is not None for actual, gold in rows)
        fn = sum(gold is not None and actual is None for actual, gold in rows)
        tn = sum(gold is None and actual is None for actual, gold in rows)
        return {
            "correct_positive": tp, "wrong_category": wrong, "false_positive": fp,
            "false_negative": fn, "true_negative": tn,
            "precision_exact_category": round(tp / max(1, tp + wrong + fp), 4),
            "recall_exact_category": round(tp / max(1, tp + wrong + fn), 4),
            "negative_specificity": round(tn / max(1, tn + fp), 4),
        }
    primary = rates(preds[:len(CASES)])
    holdout = rates(preds[len(CASES):])
    return {
        "model_revision": model_version,
        "synthetic_samples": len(CASES),
        **primary,
        "independent_holdout_samples": len(HOLDOUT_CASES),
        "holdout": holdout,
        "cold_load_seconds": round(cold_seconds, 3),
        "median_message_ms": round(statistics.median(timings), 2),
        "p95_message_ms": round(percentile(timings, .95), 2),
        "max_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "score_diagnostics": diagnostics,
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
                or result["holdout"]["precision_exact_category"] < 0.80
                or result["holdout"]["recall_exact_category"] < 0.65
                or result["holdout"]["negative_specificity"] < 0.90
                or result["p95_message_ms"] > 2500
                or result["max_rss_mib"] > 1200):
            raise SystemExit("gmail_semantic_benchmark=FAIL quality_or_resource_guard")
        print("gmail_semantic_benchmark=PASS synthetic_quality_and_resource")


if __name__ == "__main__":
    main()
