import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from app.services.tw_request_router import TWRequestRouter


class TestTWRequestRouter(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cache_file = Path(self.test_dir) / "routing_cache.json"
        initial_data = {
            "version": "1.0",
            "routes": {
                "media.taiwan.net.tw": {
                    "route": "TW_PROXY",
                    "reason": "OVERSEAS_CONNECTION_TIMEOUT",
                }
            },
        }
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)
        self.router = TWRequestRouter(cache_path=self.cache_file, drive_sync_path=None)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_is_proxy_required(self):
        self.assertTrue(self.router.is_proxy_required("media.taiwan.net.tw"))
        self.assertTrue(self.router.is_proxy_required("MEDIA.TAIWAN.NET.TW"))
        self.assertFalse(self.router.is_proxy_required("example.com"))

    def test_direct_routing_cached_as_tw_proxy(self):
        mock_proxy_resp = MagicMock(spec=requests.Response)
        mock_proxy_resp.status_code = 200

        with patch.object(self.router, "_call_proxy", return_value=mock_proxy_resp) as mock_proxy, patch(
            "requests.request"
        ) as mock_direct:
            resp = self.router.request("https://media.taiwan.net.tw/XMLReleaseAll_public/v2.0/Zh_tw/Event-json.zip")
            self.assertEqual(resp, mock_proxy_resp)
            mock_proxy.assert_called_once()
            mock_direct.assert_not_called()

    def test_direct_timeout_fallback_and_learn(self):
        mock_proxy_resp = MagicMock(spec=requests.Response)
        mock_proxy_resp.status_code = 200

        with patch(
            "requests.request", side_effect=requests.exceptions.Timeout("Connection timed out")
        ), patch.object(self.router, "_call_proxy", return_value=mock_proxy_resp) as mock_proxy:
            resp = self.router.request("https://fae.moa.gov.tw/events")
            self.assertEqual(resp, mock_proxy_resp)
            mock_proxy.assert_called_once()

            # Verify it auto-learned the route
            self.assertTrue(self.router.is_proxy_required("fae.moa.gov.tw"))

            # Read back cache file
            with open(self.cache_file, "r", encoding="utf-8") as f:
                updated = json.load(f)
            self.assertIn("fae.moa.gov.tw", updated["routes"])
            self.assertEqual(updated["routes"]["fae.moa.gov.tw"]["route"], "TW_PROXY")


if __name__ == "__main__":
    unittest.main()
