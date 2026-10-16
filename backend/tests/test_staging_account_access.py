"""Fixed staging tester access without weakening production or Owner policies."""
import hashlib
import httpx
import os
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

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
    return Request({"type": "http", "path": "/auth/me", "headers": headers})


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

    def test_owner_and_general_accounts_are_distinct_privileges(self):
        auth._enforce_account_access(
            {"sub": "owner-sub", "email": "owner@example.test"}, staging=False)
        auth._enforce_account_access(self.tester, staging=True)
        auth._enforce_account_access(self.tester, staging=False)
        auth._enforce_account_access(
            {"sub": "new-sub", "email": "new@example.test"}, staging=False)
        with self.assertRaises(HTTPException) as admin:
            owner_only(self.tester)
        self.assertEqual(admin.exception.status_code, 403)
        for invalid in ({"email": "some@example.test"}, {"sub": "sub-1"}, {}):
            with self.assertRaises(HTTPException) as ctx:
                auth._enforce_account_access(invalid, staging=False)
            self.assertEqual(ctx.exception.status_code, 401)

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
            with self.assertRaises(HTTPException) as missing_provenance:
                await auth.current_user(normal_cookie)
            self.assertEqual(missing_provenance.exception.status_code, 403)

    async def test_fixed_proxy_origin_but_not_spoofed_cloud_run(self):
        with patch("app.api.auth._verify_id_token",
                   new=AsyncMock(return_value=self.tester)):
            proxy = request("life-assistant-api-xyz-uc.a.run.app",
                "id:staging:google-token",
                x_forwarded_host=auth.STAGING_HOST, x_forwarded_proto="https")
            self.assertEqual((await auth.current_user(proxy))["sub"], "tester-sub")
            comma_proto = request("life-assistant-api-xyz-uc.a.run.app",
                "id:staging:google-token",
                x_forwarded_host=auth.STAGING_HOST, x_forwarded_proto="http,https")
            self.assertEqual((await auth.current_user(comma_proto))["sub"], "tester-sub")
            spoof = request("attacker-xyz.a.run.app", "id:staging:google-token",
                            x_forwarded_host=auth.STAGING_HOST, x_forwarded_proto="https")
            with self.assertRaises(HTTPException):
                await auth.current_user(spoof)

    async def test_browser_staging_session_without_forwarded_host(self):
        """Firebase Hosting may omit X-Forwarded-Host after OAuth callback."""
        with patch("app.api.auth._verify_id_token",
                   new=AsyncMock(return_value=self.tester)):
            proxy = request("life-assistant-api-xyz-uc.a.run.app",
                "id:staging:google-token",
                x_forwarded_proto="https",
                referer="https://" + auth.STAGING_HOST + "/today",
                sec_fetch_site="same-origin")
            self.assertEqual((await auth.current_user(proxy))["sub"], "tester-sub")

            for extra in (
                {"referer": "https://gen-lang-client-0593591102.web.app/today"},
                {"referer": "https://evil.example/today"},
                {"referer": "http://" + auth.STAGING_HOST + "/today"},
                {"referer": "https://" + auth.STAGING_HOST + ".evil.example/"},
                {"referer": "https://" + auth.STAGING_HOST + "/",
                 "sec_fetch_site": "cross-site"},
                {"referer": "https://" + auth.STAGING_HOST + "/",
                 "x_forwarded_host": "gen-lang-client-0593591102.web.app"},
                {},
            ):
                with self.subTest(extra=extra):
                    req = request("life-assistant-api-xyz-uc.a.run.app",
                        "id:staging:google-token", x_forwarded_proto="https", **extra)
                    with self.assertRaises(HTTPException) as blocked:
                        await auth.current_user(req)
                    self.assertEqual(blocked.exception.status_code, 403)

    async def test_staging_session_invalid_for_external_cloud_run_and_prod_host(self):
        with patch("app.api.auth._verify_id_token",
                   new=AsyncMock(return_value=self.tester)):
            for host in ("attacker-xyz-uc.a.run.app",
                         "gen-lang-client-0593591102.web.app"):
                req = request(host, "id:staging:google-token",
                    referer="https://" + auth.STAGING_HOST + "/")
                with self.assertRaises(HTTPException):
                    await auth.current_user(req)

    async def test_firebase_pin_tag_host_accepts_real_staging_cookie(self):
        # The exact Cloud Run candidate hostname was observed in GitHub
        # Staging release #38240040197. Firebase may omit Forwarded-Host,
        # Referer and Origin when rewriting /auth/me.
        tagged = "v3-664a32cfc9---life-assistant-api-2oo7qbkd5q-uc.a.run.app"
        with patch("app.api.auth._verify_id_token",
                   new=AsyncMock(return_value=self.tester)):
            authorized = request(tagged, "id:staging:signed-google-token",
                                 x_forwarded_proto="https")
            self.assertEqual((await auth.current_user(authorized))["sub"], "tester-sub")
            forwarded = request(tagged, "id:staging:signed-google-token",
                                x_forwarded_proto="https",
                                x_forwarded_host=auth.STAGING_HOST)
            self.assertEqual((await auth.current_user(forwarded))["sub"], "tester-sub")

            forbidden = (
                request("life-assistant-api-2oo7qbkd5q-uc.a.run.app",
                        "id:staging:signed-google-token", x_forwarded_proto="https"),
                request("v3-untrusted---life-assistant-api-2oo7qbkd5q-uc.a.run.app",
                        "id:staging:signed-google-token", x_forwarded_proto="https"),
                request(tagged, "id:staging:signed-google-token",
                        x_forwarded_proto="http"),
                request(tagged, "id:staging:signed-google-token",
                        x_forwarded_proto="https",
                        x_forwarded_host="gen-lang-client-0593591102.web.app"),
                request(tagged, "id:signed-google-token",
                        x_forwarded_proto="https"),
            )
            for item in forbidden:
                with self.subTest(host=item.headers["host"],
                                  forwarded=item.headers.get("x-forwarded-host")):
                    with self.assertRaises(HTTPException) as denied:
                        await auth.current_user(item)
                    self.assertEqual(denied.exception.status_code, 403)

    async def test_verified_staging_callback_accepts_tester_not_admin(self):
        state = "z" * 32
        req = request(auth.STAGING_HOST, "oauth:staging:" + state)
        with patch("app.api.auth._complete_login",
                   new=AsyncMock(return_value=("signed-id-token", self.tester))) as complete, \
             patch("app.api.auth._audit_staging_e2e", new_callable=AsyncMock), \
             patch("app.api.auth._create_persistent_session",
                   new=AsyncMock(return_value="s" * 64)):
            response = await auth.callback("google-code", state, req, object())
        complete.assert_awaited_once_with("google-code", auth.STAGING_REDIRECT_URI)
        self.assertEqual(response.headers["location"], "https://" + auth.STAGING_HOST + "/")
        self.assertIn("se:staging:" + "s" * 64, response.headers["set-cookie"])
        with self.assertRaises(HTTPException):
            owner_only(self.tester)

    async def test_normal_production_callback_accepts_general_user_not_admin(self):
        state = "y" * 32
        req = request("gen-lang-client-0593591102.web.app", "oauth:" + state)
        with patch("app.api.auth._complete_login",
                   new=AsyncMock(return_value=("signed-id-token", self.tester))), \
             patch("app.api.auth._create_persistent_session",
                   new=AsyncMock(return_value="s" * 64)):
            response = await auth.callback("google-code", state, req, object())
        self.assertIn("se:production:" + "s" * 64, response.headers["set-cookie"])
        self.assertNotIn("se:staging:", response.headers["set-cookie"])
        with self.assertRaises(HTTPException):
            owner_only(self.tester)

    async def test_logout_deletes_auth_cookie(self):
        response = Response()
        result = await auth.logout(request(auth.STAGING_HOST), response, object())
        self.assertEqual(result, {"status": "ok"})
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("__session=", cookie)
        self.assertIn("max-age=0", cookie)

    async def test_login_requests_google_account_chooser(self):
        with patch.object(auth.settings, "google_client_id", "client-id"):
            response = await auth.staging_login(request(auth.STAGING_HOST))
        self.assertIn("select_account", response.headers["location"])

    async def test_staging_tester_denied_unisolated_private_apis(self):
        with patch("app.api.auth._verify_id_token",
                   new=AsyncMock(return_value=self.tester)):
            for uri in ("/api/v1/drive/documents", "/api/v1/admin/feature-rollouts",
                        "/api/v1/templates", "/api/v1/drive/documents/some-id",
                        "/api/v1/free-events/curated/status",
                        "/api/v1/free-events/curated:connector",
                        "/api/v1/free-events/curated:batch",
                        "/api/v1/free-events/curated/" + "a" * 64 + "/actions/follow"):
                req = request(auth.STAGING_HOST, "id:staging:google-token")
                req.scope["path"] = uri
                with self.subTest(uri=uri):
                    with self.assertRaises(HTTPException) as denied:
                        await auth.current_user(req)
                    self.assertEqual(denied.exception.status_code, 403)

    async def test_staging_tester_can_reach_safe_task_and_preference_routes(self):
        with patch("app.api.auth._verify_id_token",
                   new=AsyncMock(return_value=self.tester)):
            for uri in ("/api/v1/ui/features", "/api/v1/me/ui-preferences",
                        "/api/v1/tasks", "/api/v1/tasks/example-id",
                        "/api/v1/integrations/google/status",
                        "/api/v1/integrations/google/calendar",
                        "/api/v1/notes", "/api/v1/notes/owned-id", "/api/v1/projects",
                        "/api/v1/projects/owned-id", "/api/v1/habits",
                        "/api/v1/shopping-lists", "/api/v1/shopping-items/item-id",
                        "/api/v1/free-events/curated",
                        "/api/v1/free-events/curated/filters",
                        "/api/v1/free-events/curated/actions",
                        "/api/v1/free-events/curated/" + "a" * 64 + "/actions/save",
                        "/api/v1/free-events/curated/" + "a" * 64 + "/actions/task",
                        "/api/v1/free-events/curated/" + "a" * 64 + "/actions/calendar_info"):
                req = request(auth.STAGING_HOST, "id:staging:google-token")
                req.scope["path"] = uri
                self.assertEqual((await auth.current_user(req))["sub"], "tester-sub")

    def test_allowed_activity_urls_are_real_registered_fastapi_routes(self):
        from app.api.curated import router as curated_router
        from app.api.curated_actions import router as actions_router
        # Source routers are not mutated by other app-mounting test fixtures.
        paths = {
            "/api/v1" + route.path
            for router in (curated_router, actions_router)
            for route in router.routes
            if hasattr(route, "path")
        }
        for path in (
            "/api/v1/free-events/curated",
            "/api/v1/free-events/curated/filters",
            "/api/v1/free-events/curated/actions",
            "/api/v1/free-events/curated/{activity_id}/actions/{kind}",
        ):
            self.assertIn(path, paths)

    async def test_secondary_user_cannot_read_null_owner_tasks(self):
        from app.api.tasks import _require_task, list_tasks
        from app.models.task import Task
        from unittest.mock import MagicMock
        legacy = SimpleNamespace(user_sub=None, deleted_at=None)
        db = SimpleNamespace(get=AsyncMock(return_value=legacy))
        with self.assertRaises(HTTPException) as denied:
            await _require_task(db, "old-owner-id", self.tester)
        self.assertEqual(denied.exception.status_code, 404)
        owned = SimpleNamespace(user_sub="tester-sub", deleted_at=None)
        db.get = AsyncMock(return_value=owned)
        self.assertIs(await _require_task(db, "test-task", self.tester), owned)

        result = MagicMock()
        result.scalars.return_value.all.return_value = [owned]
        db.execute = AsyncMock(return_value=result)
        rows = await list_tasks(user=self.tester, db=db)
        self.assertEqual(rows, [owned])
        query = str(db.execute.await_args.args[0])
        self.assertIn("tasks.user_sub", query)
        self.assertNotIn("tasks.user_sub IS NULL", query)

    async def test_null_legacy_tasks_require_configured_owner_not_just_non_tester(self):
        from app.api.tasks import _require_task, list_tasks
        from unittest.mock import MagicMock
        legacy = SimpleNamespace(user_sub=None, deleted_at=None)
        user = {"sub": "another-sub", "email": "another@example.test"}
        db = SimpleNamespace(get=AsyncMock(return_value=legacy))
        with patch.dict(os.environ, {"ALLOWED_GOOGLE_EMAIL": ""}):
            with self.assertRaises(HTTPException) as blocked:
                await _require_task(db, "legacy", user)
            self.assertEqual(blocked.exception.status_code, 404)
            db.execute = AsyncMock(return_value=MagicMock())
            await list_tasks(user=user, db=db)
            self.assertNotIn("tasks.user_sub IS NULL", str(db.execute.await_args.args[0]))
        owner = {"sub": "owner-sub", "email": "owner@example.test"}
        self.assertIs(await _require_task(db, "legacy", owner), legacy)
        await list_tasks(user=owner, db=db)
        self.assertIn("tasks.user_sub IS NULL", str(db.execute.await_args.args[0]))

    async def test_test_user_cannot_attach_owner_project_to_new_task(self):
        from app.api.tasks import create_task
        from app.models.schemas import TaskCreate
        with self.assertRaises(HTTPException) as ctx:
            await create_task(
                TaskCreate(title="Demo", project_id="owner-project"),
                user=self.tester,
                db=SimpleNamespace(get=AsyncMock(return_value=None)),
            )
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_production_general_account_can_use_audited_routes_not_admin(self):
        user = {"sub": "new-prod-sub", "email": "new-prod@example.test"}
        prod_host = "gen-lang-client-0593591102.web.app"
        with patch("app.api.auth._verify_id_token", new=AsyncMock(return_value=user)):
            for path in (
                "/auth/me", "/api/v1/ui/features", "/api/v1/me/ui-preferences",
                "/api/v1/tasks", "/api/v1/projects", "/api/v1/notes",
                "/api/v1/habits", "/api/v1/shopping-lists",
                "/api/v1/free-events/curated",
                "/api/v1/free-events/curated/filters",
                "/api/v1/free-events/curated/actions", "/api/v1/activity",
                "/api/v1/integrations/google/status",
                "/api/v1/free-events/curated/" + "a" * 64 + "/actions/save",
            ):
                req = request(prod_host, "id:verified-google-token")
                req.scope["path"] = path
                self.assertEqual((await auth.current_user(req))["sub"], "new-prod-sub", path)
            for path in (
                "/api/v1/admin/feature-rollouts",
                "/api/v1/drive/documents",
                "/api/v1/templates",
                "/api/v1/free-events/curated/status",
                "/api/v1/free-events/curated:batch",
                "/api/v1/free-events/curated:connector",
                "/api/v1/free-events/curated/" + "a" * 64 + "/actions/follow",
            ):
                req = request(prod_host, "id:verified-google-token")
                req.scope["path"] = path
                with self.assertRaises(HTTPException) as denied:
                    await auth.current_user(req)
                self.assertEqual(denied.exception.status_code, 403, path)
        with self.assertRaises(HTTPException):
            owner_only(user)

    async def test_google_token_validity_and_account_policy_are_separate(self):
        from app.services import google_identity
        token_info = {
            "aud": "test-google-client", "iss": "accounts.google.com",
            "email_verified": "true", "exp": 9999999999,
            "sub": "tester-sub", "email": "tester@example.test",
            "name": "Tester",
        }
        with patch.object(google_identity.settings, "google_client_id", "test-google-client"), \
             patch("app.services.google_identity.httpx.AsyncClient") as client:
            client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=httpx.Response(200, json=token_info))
            verified = await google_identity.verify_google_id_token("signed-id-token")
        self.assertEqual(verified["sub"], "tester-sub")
        auth._enforce_account_access(verified, staging=False)
        auth._enforce_account_access(verified, staging=True)
        with self.assertRaises(HTTPException):
            owner_only(verified)
