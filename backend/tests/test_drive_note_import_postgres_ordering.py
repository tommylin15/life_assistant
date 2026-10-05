import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.drive import DriveDocument
from app.models.note import Note
from app.services import drive_documents


class DriveNoteImportPostgresOrderingTests(unittest.IsolatedAsyncioTestCase):
    async def test_import_flushes_note_before_source_relation(self):
        document = DriveDocument(
            id="document-1",
            user_sub="user-1",
            google_file_id="google-file-1",
            name="Provider filename",
            mime_type="application/vnd.google-apps.document",
        )
        events: list[tuple[str, str | None]] = []
        db = MagicMock()

        def record_add(item):
            events.append(("add", type(item).__name__))

        async def record_flush():
            events.append(("flush", None))

        db.add = MagicMock(side_effect=record_add)
        db.flush = AsyncMock(side_effect=record_flush)

        with (
            patch(
                "app.services.drive_documents.get_document",
                new=AsyncMock(return_value=document),
            ),
            patch(
                "app.services.drive_documents.read_drive_text",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        supported=True,
                        text="Drive snapshot body",
                        source_mime_type=document.mime_type,
                    )
                ),
            ),
        ):
            note = await drive_documents.import_document_to_note(
                db,
                "user-1",
                document.id,
                title=None,
                project_id=None,
                tags=[],
            )

        self.assertIsInstance(note, Note)
        self.assertIn(("flush", None), events)
        self.assertLess(events.index(("add", "Note")), events.index(("flush", None)))
        self.assertLess(
            events.index(("flush", None)),
            events.index(("add", "NoteDriveDocument")),
        )


if __name__ == "__main__":
    unittest.main()
