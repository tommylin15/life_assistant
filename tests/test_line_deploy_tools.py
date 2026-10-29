import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

class LineDeployTests(unittest.TestCase):
    def test_disabled_pins_existing_bundle(self):
        self.assertEqual(
            load('line_deploy_flags').build_flags({'LINE_BUNDLE_REF':'life-assistant-bundle:9'}),
            ['--update-env-vars=LIFE_LINE_ENABLED=false',
             '--update-secrets=LIFE_ASSISTANT_BUNDLE=life-assistant-bundle:9'])

    def test_incomplete_config_fails_closed(self):
        with self.assertRaises(ValueError):
            load('line_deploy_flags').build_flags({'LINE_ENABLED':'true'})

    def test_pinned_shared_bundle_and_untrusted_origin(self):
        env={'LINE_ENABLED':'true','LINE_NAMESPACE':'stage','LINE_ORIGIN':'https://life.example',
             'LINE_LIFF_ID':'123-abc','LINE_LOGIN_CHANNEL_ID':'123',
             'LINE_BUNDLE_REF':'life-assistant-bundle:9'}
        flags=load('line_deploy_flags').build_flags(env)
        self.assertEqual(len(flags),2)
        self.assertEqual(flags[1], '--update-secrets=LIFE_ASSISTANT_BUNDLE=life-assistant-bundle:9')
        self.assertNotIn('LIFE_LINE_CHANNEL_SECRET=', ' '.join(flags))
        self.assertNotIn('LIFE_LINE_ACCESS_TOKEN=', ' '.join(flags))
        for key,value in [
            ('LINE_ORIGIN','https://life.example,OTHER=true'),
            ('LINE_BUNDLE_REF','life-assistant-bundle:latest'),
            ('LINE_BUNDLE_REF','other-secret:9'),
            ('LINE_BUNDLE_REF','life-assistant-bundle:9,OTHER=true'),
        ]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                load('line_deploy_flags').build_flags({**env,key:value})

    def test_latest_enabled_skips_destroyed_and_disabled(self):
        mod=load('resolve_life_bundle')
        obj=[
            {'name':'projects/p/secrets/life-assistant-bundle/versions/8','state':'DESTROYED'},
            {'name':'projects/p/secrets/life-assistant-bundle/versions/9','state':'ENABLED'},
            {'name':'projects/p/secrets/life-assistant-bundle/versions/10','state':'DISABLED'},
        ]
        self.assertEqual(mod.latest_enabled(obj),'9')
        with self.assertRaises(ValueError):
            mod.latest_enabled([obj[0],obj[2]])

    def test_preserves_serving_revision_and_refuses_mixed(self):
        mod=load('resolve_life_bundle')
        service={'status':{'traffic':[{'revisionName':'r1','percent':50},
                                      {'revisionName':'r2','percent':50},
                                      {'revisionName':'test','percent':0}]}}
        def rev(v):
            return {'spec':{'containers':[{'env':[{'name':'LIFE_ASSISTANT_BUNDLE',
                     'valueFrom':{'secretKeyRef':{'name':'life-assistant-bundle','key':v}}}]}]}}
        self.assertEqual(mod.serving_version(service,{'r1':rev('9'),'r2':rev('9')}),'9')
        with self.assertRaises(ValueError):
            mod.serving_version(service,{'r1':rev('9'),'r2':rev('10')})
        self.assertIsNone(mod.serving_version(service,{'r1':rev('latest'),'r2':rev('latest')}))

    def test_staging_receipt_is_bound_to_same_sha_and_project(self):
        mod=load('resolve_life_bundle')
        sha='a'*40
        proof={'release_sha':sha,'project':'life-project','secret':'life-assistant-bundle',
               'version':'9','stage_origin':'https://life-assistant-v3-stage-tl15.web.app'}
        self.assertEqual(mod.receipt_version(proof,sha,'life-project'),'9')
        for invalid in ({**proof,'version':'latest'},{**proof,'release_sha':'b'*40},
                        {**proof,'project':'other'}):
            with self.assertRaises(ValueError):
                mod.receipt_version(invalid,sha,'life-project')

    def test_metadata_failure_reports_operation_and_category_without_secret_content(self):
        mod=load('resolve_life_bundle')
        example=subprocess.CalledProcessError(
            1, ['gcloud'], stderr=b'PERMISSION_DENIED: access denied to resource')
        with patch.object(mod.subprocess, 'run', side_effect=example):
            with self.assertRaises(mod.SecretMetadataError) as exc:
                mod.gcloud_json('secrets', 'versions', 'list', 'life-assistant-bundle')
        self.assertEqual(str(exc.exception), 'operation=versions_list category=PERMISSION_DENIED')

    def test_metadata_other_failure_does_not_echo_raw_stderr(self):
        mod=load('resolve_life_bundle')
        example=subprocess.CalledProcessError(1, ['gcloud'], stderr=b'unexpected private diagnostic data')
        with patch.object(mod.subprocess, 'run', side_effect=example):
            with self.assertRaises(mod.SecretMetadataError) as exc:
                mod.gcloud_json('secrets', 'versions', 'list', 'life-assistant-bundle')
        self.assertEqual(str(exc.exception), 'operation=versions_list category=OTHER')
        self.assertNotIn('private diagnostic', str(exc.exception))

    def test_six_menu_cells_cover_image(self):
        result=load('line_rich_menu').menu('123-abc')
        self.assertEqual(len(result['areas']),6)
        self.assertEqual(sum(x['bounds']['width']*x['bounds']['height'] for x in result['areas']),2500*1686)
        self.assertTrue(all(x['action']['uri'].startswith('https://liff.line.me/123-abc?') for x in result['areas']))
