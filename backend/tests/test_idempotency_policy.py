from pathlib import Path
import unittest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.exc import IntegrityError

from app.errors import ApiError
from app.models.execution_log import ExecutionLog
from app.services.idempotency import (
    normalize_action_id,
    request_fingerprint,
    reserve_execution,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = REPO_ROOT / "backend" / "alembic" / "versions" / "20260928_0006_action_id_idempotency.py"
RUNTIME = REPO_ROOT / "backend" / "scripts" / "run_idempotency_acceptance.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-cloud-run.yml"
TASKS = REPO_ROOT / "backend" / "app" / "api" / "tasks.py"
PROJECTS = REPO_ROOT / "backend" / "app" / "api" / "projects.py"


class IdempotencyContractTests(unittest.TestCase):
    def test_action_id_validation_is_fail_closed(self):
        self.assertEqual(normalize_action_id("action-1"), "action-1")
        self.assertEqual(normalize_action_id("  action:1  "), "action:1")
        self.assertIsNone(normalize_action_id(None))
        for invalid in ("", "has spaces", "x" * 129, "bad/value"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ApiError) as caught:
                    normalize_action_id(invalid)
                self.assertEqual(caught.exception.status_code, 400)
                self.assertEqual(caught.exception.code, "invalid_action_id")

    def test_request_fingerprint_is_canonical(self):
        left = request_fingerprint({"b": [2, 1], "a": 1})
        right = request_fingerprint({"a": 1, "b": [2, 1]})
        different = request_fingerprint({"a": 1, "b": [1, 2]})
        self.assertEqual(left, right)
        self.assertNotEqual(left, different)
        self.assertEqual(len(left), 64)

    def test_execution_log_has_durable_idempotency_schema(self):
        self.assertIn("request_hash", ExecutionLog.__table__.columns)
        index = next(
            item
            for item in ExecutionLog.__table__.indexes
            if item.name == "uq_execution_logs_user_action_type_action_id"
        )
        self.assertTrue(index.unique)
        self.assertEqual(
            [column.name for column in index.columns],
            ["user_sub", "action_type", "action_id"],
        )
        where = str(index.dialect_options["postgresql"]["where"])
        self.assertIn("action_id IS NOT NULL", where)

    def test_task_and_project_create_accept_action_id_header(self):
        for path in (TASKS, PROJECTS):
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
            self.assertIn("ACTION_ID_HEADER", source)
            self.assertIn("reserve_execution", source)
            self.assertIn("commit_reserved_execution", source)
            self.assertIn("replay_entity", source)

    def test_migration_adds_hash_and_partial_unique_index(self):
        source = MIGRATION.read_text(encoding="utf-8")
        compile(source, str(MIGRATION), "exec")
        self.assertIn('revision: str = "20260928_0006"', source)
        self.assertIn('down_revision: Union[str, None] = "20260927_0005"', source)
        self.assertIn('sa.Column("request_hash", sa.String(length=64)', source)
        self.assertIn("uq_execution_logs_user_action_type_action_id", source)
        self.assertIn('postgresql_where=sa.text("action_id IS NOT NULL")', source)

    def test_runtime_gate_is_wired_after_cloud_domain_acceptance(self):
        runner = RUNTIME.read_text(encoding="utf-8")
        compile(runner, str(RUNTIME), "exec")
        for marker in (
            "X-Life-Assistant-Action-ID",
            "idempotency_conflict",
            "action_id_replay_same_result",
            "action_id_single_database_write",
            "action_id_single_activity_row",
            "idempotency_cleanup",
        ):
            self.assertIn(marker, runner)

        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "CORE_ACCEPTANCE_JOB: life-assistant-core-acceptance",
            workflow,
        )
        self.assertIn('gcloud run jobs execute "$CORE_ACCEPTANCE_JOB"', workflow)
        self.assertIn("Run action-id idempotency runtime acceptance", workflow)
        self.assertIn("--args=-m,scripts.run_idempotency_acceptance", workflow)
        self.assertLess(
            workflow.index("Run authenticated cloud-domain acceptance"),
            workflow.index("Run action-id idempotency runtime acceptance"),
        )


class IdempotencyReservationTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_successful_action_is_replayed(self):
        payload = {"name": "Project", "status": "active"}
        fingerprint = request_fingerprint(payload)
        existing = ExecutionLog(
            id="execution-1",
            request_id="request-1",
            action_id="action-1",
            request_hash=fingerprint,
            user_sub="user-1",
            action_type="project.create",
            entity_type="project",
            entity_id="project-1",
            provider="internal",
            status="success",
            result="created",
        )
        result = MagicMock()
        result.scalar_one_or_none.return_value = existing
        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock(
            side_effect=IntegrityError("INSERT", {}, Exception("duplicate"))
        )
        db.rollback = AsyncMock()
        db.execute = AsyncMock(return_value=result)
        db.refresh = AsyncMock()

        reservation = await reserve_execution(
            db,
            user_sub="user-1",
            action_type="project.create",
            action_id="action-1",
            request_payload=payload,
            provider="internal",
            entity_type="project",
        )

        self.assertTrue(reservation.is_replay)
        self.assertIs(reservation.execution, existing)
        db.rollback.assert_awaited_once()

    async def test_duplicate_action_with_different_payload_is_conflict(self):
        existing = ExecutionLog(
            id="execution-1",
            request_id="request-1",
            action_id="action-1",
            request_hash=request_fingerprint({"name": "Original"}),
            user_sub="user-1",
            action_type="project.create",
            entity_type="project",
            entity_id="project-1",
            provider="internal",
            status="success",
            result="created",
        )
        result = MagicMock()
        result.scalar_one_or_none.return_value = existing
        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock(
            side_effect=IntegrityError("INSERT", {}, Exception("duplicate"))
        )
        db.rollback = AsyncMock()
        db.execute = AsyncMock(return_value=result)
        db.refresh = AsyncMock()

        with self.assertRaises(ApiError) as caught:
            await reserve_execution(
                db,
                user_sub="user-1",
                action_type="project.create",
                action_id="action-1",
                request_payload={"name": "Different"},
                provider="internal",
                entity_type="project",
            )

        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(caught.exception.code, "idempotency_conflict")


if __name__ == "__main__":
    unittest.main()
