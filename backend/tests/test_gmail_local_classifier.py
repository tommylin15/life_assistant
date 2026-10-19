"""Gmail V2 local-only classification: no external inference and no guessed dates."""
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from app.services.gmail_local_classifier import (
    CLASSIFIER_VERSION, EXAMPLES, LocalDecision, active_classifier_version, classify_local, extract_due,
    _semantic_category, _examples_embeddings,
)


class GmailLocalClassifierTests(unittest.TestCase):
    def test_versioned_rule_classification_without_model(self):
        self.assertTrue(CLASSIFIER_VERSION.startswith("local-v2"))
        d = classify_local(
            "上海商銀信用卡繳款期限到期通知",
            "本期帳單繳款截止日為10月21日，本期帳單應繳總額NT$9547元",
            "billing", model_path="",
        )
        self.assertEqual(d.category, "billing")
        self.assertEqual(d.source, "rules")
        self.assertIsNone(d.due_date)
        self.assertEqual(d.due_text, "10月21日")

    def test_settled_invoices_are_not_promoted_even_if_rule_title_matches(self):
        for subject, preview in [
            ("繳費通知", "本期費用已繳清，謝謝您"),
            ("信用卡帳單通知", "暫無需繳款，併入次期"),
            ("Payment due notice", "Payment received"),
        ]:
            with self.subTest(subject=subject):
                decision = classify_local(subject, preview, "billing", model_path="")
                self.assertIsNone(decision.category)
                self.assertEqual(decision.reason_code, "billing_settled")

    def test_security_rule_survives_marketing_footer(self):
        decision = classify_local(
            "異常登入安全性警告", "頁尾：unsubscribe 訂閱電子報",
            "security", model_path="")
        self.assertEqual(decision.category, "security")

    def test_explicit_full_dates_only(self):
        self.assertEqual(
            extract_due("繳款截止：2026/10/21", "")[0].isoformat(), "2026-10-21"
        )
        self.assertEqual(
            extract_due("繳費期限：民國115年11月02日", "")[0].isoformat(), "2026-11-02"
        )
        self.assertEqual(
            extract_due("付款期限：115/11/02", "")[0].isoformat(), "2026-11-02"
        )
        self.assertEqual(extract_due("繳款截止 10月21日", ""), (None, "10月21日"))
        self.assertEqual(extract_due("繳款截止：2026/02/31", ""),
                         (None, "2026/02/31"))
        self.assertEqual(extract_due("本週有優惠", ""), (None, None))

    def test_normal_or_promotional_mail_never_promoted_by_similarity(self):
        for subject, snippet in [
            ("信用卡優惠宣傳", "本週回饋"),
            ("重要通知", "暫無需繳款併入下期"),
            ("交易通知", "payment successful"),
            ("Monthly newsletter", "Account and security updates"),
        ]:
            with self.subTest(subject=subject):
                self.assertEqual(classify_local(subject, snippet, None,
                                                model_path="/tmp/nonexistent-checkpoint").category, None)

    def test_offline_semantic_activation_changes_classifier_revision(self):
        with patch.dict("os.environ", {"GMAIL_RADAR_LOCAL_MODEL_PATH": "/fake-checkpoint"}):
            with patch("app.services.gmail_local_classifier._model_ready", return_value=False):
                self.assertEqual(active_classifier_version(), CLASSIFIER_VERSION)
            with patch("app.services.gmail_local_classifier._model_ready", return_value=True):
                self.assertEqual(active_classifier_version(), CLASSIFIER_VERSION + "-sem")

    def test_multiple_users_cannot_initialize_embeddings_concurrently(self):
        running = 0
        peak = 0
        guard = threading.Lock()

        def fake_init(_path):
            nonlocal running, peak
            with guard:
                running += 1
                peak = max(peak, running)
            time.sleep(0.01)
            with guard:
                running -= 1
            return object()

        with patch("app.services.gmail_local_classifier._examples_embeddings_cached",
                   side_effect=fake_init):
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(_examples_embeddings, ["/fake"] * 8))
        self.assertEqual(len(results), 8)
        self.assertEqual(peak, 1)

    def test_missing_model_falls_back_without_network(self):
        with patch("app.services.gmail_local_classifier._load_local_model") as loader:
            outcome = classify_local("請盡快回覆某項申請資料", "", None, model_path="/no-model")
        self.assertIsNone(outcome.category)
        loader.assert_not_called()

    def test_high_margin_multilingual_local_semantic_is_review_only(self):
        class FakeEncoder:
            def encode(self, values, normalize_embeddings=False):
                self_guard = normalize_embeddings
                if not self_guard:
                    raise AssertionError("vectors must be normalized")
                return [[1., 0.]]
        phrases = []
        vectors = []
        for category, variants in EXAMPLES.items():
            for phrase in variants:
                phrases.append((category, phrase))
                vectors.append([1., 0.] if category == "billing" else [0., 1.])
        with tempfile.TemporaryDirectory() as temp, patch(
            "app.services.gmail_local_classifier._examples_embeddings",
            return_value=(FakeEncoder(), phrases, vectors),
        ):
            d = classify_local("付款期限將屆，請確認", "請檢查您的帳單", None, model_path=temp)
        self.assertEqual(d.category, "billing")
        self.assertEqual(d.source, "local_semantic")
        self.assertEqual(d.reason_code, "semantic_review")
