"""Firebase Preview 404 propagation is retried; all identity/access gates fail closed."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v3_verify_preview import verify

SHA = "f" * 40
URL = "https://life-assistant-v3-stage-tl15--v3-ffffffffff-test0001.web.app"


class VerifyPreviewReadinessTests(unittest.TestCase):
    def test_eventual_404_recovers_only_after_exact_sha_and_401(self):
        seen = []
        responses = iter([
            (404, ""),
            (503, ""),
            (200, SHA + "\n"),
            (404, ""),
            (200, SHA),
            (401, ""),
        ])
        def fake_fetch(url):
            seen.append(url)
            return next(responses)
        verify(URL, SHA, attempts=4, delay=0, fetch=fake_fetch, sleep=lambda _: None)
        self.assertEqual(len(seen), 6)
        self.assertTrue(seen[-1].endswith("/api/v1/tasks"))

    def test_static_never_ready_is_failure(self):
        with self.assertRaisesRegex(RuntimeError, "bounded"):
            verify(URL, SHA, attempts=3, delay=0,
                   fetch=lambda _: (404, ""), sleep=lambda _: None)

    def test_official_firebaseapp_domain_can_recover_web_app_404(self):
        secondary = URL.replace(".web.app", ".firebaseapp.com")
        calls = []
        def fetch(url):
            calls.append(url)
            if url == URL + "/release.txt":
                return (404, "")
            if url == secondary + "/release.txt":
                return (200, SHA)
            if url == secondary + "/api/v1/tasks":
                return (401, "")
            self.fail("unexpected domain or resource")
        chosen = verify(URL, SHA, attempts=1, delay=0,
                        fetch=fetch, sleep=lambda _: None)
        self.assertEqual(chosen, secondary)
        self.assertEqual(len(calls), 3)

    def test_alternate_domain_wrong_sha_cannot_bypass_gate(self):
        responses = iter([(404, ""), (200, "0" * 40)])
        with self.assertRaisesRegex(RuntimeError, "SHA mismatch"):
            verify(URL, SHA, attempts=3, delay=0,
                   fetch=lambda _: next(responses), sleep=lambda _: None)

    def test_both_preview_domains_stay_fail_closed_on_404(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return (404, "")
        with self.assertRaisesRegex(RuntimeError, "bounded"):
            verify(URL, SHA, attempts=2, delay=0, fetch=fetch,
                   sleep=lambda _: None)
        self.assertEqual(len(calls), 4)

    def test_wrong_sha_fails_immediately_even_if_status_200(self):
        seen = []
        def wrong(url):
            seen.append(url)
            return (200, "0" * 40)
        with self.assertRaisesRegex(RuntimeError, "SHA mismatch"):
            verify(URL, SHA, attempts=12, delay=0, fetch=wrong, sleep=lambda _: None)
        self.assertEqual(len(seen), 1)

    def test_api_200_or_302_blocks_release(self):
        for status in (200, 302, 403):
            with self.subTest(status=status):
                responses = iter([(200, SHA), (status, "")])
                with self.assertRaisesRegex(RuntimeError, "access gate FAIL"):
                    verify(URL, SHA, attempts=1, delay=0, fetch=lambda _: next(responses))

    def test_api_eventual_404_is_allowed_only_after_401(self):
        responses = iter([(200, SHA), (404, ""), (200, SHA), (401, "")])
        verify(URL, SHA, attempts=2, delay=0, fetch=lambda _: next(responses),
               sleep=lambda _: None)

    def test_unrelated_domain_and_wrong_sha_prefix_rejected_before_http(self):
        for url in (
            "https://gen-lang-client-0593591102.web.app",
            "https://evil.example.org",
            "https://life-assistant-v3-stage-tl15--v3-eeeeeeeeee-test0001.web.app",
            "http://life-assistant-v3-stage-tl15--v3-ffffffffff-test0001.web.app",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    verify(url, SHA, fetch=lambda _: self.fail("unexpected fetch"))

    def test_release_attempt_isolated_channel_and_mismatch(self):
        channel = "v3-ffffffffff-hxn1abc" + "a3"
        url = "https://life-assistant-v3-stage-tl15--" + channel + "-freshxyz.web.app"
        def good_get(address):
            if address.endswith("/release.txt"):
                return (200, SHA)
            if address.endswith("/api/v1/tasks"):
                return (401, "")
            self.fail("unexpected URL")
        self.assertEqual(verify(url, SHA, channel=channel, attempts=1, delay=0,
                                fetch=good_get), url)
        with self.assertRaises(ValueError):
            verify(URL, SHA, channel=channel,
                   fetch=lambda _: self.fail("must not fetch wrong channel"))
        with self.assertRaises(ValueError):
            verify(url, SHA, channel="v3-eeeeeeeeee-hxn1abca3",
                   fetch=lambda _: self.fail("must not fetch wrong SHA"))
        with self.assertRaises(ValueError):
            verify(url, SHA, channel="v3-ffffffffff-hxn1abcaa0",
                   fetch=lambda _: self.fail("must not fetch invalid attempt"))
        # Firebase truncates a long channel to a different public hostname;
        # reject it before any network call or future live promotion.
        with self.assertRaisesRegex(ValueError, "hostname limit"):
            verify(url, SHA, channel="v3-ffffffffff-abcdefgha123",
                   fetch=lambda _: self.fail("must not fetch truncated host"))

    def test_invalid_limit_rejected(self):
        with self.assertRaises(ValueError):
            verify(URL, SHA, attempts=100)


if __name__ == "__main__":
    unittest.main()
