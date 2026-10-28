"""Print six-button rich menu JSON; apply only with explicit --apply and an image."""
import argparse
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from urllib.parse import urlencode


def menu(liff_id):
    if not re.fullmatch(r'[0-9]+-[A-Za-z0-9]+', liff_id):
        raise ValueError('Invalid LIFF ID')
    labels = [('快速記錄','capture'),('今日總覽','today'),('查我的資料','search'),
              ('待辦・購物','tasks'),('日曆・活動','calendar'),('我的 Life','home')]
    return {'size': {'width': 2500, 'height': 1686}, 'selected': True,
            'name': 'Life B v1', 'chatBarText': '我的生活助手',
            'areas': [{'bounds': {'x': [0,833,1666][i%3], 'y': (i//3)*843,
                'width': [833,833,834][i%3], 'height': 843},
                'action': {'type': 'uri', 'label': title,
                    'uri': 'https://liff.line.me/'+liff_id+'?'+urlencode({'page':page})}}
                for i,(title,page) in enumerate(labels)]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--liff-id', required=True)
    parser.add_argument('--image', help='2500×1686 PNG/JPEG, <=1 MB, matching the six menu cells')
    parser.add_argument('--apply', action='store_true', help='Create/upload/set default; affects all OA friends')
    args=parser.parse_args()
    body=menu(args.liff_id)
    if not args.apply:
        print(json.dumps(body,ensure_ascii=False,indent=2));return
    if not args.image:
        parser.error('--apply requires --image')
    path=Path(args.image); data=path.read_bytes()
    if not 0 < len(data) <= 1000000 or path.suffix.lower() not in ('.png','.jpg','.jpeg'):
        parser.error('Use a PNG/JPEG image <=1 MB')
    token=os.environ.get('LIFE_LINE_ACCESS_TOKEN','')
    if not token: parser.error('Set LIFE_LINE_ACCESS_TOKEN securely; do not pass tokens on the command line')
    def call(url, payload=b'', method='POST', mime='application/json'):
        req=urllib.request.Request(url,data=payload,method=method,
            headers={'Authorization':'Bearer '+token,'Content-Type':mime})
        try:
            with urllib.request.urlopen(req,timeout=15) as response:
                raw=response.read();return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'LINE API HTTP {exc.code}; no automatic retry or deletion') from None
    result=call('https://api.line.me/v2/bot/richmenu',json.dumps(body).encode())
    identity=result['richMenuId']
    print('Created richMenuId='+identity+'; keep this ID for recovery.')
    call('https://api-data.line.me/v2/bot/richmenu/'+identity+'/content',data,
         mime='image/png' if path.suffix.lower()=='.png' else 'image/jpeg')
    call('https://api.line.me/v2/bot/user/all/richmenu/'+identity)
    print('Default rich menu applied. Existing per-user menus may take precedence.')


if __name__=='__main__':
    main()
