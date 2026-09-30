import unittest
from pathlib import Path


class NotesFullTextSearchMigrationTests(unittest.TestCase):
    def test_migration_adds_gin_search_index_after_idempotency_revision(self):
        path = (
            Path(__file__).parents[1]
            / "alembic/versions/20260930_0007_notes_full_text_search.py"
        )
        source = path.read_text()
        self.assertIn('revision: str = "20260930_0007"', source)
        self.assertIn('down_revision: Union[str, None] = "20260928_0006"', source)
        self.assertIn("USING GIN", source)
        self.assertIn("to_tsvector", source)
        self.assertIn("coalesce(title, '') || ' ' || coalesce(body, '')", source)
        self.assertIn("DROP INDEX IF EXISTS ix_notes_full_text_search", source)


if __name__ == "__main__":
    unittest.main()
