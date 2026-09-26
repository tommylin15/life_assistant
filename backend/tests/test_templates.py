import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.models import schemas
from app.models.template import Template


class TemplatesContractTests(unittest.TestCase):
    def test_template_schema_contract_exists(self):
        for name in ("TemplateCreate", "TemplateUpdate", "TemplateOut"):
            self.assertTrue(hasattr(schemas, name), name)

    def test_templates_router_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec("app.api.templates"))


class TemplatesSchemaBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required = ("TemplateCreate", "TemplateUpdate", "TemplateOut")
        if not all(hasattr(schemas, name) for name in required):
            raise unittest.SkipTest("Template schemas not implemented yet")

    def test_create_requires_name_type_and_payload(self):
        body = schemas.TemplateCreate(name="Morning", template_type="routine", payload_json="opaque")
        self.assertEqual(body.payload_json, "opaque")
        with self.assertRaises(ValidationError):
            schemas.TemplateCreate(template_type="routine", payload_json="opaque")
        with self.assertRaises(ValidationError):
            schemas.TemplateCreate(name="Morning", payload_json="opaque")
        with self.assertRaises(ValidationError):
            schemas.TemplateCreate(name="Morning", template_type="routine")

    def test_update_rejects_empty_patch_and_null_fields(self):
        with self.assertRaises(ValidationError):
            schemas.TemplateUpdate()
        with self.assertRaises(ValidationError):
            schemas.TemplateUpdate(name=None)
        with self.assertRaises(ValidationError):
            schemas.TemplateUpdate(template_type=None)
        with self.assertRaises(ValidationError):
            schemas.TemplateUpdate(payload_json=None)

    def test_payload_is_opaque_and_round_trips_exactly(self):
        payload = '{ "b":2, "a":1 }'
        body = schemas.TemplateCreate(name="X", template_type="opaque", payload_json=payload)
        self.assertEqual(body.payload_json, payload)
        arbitrary = "not-json :: keep me exactly"
        body2 = schemas.TemplateCreate(name="Y", template_type="opaque", payload_json=arbitrary)
        self.assertEqual(body2.payload_json, arbitrary)

    def test_lengths_match_database_contract(self):
        with self.assertRaises(ValidationError):
            schemas.TemplateCreate(name="n" * 501, template_type="x", payload_json="p")
        with self.assertRaises(ValidationError):
            schemas.TemplateCreate(name="n", template_type="t" * 65, payload_json="p")


@unittest.skipUnless(importlib.util.find_spec("app.api.templates"), "Templates router not implemented yet")
class TemplatesRouterBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_template_returns_404(self):
        from app.api.templates import get_template
        db = AsyncMock()
        db.get.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            await get_template("missing", {"sub": "u"}, db)
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_create_preserves_opaque_payload_and_log_excludes_payload(self):
        from app.api.templates import create_template
        payload = '{ "b":2, "a":1 }'
        body = schemas.TemplateCreate(name="Exact", template_type="opaque", payload_json=payload)
        db = AsyncMock()
        db.add = MagicMock()

        async def refresh(obj):
            now = datetime.now(timezone.utc)
            obj.created_at = now
            obj.updated_at = now
        db.refresh.side_effect = refresh
        start = AsyncMock(return_value=object())
        finish = AsyncMock()
        fail = AsyncMock()
        with patch("app.api.templates.start_execution", new=start), \
             patch("app.api.templates.finish_execution", new=finish), \
             patch("app.api.templates.fail_execution", new=fail):
            result = await create_template(body, {"sub": "u"}, db)

        self.assertEqual(result.payload_json, payload)
        kwargs = start.await_args.kwargs
        self.assertEqual(kwargs["action_type"], "template.create")
        self.assertEqual(kwargs["provider"], "life_assistant")
        self.assertIn("Exact", kwargs["summary"])
        self.assertNotIn(payload, kwargs["summary"])
        self.assertNotIn("payload_json", kwargs["summary"])

    async def test_update_preserves_opaque_payload_and_only_changes_requested_field(self):
        from app.api.templates import update_template
        original = Template(id="t1", name="Old", template_type="opaque", payload_json="raw::old")
        payload = "raw::new with spaces  {} []"
        body = schemas.TemplateUpdate(payload_json=payload)
        db = AsyncMock()
        db.get.return_value = original
        async def refresh(obj):
            if obj.updated_at is None:
                obj.updated_at = datetime.now(timezone.utc)
        db.refresh.side_effect = refresh
        start = AsyncMock(return_value=object())
        finish = AsyncMock()
        fail = AsyncMock()
        with patch("app.api.templates.start_execution", new=start), \
             patch("app.api.templates.finish_execution", new=finish), \
             patch("app.api.templates.fail_execution", new=fail):
            result = await update_template("t1", body, {"sub": "u"}, db)

        self.assertEqual(result.payload_json, payload)
        self.assertEqual(result.name, "Old")
        self.assertEqual(result.template_type, "opaque")
        kwargs = start.await_args.kwargs
        self.assertEqual(kwargs["action_type"], "template.update")
        self.assertNotIn(payload, kwargs["summary"])

    def test_router_exposes_only_get_post_patch_no_delete(self):
        from app.api.templates import router
        for route in router.routes:
            methods = route.methods or set()
            self.assertNotIn("DELETE", methods)


class TemplatesMainRegistrationTests(unittest.TestCase):
    def test_main_registers_templates_router(self):
        source = (Path(__file__).parents[1] / "app/main.py").read_text()
        self.assertIn("from app.api.templates import router as templates_router", source)
        self.assertIn('app.include_router(templates_router, prefix="/api/v1")', source)


class TemplatesHttpContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_unauthenticated_templates_returns_401_with_request_id(self):
        if not importlib.util.find_spec("app.api.templates"):
            self.skipTest("Templates router not implemented yet")
        import httpx
        from fastapi import FastAPI, Request
        from app.api.templates import router

        app = FastAPI()
        @app.middleware("http")
        async def request_id_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Request-ID"] = "task5-test"
            return response
        app.include_router(router, prefix="/api/v1")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/templates")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("X-Request-ID"), "task5-test")


if __name__ == "__main__":
    unittest.main()
