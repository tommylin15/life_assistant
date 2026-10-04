import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.models.drive import DriveDocument, NoteDriveDocument
from app.models.migration_support import EntityTag, Tag
from app.models.note import Note
from app.services import drive_documents


client = TestClient(app)


class DriveNoteImportContractTests(unittest.TestCase):
    def test_note_import_route_is_registered_and_protected(self):
        paths = {route.path for route in app.routes}
        self.assertIn(
            "/api/v1/drive/documents/{document_id}/note-import",
            paths,
        )
        response = client.post(
            "/api/v1/drive/documents/document-1/note-import",
            json={},
        )
        self.assertEqual(response.status_code, 401)

    def test_note_import_schema_normalizes_title_project_and_tags(self):
        from app.models.drive_schemas import DriveNoteImportRequest

        body = DriveNoteImportRequest(
            title="  Snapshot title  ",
            project_id=" project-1 ",
            tags=[" 旅行 ", "重要", "旅行", "IMPORTANT", "important"],
        )
        self.assertEqual(body.title, "Snapshot title")
        self.assertEqual(body.project_id, "project-1")
        self.assertEqual(body.tags, ["旅行", "重要", "IMPORTANT"])


class DriveNoteImportServiceTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _document() -> DriveDocument:
        return DriveDocument(
            id="document-1",
            user_sub="user-1",
            google_file_id="google-file-1",
            name="Provider filename",
            mime_type="application/vnd.google-apps.document",
        )

    async def test_readable_drive_content_creates_independent_snapshot_relation(self):
        import_document_to_note = getattr(
            drive_documents,
            "import_document_to_note",
            None,
        )
        self.assertTrue(callable(import_document_to_note))
        if not callable(import_document_to_note):
            return

        document = self._document()
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        missing_tag = MagicMock()
        missing_tag.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=missing_tag)

        with (
            patch(
                "app.services.drive_documents.get_document",
                new=AsyncMock(return_value=document),
            ) as get_document,
            patch(
                "app.services.drive_documents.read_drive_text",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        supported=True,
                        text="Drive snapshot body",
                        source_mime_type=document.mime_type,
                    )
                ),
                create=True,
            ) as read_text,
        ):
            note = await import_document_to_note(
                db,
                "user-1",
                document.id,
                title=None,
                project_id=None,
                tags=["旅行"],
            )

        self.assertIsInstance(note, Note)
        self.assertEqual(note.title, "Provider filename")
        self.assertEqual(note.body, "Drive snapshot body")
        self.assertIsNone(note.project_id)
        get_document.assert_awaited_once_with(db, "user-1", document.id)
        read_text.assert_awaited_once_with(db, "user-1", document.google_file_id)

        added = [call.args[0] for call in db.add.call_args_list]
        relations = [item for item in added if isinstance(item, NoteDriveDocument)]
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0].note_id, note.id)
        self.assertEqual(relations[0].drive_document_id, document.id)
        self.assertEqual(relations[0].relation_type, "source_import")
        self.assertEqual(relations[0].link_source, "import")
        tags = [item for item in added if isinstance(item, Tag)]
        self.assertEqual([item.name for item in tags], ["旅行"])
        entity_tags = [item for item in added if isinstance(item, EntityTag)]
        self.assertEqual(len(entity_tags), 1)
        self.assertEqual(entity_tags[0].entity_type, "note")
        self.assertEqual(entity_tags[0].entity_id, note.id)
        db.commit.assert_awaited_once()

    async def test_unsupported_binary_returns_stable_422_without_creating_note(self):
        import_document_to_note = getattr(
            drive_documents,
            "import_document_to_note",
            None,
        )
        self.assertTrue(callable(import_document_to_note))
        if not callable(import_document_to_note):
            return

        document = self._document()
        document.mime_type = "application/pdf"
        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()

        with (
            patch(
                "app.services.drive_documents.get_document",
                new=AsyncMock(return_value=document),
            ),
            patch(
                "app.services.drive_documents.read_drive_text",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        supported=False,
                        text=None,
                        source_mime_type=document.mime_type,
                    )
                ),
                create=True,
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await import_document_to_note(
                    db,
                    "user-1",
                    document.id,
                    title=None,
                    project_id=None,
                    tags=[],
                )

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail, "drive_text_unavailable")
        db.add.assert_not_called()
        db.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
