"""Windows operational controls without changing frozen scientific settings.

Only coordinator concurrency and session stopping are overridden. Workers read
the original config and verify the original source/map/runtime fingerprint.
"""
import argparse
from contextlib import contextmanager
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimizer import controller
from optimizer.storage import atomic, read, digest


def total_time_stop(cfg, spent, session):
    total = cfg['max_wall_hours'] * 3600
    if spent + session >= max(0., total - min(20., total * .1)):
        return 'wall_budget'
    return None


@contextmanager
def operational_policy(folder, workers):
    if type(workers) is not int or not 1 <= workers <= 32:
        raise ValueError('Parallel runs must be an integer from 1 to 32')
    folder = Path(folder).resolve()
    original_epoch, original_lock = controller.assert_epoch, controller.lock
    original_stop, original_status = controller.time_stop, controller.status

    def epoch(path):
        # Validate every frozen field before overriding scheduling only.
        return {**original_epoch(path), 'max_workers': workers}

    @contextmanager
    def owned_lock(path):
        with original_lock(path):
            settings = dict(workers=workers, session_limit_disabled=True, started=time.time(),
                            launcher_runtime_sha=digest(__file__))
            history_path = folder / 'launch-runtime-history.json'
            history = read(history_path) if history_path.exists() else []
            atomic(history_path, [*history, settings])
            atomic(folder / 'launch-runtime.json', settings)
            yield

    def status(path):
        result = original_status(path)
        result.update(runtime_workers=workers, session_limit_disabled=True, max_session_hours=None)
        atomic(Path(path) / 'status.json', result)
        return result

    controller.assert_epoch, controller.lock = epoch, owned_lock
    controller.time_stop, controller.status = total_time_stop, status
    try:
        yield
    finally:
        controller.assert_epoch, controller.lock = original_epoch, original_lock
        controller.time_stop, controller.status = original_stop, original_status


def run(folder, workers):
    with operational_policy(folder, workers):
        return controller.run(folder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', required=True)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    import json
    print(json.dumps(run(args.study, args.workers), indent=2, allow_nan=False))
