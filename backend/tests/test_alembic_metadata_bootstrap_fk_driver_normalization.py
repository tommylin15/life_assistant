from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from scripts import preflight_alembic_metadata_bootstrap as preflight


class ForeignKeyActionNormalizationTests(unittest.IsolatedAsyncioTestCase):
    def test_internal_char_normalization_accepts_driver_variants(self):
        self.assertEqual("a", preflight._normalize_pg_internal_char("a"))
        self.assertEqual("a", preflight._normalize_pg_internal_char(b"a"))
        self.assertEqual("a", preflight._normalize_pg_internal_char(bytearray(b"a")))
        self.assertEqual("a", preflight._normalize_pg_internal_char(memoryview(b"a")))

    async def test_foreign_key_contracts_decode_async_driver_bytes(self):
        conn = AsyncMock()
        conn.execute.return_value = [
            SimpleNamespace(
                local_column="source_note_id",
                foreign_table="notes",
                foreign_column="id",
                update_action=b"a",
                delete_action=b"a",
                condeferrable=False,
                condeferred=False,
                convalidated=True,
            ),
            SimpleNamespace(
                local_column="target_note_id",
                foreign_table="notes",
                foreign_column="id",
                update_action=b"a",
                delete_action=b"a",
                condeferrable=False,
                condeferred=False,
                convalidated=True,
            ),
        ]

        contracts = await preflight._foreign_key_contracts(conn, "note_links")

        self.assertEqual(preflight.EXPECTED_FOREIGN_KEY_CONTRACTS["note_links"], contracts)
        preflight.validate_foreign_key_contracts("note_links", contracts)


if __name__ == "__main__":
    unittest.main()
