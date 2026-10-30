"""Fail-closed policy for automatic staging with LINE enabled."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "scripts" / "line_staging_guard.py"
spec = importlib.util.spec_from_file_location("line_staging_guard", PATH)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
DISABLED = b'{"detail":"LINE integration is not configured"}'


class LineStagingGuardTests(unittest.TestCase):
    def test_explicit_503_application_disabled_twice_allows_auto_staging(self):
        fetches = iter([(503, DISABLED), (503, DISABLED)])
        sleeps = []
        protect, reason = guard.should_protect(fetch=lambda: next(fetches),
                                               sleep=lambda sec: sleeps.append(sec))
        self.assertFalse(protect)
        self.assertEqual(reason, "line_explicitly_disabled")
        self.assertEqual(sleeps, [2])

    def test_200_blocks_even_if_body_malformed(self):
        self.assertEqual(guard.should_protect(fetch=lambda: (200, b"not-json"),
                                               sleep=lambda _: None),
                         (True, "line_config_enabled"))

    def test_enabled_during_second_probe_blocks_dispatch(self):
        sequence = iter([(503, DISABLED), (200, b'{"origin":"https://example.test"}')])
        self.assertEqual(guard.should_protect(fetch=lambda: next(sequence),
                                               sleep=lambda _: None),
                         (True, "line_config_enabled"))

    def test_unknown_fails_closed_including_gateway_503(self):
        for status, body in [
            (0, b""), (401, b""), (403, b""),
            (404, b""), (429, b""), (500, b""),
            (503, b"upstream error"), (503, b""),
            (503, b'{"detail":"other"}'),
            (503, b'{"detail":"LINE integration is not configured","extra":"ignored"}'),
        ]:
            # An exact disabled detail is the only allowed shape.
            expected = (status == 503 and body.startswith(
                b'{"detail":"LINE integration is not configured"'))
            protect, _ = guard.should_protect(fetch=lambda: (status, body), sleep=lambda _: None)
            self.assertEqual(protect, not expected, (status, body))

    def test_network_exception_fails_closed(self):
        def broken():
            raise TimeoutError("private transport details must not escape")
        self.assertEqual(guard.should_protect(fetch=broken, sleep=lambda _: None),
                         (True, "unknown_config_response"))

    def test_exact_stage_url_only(self):
        self.assertEqual(guard.STAGING_LINE_URL,
                         "https://life-assistant-v3-stage-tl15.web.app/api/v1/line/config")


if __name__ == "__main__":
    unittest.main()
