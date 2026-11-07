import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

paths = json.loads(subprocess.check_output(['go', 'env', '-json', 'GOCACHE', 'GOMODCACHE'], text=True))
roots = {'build': paths['GOCACHE'], 'modules': paths['GOMODCACHE']}
if os.environ['SNAPSHOT_GROUP'] == 'linux-checks':
    roots['extra'] = '.git/golangci-lint-cache'
out = Path(os.environ['RUNNER_TEMP']) / 'produced-cache'
out.mkdir()
archive = out / 'cache.tar.zst'
zstd = shutil.which('zstd') or 'C:/Program Files/Git/usr/bin/zstd.exe'
with archive.open('wb') as target:
    process = subprocess.Popen([zstd, '-T2', '-3', '-c'], stdin=subprocess.PIPE, stdout=target)
    with tarfile.open(fileobj=process.stdin, mode='w|', format=tarfile.PAX_FORMAT) as tar:
        for name, root in roots.items():
            tar.add(root, arcname=name)
    process.stdin.close()
    if process.wait(timeout=1200):
        raise RuntimeError('zstd failed')
with archive.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
manifest = {'group': os.environ['SNAPSHOT_GROUP'], 'sha256': digest, 'source_run': os.environ['GITHUB_RUN_ID'], 'key': os.environ['GO_CACHE_KEY'], 'production_head': '99cc6603d86a40bc5fb3388ed2a74b9646d6d259', 'archive_bytes': archive.stat().st_size}
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest))
