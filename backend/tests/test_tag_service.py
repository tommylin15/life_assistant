import unittest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.dialects import postgresql

from app.models.migration_support import EntityTag, Tag


class TagServiceContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_entity_tags_returns_shared_vocabulary_names(self):
        from app.services.tag_service import list_entity_tags

        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = ["Budget", "重要"]
        db.execute.return_value = result

        tags = await list_entity_tags(db, "note", "n1")

        self.assertEqual(tags, ["Budget", "重要"])
        statement = db.execute.await_args.args[0]
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        self.assertIn("entity_tags.entity_type = 'note'", sql)
        self.assertIn("entity_tags.entity_id = 'n1'", sql)
        db.commit.assert_not_awaited()

    async def test_replace_reuses_tags_case_insensitively_and_dedupes(self):
        from app.services.tag_service import replace_entity_tags

        existing = Tag(id="tag-existing", name="Budget")
        db = AsyncMock()

        delete_result = MagicMock()
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing
        missing_result = MagicMock()
        missing_result.scalar_one_or_none.return_value = None
        db.execute.side_effect = [delete_result, existing_result, missing_result]

        tags = await replace_entity_tags(
            db,
            "note",
            "n1",
            [" Budget ", "budget", "重要"],
        )

        self.assertEqual(tags, ["Budget", "重要"])
        self.assertEqual(db.add.call_count, 3)
        added = [call.args[0] for call in db.add.call_args_list]
        self.assertIsInstance(added[0], EntityTag)
        self.assertEqual(added[0].tag_id, "tag-existing")
        self.assertIsInstance(added[1], Tag)
        self.assertEqual(added[1].name, "重要")
        self.assertIsInstance(added[2], EntityTag)
        self.assertEqual(added[2].tag_id, added[1].id)
        db.flush.assert_awaited_once()
        db.commit.assert_not_awaited()

        delete_statement = db.execute.await_args_list[0].args[0]
        delete_sql = str(
            delete_statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        self.assertIn("entity_tags.entity_type = 'note'", delete_sql)
        self.assertIn("entity_tags.entity_id = 'n1'", delete_sql)

    async def test_additive_merge_never_removes_user_tags(self):
        from app.services.tag_service import add_entity_tags

        db = AsyncMock()
        current_result = MagicMock()
        current_result.scalars.return_value.all.return_value = ["使用者標籤"]
        missing_result = MagicMock()
        missing_result.scalar_one_or_none.return_value = None
        db.execute.side_effect = [current_result, missing_result]

        tags = await add_entity_tags(
            db,
            "drive_document",
            "d1",
            [" AI建議 ", "ai建議"],
        )

        self.assertEqual(tags, ["使用者標籤", "AI建議"])
        added = [call.args[0] for call in db.add.call_args_list]
        self.assertEqual(len(added), 2)
        self.assertIsInstance(added[0], Tag)
        self.assertIsInstance(added[1], EntityTag)
        self.assertEqual(added[1].entity_type, "drive_document")
        self.assertEqual(added[1].entity_id, "d1")
        self.assertEqual(added[1].tag_id, added[0].id)
        db.flush.assert_awaited_once()
        db.commit.assert_not_awaited()

        for call in db.execute.await_args_list:
            sql = str(call.args[0].compile(dialect=postgresql.dialect()))
            self.assertNotIn("DELETE FROM entity_tags", sql)

    async def test_additive_merge_skips_case_variant_of_existing_entity_tag(self):
        from app.services.tag_service import add_entity_tags

        db = AsyncMock()
        current_result = MagicMock()
        current_result.scalars.return_value.all.return_value = ["Budget"]
        missing_result = MagicMock()
        missing_result.scalar_one_or_none.return_value = None
        db.execute.side_effect = [current_result, missing_result]

        tags = await add_entity_tags(
            db,
            "drive_document",
            "d1",
            ["budget", " New ", "NEW"],
        )

        self.assertEqual(tags, ["Budget", "New"])
        self.assertEqual(db.execute.await_count, 2)
        self.assertEqual(db.add.call_count, 2)
        db.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
