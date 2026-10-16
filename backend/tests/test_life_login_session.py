"""Thirty-day Life session: persistence, origin binding, revocation and migration."""
import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, Response
from starlette.requests import Request

from app.api import auth


def _request(host: str, cookie: str):
    return Request({"type": "http", "path": "/auth/me", "headers": [
        (b"host", host.encode()),
        (b"cookie", ("__session=" + cookie).encode()),
    ]})


class PersistentLoginTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_login_stores_hash_only_and_survives_google_token_expiry(self):
        db = SimpleNamespace(add=MagicMock(), commit=AsyncMock())
        user = {"sub": "alice", "email": "alice@example.test",
                "name": "Alice", "exp": 1}
        bearer = await auth._create_persistent_session(db, user, staging=False)
        stored = db.add.call_args.args[0]
        self.assertEqual(stored.token_sha256,
                         hashlib.sha256(bearer.encode()).hexdigest())
        self.assertNotEqual(stored.token_sha256, bearer)
        self.assertEqual(stored.audience, "production")
        self.assertEqual(stored.user_sub, "alice")
        self.assertEqual(auth.SESSION_SECONDS, 30 * 86400)
        db.commit.assert_awaited_once()

        stored.revoked_at = None
        read_db = SimpleNamespace(get=AsyncMock(return_value=stored))
        claims = await auth.current_user(
            _request("gen-lang-client-0593591102.web.app",
                     "se:production:" + bearer), db=read_db)
        self.assertEqual(claims["sub"], "alice")
        self.assertEqual(claims["email"], user["email"])

    async def test_staging_cookie_cannot_replay_against_production(self):
        db = SimpleNamespace(add=MagicMock(), commit=AsyncMock())
        bearer = await auth._create_persistent_session(db,
            {"sub": "u2", "email": "u2@example.test", "name": "Test"}, staging=True)
        row = db.add.call_args.args[0]
        row.revoked_at = None
        check = SimpleNamespace(get=AsyncMock(return_value=row))
        stage = await auth.current_user(
            _request(auth.STAGING_HOST, "se:staging:" + bearer), db=check)
        self.assertEqual(stage["sub"], "u2")
        for host, cookie in [
            ("gen-lang-client-0593591102.web.app", "se:staging:" + bearer),
            (auth.STAGING_HOST, "se:production:" + bearer),
        ]:
            with self.subTest(host=host):
                with self.assertRaises(HTTPException) as fail:
                    await auth.current_user(_request(host, cookie), db=check)
                self.assertEqual(fail.exception.status_code, 403)

    async def test_missing_expired_and_revoked_sessions_fail_closed(self):
        bearer = "a" * 64
        cookie = "se:production:" + bearer
        row = SimpleNamespace(user_sub="alice", email="alice@example.test",
            display_name="Alice", audience="production",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            revoked_at=None)
        db = SimpleNamespace(get=AsyncMock(return_value=None))
        request = _request("gen-lang-client-0593591102.web.app", cookie)
        with self.assertRaises(HTTPException) as missing:
            await auth.current_user(request, db=db)
        self.assertEqual(missing.exception.status_code, 401)
        db.get.return_value = row
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        with self.assertRaises(HTTPException):
            await auth.current_user(request, db=db)
        row.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        row.revoked_at = datetime.now(timezone.utc)
        with self.assertRaises(HTTPException):
            await auth.current_user(request, db=db)
        with self.assertRaises(HTTPException):
            await auth.current_user(_request("gen-lang-client-0593591102.web.app",
                 "se:production:not-valid"), db=db)

    async def test_logout_revokes_server_session_and_clears_browser_cookie(self):
        bearer = "b" * 64
        record = SimpleNamespace(revoked_at=None)
        db = SimpleNamespace(get=AsyncMock(return_value=record),
                             commit=AsyncMock())
        response = Response()
        request = _request("gen-lang-client-0593591102.web.app",
                           "se:production:" + bearer)
        result = await auth.logout(request, response, db)
        self.assertEqual(result["status"], "ok")
        self.assertIsNotNone(record.revoked_at)
        db.commit.assert_awaited_once()
        self.assertIn("__session=", response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        self.assertIn("Secure", response.headers["set-cookie"])

    async def test_session_cookie_never_echoes_google_id_token(self):
        state = "x" * 32
        req = _request(auth.STAGING_HOST, "oauth:staging:" + state)
        user = {"sub": "u1", "email": "u1@example.test", "name": "User"}
        bearer = "c" * 64
        with patch("app.api.auth._complete_login",
                   new=AsyncMock(return_value=("google-id-token-secret", user))), \
             patch("app.api.auth._create_persistent_session",
                   new=AsyncMock(return_value=bearer)), \
             patch("app.api.auth._audit_staging_e2e", new=AsyncMock()):
            callback = await auth.callback("code", state, req, object())
        cookie = callback.headers["set-cookie"]
        self.assertIn("se:staging:" + bearer, cookie)
        self.assertNotIn("google-id-token-secret", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("Max-Age=2592000", cookie)
