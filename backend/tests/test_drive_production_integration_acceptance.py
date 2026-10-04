import py_compile
import unittest
from pathlib import Path

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from scripts import run_drive_knowledge_runtime_acceptance as runtime_acceptance


class DriveProductionIntegrationAcceptanceContractTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).parents[2]
        self.config_script = (
            self.repo_root / "backend/scripts/run_drive_production_config_acceptance.py"
        )
        self.ai_script = (
            self.repo_root / "backend/scripts/run_drive_external_ai_acceptance.py"
        )
        self.workflow = (
            self.repo_root / ".github/workflows/drive-knowledge-runtime-acceptance.yml"
        )
        self.ui_script = (
            self.repo_root / ".github/scripts/verify_drive_knowledge_production.mjs"
        )
        self.config_source = (
            self.repo_root / "backend/app/config.py"
        ).read_text(encoding="utf-8")

    def test_production_config_runner_exists_and_checks_runtime_loaded_picker_config(self):
        self.assertTrue(self.config_script.is_file())
        py_compile.compile(str(self.config_script), doraise=True)
        source = self.config_script.read_text(encoding="utf-8")
        for expected in (
            "GOOGLE_PICKER_DEVELOPER_KEY",
            "GOOGLE_PICKER_APP_ID",
            "google_client_id",
            "drive_picker_runtime_config=PASS",
        ):
            self.assertIn(expected, source)
        self.assertNotIn("print(developer_key", source)
        self.assertNotIn("print(app_id", source)

    def test_legacy_bundle_parser_recognizes_picker_keys(self):
        self.assertIn('"GOOGLE_PICKER_DEVELOPER_KEY"', self.config_source)
        self.assertIn('"GOOGLE_PICKER_APP_ID"', self.config_source)

    def test_live_external_ai_runner_uses_only_synthetic_context(self):
        self.assertTrue(self.ai_script.is_file())
        py_compile.compile(str(self.ai_script), doraise=True)
        source = self.ai_script.read_text(encoding="utf-8")
        for expected in (
            "get_ai_enrichment_provider",
            "DocumentEnrichmentContext",
            "RelatedNoteCandidate",
            "drive_external_ai_integration=PASS",
            "drive_external_ai_integration=NOT_VERIFIED",
        ):
            self.assertIn(expected, source)
        self.assertNotIn("DriveDocument", source)
        self.assertNotIn("SessionLocal", source)
        self.assertNotIn("googleapis.com", source)

    def test_task9_workflow_executes_runtime_config_and_live_ai_gates(self):
        self.assertTrue(self.workflow.is_file())
        source = self.workflow.read_text(encoding="utf-8")
        for expected in (
            "scripts.run_drive_production_config_acceptance",
            "scripts.run_drive_external_ai_acceptance",
            "Run Drive production config acceptance",
            "Run live external AI acceptance",
            "steps.production_config.outcome",
            "steps.external_ai.outcome",
        ):
            self.assertIn(expected, source)
        self.assertNotIn(
            'drive_external_ai_integration=NOT_VERIFIED reason=production_provider_adapter_not_enabled',
            source,
        )

    def test_drive_knowledge_ui_acceptance_waits_for_attached_flutter_root_with_diagnostics(self):
        source = self.ui_script.read_text(encoding="utf-8")
        self.assertIn("page.locator('flutter-view')", source)
        self.assertIn("state: 'attached'", source)
        self.assertIn("page.on('pageerror'", source)
        self.assertIn("page.on('console'", source)
        self.assertIn("page.on('requestfailed'", source)
        self.assertNotIn("waitForSelector('flutter-view'", source)

    def test_import_stage_failures_have_distinct_byte_safe_diagnostics(self):
        classifier = getattr(runtime_acceptance, "_exit_code_for_stage_error", None)
        self.assertTrue(callable(classifier))
        if not callable(classifier):
            return

        cases = (
            (AssertionError("HTTP 500"), 71),
            (IntegrityError("insert", {}, RuntimeError("unique violation")), 72),
            (SQLAlchemyError("database failure"), 73),
            (RuntimeError("unexpected"), 74),
        )
        observed: set[int] = set()
        for cause, expected in cases:
            error = runtime_acceptance.AcceptanceStageError("import", cause)
            code = classifier(error)
            self.assertEqual(code, expected)
            self.assertGreater(code, 0)
            self.assertLess(code, 256)
            observed.add(code)

        self.assertEqual(len(observed), len(cases))
        self.assertTrue(observed.isdisjoint(runtime_acceptance.STAGE_EXIT_CODES.values()))

    def test_non_import_stage_keeps_existing_stage_exit_code(self):
        classifier = getattr(runtime_acceptance, "_exit_code_for_stage_error", None)
        self.assertTrue(callable(classifier))
        if not callable(classifier):
            return
        error = runtime_acceptance.AcceptanceStageError(
            "verify_import",
            AssertionError("verification failed"),
        )
        self.assertEqual(
            classifier(error),
            runtime_acceptance.STAGE_EXIT_CODES["verify_import"],
        )


if __name__ == "__main__":
    unittest.main()
