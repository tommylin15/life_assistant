from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_ENV = REPO_ROOT / "backend" / "alembic" / "env.py"


class AlembicOnlineLockContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = ALEMBIC_ENV.read_text(encoding="utf-8")

    def test_postgres_lock_is_transaction_scoped(self):
        self.assertIn("pg_advisory_xact_lock", self.text)
        self.assertNotIn("pg_advisory_lock(:lock_id)", self.text)
        self.assertNotIn("pg_advisory_unlock(:lock_id)", self.text)

    def test_lock_is_acquired_inside_alembic_transaction(self):
        transaction_marker = "with context.begin_transaction():"
        lock_marker = "pg_advisory_xact_lock"
        run_marker = "context.run_migrations()"
        online_section = self.text[self.text.index("def do_run_migrations"):]
        self.assertLess(online_section.index(transaction_marker), online_section.index(lock_marker))
        self.assertLess(online_section.index(lock_marker), online_section.index(run_marker))


if __name__ == "__main__":
    unittest.main()
