import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.models import schemas
from app.models.shopping import ShoppingItem, ShoppingList


class ShoppingContractTests(unittest.TestCase):
    def test_shopping_schema_contract_exists(self):
        for name in (
            "ShoppingListCreate",
            "ShoppingItemCreate",
            "ShoppingItemUpdate",
            "ShoppingItemOut",
            "ShoppingListOut",
        ):
            self.assertTrue(hasattr(schemas, name), name)

    def test_shopping_router_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec("app.api.shopping"))


class ShoppingSchemaBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required = (
            "ShoppingListCreate",
            "ShoppingItemCreate",
            "ShoppingItemUpdate",
            "ShoppingItemOut",
            "ShoppingListOut",
        )
        if not all(hasattr(schemas, name) for name in required):
            raise unittest.SkipTest("Shopping schemas not implemented yet")

    def test_list_and_item_require_names_and_category_is_optional(self):
        with self.assertRaises(ValidationError):
            schemas.ShoppingListCreate()
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemCreate()
        body = schemas.ShoppingItemCreate(name="Milk")
        self.assertIsNone(body.category)

    def test_length_limits_match_database_columns(self):
        with self.assertRaises(ValidationError):
            schemas.ShoppingListCreate(name="x" * 501)
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemCreate(name="x" * 501)
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemCreate(name="Milk", category="x" * 256)

    def test_item_update_accepts_only_is_done_and_rejects_empty_or_null(self):
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemUpdate()
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemUpdate(is_done=None)
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemUpdate(is_done=True, name="Renamed")
        self.assertTrue(schemas.ShoppingItemUpdate(is_done=True).is_done)


@unittest.skipUnless(importlib.util.find_spec("app.api.shopping"), "Shopping router not implemented yet")
class ShoppingRouterBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_list_when_adding_item_returns_404(self):
        from app.api.shopping import create_shopping_item

        db = AsyncMock()
        db.get.return_value = None
        body = schemas.ShoppingItemCreate(name="Milk")
        with self.assertRaises(HTTPException) as ctx:
            await create_shopping_item("missing", body, {"sub": "u"}, db)
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_missing_item_when_toggling_returns_404(self):
        from app.api.shopping import update_shopping_item

        db = AsyncMock()
        db.get.return_value = None
        body = schemas.ShoppingItemUpdate(is_done=True)
        with self.assertRaises(HTTPException) as ctx:
            await update_shopping_item("missing", body, {"sub": "u"}, db)
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_list_response_nests_items_sorted_by_sort_order(self):
        from app.api.shopping import list_shopping_lists

        shopping_list = ShoppingList(id="l1", name="Groceries", project_id=None)
        shopping_list.created_at = datetime.now(timezone.utc)
        item_late = ShoppingItem(
            id="i2", list_id="l1", name="Bananas", category=None, is_done=False, sort_order=2
        )
        item_early = ShoppingItem(
            id="i1", list_id="l1", name="Milk", category=None, is_done=False, sort_order=1
        )

        db = AsyncMock()
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [shopping_list]
        item_result = MagicMock()
        item_result.scalars.return_value.all.return_value = [item_late, item_early]
        db.execute.side_effect = [list_result, item_result]

        result = await list_shopping_lists({"sub": "u"}, db)
        self.assertEqual([item.id for item in result[0].items], ["i1", "i2"])
        item_statement = db.execute.await_args_list[1].args[0]
        self.assertIn("ORDER BY shopping_items.sort_order", str(item_statement))

    async def test_create_list_logs_expected_action_and_returns_empty_items(self):
        from app.api.shopping import create_shopping_list

        db = AsyncMock()
        db.add = MagicMock()
        body = schemas.ShoppingListCreate(name="Groceries")

        async def refresh(obj):
            obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = refresh
        start = AsyncMock(return_value=object())
        finish = AsyncMock()
        with patch("app.api.shopping.start_execution", new=start), patch(
            "app.api.shopping.finish_execution", new=finish
        ), patch("app.api.shopping.fail_execution", new=AsyncMock()):
            result = await create_shopping_list(body, {"sub": "u"}, db)

        self.assertEqual(result.items, [])
        kwargs = start.await_args.kwargs
        self.assertEqual(kwargs["action_type"], "shopping_list.create")
        self.assertEqual(kwargs["provider"], "life_assistant")

    async def test_create_item_and_toggle_use_expected_audit_actions(self):
        from app.api.shopping import create_shopping_item, update_shopping_item

        shopping_list = ShoppingList(id="l1", name="Groceries", project_id=None)
        item = ShoppingItem(
            id="i1", list_id="l1", name="Milk", category=None, is_done=False, sort_order=0
        )
        db = AsyncMock()
        db.add = MagicMock()
        db.get.side_effect = [shopping_list, item]

        async def refresh(obj):
            if isinstance(obj, ShoppingItem):
                if obj.is_done is None:
                    obj.is_done = False
                if obj.sort_order is None:
                    obj.sort_order = 0

        db.refresh.side_effect = refresh
        start = AsyncMock(return_value=object())
        finish = AsyncMock()
        with patch("app.api.shopping.start_execution", new=start), patch(
            "app.api.shopping.finish_execution", new=finish
        ), patch("app.api.shopping.fail_execution", new=AsyncMock()):
            await create_shopping_item(
                "l1", schemas.ShoppingItemCreate(name="Milk"), {"sub": "u"}, db
            )
            await update_shopping_item(
                "i1", schemas.ShoppingItemUpdate(is_done=True), {"sub": "u"}, db
            )

        self.assertEqual(start.await_args_list[0].kwargs["action_type"], "shopping_item.create")
        self.assertEqual(start.await_args_list[1].kwargs["action_type"], "shopping_item.toggle")
        self.assertTrue(item.is_done)
        self.assertEqual(item.name, "Milk")
        self.assertIsNone(item.category)
        self.assertEqual(item.list_id, "l1")

    async def test_create_list_preserves_project_id_without_lookup(self):
        from app.api.shopping import create_shopping_list

        db = AsyncMock()
        db.add = MagicMock()
        body = schemas.ShoppingListCreate(name="Groceries", project_id="project-missing-ok")

        async def refresh(obj):
            obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = refresh
        with patch("app.api.shopping.start_execution", new=AsyncMock(return_value=object())), patch(
            "app.api.shopping.finish_execution", new=AsyncMock()
        ), patch("app.api.shopping.fail_execution", new=AsyncMock()):
            result = await create_shopping_list(body, {"sub": "u"}, db)

        self.assertEqual(result.project_id, "project-missing-ok")
        db.get.assert_not_called()
        added = db.add.call_args.args[0]
        self.assertEqual(added.project_id, "project-missing-ok")

    def test_router_exposes_only_approved_mutations(self):
        from app.api.shopping import router

        paths_methods = {(route.path, tuple(sorted(route.methods or []))) for route in router.routes}
        self.assertIn(("/shopping-lists", ("GET",)), paths_methods)
        self.assertIn(("/shopping-lists", ("POST",)), paths_methods)
        self.assertIn(("/shopping-lists/{list_id}", ("GET",)), paths_methods)
        self.assertIn(("/shopping-lists/{list_id}/items", ("POST",)), paths_methods)
        self.assertIn(("/shopping-items/{item_id}", ("PATCH",)), paths_methods)
        self.assertTrue(all("DELETE" not in methods for _, methods in paths_methods))


class ShoppingMainRegistrationTests(unittest.TestCase):
    def test_main_registers_shopping_router(self):
        path = Path(__file__).parents[1] / "app/main.py"
        source = path.read_text()
        self.assertIn("from app.api.shopping import router as shopping_router", source)
        self.assertIn('app.include_router(shopping_router, prefix="/api/v1")', source)


class ShoppingHttpContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_unauthenticated_shopping_list_returns_401_with_request_id(self):
        if not importlib.util.find_spec("app.api.shopping"):
            self.skipTest("Shopping router not implemented yet")
        import httpx
        from fastapi import FastAPI, Request
        from app.api.shopping import router

        app = FastAPI()

        @app.middleware("http")
        async def request_id_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Request-ID"] = "task4-test"
            return response

        app.include_router(router, prefix="/api/v1")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/shopping-lists")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("X-Request-ID"), "task4-test")


if __name__ == "__main__":
    unittest.main()
