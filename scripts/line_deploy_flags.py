"""Emit validated NUL-delimited gcloud flags; never handle secret values."""
import os
import re
import sys


def build_flags(env):
    if env.get('LINE_ENABLED') != 'true':
        return ['--update-env-vars=LIFE_LINE_ENABLED=false']
    values = {key: env.get('LINE_' + key, '').strip() for key in
              ('NAMESPACE', 'ORIGIN', 'LIFF_ID', 'LOGIN_CHANNEL_ID', 'CHANNEL_SECRET_REF', 'ACCESS_TOKEN_REF')}
    patterns = {'NAMESPACE': r'[a-zA-Z0-9_-]{1,80}', 'ORIGIN': r'https://[a-zA-Z0-9.-]+',
                'LIFF_ID': r'[0-9]+-[a-zA-Z0-9]+', 'LOGIN_CHANNEL_ID': r'[0-9]+',
                'CHANNEL_SECRET_REF': r'[a-zA-Z0-9_-]+:[1-9][0-9]*',
                'ACCESS_TOKEN_REF': r'[a-zA-Z0-9_-]+:[1-9][0-9]*'}
    for key, pattern in patterns.items():
        if not re.fullmatch(pattern, values[key]):
            raise ValueError('Missing or invalid LINE_' + key)
    return ['--update-env-vars=' + ','.join(['LIFE_LINE_ENABLED=true'] + [
        'LIFE_LINE_' + key + '=' + values[key] for key in ('NAMESPACE', 'ORIGIN', 'LIFF_ID', 'LOGIN_CHANNEL_ID')]),
        '--update-secrets=LIFE_LINE_CHANNEL_SECRET=' + values['CHANNEL_SECRET_REF'] +
        ',LIFE_LINE_ACCESS_TOKEN=' + values['ACCESS_TOKEN_REF']]


if __name__ == '__main__':
    try:
        for flag in build_flags(os.environ):
            sys.stdout.buffer.write(flag.encode() + b'\0')
    except ValueError as exc:
        sys.exit(str(exc))
