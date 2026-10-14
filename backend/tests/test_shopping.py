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
            "ShoppingListUpdate",
            "ShoppingItemsBatchCreate",
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
            "ShoppingListUpdate",
            "ShoppingItemsBatchCreate",
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

    def test_item_update_accepts_edit_and_toggle_with_validation(self):
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemUpdate()
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemUpdate(is_done=None)
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemUpdate(name=" ")
        with self.assertRaises(ValidationError):
            schemas.ShoppingListUpdate(name=None)
        self.assertTrue(schemas.ShoppingItemUpdate(is_done=True).is_done)
        self.assertEqual(schemas.ShoppingItemUpdate(name=" Renamed ").name, "Renamed")
        self.assertIsNone(schemas.ShoppingItemUpdate(category="  ").category)
        self.assertEqual(schemas.ShoppingListUpdate(name=" Travel ").name, "Travel")

    def test_batch_limits_and_blank_names(self):
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemsBatchCreate(items=[])
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemsBatchCreate(items=[schemas.ShoppingItemCreate(name="x")] * 51)
        with self.assertRaises(ValidationError):
            schemas.ShoppingItemCreate(name=" ")
        self.assertEqual(
            len(schemas.ShoppingItemsBatchCreate(items=[
                schemas.ShoppingItemCreate(name="Milk")] * 50).items), 50,
        )


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

        shopping_list = ShoppingList(id="l1", name="Groceries", project_id=None, user_sub="u")
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

        shopping_list = ShoppingList(id="l1", name="Groceries", project_id=None, user_sub="u")
        item = ShoppingItem(
            id="i1", list_id="l1", name="Milk", category=None, is_done=False, sort_order=0
        )
        db = AsyncMock()
        db.add = MagicMock()
        db.get.side_effect = [shopping_list, item, shopping_list]

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

    async def test_list_and_item_edits_are_separate_actions(self):
        from app.api.shopping import update_shopping_list, update_shopping_item

        shopping_list = ShoppingList(id="l1", name="Groceries", project_id=None, user_sub="u")
        shopping_list.created_at = datetime.now(timezone.utc)
        item = ShoppingItem(id="i1", list_id="l1", name="Milk", category=None,
                            is_done=False, sort_order=0)
        db = AsyncMock()
        db.get.side_effect = [shopping_list, item, shopping_list]
        result = MagicMock()
        result.scalars.return_value.all.return_value = [item]
        db.execute.return_value = result
        start = AsyncMock(return_value=object())
        with patch("app.api.shopping.start_execution", new=start), patch(
            "app.api.shopping.finish_execution", new=AsyncMock()
        ):
            edited_list = await update_shopping_list(
                "l1", schemas.ShoppingListUpdate(name="Travel"), {"sub": "u"}, db
            )
            edited_item = await update_shopping_item(
                "i1", schemas.ShoppingItemUpdate(name="Oat milk", category=None),
                {"sub": "u"}, db
            )
        self.assertEqual(edited_list.name, "Travel")
        self.assertEqual(edited_item.name, "Oat milk")
        self.assertIsNone(edited_item.category)
        self.assertEqual(start.await_args_list[0].kwargs["action_type"], "shopping_list.update")
        self.assertEqual(start.await_args_list[1].kwargs["action_type"], "shopping_item.update")

    async def test_batch_insert_has_one_write_commit_and_stable_order(self):
        from app.api.shopping import create_shopping_items_batch

        db = AsyncMock()
        db.get.return_value = ShoppingList(id="l1", name="Groceries", user_sub="u")
        db.add_all = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = 5
        db.execute.return_value = result
        with patch("app.api.shopping.start_execution", new=AsyncMock(return_value=object())), patch(
            "app.api.shopping.finish_execution", new=AsyncMock()
        ):
            items = await create_shopping_items_batch(
                "l1", schemas.ShoppingItemsBatchCreate(items=[
                    schemas.ShoppingItemCreate(name="Eggs"),
                    schemas.ShoppingItemCreate(name="Tea", category="Drinks"),
                ]), {"sub": "u"}, db
            )
        self.assertEqual([item.name for item in items], ["Eggs", "Tea"])
        self.assertEqual([item.sort_order for item in items], [6, 7])
        self.assertEqual(db.commit.await_count, 1)
        db.add_all.assert_called_once()

    async def test_item_delete_does_not_delete_list_and_list_delete_cascades_explicitly(self):
        from app.api.shopping import delete_shopping_item, delete_shopping_list

        db = AsyncMock()
        shopping_list = ShoppingList(id="l1", name="Groceries", user_sub="u")
        item = ShoppingItem(id="i1", list_id="l1", name="Milk", is_done=False, sort_order=0)
        db.get.side_effect = [item, shopping_list, shopping_list]
        order = []
        async def execute(*args, **kwargs):
            order.append("delete_children")
            return MagicMock()
        async def remove(*args, **kwargs):
            order.append("delete_entity")
        db.execute.side_effect = execute
        db.delete.side_effect = remove
        with patch("app.api.shopping.start_execution", new=AsyncMock(return_value=object())), patch(
            "app.api.shopping.finish_execution", new=AsyncMock()
        ):
            await delete_shopping_item("i1", {"sub": "u"}, db)
            self.assertEqual(order, ["delete_entity"])
            await delete_shopping_list("l1", {"sub": "u"}, db)
        self.assertEqual(order, ["delete_entity", "delete_children", "delete_entity"])
        self.assertEqual(db.commit.await_count, 2)

    async def test_cross_user_edits_batch_and_deletes_return_404(self):
        from app.api.shopping import (
            update_shopping_list, update_shopping_item, create_shopping_items_batch,
            delete_shopping_list, delete_shopping_item,
        )

        foreign_list = ShoppingList(id="l1", name="Other", user_sub="another")
        foreign_item = ShoppingItem(id="i1", list_id="l1", name="Milk", is_done=False)
        db = AsyncMock()
        db.get.side_effect = [
            foreign_list, foreign_item, foreign_list, foreign_list,
            foreign_list, foreign_item, foreign_list,
        ]
        with patch("app.api.shopping.start_execution", new=AsyncMock()) as audit:
            checks = [
                update_shopping_list("l1", schemas.ShoppingListUpdate(name="No"), {"sub": "u"}, db),
                update_shopping_item("i1", schemas.ShoppingItemUpdate(name="No"), {"sub": "u"}, db),
                create_shopping_items_batch(
                    "l1", schemas.ShoppingItemsBatchCreate(items=[
                        schemas.ShoppingItemCreate(name="No"),
                    ]), {"sub": "u"}, db,
                ),
                delete_shopping_list("l1", {"sub": "u"}, db),
                delete_shopping_item("i1", {"sub": "u"}, db),
            ]
            for coroutine in checks:
                with self.assertRaises(HTTPException) as ctx:
                    await coroutine
                self.assertEqual(ctx.exception.status_code, 404)
        audit.assert_not_awaited()
        db.commit.assert_not_awaited()

    async def test_create_list_rejects_missing_cross_account_project(self):
        from app.api.shopping import create_shopping_list

        db = AsyncMock()
        db.add = MagicMock()
        body = schemas.ShoppingListCreate(name="Groceries", project_id="project-missing-ok")

        async def refresh(obj):
            obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = refresh
        db.get.return_value = None
        with patch("app.api.shopping.start_execution", new=AsyncMock()) as audit:
            with self.assertRaises(HTTPException) as ctx:
                await create_shopping_list(body, {"sub": "u"}, db)
        self.assertEqual(ctx.exception.status_code, 404)
        audit.assert_not_awaited()
        db.add.assert_not_called()

    def test_router_exposes_distinct_list_item_and_batch_mutations(self):
        from app.api.shopping import router

        paths_methods = {(route.path, tuple(sorted(route.methods or []))) for route in router.routes}
        for path, method in (
            ("/shopping-lists", "GET"),
            ("/shopping-lists", "POST"),
            ("/shopping-lists/{list_id}", "GET"),
            ("/shopping-lists/{list_id}", "PATCH"),
            ("/shopping-lists/{list_id}", "DELETE"),
            ("/shopping-lists/{list_id}/items", "POST"),
            ("/shopping-lists/{list_id}/items/batch", "POST"),
            ("/shopping-items/{item_id}", "PATCH"),
            ("/shopping-items/{item_id}", "DELETE"),
        ):
            self.assertIn((path, (method,)), paths_methods)


class ShoppingMainRegistrationTests(unittest.TestCase):
    def test_main_registers_shopping_router(self):
        path = Path(__file__).parents[1] / "app/main.py"
        source = path.read_text()
        self.assertIn("from app.api.shopping import router as shopping_router", source)
        self.assertIn('app.include_router(shopping_router, prefix="/api/v1", dependencies=[Depends(CORE_FEATURE_GATES["shopping"])])', source)


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
