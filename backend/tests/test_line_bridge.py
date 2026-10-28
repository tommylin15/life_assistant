"""Security and replay regressions for the opt-in LINE thin adapter.

These are synthetic identities only; no LINE credential or real user data.
"""
import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from starlette.requests import Request

from app.api import line_bridge as line


def signed(body, secret="fake-channel-secret"):
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def request(body, signature):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    return Request({
        "type": "http", "method": "POST", "path": "/api/v1/line/webhook",
        "headers": [(b"x-line-signature", signature.encode())],
    }, receive)


class LineSignatureTests(TestCase):
    def test_signature_requires_exact_raw_bytes(self):
        raw = b'{"events":[]} '
        self.assertTrue(line.valid_webhook_signature(raw, signed(raw), "fake-channel-secret"))
        self.assertFalse(line.valid_webhook_signature(raw.strip(), signed(raw), "fake-channel-secret"))
        self.assertFalse(line.valid_webhook_signature(raw, signed(raw), "other"))
        self.assertFalse(line.valid_webhook_signature(raw, "", "fake-channel-secret"))
        self.assertFalse(line.valid_webhook_signature(raw, signed(raw), ""))

    def test_account_key_uses_explicit_environment(self):
        with patch.dict(os.environ, {"LINE_BRIDGE_ENABLED":"false", "LINE_BRIDGE_AUDIENCE":"production",
                                     "LINE_LOGIN_CHANNEL_ID":"1234"}):
            with self.assertRaises(HTTPException) as ctx:
                line._config()
            self.assertEqual(ctx.exception.status_code, 503)
        with patch.dict(os.environ, {"LINE_BRIDGE_ENABLED":"true", "LINE_BRIDGE_AUDIENCE":"testing",
                                     "LINE_LOGIN_CHANNEL_ID":"1234"}):
            with self.assertRaises(HTTPException):
                line._config()


class LineApiTests(IsolatedAsyncioTestCase):
    def env(self):
        return patch.dict(os.environ, {
            "LINE_BRIDGE_ENABLED":"true", "LINE_BRIDGE_AUDIENCE":"production",
            "LINE_LOGIN_CHANNEL_ID":"1234", "LINE_CHANNEL_SECRET":"fake-channel-secret",
            "LINE_CHANNEL_ACCESS_TOKEN":"",
        })

    async def test_rejects_unsigned_webhook_before_json_parsing(self):
        with self.env():
            db = SimpleNamespace(get=AsyncMock())
            with self.assertRaises(HTTPException) as ctx:
                await line.line_webhook(request(b"not-json", ""), db)
            self.assertEqual(ctx.exception.status_code, 401)
            db.get.assert_not_called()

    async def test_empty_events_verified_without_db(self):
        raw = b'{"destination":"Utest","events":[]}'
        with self.env():
            db = SimpleNamespace(get=AsyncMock())
            self.assertEqual(await line.line_webhook(request(raw, signed(raw)), db),
                             {"ok":True, "created":0})
            db.get.assert_not_called()

    async def test_redelivery_reuses_message_id_without_writing(self):
        uid = "U" + "a"*32
        event = {"events":[{"type":"message","source":{"type":"user","userId":uid},
                            "message":{"id":"m123","type":"text","text":"買牛奶"},
                            "timestamp":1793145600000,"replyToken":"unused"}]}
        raw = json.dumps(event).encode()
        db = SimpleNamespace(get=AsyncMock(return_value=object()), add=MagicMock(),
                             commit=AsyncMock())
        with self.env():
            self.assertEqual((await line.line_webhook(request(raw, signed(raw)), db))["created"],0)
        db.commit.assert_not_awaited()
        db.add.assert_not_called()

    async def test_valid_private_text_is_saved_once_as_draft_not_task(self):
        uid = "U" + "a"*32
        event = {"events":[{"type":"message","source":{"type":"user","userId":uid},
                            "message":{"id":"new-message","type":"text","text":"記得買牛奶"},
                            "timestamp":1793145600000,"replyToken":"unused"}]}
        raw = json.dumps(event).encode()
        account = SimpleNamespace(revoked_at=None, user_sub="owner-sub")
        db = SimpleNamespace(get=AsyncMock(side_effect=[None,account]),
                             add=MagicMock(),commit=AsyncMock())
        with self.env():
            self.assertEqual((await line.line_webhook(request(raw,signed(raw)),db))["created"],1)
        db.add.assert_called_once()
        draft = db.add.call_args.args[0]
        self.assertEqual(type(draft).__name__,"LineCaptureDraft")
        self.assertEqual(draft.user_sub,"owner-sub")
        self.assertEqual(draft.body,"記得買牛奶")
        db.commit.assert_awaited_once()

    async def test_search_requires_bounded_phrase(self):
        with self.env():
            db = SimpleNamespace(execute=AsyncMock())
            with self.assertRaises(HTTPException) as ctx:
                await line.line_search(q="x",authorization="Bearer fake",db=db)
            self.assertEqual(ctx.exception.status_code,422)
            db.execute.assert_not_awaited()

    async def test_group_messages_are_never_stored(self):
        event = {"events":[{"type":"message","source":{"type":"group","userId":"U"+"b"*32},
                            "message":{"id":"group-id","type":"text","text":"private"}}]}
        raw = json.dumps(event).encode()
        db = SimpleNamespace(get=AsyncMock(), commit=AsyncMock())
        with self.env():
            self.assertEqual((await line.line_webhook(request(raw, signed(raw)), db))["created"],0)
        db.get.assert_not_awaited()

    async def test_invalid_line_id_token_is_rejected(self):
        with self.env(), patch("app.api.line_bridge.httpx.AsyncClient") as client:
            client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=SimpleNamespace(status_code=401))
            with self.assertRaises(HTTPException) as ctx:
                await line._verified_line_user("invalid")
            self.assertEqual(ctx.exception.status_code, 401)

    async def test_identity_must_match_line_login_client_and_issuer(self):
        uid = "U" + "c"*32
        valid = {"sub":uid,"aud":"1234","iss":"https://access.line.me",
                 "exp":int(datetime.now(timezone.utc).timestamp())+100}
        with self.env(), patch("app.api.line_bridge.httpx.AsyncClient") as client:
            post = AsyncMock(return_value=SimpleNamespace(status_code=200,json=lambda:valid))
            client.return_value.__aenter__.return_value.post = post
            self.assertEqual(await line._verified_line_user("synthetic-token"),uid)
            valid["aud"] = "wrong"
            with self.assertRaises(HTTPException) as ctx:
                await line._verified_line_user("synthetic-token")
            self.assertEqual(ctx.exception.status_code,401)
            valid["aud"] = "1234"
            valid["iss"] = "https://attacker.example"
            with self.assertRaises(HTTPException):
                await line._verified_line_user("synthetic-token")

    async def test_cross_account_relink_is_blocked(self):
        uid = "U" + "d"*32
        db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(
            revoked_at=None,user_sub="another-sub")),commit=AsyncMock())
        req = Request({"type":"http","method":"POST","path":"/api/v1/line/bind",
                       "headers":[(b"host",b"life.example")]})
        with self.env(), patch("app.api.line_bridge._verified_line_user",new=AsyncMock(return_value=uid)):
            with self.assertRaises(HTTPException) as ctx:
                await line.bind_line(req,line.LineIdentity(id_token="x"*30),
                                    user={"sub":"life-user"},db=db)
            self.assertEqual(ctx.exception.status_code,409)
        db.commit.assert_not_awaited()

    async def test_revoked_account_cannot_read_drafts(self):
        db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(revoked_at=datetime.now(timezone.utc))))
        with self.env(), patch("app.api.line_bridge._verified_line_user",
                               new=AsyncMock(return_value="U"+"e"*32)):
            with self.assertRaises(HTTPException) as ctx:
                await line.line_drafts("Bearer synthetic-token",db)
            self.assertEqual(ctx.exception.status_code,403)

    async def test_google_audience_cannot_cross_stage(self):
        req = Request({"type":"http","headers":[
            (b"host",b"life-assistant-v3-stage-tl15.web.app")]})
        with self.assertRaises(HTTPException) as ctx:
            line._check_google_audience(req,"production")
        self.assertEqual(ctx.exception.status_code,403)
