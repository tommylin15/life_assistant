import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.models.drive import DriveDocument, NoteDriveDocument
from app.models.migration_support import EntityTag, Tag
from app.models.note import Note
from app.services.google_drive_files import DriveTextResult


class DriveNoteImportTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _document(*, mime_type: str = "application/vnd.google-apps.document") -> DriveDocument:
        return DriveDocument(
            id="d1",
            owner_sub="user-a",
            google_file_id="google-1",
            name="年度規劃",
            mime_type=mime_type,
            web_view_link="https://docs.google.com/document/d/google-1/edit",
        )

    async def test_readable_import_creates_independent_note_source_relation_and_tags(self):
        from app.services.drive_documents import import_document_to_note

        document = self._document()
        db = AsyncMock()
        missing_tag = MagicMock()
        missing_tag.scalar_one_or_none.return_value = None
        db.execute.return_value = missing_tag

        with (
            patch(
                "app.services.drive_documents.get_owned_document",
                new=AsyncMock(return_value=document),
            ),
            patch(
                "app.services.drive_documents.read_drive_text",
                new=AsyncMock(
                    return_value=DriveTextResult(
                        supported=True,
                        text="# 原始內容\n第一版",
                        source_mime_type=document.mime_type,
                    )
                ),
            ) as read_text,
        ):
            note = await import_document_to_note(
                db,
                "user-a",
                "d1",
                title="匯入後標題",
                project_id="p1",
                tags=["Drive", "參考"],
            )

        self.assertIsInstance(note, Note)
        self.assertEqual(note.title, "匯入後標題")
        self.assertEqual(note.body, "# 原始內容\n第一版")
        self.assertEqual(note.project_id, "p1")
        read_text.assert_awaited_once_with(
            db,
            "user-a",
            "google-1",
            document.mime_type,
        )

        added = [call.args[0] for call in db.add.call_args_list]
        source_links = [item for item in added if isinstance(item, NoteDriveDocument)]
        self.assertEqual(len(source_links), 1)
        self.assertEqual(source_links[0].drive_document_id, "d1")
        self.assertEqual(source_links[0].relation_type, "source_import")
        self.assertEqual(source_links[0].relation_origin, "import")
        self.assertEqual(len([item for item in added if isinstance(item, Tag)]), 2)
        self.assertEqual(len([item for item in added if isinstance(item, EntityTag)]), 2)
        db.commit.assert_awaited_once()

    async def test_omitted_title_uses_provider_filename_and_snapshot_never_auto_syncs(self):
        from app.services.drive_documents import import_document_to_note

        document = self._document()
        db = AsyncMock()
        with (
            patch(
                "app.services.drive_documents.get_owned_document",
                new=AsyncMock(return_value=document),
            ),
            patch(
                "app.services.drive_documents.read_drive_text",
                new=AsyncMock(
                    return_value=DriveTextResult(
                        supported=True,
                        text="snapshot v1",
                        source_mime_type=document.mime_type,
                    )
                ),
            ),
        ):
            note = await import_document_to_note(db, "user-a", "d1")

        self.assertEqual(note.title, "年度規劃")
        self.assertEqual(note.body, "snapshot v1")
        document.name = "年度規劃 v2"
        self.assertEqual(note.title, "年度規劃")
        self.assertEqual(note.body, "snapshot v1")

    async def test_unsupported_binary_returns_stable_422_without_writes(self):
        from app.services.drive_documents import import_document_to_note

        document = self._document(mime_type="application/octet-stream")
        db = AsyncMock()
        with (
            patch(
                "app.services.drive_documents.get_owned_document",
                new=AsyncMock(return_value=document),
            ),
            patch(
                "app.services.drive_documents.read_drive_text",
                new=AsyncMock(
                    return_value=DriveTextResult(
                        supported=False,
                        text=None,
                        source_mime_type=document.mime_type,
                    )
                ),
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await import_document_to_note(db, "user-a", "d1")

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail, "drive_text_unavailable")
        db.add.assert_not_called()
        db.commit.assert_not_awaited()
        db.delete.assert_not_awaited()

    async def test_provider_error_is_not_replaced_with_old_snapshot(self):
        from app.services.drive_documents import import_document_to_note

        document = self._document()
        db = AsyncMock()
        provider_error = HTTPException(403, "google_drive_access_denied")
        with (
            patch(
                "app.services.drive_documents.get_owned_document",
                new=AsyncMock(return_value=document),
            ),
            patch(
                "app.services.drive_documents.read_drive_text",
                new=AsyncMock(side_effect=provider_error),
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await import_document_to_note(db, "user-a", "d1")

        self.assertIs(ctx.exception, provider_error)
        db.add.assert_not_called()
        db.commit.assert_not_awaited()


class DriveNoteRelationshipTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _document() -> DriveDocument:
        return DriveDocument(
            id="d1",
            owner_sub="user-a",
            google_file_id="google-1",
            name="Spec",
            mime_type="text/plain",
        )

    async def test_manual_relation_is_idempotent_and_unlink_only_removes_relation(self):
        from app.services.drive_documents import (
            link_document_to_note,
            unlink_document_from_note,
        )

        document = self._document()
        note = Note(id="n1", title="Note", body="body")
        db = AsyncMock()
        db.get.return_value = note
        absent = MagicMock()
        absent.scalar_one_or_none.return_value = None
        db.execute.return_value = absent

        with patch(
            "app.services.drive_documents.get_owned_document",
            new=AsyncMock(return_value=document),
        ):
            relation = await link_document_to_note(
                db,
                "user-a",
                "d1",
                "n1",
            )

        self.assertEqual(relation.note_id, "n1")
        self.assertEqual(relation.drive_document_id, "d1")
        self.assertEqual(relation.relation_type, "related")
        self.assertEqual(relation.relation_origin, "manual")
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

        db.reset_mock()
        db.get.return_value = note
        existing = NoteDriveDocument(
            note_id="n1",
            drive_document_id="d1",
            relation_type="related",
            relation_origin="manual",
        )
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing
        db.execute.return_value = existing_result
        with patch(
            "app.services.drive_documents.get_owned_document",
            new=AsyncMock(return_value=document),
        ):
            replay = await link_document_to_note(db, "user-a", "d1", "n1")
        self.assertIs(replay, existing)
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

        db.reset_mock()
        db.get.return_value = note
        db.execute.side_effect = [existing_result, MagicMock()]
        with patch(
            "app.services.drive_documents.get_owned_document",
            new=AsyncMock(return_value=document),
        ):
            await unlink_document_from_note(db, "user-a", "d1", "n1")
        self.assertEqual(db.execute.await_count, 2)
        db.delete.assert_not_awaited()
        db.commit.assert_awaited_once()

    async def test_cross_user_document_relation_fails_before_note_mutation(self):
        from app.services.drive_documents import link_document_to_note

        db = AsyncMock()
        with patch(
            "app.services.drive_documents.get_owned_document",
            new=AsyncMock(side_effect=HTTPException(404, "Drive document not found")),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await link_document_to_note(db, "user-b", "d1", "n1")
        self.assertEqual(ctx.exception.status_code, 404)
        db.get.assert_not_awaited()
        db.add.assert_not_called()


class DriveNoteApiContractTests(unittest.TestCase):
    def test_drive_router_exposes_import_and_bidirectional_relation_routes(self):
        from app.api.drive import router

        routes = {
            (route.path, method)
            for route in router.routes
            for method in (route.methods or set())
        }
        self.assertIn(("/drive/documents/{document_id}/note-import", "POST"), routes)
        self.assertIn(("/drive/documents/{document_id}/notes", "GET"), routes)
        self.assertIn(("/drive/documents/{document_id}/notes/{note_id}", "POST"), routes)
        self.assertIn(("/drive/documents/{document_id}/notes/{note_id}", "DELETE"), routes)
        self.assertIn(("/drive/notes/{note_id}/documents", "GET"), routes)


if __name__ == "__main__":
    unittest.main()
