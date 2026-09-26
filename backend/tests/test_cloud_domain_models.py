import importlib.util
import unittest
from pathlib import Path

from sqlalchemy import Text

from app.models.habit import Habit, HabitCompletion
from app.models.note import Note, NoteLink
from app.models.shopping import ShoppingItem, ShoppingList
from app.models.template import Template


class CloudDomainModelTests(unittest.TestCase):
    def test_table_names_and_core_nullability(self):
        self.assertEqual(Note.__tablename__, "notes")
        self.assertTrue(Note.__table__.c.title.nullable)
        self.assertTrue(Note.__table__.c.body.nullable)
        self.assertFalse(Habit.__table__.c.title.nullable)
        self.assertFalse(ShoppingList.__table__.c.name.nullable)
        self.assertFalse(Template.__table__.c.payload_json.nullable)

    def test_note_links_have_composite_primary_key_and_fks(self):
        self.assertEqual(
            {c.name for c in NoteLink.__table__.primary_key.columns},
            {"source_note_id", "target_note_id"},
        )
        targets = {fk.target_fullname for fk in NoteLink.__table__.foreign_keys}
        self.assertEqual(targets, {"notes.id"})

    def test_habits_and_shopping_lists_do_not_invent_updated_at(self):
        self.assertNotIn("updated_at", Habit.__table__.c)
        self.assertNotIn("updated_at", ShoppingList.__table__.c)
        self.assertNotIn("created_at", ShoppingItem.__table__.c)
        self.assertNotIn("updated_at", ShoppingItem.__table__.c)

    def test_runtime_metadata_has_defaults_and_completion_index(self):
        self.assertIsNotNone(Habit.__table__.c.is_active.server_default)
        self.assertIsNotNone(ShoppingItem.__table__.c.is_done.server_default)
        self.assertIsNotNone(ShoppingItem.__table__.c.sort_order.server_default)
        self.assertIn(
            "ix_habit_completions_habit_id_completed_at",
            {i.name for i in HabitCompletion.__table__.indexes},
        )

    def test_template_payload_is_text(self):
        self.assertIsInstance(Template.__table__.c.payload_json.type, Text)

    def test_migration_revision_connects_to_current_head(self):
        path = (
            Path(__file__).parents[1]
            / "alembic/versions/20260926_0004_cloud_domain_parity.py"
        )
        spec = importlib.util.spec_from_file_location("cloud_domain_migration", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(module.revision, "20260926_0004")
        self.assertEqual(module.down_revision, "20260925_0003")


if __name__ == "__main__":
    unittest.main()
