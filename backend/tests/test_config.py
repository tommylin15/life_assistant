import unittest

from app.config import _parse_bundle


class BundleParsingTests(unittest.TestCase):
    def test_json_object_bundle(self):
        values, bundle_format = _parse_bundle(
            '{"DATABASE_URL":"postgresql://user:pass@10.42.0.5:5432/life_assistant","FRONTEND_URL":"https://example.test"}'
        )

        self.assertEqual(bundle_format, "json-object")
        self.assertEqual(
            values["DATABASE_URL"],
            "postgresql+asyncpg://user:pass@10.42.0.5:5432/life_assistant",
        )
        self.assertEqual(values["FRONTEND_URL"], "https://example.test")

    def test_dotenv_bundle(self):
        values, bundle_format = _parse_bundle(
            "DATABASE_URL=postgresql://user:pass@10.42.0.5:5432/life_assistant\n"
            "FRONTEND_URL=https://example.test\n"
        )

        self.assertEqual(bundle_format, "dotenv")
        self.assertEqual(
            values["DATABASE_URL"],
            "postgresql+asyncpg://user:pass@10.42.0.5:5432/life_assistant",
        )
        self.assertEqual(values["FRONTEND_URL"], "https://example.test")

    def test_raw_database_url_bundle(self):
        values, bundle_format = _parse_bundle(
            "postgresql://user:pass@10.42.0.5:5432/life_assistant"
        )

        self.assertEqual(bundle_format, "raw-database-url")
        self.assertEqual(
            values["DATABASE_URL"],
            "postgresql+asyncpg://user:pass@10.42.0.5:5432/life_assistant",
        )

    def test_unknown_bundle_fails_closed(self):
        values, bundle_format = _parse_bundle("not a supported bundle payload")

        self.assertEqual(values, {})
        self.assertEqual(bundle_format, "unknown")


if __name__ == "__main__":
    unittest.main()
