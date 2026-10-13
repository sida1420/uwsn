from pathlib import Path
from optimizer.storage import fingerprint,read

def epoch(cfg):
    return {**fingerprint(cfg), 'optimizer_layout': 'flat-v1'}

class EpochGuard:
    """Full hash at boundaries, inexpensive stat signatures between checkpoints."""
    def __init__(self,cfg,expected):
        self.cfg=cfg;self.expected=expected;self.signature=None;self.check(force=True)
    def check(self,force=False):
        from optimizer import ROOT
        paths=[ROOT/p for p in self.expected['sources']]+[ROOT/p for p in self.expected['harness']]+[Path(self.cfg['map'])]
        current=tuple((str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in paths)
        if force or current!=self.signature:
            if epoch(self.cfg)!=self.expected: raise RuntimeError('Source/map/runtime changed; campaign preserved')
            self.signature=current

def assert_campaign(folder):
    cfg=read(Path(folder)/'config.json');EpochGuard(cfg,read(Path(folder)/'provenance.json'));return cfg
