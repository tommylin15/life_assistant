import py_compile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from scripts import run_drive_external_ai_acceptance as external_ai_acceptance
from scripts import run_drive_production_config_acceptance as production_config_acceptance
from scripts import run_drive_knowledge_runtime_acceptance as runtime_acceptance


class _ConstraintError(RuntimeError):
    def __init__(self, constraint_name: str):
        super().__init__(f'constraint {constraint_name}')
        self.constraint_name = constraint_name


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

    def test_live_external_ai_runner_classifies_incomplete_config_without_exposing_values(self):
        classifier = getattr(external_ai_acceptance, "_exit_code_for_unavailable_provider", None)
        self.assertTrue(callable(classifier))
        if not callable(classifier):
            return

        cases = (
            ({"provider": "disabled", "model": "gpt-test", "api_key": "secret", "base_url": "https://example.invalid/v1"}, 84),
            ({"provider": "openai", "model": "", "api_key": "secret", "base_url": "https://example.invalid/v1"}, 86),
            ({"provider": "openai", "model": "gpt-test", "api_key": "", "base_url": "https://example.invalid/v1"}, 87),
            ({"provider": "openai", "model": "gpt-test", "api_key": "secret", "base_url": ""}, 88),
        )
        observed: set[int] = set()
        for values, expected in cases:
            code = classifier(**values)
            self.assertEqual(code, expected)
            self.assertGreater(code, 0)
            self.assertLess(code, 256)
            observed.add(code)
        self.assertEqual(len(observed), len(cases))

        source = self.ai_script.read_text(encoding="utf-8")
        self.assertNotIn("print(api_key", source)
        self.assertNotIn("print(model", source)

    def test_picker_config_classifier_reports_combined_missing_fields_without_values(self):
        classifier = getattr(production_config_acceptance, "_exit_code_for_config_state", None)
        self.assertTrue(callable(classifier))
        if not callable(classifier):
            return

        self.assertEqual(
            classifier(
                google_client_id="client",
                developer_key="",
                app_id="",
            ),
            96,
        )
        self.assertEqual(
            classifier(
                google_client_id="",
                developer_key="",
                app_id="",
            ),
            97,
        )

    def test_live_external_ai_runner_reports_combined_missing_fields(self):
        classifier = external_ai_acceptance._exit_code_for_unavailable_provider
        self.assertEqual(
            classifier(
                provider="disabled",
                model="",
                api_key="",
                base_url="https://api.openai.com/v1",
            ),
            107,
        )
        self.assertEqual(
            classifier(
                provider="",
                model="",
                api_key="",
                base_url="",
            ),
            115,
        )

    def test_live_external_ai_provider_failure_diagnostics_are_byte_safe(self):
        classifier = external_ai_acceptance._exit_code_for_provider_error
        cases = (
            (external_ai_acceptance.AIProviderError("provider_http_error"), 120),
            (external_ai_acceptance.AIProviderError("provider_http_error", status_code=400), 121),
            (external_ai_acceptance.AIProviderError("provider_http_error", status_code=401), 122),
            (external_ai_acceptance.AIProviderError("provider_http_error", status_code=408), 123),
            (external_ai_acceptance.AIProviderError("provider_http_error", status_code=429), 124),
            (external_ai_acceptance.AIProviderError("provider_http_error", status_code=503), 125),
            (external_ai_acceptance.AIProviderError("provider_http_error", status_code=418), 126),
            (external_ai_acceptance.AIProviderError("provider_invalid_output"), 127),
            (external_ai_acceptance.AIProviderError("provider_unavailable"), 128),
            (external_ai_acceptance.AIProviderError("unexpected"), 130),
        )
        observed = set()
        for exc, expected in cases:
            with self.subTest(code=exc.code, status=exc.status_code):
                actual = classifier(exc)
                self.assertEqual(actual, expected)
                self.assertGreater(actual, 0)
                self.assertLess(actual, 256)
                observed.add(actual)
        self.assertEqual(len(observed), len(cases))

    def test_live_external_ai_provider_specific_exit_preserves_provider_identity(self):
        encode = external_ai_acceptance._provider_specific_diagnostic_exit
        self.assertEqual(
            encode("gemini", external_ai_acceptance.EXIT_PROVIDER_HTTP_RATE_LIMIT),
            144,
        )
        self.assertEqual(
            encode("openrouter", external_ai_acceptance.EXIT_PROVIDER_HTTP_RATE_LIMIT),
            159,
        )
        self.assertEqual(
            encode("groq", external_ai_acceptance.EXIT_PROVIDER_HTTP_RATE_LIMIT),
            174,
        )
        self.assertEqual(
            encode("openai", external_ai_acceptance.EXIT_PROVIDER_HTTP_RATE_LIMIT),
            189,
        )
        self.assertEqual(encode("unknown", 124), 124)

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

    def test_drive_knowledge_ui_acceptance_pins_valid_browser_locale_and_timezone(self):
        source = self.ui_script.read_text(encoding="utf-8")
        self.assertIn("locale: 'zh-TW'", source)
        self.assertIn("timezoneId: 'Asia/Taipei'", source)
        self.assertIn("serviceWorkers: 'block'", source)

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

    def test_import_integrity_failure_identifies_safe_constraint_family(self):
        classifier = getattr(runtime_acceptance, "_exit_code_for_stage_error", None)
        self.assertTrue(callable(classifier))
        if not callable(classifier):
            return

        expected_codes = {
            "note_drive_documents_note_id_fkey": 75,
            "note_drive_documents_drive_document_id_fkey": 76,
            "entity_tags_pkey": 77,
            "entity_tags_tag_id_fkey": 78,
            "tags_name_key": 79,
            "note_drive_documents_pkey": 80,
        }
        observed: set[int] = set()
        for constraint_name, expected in expected_codes.items():
            cause = IntegrityError("insert", {}, _ConstraintError(constraint_name))
            error = runtime_acceptance.AcceptanceStageError("import", cause)
            code = classifier(error)
            self.assertEqual(code, expected)
            self.assertGreater(code, 0)
            self.assertLess(code, 256)
            observed.add(code)

        self.assertEqual(len(observed), len(expected_codes))
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


class DriveAIProviderScopedDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _settings():
        return SimpleNamespace(
            ai_enrichment_provider="gemini",
            ai_enrichment_model="latest-3-flash",
            ai_enrichment_fallback_provider="groq",
            ai_enrichment_fallback_model="openai/gpt-oss-120b",
            ai_enrichment_tertiary_provider="openrouter",
            ai_enrichment_tertiary_model="openrouter/free",
        )

    async def test_combined_failure_retains_mask_93_for_gemini_and_openrouter(self):
        seen = []

        async def check(*, provider_name, model):
            seen.append((provider_name, model))
            if provider_name in {"gemini", "openrouter"}:
                raise SystemExit(external_ai_acceptance.EXIT_PROVIDER_HTTP_RATE_LIMIT)

        with (
            patch.object(external_ai_acceptance.config, "settings", self._settings()),
            patch.object(external_ai_acceptance, "run_acceptance", new=check),
            self.assertRaises(SystemExit) as failure,
        ):
            await external_ai_acceptance.run_configured_providers()
        self.assertEqual(failure.exception.code, 93)
        self.assertEqual([name for name, _ in seen], ["gemini", "groq", "openrouter"])

    async def test_scoped_gemini_failure_preserves_429_without_running_fallbacks(self):
        seen = []

        async def check(*, provider_name, model):
            seen.append(provider_name)
            raise SystemExit(external_ai_acceptance.EXIT_PROVIDER_HTTP_RATE_LIMIT)

        with (
            patch.object(external_ai_acceptance.config, "settings", self._settings()),
            patch.object(external_ai_acceptance, "run_acceptance", new=check),
            self.assertRaises(SystemExit) as failure,
        ):
            await external_ai_acceptance.run_configured_providers(only_provider="gemini")
        self.assertEqual(failure.exception.code, 144)
        self.assertEqual(seen, ["gemini"])

    async def test_scoped_openrouter_failure_preserves_5xx_without_running_fallbacks(self):
        seen = []

        async def check(*, provider_name, model):
            seen.append(provider_name)
            raise SystemExit(external_ai_acceptance.EXIT_PROVIDER_HTTP_5XX)

        with (
            patch.object(external_ai_acceptance.config, "settings", self._settings()),
            patch.object(external_ai_acceptance, "run_acceptance", new=check),
            self.assertRaises(SystemExit) as failure,
        ):
            await external_ai_acceptance.run_configured_providers(only_provider="openrouter")
        self.assertEqual(failure.exception.code, 160)
        self.assertEqual(seen, ["openrouter"])

    async def test_scoped_provider_missing_from_runtime_config_is_not_verified(self):
        async def should_not_run(*, provider_name, model):
            self.fail("unconfigured provider must not be called")

        with (
            patch.object(external_ai_acceptance.config, "settings", self._settings()),
            patch.object(external_ai_acceptance, "run_acceptance", new=should_not_run),
            self.assertRaises(SystemExit) as failure,
        ):
            await external_ai_acceptance.run_configured_providers(only_provider="openai")
        self.assertEqual(failure.exception.code, external_ai_acceptance.EXIT_NOT_CONFIGURED)

    def test_workflow_runs_bounded_provider_scoped_diagnostics_only_on_failure(self):
        workflow = (
            Path(__file__).parents[2] /
            ".github/workflows/drive-knowledge-runtime-acceptance.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("--only-provider=gemini", workflow)
        self.assertIn("--only-provider=openrouter", workflow)
        self.assertIn("if: steps.external_ai.outcome == 'failure'", workflow)
        self.assertIn("continue-on-error: true", workflow)


if __name__ == "__main__":
    unittest.main()
