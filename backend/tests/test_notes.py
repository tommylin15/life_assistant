import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.confirmation import confirmation_requirement, explicit_confirmation_value
from app.models import schemas
from app.models.note import Note, NoteLink


class NotesContractTests(unittest.TestCase):
    def test_note_schema_contract_exists(self):
        for name in (
            "NoteCreate",
            "NoteUpdate",
            "NoteOut",
            "NoteLinkCreate",
            "NoteTagsReplace",
            "NoteTagsOut",
        ):
            self.assertTrue(hasattr(schemas, name), name)

    def test_notes_router_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec("app.api.notes"))


class NotesSchemaBehaviorTests(unittest.TestCase):
    def test_create_requires_title_and_body_but_allows_empty_strings(self):
        self.assertEqual(
            schemas.NoteCreate(title="", body="").model_dump(),
            {"title": "", "body": "", "project_id": None},
        )
        with self.assertRaises(ValidationError):
            schemas.NoteCreate(body="x")
        with self.assertRaises(ValidationError):
            schemas.NoteCreate(title="x")

    def test_update_rejects_empty_patch_and_null_title_or_body(self):
        with self.assertRaises(ValidationError):
            schemas.NoteUpdate()
        with self.assertRaises(ValidationError):
            schemas.NoteUpdate(title=None)
        with self.assertRaises(ValidationError):
            schemas.NoteUpdate(body=None)
        self.assertIsNone(schemas.NoteUpdate(project_id=None).project_id)

    def test_out_preserves_legacy_null_title_and_body(self):
        now = datetime.now(timezone.utc)
        out = schemas.NoteOut(
            id="n1",
            title=None,
            body=None,
            project_id=None,
            created_at=now,
            updated_at=now,
        )
        self.assertIsNone(out.title)
        self.assertIsNone(out.body)

    def test_note_tags_trim_dedupe_case_insensitively_and_reject_empty(self):
        payload = schemas.NoteTagsReplace(
            tags=["  旅行 ", "重要", "旅行", "IMPORTANT", "important"]
        )
        self.assertEqual(payload.tags, ["旅行", "重要", "IMPORTANT"])
        with self.assertRaises(ValidationError):
            schemas.NoteTagsReplace(tags=["ok", "   "])


class NotesRouterBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_notes_search_uses_postgres_fts_with_literal_contains_fallback(self):
        from app.api.notes import list_notes

        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        await list_notes(q="家庭旅行", _user={"sub": "u"}, db=db)

        statement = db.execute.await_args.args[0]
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        self.assertIn("to_tsvector", sql)
        self.assertIn("plainto_tsquery", sql)
        self.assertIn("@@", sql)
        self.assertIn("lower(notes.title)", sql)
        self.assertIn("lower(notes.body)", sql)

    async def test_list_notes_blank_search_keeps_recent_notes_query(self):
        from app.api.notes import list_notes

        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        await list_notes(q="   ", _user={"sub": "u"}, db=db)

        statement = db.execute.await_args.args[0]
        sql = str(statement.compile(dialect=postgresql.dialect()))
        self.assertNotIn("to_tsvector", sql)
        self.assertIn("ORDER BY notes.updated_at DESC", sql)

    async def test_self_link_returns_422_before_db_access(self):
        from app.api.notes import create_note_link

        db = AsyncMock()
        with self.assertRaises(HTTPException) as ctx:
            await create_note_link(
                "n1",
                schemas.NoteLinkCreate(target_note_id="n1"),
                {"sub": "u"},
                db,
            )
        self.assertEqual(ctx.exception.status_code, 422)
        db.get.assert_not_awaited()

    async def test_duplicate_reverse_link_is_idempotent_without_insert(self):
        from app.api.notes import create_note_link

        source = Note(id="a", title="A", body="")
        target = Note(id="b", title="B", body="")
        db = AsyncMock()
        db.get.side_effect = [source, target]
        result = MagicMock()
        result.scalar_one_or_none.return_value = object()
        db.execute.return_value = result
        with patch("app.api.notes.start_execution", new=AsyncMock()) as start:
            response = await create_note_link(
                "a",
                schemas.NoteLinkCreate(target_note_id="b"),
                {"sub": "u"},
                db,
            )
        self.assertIsNone(response)
        start.assert_not_awaited()
        db.add.assert_not_called()

    async def test_unlink_deletes_bidirectional_link(self):
        from app.api.notes import delete_note_link

        source = Note(id="a", title="A", body="")
        target = Note(id="b", title="B", body="")
        db = AsyncMock()
        db.get.side_effect = [source, target]
        existing = MagicMock()
        existing.scalar_one_or_none.return_value = NoteLink(
            source_note_id="b",
            target_note_id="a",
        )
        db.execute.side_effect = [existing, MagicMock()]

        with (
            patch("app.api.notes.start_execution", new=AsyncMock(return_value=object())),
            patch("app.api.notes.finish_execution", new=AsyncMock()) as finish,
            patch("app.api.notes.fail_execution", new=AsyncMock()),
        ):
            await delete_note_link("a", "b", {"sub": "u"}, db)

        self.assertEqual(db.execute.await_count, 2)
        db.commit.assert_awaited_once()
        finish.assert_awaited_once()

    async def test_missing_source_or_target_returns_404(self):
        from app.api.notes import create_note_link

        db = AsyncMock()
        db.get.return_value = None
        with self.assertRaises(HTTPException) as source_ctx:
            await create_note_link(
                "missing",
                schemas.NoteLinkCreate(target_note_id="b"),
                {"sub": "u"},
                db,
            )
        self.assertEqual(source_ctx.exception.status_code, 404)

        db = AsyncMock()
        db.get.side_effect = [Note(id="a", title="A", body=""), None]
        with self.assertRaises(HTTPException) as target_ctx:
            await create_note_link(
                "a",
                schemas.NoteLinkCreate(target_note_id="missing"),
                {"sub": "u"},
                db,
            )
        self.assertEqual(target_ctx.exception.status_code, 404)

    async def test_delete_note_cleans_links_tags_and_drive_relations_before_delete(self):
        from app.api.notes import delete_note

        note = Note(id="a", title="A", body="")
        db = AsyncMock()
        db.get.return_value = note
        with (
            patch("app.api.notes.start_execution", new=AsyncMock(return_value=object())),
            patch("app.api.notes.finish_execution", new=AsyncMock()),
            patch("app.api.notes.fail_execution", new=AsyncMock()),
        ):
            await delete_note("a", {"sub": "u"}, db)
        self.assertEqual(db.execute.await_count, 3)
        db.delete.assert_awaited_once_with(note)
        db.commit.assert_awaited()

    async def test_replace_tags_reuses_existing_tag_and_creates_missing_tag(self):
        from app.api.notes import replace_note_tags

        note = Note(id="a", title="A", body="")
        existing_tag = MagicMock()
        existing_tag.id = "existing"
        db = AsyncMock()
        db.get.return_value = note

        delete_result = MagicMock()
        first_lookup = MagicMock()
        first_lookup.scalar_one_or_none.return_value = existing_tag
        second_lookup = MagicMock()
        second_lookup.scalar_one_or_none.return_value = None
        db.execute.side_effect = [delete_result, first_lookup, second_lookup]

        with (
            patch("app.api.notes.start_execution", new=AsyncMock(return_value=object())),
            patch("app.api.notes.finish_execution", new=AsyncMock()),
            patch("app.api.notes.fail_execution", new=AsyncMock()),
        ):
            response = await replace_note_tags(
                "a",
                schemas.NoteTagsReplace(tags=["既有", "新增"]),
                {"sub": "u"},
                db,
            )

        self.assertEqual(response.tags, ["既有", "新增"])
        self.assertEqual(db.add.call_count, 3)
        db.flush.assert_awaited_once()
        db.commit.assert_awaited_once()


class NotesConfirmationPolicyTests(unittest.TestCase):
    def test_note_delete_requires_target_bound_explicit_confirmation(self):
        self.assertEqual(
            confirmation_requirement("DELETE", "/api/v1/notes/n-1"),
            ("note.delete", "n-1"),
        )
        self.assertEqual(
            explicit_confirmation_value("note.delete", "n-1"),
            "explicit_user:note.delete:n-1",
        )
        self.assertIsNone(
            confirmation_requirement("DELETE", "/api/v1/notes/n-1/links/n-2")
        )


class NotesMainRegistrationTests(unittest.TestCase):
    def test_main_registers_notes_router(self):
        path = Path(__file__).parents[1] / "app/main.py"
        source = path.read_text()
        self.assertIn("from app.api.notes import router as notes_router", source)
        self.assertIn('app.include_router(notes_router, prefix="/api/v1", dependencies=[Depends(feature_gate("notes"))])', source)


class NotesHttpContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_unauthenticated_notes_returns_401_with_request_id(self):
        import httpx
        from fastapi import FastAPI, Request
        from app.api.notes import router

        app = FastAPI()

        @app.middleware("http")
        async def request_id_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Request-ID"] = "task2-test"
            return response

        app.include_router(router, prefix="/api/v1")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/notes")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("X-Request-ID"), "task2-test")


class NotesSourceContractTests(unittest.TestCase):
    def test_router_uses_life_assistant_audit_without_note_body_in_summaries(self):
        path = Path(__file__).parents[1] / "app/api/notes.py"
        source = path.read_text()
        self.assertIn('provider="life_assistant"', source)
        self.assertNotIn("summary=body.", source)
        self.assertNotIn("summary=body.body", source)


if __name__ == "__main__":
    unittest.main()
