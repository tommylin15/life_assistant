import unittest

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.drive import (
    DriveDocument,
    DriveWorkspace,
    DriveWorkspaceDocument,
    NoteDriveDocument,
    ProjectDriveDocument,
)


class DriveModelTests(unittest.TestCase):
    def test_workspace_and_document_are_scoped_to_google_user(self):
        self.assertFalse(DriveWorkspace.__table__.c.user_sub.nullable)
        self.assertFalse(DriveDocument.__table__.c.user_sub.nullable)

        workspace_unique = {
            tuple(column.name for column in constraint.columns)
            for constraint in DriveWorkspace.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        document_unique = {
            tuple(column.name for column in constraint.columns)
            for constraint in DriveDocument.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        }

        self.assertIn(("user_sub", "google_folder_id"), workspace_unique)
        self.assertIn(("user_sub", "google_file_id"), document_unique)

    def test_workspace_flags_have_database_defaults(self):
        self.assertIsNotNone(DriveWorkspace.__table__.c.is_enabled.server_default)
        self.assertIsNotNone(DriveWorkspace.__table__.c.is_default.server_default)

    def test_workspace_document_relationship_is_unique_by_composite_primary_key(self):
        self.assertEqual(
            {column.name for column in DriveWorkspaceDocument.__table__.primary_key.columns},
            {"workspace_id", "drive_document_id"},
        )
        self.assertEqual(
            {fk.target_fullname for fk in DriveWorkspaceDocument.__table__.foreign_keys},
            {"drive_workspaces.id", "drive_documents.id"},
        )

    def test_project_document_relationship_is_many_to_many_join(self):
        self.assertEqual(
            {column.name for column in ProjectDriveDocument.__table__.primary_key.columns},
            {"project_id", "drive_document_id"},
        )
        self.assertEqual(
            {fk.target_fullname for fk in ProjectDriveDocument.__table__.foreign_keys},
            {"projects.id", "drive_documents.id"},
        )

    def test_note_document_relationship_has_explicit_relation_and_source_constraints(self):
        self.assertEqual(
            {column.name for column in NoteDriveDocument.__table__.primary_key.columns},
            {"note_id", "drive_document_id"},
        )
        self.assertEqual(
            {fk.target_fullname for fk in NoteDriveDocument.__table__.foreign_keys},
            {"notes.id", "drive_documents.id"},
        )

        checks = {
            constraint.name: str(constraint.sqltext)
            for constraint in NoteDriveDocument.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        }
        self.assertIn("source_import", checks["ck_note_drive_documents_relation_type"])
        self.assertIn("related", checks["ck_note_drive_documents_relation_type"])
        self.assertIn("manual", checks["ck_note_drive_documents_link_source"])
        self.assertIn("ai_accepted", checks["ck_note_drive_documents_link_source"])
        self.assertIn("import", checks["ck_note_drive_documents_link_source"])


if __name__ == "__main__":
    unittest.main()
