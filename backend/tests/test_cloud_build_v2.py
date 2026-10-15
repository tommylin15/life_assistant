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
            if workflow.name == 'ci.yml':
                continue
            source = workflow.read_text()
            self.assertNotIn('--no-dry-run', source)
            if workflow.name == 'v3-cutover-once-after-release.yml':
                # Strict one-time audited Release completion is the sole
                # exception to the legacy ban on workflow_run chains.
                if 'workflow_run:' in source:
                    self.assertIn('types:', source)
                    self.assertIn('completed', source)
                    self.assertIn(
                        'github.event.workflow_run.id == 37795789924', source
                    )
                    self.assertIn(
                        "github.event.workflow_run.conclusion == 'success'", source
                    )
                else:
                    # One-file push bootstrap is permitted exactly once, with
                    # full CI and immutable release evidence before dispatch.
                    self.assertIn('workflow_dispatch:', source)
                    self.assertIn('push:', source)
                    self.assertIn('branches: [main]', source)
                    self.assertIn(
                        '.github/workflows/v3-cutover-once-after-release.yml',
                        source
                    )
                    self.assertIn("github.event_name == 'push'", source)
                    self.assertNotIn('workflow_run:', source)
                self.assertIn(
                    '25ff10c61abc15e557996b6070e02abf3b54a97b', source
                )
                self.assertIn('Retain latest 10 revisions after all live gates PASS', source)
                self.assertIn('gh workflow run v3-cutover-disable-triggers.yml', source)
                self.assertNotIn('gcloud run services update-traffic', source)
                self.assertNotIn('updateMask=disabled', source)
            elif workflow.name == 'v3-auto-staging-after-ci.yml':
                # Owner-approved 2026-10-10 exception: only main's successful
                # four-job push CI may dispatch staging. Not production.
                self.assertIn('workflow_run:', source)
                self.assertIn('workflows: ["CI"]', source)
                self.assertIn("workflow_run.event == 'push'", source)
                self.assertIn("workflow_run.conclusion == 'success'", source)
                self.assertIn('--raw-field promote=false', source)
                self.assertIn('--raw-field publish_staging=true', source)
                self.assertNotIn('--raw-field promote=true', source)
                self.assertNotIn('gcloud run services update-traffic', source)
            elif workflow.name == 'v3-auto-production-hosting-after-release.yml':
                # A completed manual V3 release may dispatch production Hosting
                # only after *all* live, rollback, and exact-SHA gates pass.
                # A successful staging-only release cannot qualify.
                self.assertIn('workflow_run:', source)
                self.assertIn('workflows: ["V3 Release - GHCR to Cloud Run"]', source)
                self.assertIn("workflow_run.event == 'workflow_dispatch'", source)
                self.assertIn("workflow_run.conclusion == 'success'", source)
                self.assertIn('MAIN_SHA', source)
                self.assertIn('all(.[];', source)
                for gate in (
                    'Promote exact Preview to independent fixed staging live and verify pinned routes',
                    'Reconfirm source SHA and live traffic, then promote',
                    'Post-promotion live health, PostgreSQL and access gates',
                    'Controlled rollback rehearsal and restore promoted live traffic',
                    'Retain latest 10 revisions after all live gates PASS',
                    'Pin curated handoff Job after verified production promotion',
                ):
                    self.assertIn(gate, source)
                self.assertIn('gh workflow run deploy-firebase-hosting.yml', source)
                self.assertNotIn('gh workflow run v3-release-ghcr.yml', source)
                self.assertNotIn('--raw-field promote=true', source)
                self.assertNotIn('gcloud run services update-traffic', source)
            elif workflow.name == 'life-01-07-one-time-acceptance.yml':
                # 2026-10-14 explicit user-authorized *single* importer
                # acceptance. It cannot re-run on arbitrary CI success,
                # promote production, change a Job, or remove rollback tags.
                self.assertIn('workflow_run:', source)
                self.assertIn('workflows: [CI]', source)
                self.assertIn("workflow_run.event == 'push'", source)
                self.assertIn("workflow_run.conclusion == 'success'", source)
                self.assertIn('53c131ea32bd372cf7ec25268f977e26fb41f6e6', source)
                self.assertIn('BATCH_SUBJECT:', source)
                self.assertIn('git rev-parse HEAD^', source)
                self.assertIn('unique | length==4', source)
                self.assertIn('v3_curated_handoff_alignment.py', source)
                self.assertIn('run_cloud_run_job_with_diagnostics.sh', source)
                for forbidden in ('gcloud run services update-traffic',
                                  'gcloud run jobs update', 'gcloud run revisions delete',
                                  '--apply --live-passed', 'schedule:',
                                  '--raw-field promote=true'):
                    self.assertNotIn(forbidden, source)
            elif workflow.name == 'life-cloud-run-retirement-apply.yml':
                # 2026-10-15 user explicitly approved retiring 0%-traffic old
                # revisions after a successful same-SHA V3 release. Only
                # life-assistant-api, no services/jobs or cross-project writes.
                self.assertIn('workflow_run:', source)
                self.assertIn('workflows: ["V3 Release - GHCR to Cloud Run"]', source)
                self.assertIn("workflow_run.conclusion == 'success'", source)
                self.assertIn("workflow_run.event == 'workflow_dispatch'", source)
                self.assertIn("workflow_run.head_branch == 'main'", source)
                self.assertIn('MAIN_SHA', source)
                self.assertIn('life_cloud_run_retirement_apply.py', source)
                self.assertIn('test_life_cloud_run_retirement.py', source)
                self.assertNotIn('push:', source)
                self.assertNotIn('gcloud run jobs delete', source)
                self.assertNotIn('gcloud run services delete', source)
            elif workflow.name == 'life-gemini-p0v-signed-smoke.yml':
                # Approved 2026-10-13 P0-V: only after V3 staging-only SUCCESS,
                # exact main SHA and four CI gates. This workflow may execute
                # ONE existing Job for a real text smoke, not deploy/mutate.
                self.assertIn('workflow_dispatch:', source)
                self.assertNotIn('push:', source)
                self.assertNotIn('workflow_run:', source)
                self.assertNotIn('bootstrap_source_mismatch', source)
                self.assertIn('current_sha" = "$SOURCE_SHA"', source)
                self.assertIn('.event=="workflow_dispatch" and .conclusion=="success"', source)
                self.assertIn("Require explicit promotion selection", source)
                self.assertIn('.conclusion=="skipped"', source)
                self.assertIn('unique | length==4', source)
                self.assertIn('gcloud run jobs execute "$JOB"', source)
                self.assertIn('SOURCE_RUN', source)
                self.assertIn('SOURCE_SHA', source)
                for forbidden in (
                    'gcloud run deploy ', 'gcloud run services update',
                    'gcloud run jobs update', 'add-iam-policy-binding',
                    'allUsers', '--raw-field promote=true',
                    'firebase deploy', 'update-traffic',
                ):
                    self.assertNotIn(forbidden, source)
            else:
                self.assertIn('workflow_dispatch:', source)
                self.assertNotIn('workflow_run:', source)

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
    async def test_valid_google_identity_is_general_user_not_owner(self):
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
            # A verified Google identity is allowed to sign in, but it does
            # not gain Owner privilege or bypass the general-user route gate.
            verified = await google_identity.verify_google_id_token('test-non-secret')
            from app.api.auth import _enforce_account_access, _enforce_general_user_route
            from app.api.ui_policies import owner_only
            from starlette.requests import Request
            _enforce_account_access(verified, staging=False)
            with self.assertRaises(HTTPException) as error:
                owner_only(verified)
            self.assertEqual(error.exception.status_code, 403)
            req = Request({"type": "http", "path": "/api/v1/templates", "headers": []})
            with self.assertRaises(HTTPException) as error:
                _enforce_general_user_route(req, verified)
            self.assertEqual(error.exception.status_code, 403)


if __name__ == '__main__':
    unittest.main()
