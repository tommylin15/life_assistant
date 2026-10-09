import importlib.util
import unittest
from pathlib import Path


class DriveMigrationTests(unittest.TestCase):
    def setUp(self):
        self.backend_root = Path(__file__).parents[1]
        self.migration_path = (
            self.backend_root
            / "alembic/versions/20261001_0008_drive_core_persistence.py"
        )

    def _load_migration(self):
        spec = importlib.util.spec_from_file_location(
            "drive_core_persistence_migration",
            self.migration_path,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_revision_extends_current_alembic_head(self):
        module = self._load_migration()
        self.assertEqual(module.revision, "20261001_0008")
        self.assertEqual(module.down_revision, "20260930_0007")

    def test_upgrade_creates_only_additive_drive_core_tables(self):
        source = self.migration_path.read_text(encoding="utf-8")
        upgrade_source = source.split("def upgrade() -> None:", 1)[1].split(
            "def downgrade() -> None:",
            1,
        )[0]

        for table_name in (
            "drive_workspaces",
            "drive_documents",
            "drive_workspace_documents",
            "project_drive_documents",
            "note_drive_documents",
        ):
            self.assertIn(f'"{table_name}"', upgrade_source)

        self.assertNotIn("drop_table(", upgrade_source)
        self.assertNotIn("drop_column(", upgrade_source)
        self.assertNotIn("DROP TABLE", upgrade_source.upper())

    def test_migration_pins_user_isolation_relationships_and_note_semantics(self):
        source = self.migration_path.read_text(encoding="utf-8")
        for expected in (
            "uq_drive_workspaces_user_folder",
            "uq_drive_documents_user_file",
            "projects.id",
            "notes.id",
            "drive_documents.id",
            "source_import",
            "related",
            "ai_accepted",
            'ondelete="CASCADE"',
        ):
            self.assertIn(expected, source)

    def test_alembic_metadata_imports_drive_models(self):
        env_source = (self.backend_root / "alembic/env.py").read_text(encoding="utf-8")
        self.assertIn("from app.models.drive import", env_source)
        for model_name in (
            "DriveDocument",
            "DriveWorkspace",
            "DriveWorkspaceDocument",
            "NoteDriveDocument",
            "ProjectDriveDocument",
            "DriveEnrichmentSettings",
            "DriveDocumentEnrichmentRun",
            "DriveNoteLinkSuggestion",
        ):
            self.assertIn(model_name, env_source)

    def test_release_gate_targets_current_head_and_requires_enrichment_tables(self):
        release_source = (
            self.backend_root / "scripts/apply_cloud_domain_parity_release.py"
        ).read_text(encoding="utf-8")
        self.assertIn('PREVIOUS_RELEASE_REVISION = "20261007_0010"', release_source)
        self.assertIn('RELEASE_TARGET_REVISION = "20261009_0011"', release_source)
        for table_name in (
            "drive_workspaces",
            "drive_documents",
            "drive_workspace_documents",
            "project_drive_documents",
            "note_drive_documents",
            "drive_enrichment_settings",
            "drive_document_enrichment_runs",
            "drive_note_link_suggestions",
            "ai_provider_preferences",
        ):
            self.assertIn(f'"{table_name}"', release_source)


if __name__ == "__main__":
    unittest.main()
