import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.models.drive import DriveDocument


class DriveTagSchemaTests(unittest.TestCase):
    def test_drive_tag_schema_normalizes_case_insensitive_duplicates(self):
        from app.models.drive_schemas import DriveTagsOut, DriveTagsReplace

        payload = DriveTagsReplace(tags=[" Budget ", "budget", "重要"])
        self.assertEqual(payload.tags, ["Budget", "重要"])
        self.assertEqual(DriveTagsOut(tags=payload.tags).tags, ["Budget", "重要"])


class DriveTagApiContractTests(unittest.TestCase):
    def test_drive_router_has_get_and_put_tag_routes(self):
        from app.api.drive import router

        routes = {(route.path, frozenset(route.methods or set())) for route in router.routes}
        self.assertIn(
            ("/drive/documents/{document_id}/tags", frozenset({"GET"})),
            routes,
        )
        self.assertIn(
            ("/drive/documents/{document_id}/tags", frozenset({"PUT"})),
            routes,
        )


class DriveTagApiBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_validates_owned_document_before_reading_tags(self):
        from app.api.drive import list_drive_document_tags

        db = AsyncMock()
        with (
            patch(
                "app.api.drive.get_owned_document",
                new=AsyncMock(side_effect=HTTPException(404, "Drive document not found")),
            ) as owned,
            patch("app.api.drive.list_entity_tags", new=AsyncMock()) as list_tags,
        ):
            with self.assertRaises(HTTPException) as ctx:
                await list_drive_document_tags("d1", {"sub": "user-b"}, db)

        self.assertEqual(ctx.exception.status_code, 404)
        owned.assert_awaited_once_with(db, "user-b", "d1")
        list_tags.assert_not_awaited()

    async def test_list_uses_drive_document_entity_namespace(self):
        from app.api.drive import list_drive_document_tags

        db = AsyncMock()
        document = DriveDocument(
            id="d1",
            owner_sub="user-a",
            google_file_id="g1",
            name="Budget",
            mime_type="text/plain",
        )
        with (
            patch("app.api.drive.get_owned_document", new=AsyncMock(return_value=document)),
            patch(
                "app.api.drive.list_entity_tags",
                new=AsyncMock(return_value=["Budget", "重要"]),
            ) as list_tags,
        ):
            response = await list_drive_document_tags("d1", {"sub": "user-a"}, db)

        self.assertEqual(response.tags, ["Budget", "重要"])
        list_tags.assert_awaited_once_with(db, "drive_document", "d1")

    async def test_replace_is_owner_scoped_and_commits_service_result(self):
        from app.api.drive import replace_drive_document_tags
        from app.models.drive_schemas import DriveTagsReplace

        db = AsyncMock()
        document = DriveDocument(
            id="d1",
            owner_sub="user-a",
            google_file_id="g1",
            name="Budget",
            mime_type="text/plain",
        )
        with (
            patch("app.api.drive.get_owned_document", new=AsyncMock(return_value=document)) as owned,
            patch(
                "app.api.drive.replace_entity_tags",
                new=AsyncMock(return_value=["Budget", "重要"]),
            ) as replace_tags,
            patch("app.api.drive.start_execution", new=AsyncMock(return_value=object())),
            patch("app.api.drive.finish_execution", new=AsyncMock()) as finish,
            patch("app.api.drive.fail_execution", new=AsyncMock()),
        ):
            response = await replace_drive_document_tags(
                "d1",
                DriveTagsReplace(tags=[" Budget ", "budget", "重要"]),
                {"sub": "user-a"},
                db,
            )

        self.assertEqual(response.tags, ["Budget", "重要"])
        owned.assert_awaited_once_with(db, "user-a", "d1")
        replace_tags.assert_awaited_once_with(
            db,
            "drive_document",
            "d1",
            ["Budget", "重要"],
        )
        db.commit.assert_awaited_once()
        finish.assert_awaited_once()

    async def test_replace_cross_user_document_fails_before_tag_mutation(self):
        from app.api.drive import replace_drive_document_tags
        from app.models.drive_schemas import DriveTagsReplace

        db = AsyncMock()
        with (
            patch(
                "app.api.drive.get_owned_document",
                new=AsyncMock(side_effect=HTTPException(404, "Drive document not found")),
            ),
            patch("app.api.drive.replace_entity_tags", new=AsyncMock()) as replace_tags,
            patch("app.api.drive.start_execution", new=AsyncMock()) as start,
        ):
            with self.assertRaises(HTTPException) as ctx:
                await replace_drive_document_tags(
                    "d1",
                    DriveTagsReplace(tags=["private"]),
                    {"sub": "other-user"},
                    db,
                )

        self.assertEqual(ctx.exception.status_code, 404)
        replace_tags.assert_not_awaited()
        start.assert_not_awaited()
        db.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
