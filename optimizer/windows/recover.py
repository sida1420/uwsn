"""Repair launcher statuses, preserving the scientific harness and checkpoints."""
import argparse
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimizer.storage import atomic, assert_epoch, lock, read
from optimizer.controller import same_process
import psutil


def recover(folder):
    folder = Path(folder).resolve()
    with lock(folder / 'controller.lock'):
        assert_epoch(folder)
        state = read(folder / 'state.json')
        for job in state['jobs'].values():
            if job.get('pid') and same_process(job['pid'], job['created']):
                try:
                    psutil.Process(job['pid']).wait(timeout=15)
                except psutil.TimeoutExpired:
                    raise RuntimeError('Previous worker is still checkpointing. Wait before resuming.')
        repaired = []
        for key, job in state['jobs'].items():
            if job['status'] == 'running':
                job['status'] = 'paused'
                job.pop('pid', None)
                repaired.append(key)
        if repaired:
            state.setdefault('launcher_recoveries', []).append(dict(time=time.time(), trials=repaired))
            atomic(folder / 'state.json', state)
        print('Ready to resume. Recovered trials: ' + (', '.join(repaired) or 'none'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', required=True)
    args = parser.parse_args()
    try:
        recover(args.study)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(10 if str(exc).startswith('Already locked:') else 1)
