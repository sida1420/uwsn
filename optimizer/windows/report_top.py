"""Add a full top-five parameter comparison without changing study fingerprints."""
import argparse
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from optimizer.config import SPACE
from optimizer.storage import assert_epoch, atomic, read

START = '<!-- top-five-start -->'
END = '<!-- top-five-end -->'


def generate(folder):
    folder = Path(folder).resolve()
    cfg = assert_epoch(folder)
    if cfg['mode'] != 'scientific' or cfg['study_role'] != 'training':
        return []
    state = read(folder / 'state.json')
    candidates = []
    for key, job in state['jobs'].items():
        path = folder / 'trials' / key / 'aggregate.json'
        if key == 'reference' or job['status'] != 'complete' or not path.exists():
            continue
        metrics = read(path)
        if metrics['feasible']:
            candidates.append(dict(trial=job['number'], parameters=job['parameters'], **metrics))
    top = sorted(candidates, key=lambda r: (-r['mean_service_capped'], r['energy_K_mean'], r['trial']))[:5]
    atomic(folder / 'top-five-trials.json', top)
    names = list(SPACE) + sorted(set().union(*(r['parameters'] for r in top)) - set(SPACE))
    with (folder / 'top-five-parameters.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['rank','trial','mean_service','mean_energy_J',*names])
        writer.writeheader()
        for rank, row in enumerate(top, 1):
            writer.writerow(dict(rank=rank, trial=row['trial'], mean_service=row['mean_service_capped'],
                                 mean_energy_J=row['energy_K_mean'], **row['parameters']))
    lines = [START, '## Five best feasible trials', '',
             'Ranked by mean capped service, then lower mean energy. Each passes the +2% energy limit. '
             'These are training results; independent validation remains.', '',
             '| Rank | Trial | Mean service rounds | Mean energy over 2611 rounds (J) | Energy vs SimpleACO |',
             '|---:|---:|---:|---:|---:|']
    for rank, row in enumerate(top, 1):
        lines.append(f"| {rank} | {row['trial']} | {row['mean_service_capped']:.3f} | {row['energy_K_mean']:.6f} | {(row['energy_ratio']-1)*100:+.2f}% |")
    if not top:
        lines += ['', 'No complete feasible trials are available.']
    else:
        lines += ['', '### Full parameter values', '',
                  '| Parameter | ' + ' | '.join(f"Trial {row['trial']}" for row in top) + ' |',
                  '|---|' + '---|' * len(top)]
        for name in names:
            lines.append('| ' + name + ' | ' + ' | '.join(str(row['parameters'][name]) for row in top) + ' |')
        lines += ['', 'Full precision is retained in `top-five-trials.json` and `top-five-parameters.csv`.']
    lines += [END, '', '']
    report_path = folder / 'final-report.md'
    report = report_path.read_text(encoding='utf-8')
    if START in report:
        before, remainder = report.split(START, 1)
        _, after = remainder.split(END, 1)
        report = before + after.lstrip('\n')
    anchor = '| Trial | State | Mean capped service'
    position = report.find(anchor)
    if position < 0: position = len(report)
    report = report[:position] + '\n'.join(lines) + report[position:]
    report_path.write_text(report, encoding='utf-8')
    return top


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', required=True)
    args = parser.parse_args()
    top = generate(args.study)
    print('Top feasible trials: ' + ', '.join(str(row['trial']) for row in top))
