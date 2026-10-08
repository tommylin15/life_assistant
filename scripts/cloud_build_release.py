"""Life Assistant regional Cloud Build release; never manages scheduled jobs.

Evidence stays in Cloud Logging. PROMOTE=false runs candidate/preview gates only.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

PROJECT = 'gen-lang-client-0593591102'
REGION = 'us-central1'
SERVICE = 'life-assistant-api'
CALLER_SA = 'omniagent-codex-life-client@gen-lang-client-0593591102.iam.gserviceaccount.com'
SITE = PROJECT
LIVE = f'https://{SITE}.web.app'
IMAGE = f'{REGION}-docker.pkg.dev/{PROJECT}/cloud-run-source-deploy/life-assistant-backend'
STATE = Path('.release')
ACTIVE = {'PENDING', 'QUEUED', 'WORKING'}
CORE = ('run_cloud_domain_parity_acceptance', 'run_checklist_cloud_acceptance',
        'run_idempotency_acceptance', 'run_google_failure_acceptance',
        'run_sqlite_backfill_acceptance', 'run_sqlite_backfill_failure_acceptance')
POST = ('run_notes_product_acceptance', 'run_project_drive_runtime_acceptance',
        'run_drive_ai_enrichment_acceptance', 'run_drive_production_config_acceptance',
        'run_drive_knowledge_runtime_acceptance', 'run_drive_google_integration_acceptance',
        'run_calendar_true_account_read_acceptance', 'run_shared_codex_identity_acceptance',
        'run_drive_external_ai_acceptance')
UI = ('task', 'project', 'notes', 'drive', 'habits', 'shopping', 'calendar', 'drive_knowledge')


def run(*args, capture=False, **kwargs):
    return subprocess.run(args, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None, **kwargs).stdout


def gcloud(*args, capture=False):
    return run('gcloud', *args, '--project', PROJECT, capture=capture)


def read_json(*args):
    return json.loads(gcloud(*args, '--format=json', capture=True))


def record(gate, status='PASS', **details):
    event = dict(gate=gate, status=status, release_sha=os.environ.get('RELEASE_SHA'), **details)
    print(json.dumps(event), flush=True)


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def changes(paths):
    # Compare against deployed release, not HEAD^: batched pushes cannot hide changes.
    backend = any(p.startswith(('backend/', 'scripts/', 'tests/', '.github/', 'cloudbuild'))
                  or p in ('firebase.json', 'pubspec.yaml', 'pubspec.lock') for p in paths)
    frontend = any(p.startswith(('lib/', 'web/', 'assets/', 'branding/', 'test/', 'tests/',
                                'scripts/', '.github/', 'cloudbuild'))
                   or p in ('firebase.json', 'pubspec.yaml', 'pubspec.lock') for p in paths)
    return backend, frontend


def current_main():
    return run('git', 'ls-remote', 'https://github.com/tommylin15/life_assistant.git',
               'refs/heads/main', capture=True).split()[0]


def assert_current():
    if current_main() != os.environ['RELEASE_SHA']:
        raise RuntimeError('superseded_main_release; refusing mutation')


def prepare():
    STATE.mkdir(exist_ok=True)
    sha = os.environ['RELEASE_SHA']
    assert re.fullmatch(r'[0-9a-f]{40}', sha), 'full Git SHA required'
    assert os.environ['GCP_PROJECT_ID'] == PROJECT
    assert os.environ['GCP_REGION'] == REGION
    build = read_json('builds', 'describe', os.environ['BUILD_ID'], '--region', REGION)
    trigger_id = build.get('buildTriggerId')
    assert trigger_id, 'repository push trigger required'
    os.environ['TRIGGER_ID'] = trigger_id
    (STATE / 'trigger-id').write_text(trigger_id)
    mode = os.environ['PIPELINE']
    assert mode in ('ci', 'release'), 'unknown pipeline mode'
    trigger = read_json('builds', 'triggers', 'describe', trigger_id, '--region', REGION)
    if mode == 'ci':
        assert trigger['repositoryEventConfig']['push']['branch'] == '^main$'
        assert os.environ['PROMOTE'] == 'false', 'push CI must not promote'
    else:
        assert not trigger.get('repositoryEventConfig'), 'release must be explicitly invoked'
        ci_trigger = read_json('builds', 'triggers', 'describe', 'life-assistant-v2-main', '--region', REGION)
        ci_builds = read_json('builds', 'list', '--region', REGION,
                             '--filter', 'buildTriggerId=' + ci_trigger['id'] + ' AND status=SUCCESS', '--limit=100')
        assert any(b.get('substitutions', {}).get('COMMIT_SHA') == sha for b in ci_builds), 'exact-SHA Push CI PASS required'
        (STATE / 'release').touch()
    if current_main() != sha:
        (STATE / 'skip').touch()
        record('release', 'SUPERSEDED')
        return
    prior = read_json('builds', 'list', '--region', REGION,
                      '--filter', f"buildTriggerId={trigger_id} AND status=SUCCESS", '--limit=100')
    verified = [b for b in prior if b.get('substitutions', {}).get('_PIPELINE') == mode
                and (mode == 'ci' or b.get('substitutions', {}).get('_PROMOTE') == 'true')]
    try:
        baseline = (verified[0]['substitutions']['COMMIT_SHA'] if verified else
                    fetch(LIVE + '/release.txt?cloudbuild=' + sha).decode().strip())
        assert re.fullmatch(r'[0-9a-f]{40}', baseline)
        if not Path('.git').is_dir():
            run('git', 'init')
        run('git', 'fetch', '--no-tags', 'https://github.com/tommylin15/life_assistant.git', baseline, sha)
        paths = run('git', 'diff', '--name-only', baseline, sha, capture=True).splitlines()
        backend, frontend = changes(paths)
    except (urllib.error.URLError, AssertionError, subprocess.CalledProcessError):
        baseline, backend, frontend = None, True, True
    # First V2 push must prove the whole replacement chain, even on identical code.
    if mode == 'release' and not verified:
        backend = frontend = True
    if not backend and not frontend:
        (STATE / 'skip').touch()
        record('paths', 'NO_DEPLOY', baseline=baseline)
        return
    if backend:
        (STATE / 'backend').touch()
    if frontend:
        (STATE / 'frontend').touch()
    # Backend-only changes must test the existing frontend against the
    # no-traffic candidate, not accidentally test the LIVE API. Build an
    # isolated Preview but never publish unchanged Flutter to Hosting live.
    if mode == 'release' and backend and not frontend:
        (STATE / 'frontend-preview').touch()
        record('frontend', 'PREVIEW_ONLY', reason='candidate_api_compatibility')
    elif mode == 'release' and not frontend:
        record('frontend', 'UNCHANGED')
    record('paths', baseline=baseline, backend=backend, frontend=frontend)


def flutter_sdk():
    releases = json.loads(fetch('https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json'))
    release = next(r for r in releases['releases'] if r['version'] == '3.47.3'
                   and r['channel'] == 'stable' and r.get('dart_sdk_arch', 'x64') == 'x64')
    archive = STATE / 'flutter.tar.xz'
    urllib.request.urlretrieve(releases['base_url'] + '/' + release['archive'], archive)
    with archive.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == release['sha256']
    run('tar', '-xJf', str(archive), '-C', str(STATE))
    archive.unlink()


def verify_build():
    for path in ('icons/life-assistant-192-v8.png', 'icons/life-assistant-512-v8.png',
                 'branding/life-assistant-hero-v8.png'):
        assert (Path('web') / path).read_bytes() == (Path('build/web') / path).read_bytes()
    assert '/manifest-v6.json' in Path('build/web/index.html').read_text()
    manifest = json.loads(Path('build/web/manifest-v6.json').read_text())
    assert manifest['id'] == '/life-assistant-v6'
    record('flutter_build_branding')


def serialized_release():
    mine = read_json('builds', 'describe', os.environ['BUILD_ID'], '--region', REGION)
    deadline = time.monotonic() + 1800
    while True:
        builds = read_json('builds', 'list', '--region', REGION,
                           '--filter', f"buildTriggerId={os.environ['TRIGGER_ID']}", '--limit', '1000')
        older = [b for b in builds if (b['createTime'], b['id']) < (mine['createTime'], mine['id'])]
        if any(b.get('status') in ACTIVE for b in older):
            if time.monotonic() > deadline:
                raise RuntimeError('release serialization timeout')
            record('serialization', 'WAIT')
            time.sleep(30)
            continue
        assert_current()
        # Successful same-SHA prior executions must not repeat migrations/provider work.
        if any(b.get('status') == 'SUCCESS' and b.get('substitutions', {}).get('COMMIT_SHA')
               == os.environ['RELEASE_SHA'] and b.get('substitutions', {}).get('_PROMOTE')
               == os.environ.get('PROMOTE') for b in older):
            record('duplicate_release', 'SKIPPED')
            return False
        return True


def wait_legacy_deployments():
    # During migration, let the old main-push chain finish before touching its
    # service/jobs. After cutover the repository variable disables that chain.
    url = ('https://api.github.com/repos/tommylin15/life_assistant/actions/runs'
           '?head_sha=' + os.environ['RELEASE_SHA'] + '&per_page=100')
    deadline = time.monotonic() + 1800
    while True:
        runs = json.loads(fetch(url))['workflow_runs']
        pending = [r for r in runs if r['name'] in ('CI', 'Deploy Cloud Run',
                    'Deploy Firebase Hosting', 'Post-deploy Runtime Acceptance',
                    'Drive Knowledge Runtime Acceptance', 'Calendar True Account Acceptance')
                   and r['status'] != 'completed']
        if not pending:
            record('legacy_deployments_finished', failures=[r['id'] for r in runs
                   if r.get('conclusion') == 'failure'])
            return
        if time.monotonic() > deadline:
            raise RuntimeError('legacy deployment still active; refusing double deployment')
        record('legacy_deployments', 'WAIT', runs=[r['id'] for r in pending])
        time.sleep(60)


def job(module, image, base_url=None):
    name = 'life-assistant-db-migrate' if module == 'apply_cloud_domain_parity_release' else (
        'life-assistant-core-acceptance' if module in CORE else 'life-assistant-postdeploy-acceptance')
    env = dict(DATABASE_HOST='10.42.0.5', DATABASE_PORT='5432', DATABASE_NAME='life_assistant',
               DATABASE_USER='life_assistant_user', DATABASE_SSLMODE='require',
               FRONTEND_URL=LIVE, GOOGLE_REDIRECT_URI=LIVE + '/auth/callback',
               GOOGLE_PICKER_APP_ID='131494961796', CODEX_PRIMARY_ENABLED='true',
               ALEMBIC_METADATA_BOOTSTRAP_APPROVED_REVISION='20260926_0004',
               DRIVE_ACCEPTANCE_USER_SUB=os.environ['DRIVE_ACCEPTANCE_USER_SUB'],
               DRIVE_ACCEPTANCE_GOOGLE_FILE_ID=os.environ['DRIVE_ACCEPTANCE_GOOGLE_FILE_ID'],
               ACCEPTANCE_OWNER_EMAIL=os.environ['ACCEPTANCE_OWNER_EMAIL'])
    if base_url:
        env['ACCEPTANCE_BASE_URL'] = base_url
    gcloud('run', 'jobs', 'update', name, '--region', REGION, '--image', image,
           '--service-account', CALLER_SA, '--command', 'python', '--args=-m,scripts.' + module,
           '--max-retries', '0', '--update-env-vars', ','.join(f'{k}={v}' for k, v in env.items()), '--quiet')
    run('bash', '.github/scripts/run_cloud_run_job_with_diagnostics.sh', name,
        'gcloud', 'run', 'jobs', 'execute', name, '--project', PROJECT,
        '--region', REGION, '--args=-m,scripts.' + module, '--task-timeout', '20m' if module == 'run_live_release_acceptance' else '10m',
        '--wait', '--quiet', env={**os.environ, 'GCP_PROJECT_ID': PROJECT,
        'RUN_JOB_MAX_WAIT_SECONDS': '1260' if module == 'run_live_release_acceptance' else '660'})
    execution = read_json('run', 'jobs', 'executions', 'list', '--job', name,
                          '--region', REGION, '--sort-by=~metadata.creationTimestamp', '--limit=1')[0]
    record(module, execution=execution['metadata']['name'], image=image)


def runtime_gates(modules, image):
    failed = []
    for module in modules:
        try:
            job(module, image)
        except subprocess.CalledProcessError:
            record(module, 'FAIL')
            failed.append(module)
            if module == 'run_drive_external_ai_acceptance':
                # Keep aggregate failure; diagnostics must never turn it into PASS.
                for provider in ('gemini', 'openrouter'):
                    try:
                        run('bash', '.github/scripts/run_cloud_run_job_with_diagnostics.sh',
                            'life-assistant-postdeploy-acceptance', 'gcloud', 'run', 'jobs', 'execute',
                            'life-assistant-postdeploy-acceptance', '--project', PROJECT,
                            '--region', REGION, '--args=-m,scripts.' + module + ',--only-provider=' + provider,
                            '--task-timeout=10m', '--wait', '--quiet')
                    except subprocess.CalledProcessError:
                        record('provider_diagnostic_' + provider, 'FAIL')
    if failed:
        raise RuntimeError('mandatory runtime gates failed: ' + ','.join(failed))


def ui_gates(url):
    failures = []
    for name in UI:
        filename = f'verify_{name}_ui_production.mjs' if name != 'drive_knowledge' else 'verify_drive_knowledge_production.mjs'
        try:
            run('node', '.github/scripts/' + filename, env={**os.environ, 'BASE_URL': url})
            record('ui_' + name, url=url, api_interception=True)
        except subprocess.CalledProcessError:
            record('ui_' + name, 'FAIL', url=url)
            failures.append(name)
    if failures:
        raise RuntimeError('UI gates failed: ' + ','.join(failures))


def http_gates(url, hosting=False, expected_sha=None):
    run('curl', '--fail', '--silent', '--show-error', '--retry', '5', '--retry-all-errors', url + '/health') if not hosting else None
    if not hosting:
        run('curl', '--fail', '--silent', '--show-error', url + '/ready')
    status = run('curl', '--silent', '--show-error', '--output', '/dev/null',
                 '--write-out', '%{http_code}', url + '/api/v1/tasks', capture=True)
    assert status == '401', f'unauthenticated API status={status}'
    headers = run('curl', '--silent', '--show-error', '--dump-header', '-',
                  '--output', '/dev/null', url + '/auth/login', capture=True)
    assert re.search(r'HTTP/[\d.]+ 30[2378]', headers)
    assert re.search(r'(?im)^location: https://accounts.google.com/o/oauth2/v2/auth\?', headers)
    assert re.search(r'(?im)^set-cookie: __session=', headers)
    if hosting:
        for attempt in range(36):
            if fetch(url + '/release.txt?sha=' + os.environ['RELEASE_SHA'] + f'&attempt={attempt}').decode().strip() == (expected_sha or os.environ.get('FRONTEND_SHA', os.environ['RELEASE_SHA'])):
                break
            time.sleep(5)
        else:
            raise RuntimeError('exact Hosting SHA not observed')
        headers = run('curl', '--silent', '--show-error', '--head', url + '/index.html', capture=True)
        assert re.search(r'(?im)^cache-control:.*(?:no-cache|no-store|must-revalidate)', headers)
        for path in ('icons/life-assistant-192-v8.png', 'branding/life-assistant-hero-v8.png'):
            expected = Path('build/web') / path if ((STATE / 'frontend').exists() or (STATE / 'frontend-preview').exists()) else Path('web') / path
            assert fetch(url + '/' + path) == expected.read_bytes()
        assert json.loads(fetch(url + '/manifest-v6.json'))['id'] == '/life-assistant-v6'
    record('hosting_http' if hosting else 'candidate_http', url=url)


def inventories():
    # Read scheduler; NEVER create, execute, update or delete any schedule.
    schedules = read_json('scheduler', 'jobs', 'list', '--location', REGION)
    scheduled = [{k: s.get(k) for k in ('name', 'schedule', 'timeZone', 'state')} for s in schedules]
    jobs = read_json('run', 'jobs', 'list', '--region', REGION)
    runtime = {j['metadata']['name']: j['spec']['template']['spec']['template']['spec']['containers'][0]['image']
               for j in jobs if j['metadata']['name'].startswith('life-assistant-')}
    return {'scheduler': scheduled, 'jobs': runtime}


def cleanup_plan():
    # Protect ALL existing revisions/jobs in this shared project; delete only exact Life Assistant packages.
    refs = set()
    for revision in read_json('run', 'revisions', 'list', '--region', REGION):
        refs.update(c['image'] for c in revision.get('spec', {}).get('containers', []))
    for j in read_json('run', 'jobs', 'list', '--region', REGION):
        refs.update(c['image'] for c in j['spec']['template']['spec']['template']['spec']['containers'])
    images = read_json('artifacts', 'docker', 'images', 'list',
                       f'{REGION}-docker.pkg.dev/{PROJECT}/cloud-run-source-deploy', '--include-tags')
    candidates = []
    for item in images:
        package = item.get('package', '')
        digest = item.get('version', '').split('/')[-1]
        if package.split('/')[-1] not in ('life-assistant-backend', 'life-assistant-api', 'life-assistant-db-migrate'):
            continue
        ref = package + '@' + digest
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
            raise RuntimeError('unresolved inventory digest')
        # Mutable references cannot safely be interpreted: protect the whole package.
        if ref not in refs and not any(r.startswith(package + ':') for r in refs):
            candidates.append(ref)
    record('artifact_cleanup', 'DRY_RUN', candidates=candidates, protected=sorted(refs))
    (STATE / 'cleanup-plan.json').write_text(json.dumps(candidates, indent=2))
    return candidates


def restore_release(previous, revision, previous_hosting):
    # A manual recovery/newer runtime must never be overwritten by stale rollback.
    service = read_json('run', 'services', 'describe', SERVICE, '--region', REGION)
    actual = {t['revisionName']: t['percent'] for t in service['status']['traffic'] if t.get('percent')}
    if actual == {revision: 100}:
        gcloud('run', 'services', 'update-traffic', SERVICE, '--region', REGION,
               '--to-revisions', ','.join(f'{r}={p}' for r, p in previous.items()), '--quiet')
        record('rollback', 'BACKEND_RESTORED', traffic=previous)
    else:
        record('rollback', 'BACKEND_NOT_OVERWRITTEN', traffic=actual)
    if fetch(LIVE + '/release.txt?rollback=' + os.environ['RELEASE_SHA']).decode().strip() == os.environ['RELEASE_SHA']:
        run('firebase', 'hosting:clone', SITE + ':@' + previous_hosting, SITE + ':live',
            '--project', PROJECT, '--non-interactive')
        record('rollback', 'HOSTING_RESTORED', hosting_version=previous_hosting)
    else:
        record('rollback', 'HOSTING_NOT_OVERWRITTEN')


def deploy():
    os.environ['TRIGGER_ID'] = (STATE / 'trigger-id').read_text()
    if not serialized_release():
        return
    wait_legacy_deployments()
    assert_current()
    if not all(os.environ.get(v) for v in ('DRIVE_ACCEPTANCE_USER_SUB', 'DRIVE_ACCEPTANCE_GOOGLE_FILE_ID')):
        raise RuntimeError('real Drive fixture required; gate cannot be skipped')
    before = inventories()
    record('baseline_inventory', inventory=before)
    service = read_json('run', 'services', 'describe', SERVICE, '--region', REGION)
    previous = {t['revisionName']: t['percent'] for t in service['status']['traffic'] if t.get('percent')}
    access = gcloud('auth', 'print-access-token', capture=True).strip()
    request = urllib.request.Request(
        'https://firebasehosting.googleapis.com/v1beta1/sites/' + SITE + '/channels/live/releases?pageSize=1',
        headers={'Authorization': 'Bearer ' + access})
    with urllib.request.urlopen(request, timeout=30) as response:
        previous_hosting = json.load(response)['releases'][0]['version']['name'].split('/')[-1]
    record('rollback_baseline', hosting_version=previous_hosting, traffic=previous)
    image = service['spec']['template']['spec']['containers'][0]['image']
    if (STATE / 'backend').exists():
        info = read_json('artifacts', 'docker', 'images', 'describe', IMAGE + ':' + os.environ['RELEASE_SHA'])
        image = IMAGE + '@' + info['image_summary']['digest']
        job('apply_cloud_domain_parity_release', image)
        assert_current()
        gcloud('run', 'deploy', SERVICE, '--region', REGION, '--image', image,
               '--service-account', CALLER_SA, '--no-traffic', '--tag=v2-candidate', '--update-labels', 'release-sha=' + os.environ['RELEASE_SHA'],
               '--update-env-vars', 'CODEX_PRIMARY_ENABLED=true,ALLOWED_GOOGLE_EMAIL=' + os.environ['ACCEPTANCE_OWNER_EMAIL'], '--quiet')
        service = read_json('run', 'services', 'describe', SERVICE, '--region', REGION)
    revision = service['status']['latestReadyRevisionName'] if (STATE / 'backend').exists() else next(iter(previous))
    if not (STATE / 'backend').exists():
        served = read_json('run', 'revisions', 'describe', revision, '--region', REGION)
        image = served['spec']['containers'][0]['image']
    environment = service['spec']['template']['spec']['containers'][0].get('env', [])
    allowlist = next((e.get('value') for e in environment if e['name'] == 'ALLOWED_GOOGLE_EMAIL'), None)
    assert allowlist == os.environ['ACCEPTANCE_OWNER_EMAIL'], 'single-owner API allowlist required'
    record('single_owner_allowlist', scope='single-user product; no multi-owner collaboration')
    candidate = (next(t['url'] for t in service['status']['traffic'] if t.get('tag') == 'v2-candidate')
                 if (STATE / 'backend').exists() else service['status']['url'])
    record('candidate', revision=revision, image=image, previous_traffic=previous, url=candidate)
    http_gates(candidate)
    runtime_gates(CORE, image)
    job('run_live_release_acceptance', image, candidate)
    runtime_failures = []
    try:
        runtime_gates(POST, image)
    except RuntimeError as exc:
        runtime_failures.append(str(exc))
    # pinTag previews the no-traffic revision while keeping the official OAuth callback.
    channel = None
    os.environ['FRONTEND_SHA'] = os.environ['RELEASE_SHA'] if (STATE / 'frontend').exists() else fetch(LIVE + '/release.txt').decode().strip()
    if (STATE / 'frontend').exists() or (STATE / 'frontend-preview').exists():
        config = json.loads(Path('firebase.json').read_text())
        for rewrite in config['hosting']['rewrites']:
            if 'run' in rewrite and (STATE / 'backend').exists():
                rewrite['run']['pinTag'] = True
        Path('firebase.v2.json').write_text(json.dumps(config, indent=2))
        channel = 'v2-' + os.environ['RELEASE_SHA'][:12]
        raw = run('firebase', 'hosting:channel:deploy', channel, '--expires=1d', '--project', PROJECT,
                  '--config=firebase.v2.json', '--non-interactive', '--json', capture=True)
        preview = json.loads(raw)['result'][SITE]['url']
        record('preview', url=preview, channel=channel)
        http_gates(preview, hosting=True, expected_sha=os.environ['RELEASE_SHA'])
        ui_gates(preview)
        job('run_live_release_acceptance', image, preview)
    else:
        # Backend contract compatibility with the actual unchanged frontend.
        ui_gates(LIVE)
        job('run_live_release_acceptance', image, LIVE)
    if runtime_failures:
        raise RuntimeError('; '.join(runtime_failures))
    if os.environ.get('PROMOTE') != 'true':
        record('release', 'CANDIDATE_ONLY', reason='live promotion disabled')
        return
    assert_current()
    promoted = False
    try:
        if (STATE / 'backend').exists():
            gcloud('run', 'services', 'update-traffic', SERVICE, '--region', REGION,
                   '--to-revisions', revision + '=100', '--quiet')
        promoted = True
        # Clone the verified preview; never rebuild/reupload a different live artifact.
        if channel and (STATE / 'frontend').exists():
            run('firebase', 'hosting:clone', SITE + ':' + channel, SITE + ':live', '--project', PROJECT,
                '--non-interactive')
        http_gates(LIVE, hosting=True)
        job('run_live_release_acceptance', image, LIVE)
        ui_gates(LIVE)
        runtime_gates(POST, image)
        after = inventories()
        assert before['scheduler'] == after['scheduler'], 'scheduler readback changed'
        record('scheduler_jobs_readback', inventory=after)
        cleanup_plan()
        record('release', 'PASS', revision=revision, image=image, hosting_sha=os.environ['FRONTEND_SHA'])
    except Exception:
        if promoted:
            restore_release(previous, revision, previous_hosting)
        raise


if __name__ == '__main__':
    {'prepare': prepare, 'flutter-sdk': flutter_sdk, 'verify-build': verify_build,
     'deploy': deploy}[sys.argv[1]]()
