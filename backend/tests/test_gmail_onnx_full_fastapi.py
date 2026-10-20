"""Full Life ONNX staging readiness never silently falls back to rules-only."""
import os
import unittest
from unittest.mock import AsyncMock, patch

from app import main


class FullLifeGmailOnnxReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_rules_only_ready_stays_backward_compatible(self):
        with patch.dict(os.environ, {}, clear=False), \
             patch("app.main.db_session.check_database", new_callable=AsyncMock):
            os.environ.pop("GMAIL_RADAR_LOCAL_MODEL_PATH", None)
            result = await main.ready()
        self.assertEqual(result, {"status": "ok", "database": "ok"})

    async def test_onnx_candidate_must_prove_loaded_model(self):
        with patch.dict(os.environ, {"GMAIL_RADAR_LOCAL_MODEL_PATH": "/opt/gmail-onnx"}), \
             patch("app.main.db_session.check_database", new_callable=AsyncMock), \
             patch("app.main.active_classifier_version", return_value="local-v2.5-sem"):
            result = await main.ready()
        self.assertEqual(result.get("gmail_model"), "local_semantic_ready")

    async def test_onnx_candidate_bad_artifact_fails_closed(self):
        with patch.dict(os.environ, {"GMAIL_RADAR_LOCAL_MODEL_PATH": "/bad"}), \
             patch("app.main.db_session.check_database", new_callable=AsyncMock), \
             patch("app.main.active_classifier_version", return_value="local-v2.5"):
            result = await main.ready()
            with self.assertRaisesRegex(RuntimeError, "offline_gmail_model_unavailable"):
                await main.startup()
        self.assertEqual(result.status_code, 503)
