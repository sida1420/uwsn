"""Independent topology seeds reserved from development; one subprocess at a time."""
import argparse
from pathlib import Path
import subprocess
import sys

PLAN = Path(__file__).resolve().parents[1]
ROOT = PLAN.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', nargs='+', type=int, default=[74, 75])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    grid = [('normal', 50, 11, 12), ('normal', 100, 13, 14), ('normal', 200, 15, 16),
            ('clustered', 50, 17, 18), ('clustered', 100, 19, 20), ('clustered', 200, 21, 22),
            ('uniform', 50, 23, 24), ('uniform', 100, 25, 26), ('uniform', 200, 27, 28)]
    for distribution, count, first, second in grid:
        command = [sys.executable, str(PLAN/'run-experiments.py'), '--skip-audited',
            '--output', str(args.output/f'{distribution}-{count}'), '--distributions', distribution,
            '--nodes', str(count), '--scenario-seeds', str(first), str(second), '--budget', '40',
            '--seeds', *map(str, args.seeds), '--variants', 'B0', 'V2', 'V5', 'V6',
            'V2+V5', 'V2+V6', 'R0', 'D0', 'D40total']
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
