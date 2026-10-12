"""Non-destructive P1 tenant ownership and cross-account guards."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.models.project import Project
from app.models.note import Note
from app.models.habit import Habit
from app.models.shopping import ShoppingList, ShoppingItem
from app.services.ownership import can_access, get_owned, require_project, visible_clause


class TenantOwnershipTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"ALLOWED_GOOGLE_EMAIL": "owner@example.test"})
        env.start()
        self.addCleanup(env.stop)
        self.owner = {"sub": "owner-sub", "email": "owner@example.test"}
        self.alice = {"sub": "alice-sub", "email": "alice@example.test"}
        self.bob = {"sub": "bob-sub", "email": "bob@example.test"}

    def test_legacy_rows_only_visible_to_owner(self):
        for model in (Project, Note, Habit, ShoppingList):
            self.assertTrue(model.__table__.c.user_sub.nullable)
            legacy = SimpleNamespace(user_sub=None)
            self.assertTrue(can_access(legacy, self.owner))
            self.assertFalse(can_access(legacy, self.alice))
            self.assertIn("IS NULL", str(visible_clause(model, self.owner)))
            self.assertNotIn("IS NULL", str(visible_clause(model, self.alice)))

    def test_tenants_cannot_see_each_others_rows(self):
        for model in (Project, Note, Habit, ShoppingList):
            alice_row = SimpleNamespace(user_sub=self.alice["sub"])
            self.assertTrue(can_access(alice_row, self.alice))
            self.assertFalse(can_access(alice_row, self.bob))
            self.assertFalse(can_access(alice_row, self.owner))
            self.assertIn("user_sub", str(visible_clause(model, self.bob)))

    async def test_cross_account_direct_lookup_is_404(self):
        for model in (Project, Note, Habit, ShoppingList):
            db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(user_sub="alice-sub")))
            with self.assertRaises(HTTPException) as ctx:
                await get_owned(db, model, "foreign-id", self.bob, "Resource")
            self.assertEqual(ctx.exception.status_code, 404)

    async def test_cannot_link_foreign_project(self):
        db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(user_sub="alice-sub")))
        with self.assertRaises(HTTPException) as ctx:
            await require_project(db, "foreign-project", self.bob)
        self.assertEqual(ctx.exception.status_code, 404)
        await require_project(db, None, self.bob)

    async def test_shopping_item_requires_own_parent(self):
        from app.api.shopping import update_shopping_item
        from app.models.schemas import ShoppingItemUpdate
        item = ShoppingItem(id="item-a", list_id="alice-list", name="Milk", is_done=False)
        db = SimpleNamespace(get=AsyncMock(side_effect=[
            item, SimpleNamespace(user_sub="alice-sub")
        ]))
        with self.assertRaises(HTTPException) as ctx:
            await update_shopping_item("item-a", ShoppingItemUpdate(is_done=True), self.bob, db)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertFalse(item.is_done)
