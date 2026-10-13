"""Atomic outputs, exclusive coordinator lock, and reproducibility fingerprints."""
from contextlib import contextmanager
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import pickle
import platform
import time
import uuid
from optimizer import ROOT, PACKAGE

def digest(path): return sha256(Path(path).read_bytes()).hexdigest()

def fingerprint(cfg):
    return dict(configuration=json.loads(json.dumps(cfg)),map_sha=digest(cfg['map']),
        sources={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'src').rglob('*.py'))},
        harness={str(p.relative_to(ROOT)):digest(p) for p in sorted(PACKAGE.glob('*.py'))},
        python=platform.python_version(),
        versions={name:importlib.metadata.version(name) for name in ('numpy','optuna','PyYAML','psutil')})

def atomic(path,value,binary=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with tmp.open('wb' if binary else 'w', **({} if binary else {'encoding':'utf-8'})) as f:
            if binary: pickle.dump(value,f,protocol=pickle.HIGHEST_PROTOCOL)
            else: json.dump(value,f,indent=2,allow_nan=False)
            f.flush();os.fsync(f.fileno())
        # Windows readers may briefly hold a handle that disallows deletion.
        for attempt in range(20):
            try:
                os.replace(tmp,path);break
            except PermissionError:
                if attempt==19: raise
                time.sleep(.025)
    finally:
        if tmp.exists(): tmp.unlink()

def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def unpickle(path):
    # Only checkpoints produced in this trusted local study directory.
    with Path(path).open('rb') as f: return pickle.load(f)

def disk_mb(folder):
    total=0
    for path in Path(folder).rglob('*'):
        try:
            if path.is_file(): total+=path.stat().st_size
        except FileNotFoundError:
            # Worker atomic replacements can remove a temporary file between
            # enumeration and stat. The next pass counts its committed target.
            continue
    return total/(1024**2)

@contextmanager
def lock(path):
    """Kernel lock releases automatically on process death; local disks only."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        f.seek(0);f.write(b'0');f.flush();f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc: raise RuntimeError(f'Already locked: {path}') from exc
        try: yield
        finally:
            f.seek(0)
            if os.name=='nt': msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(f.fileno(),fcntl.LOCK_UN)
