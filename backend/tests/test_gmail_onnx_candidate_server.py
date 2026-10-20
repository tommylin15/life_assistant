"""ONNX canary must not become another user-facing Gmail endpoint."""
import unittest

from scripts.gmail_onnx_candidate_server import app, _smoke


class CandidateSecurityTests(unittest.TestCase):
    def test_only_fixed_health_and_synthetic_endpoints(self):
        paths = {route.path for route in app.routes}
        self.assertEqual(paths, {"/health", "/ready", "/synthetic-smoke"})
        for disallowed in ("/gmail", "/inbox", "/message", "/classify", "/predict"):
            self.assertNotIn(disallowed, paths)

    def test_has_no_route_accepting_arbitrary_email(self):
        for route in app.routes:
            if hasattr(route, "body_field"):
                self.assertIsNone(route.body_field)

    def test_synthetic_only_readiness_payload(self):
        from unittest.mock import patch
        with patch("scripts.gmail_onnx_candidate_server.classify_local") as classify:
            outputs = ["billing", "pickup", "security", None, None]
            classify.side_effect = [
                type("SyntheticDecision", (), {"category": category})()
                for category in outputs
            ]
            result = _smoke()
        self.assertTrue(result["pass"])
        self.assertEqual(result["cases"], 5)
        self.assertNotIn("subject", result)
        self.assertNotIn("snippet", result)
