#!/usr/bin/env python3
"""Download public pyrekordbox test ANLZ only; no audio, no owner export."""
import hashlib,json,urllib.request,urllib.parse
from pathlib import Path
COMMIT='f695541827cc488af267d6ca8a8e0052598d85a0'
root=Path(__file__).resolve().parents[1]
tree=json.load(urllib.request.urlopen(f'https://api.github.com/repos/dylanljones/pyrekordbox/git/trees/{COMMIT}?recursive=1',timeout=30))
files=[t['path'] for t in tree['tree'] if '/USBANLZ/' in t['path'] and t['path'].endswith('.DAT')]
manifest=[]
for name in files:
    url=f'https://raw.githubusercontent.com/dylanljones/pyrekordbox/{COMMIT}/'+urllib.parse.quote(name)
    data=urllib.request.urlopen(url,timeout=30).read();relative=Path('private/fixtures')/name
    dest=root/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and dest.read_bytes()!=data:raise ValueError('Existing fixture differs')
    dest.write_bytes(data);manifest.append({'file':str(relative),'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(root/'evidence/reference-fixtures.json').write_text(json.dumps({'repository':'dylanljones/pyrekordbox','commit':COMMIT,'kind':'public upstream test data; not owner USB','files':manifest},indent=2)+'\n')
print(f'{len(files)} public DAT fixtures downloaded under private/fixtures')
