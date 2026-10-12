"""Fixed staging tester access without weakening production or Owner policies."""
import hashlib
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, Response
from starlette.requests import Request

from app.api import auth
from app.api.ui_policies import owner_only


def request(host, cookie="", **extra):
    headers = [(b"host", host.encode())]
    if cookie:
        headers.append((b"cookie", ("__session=" + cookie).encode()))
    headers += [(key.replace("_", "-").encode(), value.encode())
                for key, value in extra.items()]
    return Request({"type": "http", "headers": headers})


class StagingAccountTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"ALLOWED_GOOGLE_EMAIL": "owner@example.test"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.tester = {"sub": "tester-sub", "email": "tester@example.test",
                       "name": "Tester", "exp": 9999999999}
        digest = hashlib.sha256(self.tester["email"].encode()).hexdigest()
        self.test_digest = patch.object(auth, "_STAGING_TESTER_EMAIL_DIGESTS",
                                        frozenset({digest}))
        self.test_digest.start()
        self.addCleanup(self.test_digest.stop)

    def test_owner_and_fixed_staging_tester_have_different_privileges(self):
        auth._enforce_account_access(
            {"email": "owner@example.test"}, staging=False)
        auth._enforce_account_access(self.tester, staging=True)
        with self.assertRaises(HTTPException) as ctx:
            auth._enforce_account_access(self.tester, staging=False)
        self.assertEqual(ctx.exception.status_code, 403)
        with self.assertRaises(HTTPException) as admin:
            owner_only(self.tester)
        self.assertEqual(admin.exception.status_code, 403)
        with self.assertRaises(HTTPException):
            auth._enforce_account_access(
                {"email": "unauthorized@example.test"}, staging=True)

    async def test_staging_cookie_is_not_enough_on_production_origin(self):
        with patch("app.api.auth._verify_id_token",
                   new=AsyncMock(return_value=self.tester)):
            stage = request(auth.STAGING_HOST, "id:staging:google-token")
            self.assertEqual((await auth.current_user(stage))["sub"], "tester-sub")
            prod = request("gen-lang-client-0593591102.web.app",
                           "id:staging:google-token")
            with self.assertRaises(HTTPException) as blocked:
                await auth.current_user(prod)
            self.assertEqual(blocked.exception.status_code, 403)
            normal_cookie = request(auth.STAGING_HOST, "id:google-token")
            with self.assertRaises(HTTPException):
                await auth.current_user(normal_cookie)

    async def test_fixed_proxy_origin_but_not_spoofed_cloud_run(self):
        with patch("app.api.auth._verify_id_token",
                   new=AsyncMock(return_value=self.tester)):
            proxy = request("life-assistant-api-xyz-uc.a.run.app",
                "id:staging:google-token",
                x_forwarded_host=auth.STAGING_HOST, x_forwarded_proto="https")
            self.assertEqual((await auth.current_user(proxy))["sub"], "tester-sub")
            spoof = request("attacker-xyz.a.run.app", "id:staging:google-token",
                            x_forwarded_host=auth.STAGING_HOST, x_forwarded_proto="https")
            with self.assertRaises(HTTPException):
                await auth.current_user(spoof)

    async def test_verified_staging_callback_accepts_tester_not_admin(self):
        state = "z" * 32
        req = request(auth.STAGING_HOST, "oauth:staging:" + state)
        with patch("app.api.auth._complete_login",
                   new=AsyncMock(return_value=("signed-id-token", self.tester))) as complete, \
             patch("app.api.auth._audit_staging_e2e", new_callable=AsyncMock):
            response = await auth.callback("google-code", state, req, object())
        complete.assert_awaited_once_with("google-code", auth.STAGING_REDIRECT_URI)
        self.assertEqual(response.headers["location"], "https://" + auth.STAGING_HOST + "/")
        self.assertIn("id:staging:signed-id-token", response.headers["set-cookie"])
        with self.assertRaises(HTTPException):
            owner_only(self.tester)

    async def test_normal_production_callback_rejects_tester(self):
        state = "y" * 32
        req = request("gen-lang-client-0593591102.web.app", "oauth:" + state)
        with patch("app.api.auth._complete_login",
                   new=AsyncMock(return_value=("signed-id-token", self.tester))):
            with self.assertRaises(HTTPException) as blocked:
                await auth.callback("google-code", state, req, object())
        self.assertEqual(blocked.exception.status_code, 403)

    async def test_logout_deletes_auth_cookie(self):
        response = Response()
        result = await auth.logout(response)
        self.assertEqual(result, {"status": "ok"})
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("__session=", cookie)
        self.assertIn("max-age=0", cookie)

    async def test_login_requests_google_account_chooser(self):
        with patch.object(auth.settings, "google_client_id", "client-id"):
            response = await auth.staging_login(request(auth.STAGING_HOST))
        self.assertIn("select_account", response.headers["location"])
