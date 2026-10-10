from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
from fastapi import HTTPException
from starlette.requests import Request

from app.api import auth


class AuthApiTests(IsolatedAsyncioTestCase):
    async def test_login_sets_state_cookie_and_uses_configured_redirect(self):
        original_client_id = auth.settings.google_client_id
        original_redirect = auth.settings.google_redirect_uri
        try:
            auth.settings.google_client_id = "client-id"
            auth.settings.google_redirect_uri = "https://example.test/auth/callback"

            response = await auth.login(Request({"type": "http", "headers": [(b"host", b"example.test")]}))

            location = response.headers["location"]
            query = parse_qs(urlparse(location).query)
            self.assertEqual(query["client_id"], ["client-id"])
            self.assertEqual(
                query["redirect_uri"],
                ["https://example.test/auth/callback"],
            )
            self.assertIn("state", query)
            self.assertEqual(set(query["scope"][0].split()), {"openid", "email", "profile"})
            self.assertNotIn("gmail", query["scope"][0])
            self.assertNotIn("calendar", query["scope"][0])
            self.assertIn(auth.SESSION_COOKIE, response.headers["set-cookie"])
            self.assertIn("HttpOnly", response.headers["set-cookie"])
            self.assertIn("Secure", response.headers["set-cookie"])
        finally:
            auth.settings.google_client_id = original_client_id
            auth.settings.google_redirect_uri = original_redirect

    async def test_login_rejects_missing_client_id(self):
        original_client_id = auth.settings.google_client_id
        try:
            auth.settings.google_client_id = ""
            with self.assertRaises(HTTPException) as ctx:
                await auth.login(Request({"type": "http", "headers": [(b"host", b"example.test")]}))
            self.assertEqual(ctx.exception.status_code, 503)
        finally:
            auth.settings.google_client_id = original_client_id

    async def test_fixed_staging_domain_uses_staging_google_callback(self):
        request = Request({"type": "http", "headers": [
            (b"host", b"life-assistant-v3-stage-tl15.web.app"),
        ]})
        with patch.object(auth.settings, "google_client_id", "client-id"):
            response = await auth.login(request)
        params = parse_qs(urlparse(response.headers["location"]).query)
        self.assertEqual(params["redirect_uri"], [
            "https://life-assistant-v3-stage-tl15.web.app/auth/callback"
        ])
        self.assertEqual(auth.frontend_for_request(request),
                         "https://life-assistant-v3-stage-tl15.web.app")

    async def test_explicit_staging_login_needs_no_forwarded_proxy_headers(self):
        request = Request({"type": "http", "headers": [
            (b"host", b"life-assistant-api-abc-uc.a.run.app"),
            (b"x-forwarded-proto", b"http,https"),
        ]})
        with patch.object(auth.settings, "google_client_id", "client-id"):
            response = await auth.staging_login(request)
        query = parse_qs(urlparse(response.headers["location"]).query)
        self.assertEqual(query["redirect_uri"], [auth.STAGING_REDIRECT_URI])
        self.assertIn("oauth:staging:", response.headers["set-cookie"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("Secure", response.headers["set-cookie"])
        # Preview and production still use their original callback path.
        with patch.object(auth.settings, "google_client_id", "client-id"):
            prod = await auth.login(request)
        self.assertEqual(parse_qs(urlparse(prod.headers["location"]).query)["redirect_uri"],
                         [auth.settings.google_redirect_uri])

    async def test_explicit_staging_callback_uses_state_not_proxy_headers(self):
        req = Request({"type": "http", "headers": [
            (b"host", b"life-assistant-api-abc-uc.a.run.app"),
        ]})
        state = "n" * 32
        callback_req = Request({"type": "http", "headers": [
            (b"host", b"life-assistant-api-abc-uc.a.run.app"),
            (b"cookie", f"__session=oauth:staging:{state}".encode()),
        ]})
        user = {"sub": "test", "email": "owner@example.test",
                "name": "Owner", "exp": 9999999999}
        with patch("app.api.auth._complete_login",
                   new=AsyncMock(return_value=("jwt-token", user))) as complete, \
             patch("app.api.auth._audit_staging_e2e", new_callable=AsyncMock) as audit:
            response = await auth.callback("google-code", state, callback_req, object())
        complete.assert_awaited_once_with("google-code", auth.STAGING_REDIRECT_URI)
        audit.assert_awaited_once()
        self.assertEqual(response.headers["location"],
                         "https://life-assistant-v3-stage-tl15.web.app/")
        self.assertIn("id:staging:jwt-token", response.headers["set-cookie"])
        with patch("app.api.auth._verify_id_token",
                   new=AsyncMock(return_value=user)) as verify:
            session_request = Request({"type": "http", "headers": [
                (b"cookie", b"__session=id:staging:jwt-token"),
            ]})
            logged_in = await auth.current_user(session_request)
        verify.assert_awaited_once_with("jwt-token")
        self.assertEqual(logged_in["email"], user["email"])
        self.assertEqual(auth.oauth_redirect_for_request(session_request),
                         auth.STAGING_REDIRECT_URI)

    async def test_staging_callback_rejects_wrong_state_even_with_cookie(self):
        callback_req = Request({"type": "http", "headers": [
            (b"cookie", b"__session=oauth:staging:correct"),
        ]})
        with patch("app.api.auth._complete_login", new_callable=AsyncMock) as exchange:
            with self.assertRaises(HTTPException) as ctx:
                await auth.callback("google-code", "wrong", callback_req, object())
        self.assertEqual(ctx.exception.status_code, 400)
        exchange.assert_not_awaited()

    async def test_firebase_proxy_exact_fixed_origin_selects_staging(self):
        request = Request({"type": "http", "headers": [
            (b"host", b"life-assistant-api-abc-uc.a.run.app"),
            (b"x-forwarded-host", b"life-assistant-v3-stage-tl15.web.app"),
            (b"x-forwarded-proto", b"https"),
        ]})
        self.assertEqual(auth.oauth_redirect_for_request(request),
                         auth.STAGING_REDIRECT_URI)
        request_url_header = Request({"type": "http", "headers": [
            (b"host", b"life-assistant-api-abc-uc.a.run.app"),
            (b"x-forwarded-host", b"https://life-assistant-v3-stage-tl15.web.app"),
            (b"x-forwarded-proto", b"https"),
        ]})
        self.assertEqual(auth.oauth_redirect_for_request(request_url_header),
                         auth.STAGING_REDIRECT_URI)

    async def test_firebase_proxy_host_spoof_and_scheme_are_rejected(self):
        for hostname, forwarded, proto in (
            ("attacker.run.app", auth.STAGING_HOST, "https"),
            ("life-assistant-api-abc-uc.a.run.app", "evil.example", "https"),
            ("life-assistant-api-abc-uc.a.run.app", auth.STAGING_HOST, "http"),
        ):
            with self.subTest(hostname=hostname, proto=proto):
                request = Request({"type": "http", "headers": [
                    (b"host", hostname.encode()),
                    (b"x-forwarded-host", forwarded.encode()),
                    (b"x-forwarded-proto", proto.encode()),
                ]})
                self.assertEqual(auth.oauth_redirect_for_request(request),
                                 auth.settings.google_redirect_uri)

    async def test_forwarded_host_spoof_cannot_enable_staging_oauth(self):
        request = Request({"type": "http", "headers": [
            (b"host", b"life-assistant-api-xyz.a.run.app"),
            (b"x-forwarded-host", b"life-assistant-v3-stage-tl15.web.app"),
        ]})
        self.assertEqual(auth.oauth_redirect_for_request(request),
                         auth.settings.google_redirect_uri)

    async def test_preview_channel_cannot_impersonate_fixed_staging_oauth(self):
        request = Request({"type": "http", "headers": [
            (b"host", b"life-assistant-v3-stage-tl15--v3-aaaaaaaaaa.web.app"),
        ]})
        self.assertEqual(auth.oauth_redirect_for_request(request),
                         auth.settings.google_redirect_uri)

    async def test_staging_google_e2e_audit_requires_real_owner_and_exact_revision(self):
        stage = Request({"type": "http", "headers": [(b"host", b"life-assistant-v3-stage-tl15.web.app")]})
        other = Request({"type": "http", "headers": [(b"host", b"gen-lang-client-0593591102.web.app")]})
        db = object()
        owner = {"sub": "owner-sub", "email": "owner@example.test"}
        with patch.dict("os.environ", {"ALLOWED_GOOGLE_EMAIL": "owner@example.test",
                                       "K_REVISION": "life-assistant-api-00200-abc"}):
            with patch("app.api.auth.start_execution", new_callable=AsyncMock) as start, \
                 patch("app.api.auth.finish_execution", new_callable=AsyncMock) as finish:
                start.return_value = object()
                await auth._audit_staging_e2e(db, stage, owner, "staging_google_callback")
                start.assert_awaited_once()
                self.assertEqual(start.await_args.kwargs["entity_id"], "life-assistant-api-00200-abc")
                self.assertEqual(start.await_args.kwargs["action_type"], "staging_google_callback")
                finish.assert_awaited_once()
                start.reset_mock(); finish.reset_mock()
                await auth._audit_staging_e2e(db, other, owner, "staging_google_callback")
                await auth._audit_staging_e2e(db, stage, {"sub": "bad", "email": "attacker@example.test"},
                                              "staging_google_callback")
                start.assert_not_awaited()
                finish.assert_not_awaited()

    async def test_staging_google_e2e_denies_missing_allowlist_and_revision(self):
        stage = Request({"type": "http", "headers": [(b"host", b"life-assistant-v3-stage-tl15.web.app")]})
        owner = {"sub": "owner-sub", "email": "owner@example.test"}
        for cfg in ({"ALLOWED_GOOGLE_EMAIL": "", "K_REVISION": "life-assistant-api-00200-abc"},
                    {"ALLOWED_GOOGLE_EMAIL": "owner@example.test", "K_REVISION": ""}):
            with patch.dict("os.environ", cfg):
                with patch("app.api.auth.start_execution", new_callable=AsyncMock) as start:
                    await auth._audit_staging_e2e(object(), stage, owner, "staging_google_session")
                    start.assert_not_awaited()

    async def test_current_user_rejects_missing_session(self):
        request = Request({"type": "http", "headers": []})
        with self.assertRaises(HTTPException) as ctx:
            await auth.current_user(request)
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_current_user_accepts_verified_cookie(self):
        request = Request({
            "type": "http",
            "headers": [(b"cookie", b"__session=id:test-token")],
        })
        claims = {
            "sub": "123",
            "email": "user@example.test",
            "name": "User",
            "exp": 9999999999,
        }
        with patch(
            "app.api.auth._verify_id_token",
            new=AsyncMock(return_value=claims),
        ) as verify:
            user = await auth.current_user(request)

        self.assertEqual(user["email"], "user@example.test")
        verify.assert_awaited_once_with("test-token")

    def test_google_error_code_returns_machine_readable_error_only(self):
        response = httpx.Response(
            400,
            json={
                "error": "invalid_client",
                "error_description": "client secret is wrong and must not leak",
            },
        )
        self.assertEqual(auth._google_error_code(response), "invalid_client")

    def test_google_error_code_rejects_unexpected_payload(self):
        response = httpx.Response(400, content=b"not-json")
        self.assertEqual(auth._google_error_code(response), "unknown_error")
