"""Real HTTPS + Google identity + PostgreSQL acceptance, with exact-ID cleanup.

No dependency overrides or ASGI transport. Refresh credentials stay in memory
inside the existing VPC-capable acceptance job; never export session cookies.
"""
import asyncio
import os
import subprocess
import sys
import uuid
from urllib.parse import urlparse

import httpx
from sqlalchemy import delete, select

from app.config import settings
from app.db.session import SessionLocal
from app.models.google_integration import GoogleConnection
from app.models.task import Task
from app.models.execution_log import ExecutionLog
from app.services.google_identity import verify_google_id_token
from app.services.google_oauth import decrypt_token, GOOGLE_TOKEN_URL


async def live_browser(base, token):
    # ponytail: install browser only in acceptance executions; bake a dedicated
    # runner image only if measured repeated downloads outweigh its storage cost.
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'playwright==1.55.0'], check=True)
    subprocess.run([sys.executable, '-m', 'playwright', 'install', '--with-deps', 'chromium'], check=True)
    from playwright.async_api import async_playwright
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(args=['--no-sandbox'])
        try:
            for width, height in ((1440, 1100), (390, 844)):
                context = await browser.new_context(viewport={'width': width, 'height': height})
                await context.add_cookies([{'name': '__session', 'value': 'id:' + token,
                    'url': base, 'secure': True, 'httpOnly': True, 'sameSite': 'Lax'}])
                page = await context.new_page()
                for path, api in (('/tasks', '/tasks'), ('/projects', '/projects'),
                                  ('/more/notes', '/notes'), ('/more/habits', '/habits'),
                                  ('/more/shopping', '/shopping-lists'),
                                  ('/calendar', '/integrations/google/calendar/events'),
                                  ('/more/drive', '/drive/documents')):
                    # Observe actual network. Never page.route / route.fulfill.
                    async with page.expect_response(lambda r: '/api/v1' + api in r.url,
                                                    timeout=60000) as pending:
                        await page.goto(base + path, wait_until='domcontentloaded')
                    response = await pending.value
                    assert response.status == 200, 'real UI API request failed'
                    await page.wait_for_selector('flutter-view', timeout=60000)
                    placeholder = page.locator('flt-semantics-placeholder')
                    if await placeholder.count():
                        await placeholder.first.evaluate('(el) => el.click()')
                    assert await page.locator('flutter-view').is_visible()
                    print(f'live_ui_read={path}:PASS viewport={width}', flush=True)
                await context.close()
        finally:
            await browser.close()


def allowed_url(value):
    parsed = urlparse(value)
    host = parsed.hostname or ''
    return parsed.scheme == 'https' and not parsed.username and not parsed.password and (
        host == 'gen-lang-client-0593591102.web.app'
        or host.startswith('gen-lang-client-0593591102--') and host.endswith('.web.app')
        or host.startswith(('life-assistant-api-', 'v2-candidate---life-assistant-api-'))
        and host.endswith('-2oo7qbkd5q-uc.a.run.app'))


async def main():
    base = os.environ['ACCEPTANCE_BASE_URL'].rstrip('/')
    assert allowed_url(base), 'unapproved acceptance origin'
    owner = os.environ['DRIVE_ACCEPTANCE_USER_SUB']
    async with SessionLocal() as db:
        connection = await db.get(GoogleConnection, owner)
        assert connection is not None, 'explicit owner fixture missing'
        refresh = decrypt_token(connection.encrypted_refresh_token)
    assert refresh, 'reauthorization required for real identity gate'
    task_id = None
    title = '[ACCEPTANCE TEST] CI/CD V2 ' + str(uuid.uuid4())
    async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data={
            'client_id': settings.google_client_id,
            'client_secret': settings.google_client_secret,
            'refresh_token': refresh, 'grant_type': 'refresh_token'})
        assert response.status_code == 200, 'Google refresh failed; reauthorization required'
        token = response.json().get('id_token')
        claims = await verify_google_id_token(token)
        assert claims['sub'] == owner, 'OAuth fixture owner mismatch'
        assert claims['email'] == os.environ['ACCEPTANCE_OWNER_EMAIL'], 'owner email mismatch'
        client.cookies.set('__session', 'id:' + token)
        try:
            response = await client.get(base + '/auth/me')
            assert response.status_code == 200, 'real signed session rejected'
            print('live_signed_google_identity=PASS', flush=True)
            for path in ('tasks', 'projects', 'notes', 'habits', 'shopping-lists', 'activity',
                         'integrations/google/status', 'integrations/google/calendar/events',
                         'integrations/google/gmail/messages', 'drive/documents', 'drive/picker-config'):
                response = await client.get(base + '/api/v1/' + path)
                assert response.status_code == 200, 'live read failed: ' + path + ' status=' + str(response.status_code)
                print('live_read=' + path + ':PASS', flush=True)
            response = await client.post(base + '/api/v1/tasks', json={'title': title})
            assert response.status_code == 201, 'live Task create failed'
            task_id = response.json()['id']
            async with SessionLocal() as db:
                task = await db.get(Task, task_id)
                assert task and task.title == title, 'real PostgreSQL persistence failed'
                event = await db.scalar(select(ExecutionLog).where(
                    ExecutionLog.entity_id == task_id, ExecutionLog.user_sub == owner))
                assert event, 'owner-bound execution evidence missing'
            response = await client.post(base + '/api/v1/tasks/' + task_id + '/complete')
            assert response.status_code == 200 and response.json()['status'] == 'completed'
            print('live_task_postgres_execution=PASS', flush=True)
            if urlparse(base).hostname.endswith('.web.app'):
                await live_browser(base, token)
            client.cookies.set('__session', 'id:invalid-token')
            response = await client.get(base + '/api/v1/tasks')
            assert response.status_code == 401, 'invalid identity was accepted'
            print('live_invalid_identity_denied=PASS', flush=True)
        finally:
            if task_id:
                async with SessionLocal() as db:
                    # ID + unique title protects real rows even after a failed request.
                    await db.execute(delete(Task).where(Task.id == task_id, Task.title == title))
                    await db.commit()
                print('live_fixture_exact_cleanup=PASS', flush=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as exc:
        # Never stringify exceptions containing HTTP request credentials.
        print('live_release_acceptance=FAIL category=' + type(exc).__name__, flush=True)
        sys.exit(1)
