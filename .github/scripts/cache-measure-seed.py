import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

snapshot = Path(os.environ['RUNNER_TEMP']) / 'snapshot'
manifest = json.loads((snapshot / 'manifest.json').read_text())
archive = snapshot / 'cache.tar.zst'
with archive.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == manifest['sha256']
assert manifest['group'] == os.environ['SNAPSHOT_GROUP']
print(json.dumps(manifest))
paths = json.loads(subprocess.check_output(['go', 'env', '-json', 'GOCACHE', 'GOMODCACHE'], text=True))
roots = {'build': paths['GOCACHE'], 'modules': paths['GOMODCACHE']}
if manifest['group'] == 'linux-checks':
    roots['extra'] = '.git/golangci-lint-cache'
staging = Path(os.environ['RUNNER_TEMP']) / 'cache-seed'
staging.mkdir()
zstd = shutil.which('zstd') or 'C:/Program Files/Git/usr/bin/zstd.exe'
process = subprocess.Popen([zstd, '-d', '-c', str(archive)], stdout=subprocess.PIPE)
with tarfile.open(fileobj=process.stdout, mode='r|') as tar:
    tar.extractall(staging, filter='fully_trusted')
if process.wait(timeout=1200):
    raise RuntimeError('zstd failed')
for name, destination in roots.items():
    target = Path(destination)
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(staging / name), target)
archive.unlink()
