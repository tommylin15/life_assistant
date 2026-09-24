import os
import unittest
from unittest.mock import patch

from app.config import _load_bundle, _parse_bundle


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

    def test_opaque_secret_can_be_explicitly_wired_as_database_password(self):
        env = {
            "LIFE_ASSISTANT_BUNDLE": "p@ss word/with:specials",
            "LIFE_ASSISTANT_OPAQUE_SECRET_KIND": "database-password",
            "DATABASE_HOST": "10.42.0.5",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "life_assistant",
            "DATABASE_USER": "life_assistant_user",
            "DATABASE_SSLMODE": "require",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("DATABASE_URL", None)
            bundle_format = _load_bundle()
            database_url = os.environ["DATABASE_URL"]

        self.assertEqual(bundle_format, "opaque-database-password")
        self.assertTrue(database_url.startswith("postgresql+asyncpg://life_assistant_user:"))
        self.assertIn("@10.42.0.5:5432/life_assistant?sslmode=require", database_url)
        self.assertNotIn("p@ss word/with:specials", database_url)


if __name__ == "__main__":
    unittest.main()
