import os
import unittest
from unittest.mock import patch

from app.config import _bundle_structure_hints, _load_bundle, _parse_bundle


class BundleParsingTests(unittest.TestCase):
    def setUp(self):
        self.db_env = {
            "DATABASE_HOST": "10.42.0.5",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "life_assistant",
            "DATABASE_USER": "life_assistant_user",
            "DATABASE_SSLMODE": "require",
        }

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

    def test_asyncpg_sslmode_query_is_normalized_to_ssl(self):
        values, bundle_format = _parse_bundle(
            "postgresql://user:pass@10.42.0.5:5432/life_assistant?sslmode=require"
        )

        self.assertEqual(bundle_format, "raw-database-url")
        self.assertEqual(
            values["DATABASE_URL"],
            "postgresql+asyncpg://user:pass@10.42.0.5:5432/life_assistant?ssl=require",
        )

    def test_colon_comma_bundle_preserves_database_url_colons(self):
        values, bundle_format = _parse_bundle(
            "DATABASE_URL:postgresql://life_assistant_user:secret@10.42.0.5:5432/life_assistant?sslmode=require,"
            "GOOGLE_CLIENT_ID:client-id,"
            "GOOGLE_CLIENT_SECRET:client:secret"
        )

        self.assertEqual(bundle_format, "colon-comma")
        self.assertEqual(
            values["DATABASE_URL"],
            "postgresql+asyncpg://life_assistant_user:secret@10.42.0.5:5432/life_assistant?ssl=require",
        )
        self.assertEqual(values["GOOGLE_CLIENT_ID"], "client-id")
        self.assertEqual(values["GOOGLE_CLIENT_SECRET"], "client:secret")

    def test_json_password_field_builds_database_url(self):
        env = {
            **self.db_env,
            "LIFE_ASSISTANT_BUNDLE": '{"DATABASE_PASSWORD":"p@ss word/with:specials","GOOGLE_CLIENT_ID":"client"}',
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("DATABASE_URL", None)
            bundle_format = _load_bundle()
            database_url = os.environ["DATABASE_URL"]

        self.assertEqual(bundle_format, "json-object")
        self.assertTrue(database_url.startswith("postgresql+asyncpg://life_assistant_user:"))
        self.assertIn("@10.42.0.5:5432/life_assistant?ssl=require", database_url)
        self.assertNotIn("p@ss word/with:specials", database_url)

    def test_dotenv_password_field_builds_database_url(self):
        env = {
            **self.db_env,
            "LIFE_ASSISTANT_BUNDLE": "DB_PASSWORD=p@ss-word\nGOOGLE_CLIENT_ID=client\n",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("DATABASE_URL", None)
            bundle_format = _load_bundle()
            database_url = os.environ["DATABASE_URL"]

        self.assertEqual(bundle_format, "dotenv")
        self.assertIn("@10.42.0.5:5432/life_assistant?ssl=require", database_url)

    def test_yaml_nested_password_field_builds_database_url(self):
        env = {
            **self.db_env,
            "LIFE_ASSISTANT_BUNDLE": "database:\n  password: p@ss-word\ngoogle_client_id: client\n",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("DATABASE_URL", None)
            bundle_format = _load_bundle()
            database_url = os.environ["DATABASE_URL"]

        self.assertEqual(bundle_format, "yaml-object")
        self.assertIn("@10.42.0.5:5432/life_assistant?ssl=require", database_url)

    def test_double_encoded_json_bundle_is_supported(self):
        values, bundle_format = _parse_bundle(
            '"{\\"DATABASE_PASSWORD\\":\\"secret\\"}"'
        )

        self.assertEqual(bundle_format, "json-object")
        self.assertEqual(values["DATABASE_PASSWORD"], "secret")

    def test_bundle_structure_hints_do_not_expose_values(self):
        shape, password_hints, key_hints = _bundle_structure_hints(
            "DB_PASS:super-secret-value,GOOGLE_CLIENT_SECRET:other-secret"
        )

        self.assertIn("colon", shape)
        self.assertIn("comma", shape)
        self.assertIn("DB_PASS", password_hints)
        self.assertIn("DB_PASS", key_hints)
        self.assertIn("GOOGLE_CLIENT_SECRET", key_hints)
        rendered = repr((shape, password_hints, key_hints))
        self.assertNotIn("super-secret-value", rendered)
        self.assertNotIn("other-secret", rendered)

    def test_unknown_bundle_fails_closed(self):
        env = {**self.db_env, "LIFE_ASSISTANT_BUNDLE": "not a supported bundle payload"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("DATABASE_URL", None)
            bundle_format = _load_bundle()

        self.assertEqual(bundle_format, "unknown")
        self.assertNotIn("DATABASE_URL", os.environ)


if __name__ == "__main__":
    unittest.main()
