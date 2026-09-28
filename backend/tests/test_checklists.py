import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.models import schemas
from app.models.migration_support import ChecklistItem
from app.models.task import Task


class ChecklistSchemaTests(unittest.TestCase):
    def test_checklist_schema_contract_exists(self):
        for name in ("ChecklistItemCreate", "ChecklistItemUpdate", "ChecklistItemOut"):
            self.assertTrue(hasattr(schemas, name), name)

    def test_create_requires_nonempty_title_and_nonnegative_sort_order(self):
        with self.assertRaises(ValidationError):
            schemas.ChecklistItemCreate(title="")
        with self.assertRaises(ValidationError):
            schemas.ChecklistItemCreate(title="Item", sort_order=-1)
        body = schemas.ChecklistItemCreate(title="Item")
        self.assertIsNone(body.sort_order)

    def test_update_requires_non_null_known_change(self):
        with self.assertRaises(ValidationError):
            schemas.ChecklistItemUpdate()
        with self.assertRaises(ValidationError):
            schemas.ChecklistItemUpdate(is_done=None)
        with self.assertRaises(ValidationError):
            schemas.ChecklistItemUpdate(title=None)
        with self.assertRaises(ValidationError):
            schemas.ChecklistItemUpdate(title="Item", unknown=True)
        self.assertTrue(schemas.ChecklistItemUpdate(is_done=True).is_done)


class ChecklistRouterTests(unittest.IsolatedAsyncioTestCase):
    def _task(self, task_id: str = "task-1") -> Task:
        task = Task(id=task_id, title="Task")
        task.deleted_at = None
        return task

    def _item(
        self,
        item_id: str = "item-1",
        task_id: str = "task-1",
        *,
        sort_order: int = 0,
    ) -> ChecklistItem:
        return ChecklistItem(
            id=item_id,
            task_id=task_id,
            title="Item",
            is_done=False,
            sort_order=sort_order,
            created_at=datetime.now(timezone.utc),
        )

    def test_router_exposes_nested_checklist_contract(self):
        from app.api.tasks import router

        paths_methods = {(route.path, tuple(sorted(route.methods or []))) for route in router.routes}
        self.assertIn(("/tasks/{task_id}/checklist", ("GET",)), paths_methods)
        self.assertIn(("/tasks/{task_id}/checklist", ("POST",)), paths_methods)
        self.assertIn(("/tasks/{task_id}/checklist/{item_id}", ("PATCH",)), paths_methods)
        self.assertIn(("/tasks/{task_id}/checklist/{item_id}", ("DELETE",)), paths_methods)

    async def test_list_requires_existing_task_and_uses_stable_order(self):
        from app.api.tasks import list_checklist_items

        db = AsyncMock()
        db.get.return_value = self._task()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [
            self._item("item-1", sort_order=1),
            self._item("item-2", sort_order=2),
        ]
        db.execute.return_value = result

        items = await list_checklist_items("task-1", {"sub": "u"}, db)
        self.assertEqual([item.id for item in items], ["item-1", "item-2"])
        statement = str(db.execute.await_args.args[0])
        self.assertIn("ORDER BY checklist_items.sort_order ASC", statement)
        self.assertIn("checklist_items.created_at ASC", statement)
        self.assertIn("checklist_items.id ASC", statement)

    async def test_create_binds_action_id_to_task_and_payload(self):
        from app.api.tasks import create_checklist_item

        db = AsyncMock()
        db.add = MagicMock()
        db.get.return_value = self._task()
        reservation = SimpleNamespace(is_replay=False)
        reserve = AsyncMock(return_value=reservation)
        commit = AsyncMock()

        with patch("app.api.tasks.reserve_execution", new=reserve), patch(
            "app.api.tasks.commit_reserved_execution", new=commit
        ):
            item = await create_checklist_item(
                "task-1",
                schemas.ChecklistItemCreate(title="First", sort_order=3),
                {"sub": "user-1"},
                db,
                "checklist-action-1",
            )

        self.assertEqual(item.task_id, "task-1")
        self.assertEqual(item.title, "First")
        self.assertEqual(item.sort_order, 3)
        kwargs = reserve.await_args.kwargs
        self.assertEqual(kwargs["action_type"], "checklist_item.create")
        self.assertEqual(kwargs["action_id"], "checklist-action-1")
        self.assertEqual(
            kwargs["request_payload"],
            {"task_id": "task-1", "title": "First", "sort_order": 3},
        )
        self.assertEqual(commit.await_args.kwargs["entity_type"], "checklist_item")

    async def test_create_without_sort_order_appends_after_current_max(self):
        from app.api.tasks import create_checklist_item

        db = AsyncMock()
        db.add = MagicMock()
        db.get.return_value = self._task()
        max_result = MagicMock()
        max_result.scalar_one.return_value = 5
        db.execute.return_value = max_result

        with patch(
            "app.api.tasks.reserve_execution",
            new=AsyncMock(return_value=SimpleNamespace(is_replay=False)),
        ), patch("app.api.tasks.commit_reserved_execution", new=AsyncMock()):
            item = await create_checklist_item(
                "task-1",
                schemas.ChecklistItemCreate(title="Auto"),
                {"sub": "user-1"},
                db,
                None,
            )

        self.assertEqual(item.sort_order, 5)

    async def test_update_rejects_item_from_another_task(self):
        from app.api.tasks import update_checklist_item

        db = AsyncMock()
        db.get.side_effect = [self._task("task-1"), self._item("item-1", "task-2")]
        with self.assertRaises(HTTPException) as ctx:
            await update_checklist_item(
                "task-1",
                "item-1",
                schemas.ChecklistItemUpdate(is_done=True),
                {"sub": "u"},
                db,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_update_persists_fields_and_audits(self):
        from app.api.tasks import update_checklist_item

        item = self._item()
        db = AsyncMock()
        db.get.side_effect = [self._task(), item]
        start = AsyncMock(return_value=object())
        finish = AsyncMock()
        with patch("app.api.tasks.start_execution", new=start), patch(
            "app.api.tasks.finish_execution", new=finish
        ), patch("app.api.tasks.fail_execution", new=AsyncMock()):
            result = await update_checklist_item(
                "task-1",
                "item-1",
                schemas.ChecklistItemUpdate(title="Renamed", is_done=True, sort_order=4),
                {"sub": "u"},
                db,
            )

        self.assertEqual(result.title, "Renamed")
        self.assertTrue(result.is_done)
        self.assertEqual(result.sort_order, 4)
        self.assertEqual(start.await_args.kwargs["action_type"], "checklist_item.update")
        finish.assert_awaited_once()

    async def test_delete_task_cleans_checklist_children_before_parent(self):
        from app.api.tasks import delete_task

        task = self._task()
        db = AsyncMock()
        db.get.return_value = task
        events: list[str] = []

        async def execute(statement):
            self.assertIn("DELETE FROM checklist_items", str(statement))
            events.append("children")
            return MagicMock()

        async def delete_parent(obj):
            self.assertIs(obj, task)
            events.append("task")

        db.execute.side_effect = execute
        db.delete.side_effect = delete_parent
        with patch("app.api.tasks.start_execution", new=AsyncMock(return_value=object())), patch(
            "app.api.tasks.finish_execution", new=AsyncMock()
        ), patch("app.api.tasks.fail_execution", new=AsyncMock()):
            await delete_task("task-1", {"sub": "u"}, db)

        self.assertEqual(events, ["children", "task"])
        db.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
