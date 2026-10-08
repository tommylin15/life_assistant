import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.confirmation import confirmation_requirement, explicit_confirmation_value
from app.main import app
from app.models.drive import DriveDocument, NoteDriveDocument
from app.models.note import Note
from app.services import drive_documents


client = TestClient(app)


class DriveNoteRelationshipContractTests(unittest.TestCase):
    def test_bidirectional_relationship_routes_are_registered_and_protected(self):
        paths = {route.path for route in app.routes if hasattr(route, "path")}
        self.assertIn("/api/v1/drive/documents/{document_id}/notes", paths)
        self.assertIn("/api/v1/drive/documents/{document_id}/notes/{note_id}", paths)
        self.assertIn("/api/v1/drive/notes/{note_id}/documents", paths)

        response = client.get("/api/v1/drive/documents/document-1/notes")
        self.assertEqual(response.status_code, 401)

    def test_unlink_requires_target_bound_explicit_confirmation(self):
        path = "/api/v1/drive/documents/document-1/notes/note-1"
        target = "document-1:note-1"
        self.assertEqual(
            confirmation_requirement("DELETE", path),
            ("drive.document.note.detach", target),
        )
        self.assertEqual(
            explicit_confirmation_value("drive.document.note.detach", target),
            "explicit_user:drive.document.note.detach:document-1:note-1",
        )


class DriveNoteRelationshipServiceTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _document(user_sub: str = "user-1") -> DriveDocument:
        return DriveDocument(
            id="document-1",
            user_sub=user_sub,
            google_file_id="google-file-1",
            name="Provider filename",
            mime_type="application/vnd.google-apps.document",
        )

    async def test_manual_attach_is_idempotent_and_never_overwrites_source_import(self):
        attach = getattr(drive_documents, "attach_document_note", None)
        self.assertTrue(callable(attach))
        if not callable(attach):
            return

        document = self._document()
        note = Note(id="note-1", title="Note", body="Body")
        source_relation = NoteDriveDocument(
            note_id=note.id,
            drive_document_id=document.id,
            relation_type="source_import",
            link_source="import",
        )
        db = MagicMock()
        db.get = AsyncMock(side_effect=[note, source_relation])
        db.add = MagicMock()

        with patch(
            "app.services.drive_documents.get_document",
            new=AsyncMock(return_value=document),
        ) as get_document:
            relation, created = await attach(
                db,
                "user-1",
                document.id,
                note.id,
            )

        self.assertFalse(created)
        self.assertIs(relation, source_relation)
        self.assertEqual(relation.relation_type, "source_import")
        self.assertEqual(relation.link_source, "import")
        db.add.assert_not_called()
        get_document.assert_awaited_once_with(db, "user-1", document.id)

    async def test_manual_attach_creates_related_manual_relation(self):
        attach = getattr(drive_documents, "attach_document_note", None)
        self.assertTrue(callable(attach))
        if not callable(attach):
            return

        document = self._document()
        note = Note(id="note-1", title="Note", body="Body")
        db = MagicMock()
        db.get = AsyncMock(side_effect=[note, None])
        db.add = MagicMock()

        with patch(
            "app.services.drive_documents.get_document",
            new=AsyncMock(return_value=document),
        ):
            relation, created = await attach(
                db,
                "user-1",
                document.id,
                note.id,
            )

        self.assertTrue(created)
        self.assertEqual(relation.note_id, note.id)
        self.assertEqual(relation.drive_document_id, document.id)
        self.assertEqual(relation.relation_type, "related")
        self.assertEqual(relation.link_source, "manual")
        db.add.assert_called_once_with(relation)

    async def test_manual_attach_rejects_unknown_note_before_creating_relation(self):
        attach = getattr(drive_documents, "attach_document_note", None)
        self.assertTrue(callable(attach))
        if not callable(attach):
            return

        document = self._document()
        db = MagicMock()
        db.get = AsyncMock(return_value=None)
        db.add = MagicMock()

        with patch(
            "app.services.drive_documents.get_document",
            new=AsyncMock(return_value=document),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await attach(db, "user-1", document.id, "missing-note")

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Note not found")
        db.add.assert_not_called()

    async def test_unlink_deletes_only_related_relationship(self):
        detach = getattr(drive_documents, "detach_document_note", None)
        self.assertTrue(callable(detach))
        if not callable(detach):
            return

        document = self._document()
        relation = NoteDriveDocument(
            note_id="note-1",
            drive_document_id=document.id,
            relation_type="related",
            link_source="manual",
        )
        db = MagicMock()
        db.get = AsyncMock(return_value=relation)
        db.delete = AsyncMock()

        with patch(
            "app.services.drive_documents.get_document",
            new=AsyncMock(return_value=document),
        ):
            removed = await detach(db, "user-1", document.id, "note-1")

        self.assertTrue(removed)
        db.delete.assert_awaited_once_with(relation)

    async def test_unlink_refuses_to_remove_source_import_relation(self):
        detach = getattr(drive_documents, "detach_document_note", None)
        self.assertTrue(callable(detach))
        if not callable(detach):
            return

        document = self._document()
        relation = NoteDriveDocument(
            note_id="note-1",
            drive_document_id=document.id,
            relation_type="source_import",
            link_source="import",
        )
        db = MagicMock()
        db.get = AsyncMock(return_value=relation)
        db.delete = AsyncMock()

        with patch(
            "app.services.drive_documents.get_document",
            new=AsyncMock(return_value=document),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await detach(db, "user-1", document.id, "note-1")

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "Drive source import relation cannot be unlinked")
        db.delete.assert_not_awaited()

    async def test_document_and_note_listings_are_bidirectional_and_user_scoped(self):
        list_notes = getattr(drive_documents, "list_document_note_relations", None)
        list_documents = getattr(drive_documents, "list_note_document_relations", None)
        self.assertTrue(callable(list_notes))
        self.assertTrue(callable(list_documents))
        if not callable(list_notes) or not callable(list_documents):
            return

        document = self._document()
        note = Note(id="note-1", title="Note", body="Body")
        relation = NoteDriveDocument(
            note_id=note.id,
            drive_document_id=document.id,
            relation_type="related",
            link_source="manual",
        )
        first_result = MagicMock()
        first_result.all.return_value = [(note, relation)]
        second_result = MagicMock()
        second_result.all.return_value = [(document, relation)]
        db = MagicMock()
        db.get = AsyncMock(return_value=note)
        db.execute = AsyncMock(side_effect=[first_result, second_result])

        with patch(
            "app.services.drive_documents.get_document",
            new=AsyncMock(return_value=document),
        ):
            notes = await list_notes(db, "user-1", document.id)
            documents = await list_documents(db, "user-1", note.id)

        self.assertEqual(notes, [(note, relation)])
        self.assertEqual(documents, [(document, relation)])
        reverse_statement = str(db.execute.await_args_list[1].args[0])
        self.assertIn("drive_documents.user_sub", reverse_statement)


if __name__ == "__main__":
    unittest.main()
