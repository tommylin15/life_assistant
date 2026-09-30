import importlib
import importlib.util
import unittest

from sqlalchemy import Index, UniqueConstraint


class DriveModelContractTests(unittest.TestCase):
    def _module(self):
        self.assertIsNotNone(importlib.util.find_spec("app.models.drive"))
        return importlib.import_module("app.models.drive")

    def test_drive_model_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec("app.models.drive"))

    def test_drive_schema_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec("app.models.drive_schemas"))

    def test_drive_tables_and_owner_scoped_provider_uniques(self):
        module = self._module()
        self.assertEqual(module.DriveWorkspace.__tablename__, "drive_workspaces")
        self.assertEqual(module.DriveDocument.__tablename__, "drive_documents")
        self.assertEqual(module.DriveAiSettings.__tablename__, "drive_ai_settings")

        workspace_columns = module.DriveWorkspace.__table__.c
        document_columns = module.DriveDocument.__table__.c
        settings_columns = module.DriveAiSettings.__table__.c
        self.assertFalse(workspace_columns.owner_sub.nullable)
        self.assertFalse(document_columns.owner_sub.nullable)
        self.assertFalse(settings_columns.owner_sub.nullable)

        workspace_uniques = {
            tuple(constraint.columns.keys())
            for constraint in module.DriveWorkspace.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        document_uniques = {
            tuple(constraint.columns.keys())
            for constraint in module.DriveDocument.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        self.assertIn(("owner_sub", "google_folder_id"), workspace_uniques)
        self.assertIn(("owner_sub", "google_file_id"), document_uniques)

    def test_relationship_tables_use_composite_identity(self):
        module = self._module()
        for model, expected in (
            (module.DriveWorkspaceDocument, {"workspace_id", "drive_document_id"}),
            (module.ProjectDriveDocument, {"project_id", "drive_document_id"}),
        ):
            primary = {column.name for column in model.__table__.primary_key.columns}
            self.assertEqual(primary, expected)

        note_primary = {
            column.name for column in module.NoteDriveDocument.__table__.primary_key.columns
        }
        self.assertEqual(
            note_primary,
            {"note_id", "drive_document_id", "relation_type"},
        )

    def test_ai_settings_defaults_and_default_workspace_partial_unique_index(self):
        module = self._module()
        settings_columns = module.DriveAiSettings.__table__.c
        self.assertEqual(settings_columns.auto_tags.default.arg, True)
        self.assertEqual(settings_columns.suggest_related_notes.default.arg, True)
        self.assertEqual(settings_columns.allow_content_analysis.default.arg, False)
        self.assertEqual(settings_columns.max_related_notes.default.arg, 5)

        indexes = [
            index
            for index in module.DriveWorkspace.__table__.indexes
            if isinstance(index, Index)
        ]
        default_indexes = [
            index
            for index in indexes
            if index.name == "uq_drive_workspaces_default_per_owner"
        ]
        self.assertEqual(len(default_indexes), 1)
        self.assertTrue(default_indexes[0].unique)
        self.assertIsNotNone(
            default_indexes[0].dialect_options["postgresql"].get("where")
        )


if __name__ == "__main__":
    unittest.main()
