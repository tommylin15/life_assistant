"""Redaction contract for V3 Firebase CLI error diagnostics."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / ".github/scripts/v3_firebase_error.py"
spec = importlib.util.spec_from_file_location("v3_firebase_error", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FirebaseDiagnosticsTests(unittest.TestCase):
    def test_permission_denied_is_classified_without_message(self):
        error = '{"status":"error","error":"Permission denied token=secret-value 403"}'
        result = module.summarize(error, "", 2)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("PERMISSION_OR_IAM", result["categories"])
        self.assertIn("403", result["http_codes"])
        self.assertNotIn("secret-value", str(result))
        self.assertTrue(result["message_redacted"])

    def test_unknown_provider_error_stays_redacted(self):
        result = module.summarize(
            '{"error":"Sensitive: ya29.user-private-token"}', "", 2)
        self.assertNotIn("ya29", str(result))
        self.assertIn("UNKNOWN_REDACTED", result["categories"])

    def test_preview_revision_category(self):
        result = module.summarize("Cloud Run revision cannot pinTag", "", 2)
        self.assertIn("PIN_TAG_OR_REVISION", result["categories"])


if __name__ == "__main__":
    unittest.main()
