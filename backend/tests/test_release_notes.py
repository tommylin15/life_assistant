import unittest

from fastapi import Response
from app.api.release_notes import (
    BackendReleaseNote,
    PUBLISHED_NOTES,
    release_notes,
)


class ReleaseNotesTests(unittest.TestCase):
    def test_only_source_approved_backend_updates_are_public(self):
        response = Response()
        payload = release_notes(response)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(payload["notes"], [])
        self.assertEqual(PUBLISHED_NOTES, ())

    def test_backend_note_requires_stable_id_date_and_small_copy(self):
        from pydantic import ValidationError
        from datetime import date

        note = BackendReleaseNote(
            id="backend-20261019-calendar",
            title="日曆操作更順暢",
            changes=["修正事件儲存後的畫面更新。"],
            published_on=date(2026, 10, 19),
            feature_key="calendar",
        )
        self.assertEqual(note.model_dump(mode="json")["published_on"], "2026-10-19")
        with self.assertRaises(ValidationError):
            BackendReleaseNote(
                id="bad", title="x", changes=[],
                published_on=date(2026, 10, 19),
            )


if __name__ == "__main__":
    unittest.main()
