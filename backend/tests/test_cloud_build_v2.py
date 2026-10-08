import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import os

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('cloud_build_release', ROOT / 'scripts/cloud_build_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class CloudBuildV2Tests(unittest.TestCase):
    def test_batched_path_detection(self):
        self.assertEqual(release.changes(['backend/app/main.py']), (True, False))
        self.assertEqual(release.changes(['lib/main_web.dart']), (False, True))
        self.assertEqual(release.changes(['cloudbuild.yaml']), (True, True))
        self.assertEqual(release.changes(['doc/todo.md']), (False, False))

    def test_backend_only_release_builds_candidate_preview_but_not_live_frontend(self):
        config = (ROOT / 'cloudbuild.yaml').read_text()
        self.assertIn('test -f .release/frontend-preview || exit 0', config)
        source = (ROOT / 'scripts/cloud_build_release.py').read_text()
        self.assertIn("(STATE / 'frontend-preview').touch()", source)
        self.assertIn("if (STATE / 'frontend').exists() or (STATE / 'frontend-preview').exists():", source)
        self.assertIn("http_gates(preview, hosting=True, expected_sha=os.environ['RELEASE_SHA'])", source)
        self.assertIn("if channel and (STATE / 'frontend').exists():", source)

    def test_backend_only_release_prepare_marks_preview_only(self):
        import tempfile
        sha = 'f' * 40
        old_sha = 'a' * 40
        responses = [
            {'buildTriggerId': 'manual-release'},
            {'name': 'life-assistant-v2-release'},
            {'id': 'ci-trigger'},
            [{'substitutions': {'COMMIT_SHA': sha}}],
            [{'substitutions': {'_PIPELINE': 'release', '_PROMOTE': 'true',
                                'COMMIT_SHA': old_sha}}],
        ]
        def git_run(*args, **kwargs):
            if args[:2] == ('git', 'diff'):
                return 'backend/app/main.py\\n'
            return ''
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(release, 'STATE', Path(folder)),
            patch.dict(os.environ, {'RELEASE_SHA': sha, 'BUILD_ID': 'build',
                                    'GCP_PROJECT_ID': release.PROJECT,
                                    'GCP_REGION': release.REGION,
                                    'PIPELINE': 'release', 'PROMOTE': 'false'}),
            patch.object(release, 'read_json', side_effect=responses),
            patch.object(release, 'current_main', return_value=sha),
            patch.object(release, 'run', side_effect=git_run),
        ):
            release.prepare()
            self.assertTrue((Path(folder) / 'backend').exists())
            self.assertTrue((Path(folder) / 'frontend-preview').exists())
            self.assertFalse((Path(folder) / 'frontend').exists())

    def test_existing_gates_are_preserved(self):
        self.assertEqual(len(release.CORE), 6)
        for gate in ('run_drive_external_ai_acceptance', 'run_calendar_true_account_read_acceptance',
                     'run_shared_codex_identity_acceptance', 'run_drive_google_integration_acceptance'):
            self.assertIn(gate, release.POST)
        self.assertEqual(len(release.UI), 8)

    def test_origin_boundary_for_real_credentials(self):
        from scripts.run_live_release_acceptance import allowed_url
        self.assertTrue(allowed_url('https://gen-lang-client-0593591102.web.app'))
        self.assertTrue(allowed_url('https://v2-candidate---life-assistant-api-2oo7qbkd5q-uc.a.run.app'))
        self.assertFalse(allowed_url('http://localhost:8080'))
        self.assertFalse(allowed_url('https://attacker.web.app'))
        self.assertFalse(allowed_url('https://gen-lang-client-0593591102.web.app.attacker.test'))
        self.assertFalse(allowed_url('https://life-assistant-api-otherproject-uc.a.run.app'))

    def test_regional_logs_and_no_nested_build(self):
        config = (ROOT / 'cloudbuild.yaml').read_text()
        self.assertIn('CLOUD_LOGGING_ONLY', config)
        self.assertNotIn('logsBucket', config)
        self.assertNotIn('gcloud builds submit', config)
        self.assertIn('us-central1', config)

    def test_push_does_not_enter_mutation_steps_and_legacy_is_manual(self):
        import yaml
        config = yaml.safe_load((ROOT / 'cloudbuild.yaml').read_text())
        self.assertEqual(config['substitutions']['_PIPELINE'], 'ci')
        self.assertEqual(config['substitutions']['_PROMOTE'], 'false')
        for step in config['steps'][-2:]:
            self.assertIn('test -f .release/release || exit 0', step['args'][-1])
        for workflow in (ROOT / '.github/workflows').glob('*.yml'):
            if workflow.name != 'ci.yml':
                source = workflow.read_text()
                self.assertIn('workflow_dispatch:', source)
                self.assertNotIn('workflow_run:', source)
                self.assertNotIn('--no-dry-run', source)

    def test_duplicate_sha_phase_is_idempotent_but_promotion_is_distinct(self):
        mine = {'id': 'b', 'createTime': '2'}
        previous = {'id': 'a', 'createTime': '1', 'status': 'SUCCESS',
                    'substitutions': {'COMMIT_SHA': 'f' * 40, '_PROMOTE': 'false'}}
        with patch.dict(os.environ, {'BUILD_ID': 'b', 'TRIGGER_ID': 't',
                                    'RELEASE_SHA': 'f' * 40, 'PROMOTE': 'false'}), \
             patch.object(release, 'read_json', side_effect=[mine, [previous]]), \
             patch.object(release, 'assert_current'):
            self.assertFalse(release.serialized_release())
        with patch.dict(os.environ, {'BUILD_ID': 'b', 'TRIGGER_ID': 't',
                                    'RELEASE_SHA': 'f' * 40, 'PROMOTE': 'true'}), \
             patch.object(release, 'read_json', side_effect=[mine, [previous]]), \
             patch.object(release, 'assert_current'):
            self.assertTrue(release.serialized_release())

    def test_stale_sha_cannot_promote(self):
        with patch.dict(os.environ, {'RELEASE_SHA': 'a' * 40}), \
             patch.object(release, 'current_main', return_value='b' * 40):
            with self.assertRaises(RuntimeError):
                release.assert_current()

    def test_cleanup_protects_runtime_digest_and_other_project_packages(self):
        digest = 'sha256:' + 'a' * 64
        package = release.IMAGE
        revisions = [{'spec': {'containers': [{'image': package + '@' + digest}]}}]
        images = [{'package': package, 'version': digest},
                  {'package': package, 'version': 'sha256:' + 'b' * 64},
                  {'package': package.replace('life-assistant-backend', 'janus-api'),
                   'version': 'sha256:' + 'c' * 64}]
        import tempfile
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(release, 'STATE', Path(directory)), \
             patch.object(release, 'read_json', side_effect=[revisions, [], images]):
            self.assertEqual(release.cleanup_plan(), [package + '@sha256:' + 'b' * 64])

    def test_rollback_restores_owned_failed_release(self):
        service = {'status': {'traffic': [{'revisionName': 'candidate', 'percent': 100}]}}
        with patch.dict(os.environ, {'RELEASE_SHA': 'f' * 40}), \
             patch.object(release, 'read_json', return_value=service), \
             patch.object(release, 'fetch', return_value=('f' * 40).encode()), \
             patch.object(release, 'gcloud') as gcloud, patch.object(release, 'run') as run:
            release.restore_release({'normal': 100}, 'candidate', 'hosting-normal')
            self.assertIn('normal=100', gcloud.call_args.args)
            self.assertIn(release.SITE + ':@hosting-normal', run.call_args.args)

    def test_rollback_never_overwrites_newer_runtime_or_hosting(self):
        service = {'status': {'traffic': [{'revisionName': 'newer', 'percent': 100}]}}
        with patch.dict(os.environ, {'RELEASE_SHA': 'f' * 40}), \
             patch.object(release, 'read_json', return_value=service), \
             patch.object(release, 'fetch', return_value=('a' * 40).encode()), \
             patch.object(release, 'gcloud') as gcloud, patch.object(release, 'run') as run:
            release.restore_release({'normal': 100}, 'candidate', 'hosting-normal')
            gcloud.assert_not_called()
            run.assert_not_called()


class OwnerIdentityTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_google_identity_of_another_owner_is_denied(self):
        import httpx
        from fastapi import HTTPException
        from app.services import google_identity
        claims = {'aud': 'v2-test-client', 'iss': 'https://accounts.google.com',
                  'email_verified': 'true', 'exp': 9999999999,
                  'email': 'another-owner@example.invalid', 'sub': 'another-owner'}
        client_type = httpx.AsyncClient
        with patch.object(google_identity.settings, 'google_client_id', 'v2-test-client'), \
             patch.dict('os.environ', {'ALLOWED_GOOGLE_EMAIL': 'owner@example.invalid'}), \
             patch.object(google_identity.httpx, 'AsyncClient', side_effect=lambda **kw:
                          client_type(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=claims)), **kw)):
            with self.assertRaises(HTTPException) as error:
                await google_identity.verify_google_id_token('test-non-secret')
            self.assertEqual(error.exception.status_code, 403)


if __name__ == '__main__':
    unittest.main()
