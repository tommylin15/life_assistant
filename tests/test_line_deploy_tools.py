import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

class LineDeployTests(unittest.TestCase):
    def test_disabled_by_default(self):
        self.assertEqual(load('line_deploy_flags').build_flags({}),['--update-env-vars=LIFE_LINE_ENABLED=false'])

    def test_incomplete_config_fails_closed(self):
        with self.assertRaises(ValueError):
            load('line_deploy_flags').build_flags({'LINE_ENABLED':'true'})

    def test_pinned_secret_versions_and_untrusted_origin(self):
        env={'LINE_ENABLED':'true','LINE_NAMESPACE':'stage','LINE_ORIGIN':'https://life.example',
             'LINE_LIFF_ID':'123-abc','LINE_LOGIN_CHANNEL_ID':'123',
             'LINE_CHANNEL_SECRET_REF':'line-secret:2','LINE_ACCESS_TOKEN_REF':'line-token:3'}
        flags=load('line_deploy_flags').build_flags(env)
        self.assertEqual(len(flags),2)
        self.assertIn('line-secret:2',flags[1])
        for key,value in [('LINE_ORIGIN','https://life.example,OTHER=true'),('LINE_CHANNEL_SECRET_REF','secret:latest')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                load('line_deploy_flags').build_flags({**env,key:value})

    def test_six_menu_cells_cover_image(self):
        result=load('line_rich_menu').menu('123-abc')
        self.assertEqual(len(result['areas']),6)
        self.assertEqual(sum(x['bounds']['width']*x['bounds']['height'] for x in result['areas']),2500*1686)
        self.assertTrue(all(x['action']['uri'].startswith('https://liff.line.me/123-abc?') for x in result['areas']))
