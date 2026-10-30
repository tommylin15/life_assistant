"""Boundary tests use isolated SQLite; actual LINE/Google/Postgres UAT is separate."""
import base64
import hashlib
import hmac
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.api import line, inbox
from app.api.auth import current_user
from app.db.session import Base, get_db
from app.main import app
from app.models.execution_log import ExecutionLog
from app.models.line import LineBinding, LineEvent, LineLinkTicket, LineSession
from app.models.curated import FeatureRollout
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.models.shopping import ShoppingList, ShoppingItem
from app.services import line_channel as channel

ORIGIN = 'https://life.example'
IDENTITY = 'U' + 'a' * 32
ENV = dict(LIFE_LINE_ENABLED='true', LIFE_LINE_NAMESPACE='test', LIFE_LINE_ORIGIN=ORIGIN,
           LIFE_LINE_LIFF_ID='123-test', LIFE_LINE_LOGIN_CHANNEL_ID='123',
           LIFE_LINE_CHANNEL_SECRET='synthetic-test-secret', LIFE_LINE_ACCESS_TOKEN='synthetic-token',
           ALLOWED_GOOGLE_EMAIL='owner@example.test')
USER = {'sub': 'owner-sub', 'email': 'owner@example.test', 'name': 'Owner'}


class TransportTests(unittest.TestCase):
    def test_signature_is_raw_body_bound(self):
        raw = b'{"events":[]}'
        sig = base64.b64encode(hmac.new(b'secret', raw, hashlib.sha256).digest()).decode()
        channel.verify_signature(raw, sig, 'secret')
        with self.assertRaises(HTTPException):
            channel.verify_signature(raw + b' ', sig, 'secret')

    def test_configuration_defaults_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException):
                channel.configuration()

    def test_owner_line_session_has_no_admin_or_drive(self):
        for path in ['/api/v1/admin/feature-rollouts', '/api/v1/drive/files',
                     '/api/v1/integrations/google/gmail/messages', '/api/v1/line/link/confirm',
                     '/api/v1/free-events/curated:connector']:
            self.assertFalse(channel.permitted_line_path(path, 'GET'))
        self.assertTrue(channel.permitted_line_path('/api/v1/tasks', 'GET'))


class LineAPITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, ENV)
        self.env.start()
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda c: Base.metadata.create_all(c, tables=[
                ExecutionLog.__table__, LineBinding.__table__, LineEvent.__table__, LineLinkTicket.__table__, LineSession.__table__,
                __import__("app.models.line_capture", fromlist=["LineCapture"]).LineCapture.__table__,
                FeatureRollout.__table__, Project.__table__, Note.__table__, Task.__table__,
                ShoppingList.__table__, ShoppingItem.__table__]))
        async def db_override():
            async with self.sessions() as session:
                yield session
        app.dependency_overrides[get_db] = db_override
        app.dependency_overrides[current_user] = lambda: dict(USER)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN,
                                       headers={'Origin': ORIGIN})
        self.replies = patch.object(line, 'reply_message', new_callable=AsyncMock)
        self.reply = self.replies.start()

    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        self.replies.stop()
        self.env.stop()
        await self.client.aclose()
        await self.engine.dispose()

    async def send(self, value, event_id='evt1', identity=IDENTITY, source='user', type_='message'):
        raw = json.dumps({'events': [{'type': type_, 'webhookEventId': event_id,
            'timestamp': int(channel.utcnow().timestamp()*1000), 'source': {'type': source, 'userId': identity},
            'replyToken': 'synthetic-reply', 'message': {'type': 'text', 'text': value}}]}).encode()
        sig = base64.b64encode(hmac.new(ENV['LIFE_LINE_CHANNEL_SECRET'].encode(),raw,hashlib.sha256).digest()).decode()
        return await self.client.post('/api/v1/line/webhook', content=raw, headers={'x-line-signature': sig})

    async def bind(self):
        r = await self.client.post('/api/v1/line/link/start', json={})
        self.assertEqual(r.status_code, 200, r.text)
        code = r.json()['code']
        r = await self.send('綁定 '+code, 'link')
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.client.post('/api/v1/line/link/confirm', json={'code':code})
        self.assertEqual(r.status_code, 200, r.text)
        return code

    async def line_login(self):
        with patch.object(line, 'verify_id_token', AsyncMock(return_value=IDENTITY)):
            r=await self.client.post('/api/v1/line/session',json={'id_token':'x'*30})
            self.assertEqual(r.status_code,200,r.text)
        app.dependency_overrides.pop(current_user, None)

    async def test_binding_requires_both_sides_and_rejects_replay(self):
        r=await self.client.post('/api/v1/line/link/start',json={})
        code=r.json()['code']
        self.assertEqual((await self.client.post('/api/v1/line/link/confirm',json={'code':code})).status_code,409)
        await self.send('綁定 '+code,'link')
        self.assertTrue((await self.client.post('/api/v1/line/link/check',json={'code':code})).json()['ready'])
        self.assertEqual((await self.client.post('/api/v1/line/link/confirm',json={'code':code})).status_code,200)
        self.assertEqual((await self.client.post('/api/v1/line/link/confirm',json={'code':code})).status_code,409)

    async def test_group_and_bad_signature_never_capture(self):
        await self.bind()
        self.assertEqual((await self.send('private','group',source='group')).status_code,200)
        r=await self.client.post('/api/v1/line/webhook',content=b'{"events":[]}',headers={'x-line-signature':'bad'})
        self.assertEqual(r.status_code,401)
        async with self.sessions() as db:
            rows=(await db.scalars(select(LineEvent))).all()
            self.assertEqual(len(rows),1) # only binding event

    async def test_redelivery_creates_one_draft(self):
        await self.bind()
        self.assertEqual((await self.send('買牛奶')).status_code,200)
        self.assertEqual((await self.send('買牛奶')).status_code,200)
        r=await self.client.get('/api/v1/line/drafts')
        self.assertEqual(len(r.json()['items']),1)
        self.assertEqual(r.json()['items'][0]['text'],'買牛奶')
        self.assertEqual(self.reply.await_count,2) # link acknowledgment + capture acknowledgment

    async def test_v2_activity_chat_alias_is_not_saved_as_a_draft(self):
        await self.bind()
        with patch('app.services.line_v2.handle_postback',
                   AsyncMock(return_value=[{'type': 'text', 'text': '活動摘要測試'}])) as handler:
            result = await self.send('活動', event_id='v2-activity-chat')
            self.assertEqual(result.status_code, 200, result.text)
            handler.assert_awaited_once()
            self.assertEqual(handler.await_args.args[0]['postback']['data'],
                             'v=2&cmd=events.latest')
        draft_list = await self.client.get('/api/v1/line/drafts')
        self.assertEqual(draft_list.status_code, 200)
        self.assertEqual(draft_list.json()['items'], [])

    async def test_v2_postback_reuses_authenticated_binding_and_event_dedupe(self):
        await self.bind()
        raw = json.dumps({'events': [{'type': 'postback',
            'webhookEventId': 'v2-activity-1',
            'timestamp': int(channel.utcnow().timestamp() * 1000),
            'source': {'type': 'user', 'userId': IDENTITY},
            'replyToken': 'v2-reply',
            'postback': {'data': 'v=2&cmd=events.latest'}}]}).encode()
        signature = base64.b64encode(hmac.new(
            ENV['LIFE_LINE_CHANNEL_SECRET'].encode(), raw, hashlib.sha256).digest()).decode()
        with patch('app.services.line_v2.handle_postback',
                   AsyncMock(return_value=[{'type': 'text', 'text': 'LINE v2 activity fixture'}])) as handler:
            first = await self.client.post('/api/v1/line/webhook', content=raw,
                                           headers={'x-line-signature': signature})
            second = await self.client.post('/api/v1/line/webhook', content=raw,
                                            headers={'x-line-signature': signature})
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(second.status_code, 200, second.text)
            handler.assert_awaited_once()
        async with self.sessions() as db:
            rows = (await db.scalars(select(LineEvent).where(LineEvent.text == ''))).all()
            self.assertEqual(len(rows), 2)  # link + one deduplicated postback
        self.assertEqual(self.reply.await_count, 2)  # link + one postback reply

    async def test_reply_failure_keeps_draft_for_retrieval(self):
        await self.bind()
        self.reply.side_effect=HTTPException(503,'LINE unavailable')
        self.assertEqual((await self.send('記得繳費')).status_code,503)
        r=await self.client.get('/api/v1/line/drafts')
        self.assertEqual(len(r.json()['items']),1)
        self.reply.side_effect=None
        self.assertEqual((await self.send('記得繳費')).status_code,200)
        self.assertEqual(len((await self.client.get('/api/v1/line/drafts')).json()['items']),1)

    async def test_line_identity_uses_binding_and_unlink_revokes_cookie(self):
        await self.bind()
        await self.line_login()
        self.assertEqual((await self.client.get('/auth/me')).status_code,200)
        self.assertEqual((await self.client.get('/api/v1/admin/feature-rollouts')).status_code,403)
        self.assertEqual((await self.client.post('/api/v1/line/link/start',json={})).status_code,403)
        app.dependency_overrides[current_user]=lambda:dict(USER)
        self.assertEqual((await self.client.post('/api/v1/line/link/unlink',json={})).status_code,200)
        app.dependency_overrides.pop(current_user)
        self.assertEqual((await self.client.get('/auth/me')).status_code,401)

    async def test_unfollow_revokes_existing_line_session(self):
        await self.bind()
        await self.line_login()
        await self.send('', 'unfollow', type_='unfollow')
        self.assertEqual((await self.client.get('/auth/me')).status_code,401)

    async def test_mutations_reject_wrong_origin(self):
        r=await self.client.post('/api/v1/line/link/start',json={},headers={'Origin':'https://attacker.test'})
        self.assertEqual(r.status_code,403)
        await self.bind()
        await self.line_login()
        r=await self.client.post('/api/v1/inbox/commit',json={'items':[]},headers={'Origin':'https://attacker.test'})
        self.assertEqual(r.status_code,403)

    async def test_search_is_owner_scoped_and_escapes_like_wildcards(self):
        async with self.sessions() as db:
            db.add_all([Note(id='a',user_sub=USER['sub'],title='water 100%',body='owner'),
                        Note(id='b',user_sub='other',title='water 100%',body='secret'),
                        Note(id='c',user_sub=USER['sub'],title='unrelated',body='other')])
            await db.commit()
        r=await self.client.get('/api/v1/line/search?kind=notes&q=%25')
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual([x['id'] for x in r.json()['items']],['a'])

    async def test_foreign_draft_is_not_accessible(self):
        await self.bind()
        await self.send('我的筆記')
        r=await self.client.get('/api/v1/line/drafts')
        key=r.json()['items'][0]['id']
        app.dependency_overrides[current_user]=lambda:{'sub':'other','email':'other@example.test','name':'Other'}
        async with self.sessions() as db:
            db.add_all([FeatureRollout(feature_key=k,status='enabled',audience='all',revision=1) for k in ['line','life_inbox']])
            await db.commit()
        self.assertEqual((await self.client.get('/api/v1/line/drafts/'+key)).status_code,404)

    async def test_rollout_rechecked_after_login(self):
        await self.bind()
        await self.line_login()
        async with self.sessions() as db:
            db.add(FeatureRollout(feature_key='line',status='hidden',audience='all',revision=1))
            await db.commit()
        self.assertEqual((await self.client.get('/auth/me')).status_code,403)

    async def test_draft_relative_date_uses_original_capture_date(self):
        await self.bind()
        await self.send('明天下午三點去看牙醫')
        key=(await self.client.get('/api/v1/line/drafts')).json()['items'][0]['id']
        r=await self.client.post('/api/v1/inbox/interpret',json={'text':'明天下午三點去看牙醫','line_event_id':key})
        self.assertEqual(r.status_code,200,r.text)
        start=r.json()['candidates'][0]['fields']['start']
        expected=(channel.utcnow().astimezone(__import__('zoneinfo').ZoneInfo('Asia/Taipei'))+timedelta(days=1)).date().isoformat()
        self.assertTrue(start.startswith(expected),start)


class IDTokenTests(unittest.IsolatedAsyncioTestCase):
    async def test_verified_wrong_audience_is_rejected(self):
        response=httpx.Response(200,json={'aud':'wrong','iss':'https://access.line.me','exp':channel.utcnow().timestamp()+100,'sub':IDENTITY},request=httpx.Request('POST','https://api.line.me/oauth2/v2.1/verify'))
        client=AsyncMock();client.__aenter__.return_value=client;client.post.return_value=response
        with patch.dict(os.environ,ENV),patch.object(channel.httpx,'AsyncClient',return_value=client):
            with self.assertRaises(HTTPException):
                await channel.verify_id_token('synthetic',channel.configuration())
