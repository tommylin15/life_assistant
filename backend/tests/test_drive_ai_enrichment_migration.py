import importlib.util
import unittest
from pathlib import Path


class DriveAIEnrichmentMigrationTests(unittest.TestCase):
    def setUp(self):
        self.backend_root = Path(__file__).parents[1]
        self.migration_path = (
            self.backend_root
            / "alembic/versions/20261002_0009_drive_ai_enrichment.py"
        )

    def _load_migration(self):
        spec = importlib.util.spec_from_file_location(
            "drive_ai_enrichment_migration",
            self.migration_path,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_revision_extends_drive_core_head(self):
        module = self._load_migration()
        self.assertEqual(module.revision, "20261002_0009")
        self.assertEqual(module.down_revision, "20261001_0008")

    def test_upgrade_is_additive_and_creates_required_tables(self):
        source = self.migration_path.read_text(encoding="utf-8")
        upgrade_source = source.split("def upgrade() -> None:", 1)[1].split(
            "def downgrade() -> None:",
            1,
        )[0]
        for table_name in (
            "drive_enrichment_settings",
            "drive_document_enrichment_runs",
            "drive_note_link_suggestions",
        ):
            self.assertIn(f'"{table_name}"', upgrade_source)
        self.assertNotIn("drop_table(", upgrade_source)
        self.assertNotIn("drop_column(", upgrade_source)

    def test_migration_pins_privacy_cache_and_decision_contracts(self):
        source = self.migration_path.read_text(encoding="utf-8")
        for expected in (
            "allow_document_content",
            "content_fingerprint",
            "succeeded",
            "partial",
            "failed",
            "skipped",
            "pending",
            "accepted",
            "rejected",
            "uq_drive_note_suggestions_run_note",
            'ondelete="CASCADE"',
        ):
            self.assertIn(expected, source)


if __name__ == "__main__":
    unittest.main()
