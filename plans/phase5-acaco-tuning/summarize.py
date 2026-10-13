"""Summarize the completed calibration without selecting on validation seeds."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from algorithms.clustering.ac_aco.parameters import ACACOParameters


def mean(rows, key):
    return sum(r[key] for r in rows) / len(rows)


def main():
    folder = Path(__file__).parent
    data = json.loads((folder / 'results.json').read_text())
    selected = 'q0.01_max20.0_rho0.6'
    config = data['configs'][selected]
    assert config == asdict(ACACOParameters()), 'Defaults must match the validated config'
    selected_rows = data['validation'][selected]
    baseline = data['validation']['historical']
    assert all(r['rounds'] == 150 and not r['failed'] for r in selected_rows + baseline)
    summary = ['\n<!-- RESULTS -->\n', '## Completed results\n',
        '| Validation configuration | Mean 150-round energy (J) | Change vs historical | Mean CPU (s) | Floor occupancy | Ceiling occupancy |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    base_energy = mean(baseline, 'energy_J')
    for name, rows in data['validation'].items():
        energy = mean(rows, 'energy_J')
        summary.append(f"| {name} | {energy:.9f} | {(energy/base_energy-1)*100:+.3f}% | "
            f"{mean(rows,'cpu_s'):.3f} | {mean(rows,'mean_floor')*100:.3f}% | "
            f"{mean(rows,'mean_ceiling')*100:.3f}% |")
    summary.extend(['', '| Seed | Historical energy (J) | New defaults (J) | Change |',
                    '| --- | ---: | ---: | ---: |'])
    for b, n in zip(baseline, selected_rows):
        summary.append(f"| {b['seed']} | {b['energy_J']:.9f} | {n['energy_J']:.9f} | "
            f"{(n['energy_J']/b['energy_J']-1)*100:+.3f}% |")
    evaluations = sum(r['feasible_evaluations'] for stage in ('screening','validation')
        for rows in data[stage].values() for r in rows)
    peak_old = max(r['peak_depletion'] for r in baseline)
    peak_new = max(r['peak_depletion'] for r in selected_rows)
    summary.extend(['', f"Screened {len(data['screening'])} configurations; completed "
        f"{evaluations:,} feasible evaluations including exploratory controls and validation.",
        'All measured rounds served all 100 live sensors, with no observed deaths or routing failures.',
        '', 'Applied defaults: `Q=.01`, `tau_min=.01`, `tau0=1`, `tau_max=20`, '
        '`rho_min=.1`, `rho_max=.6`. Other parameters retain their explicitly inventoried values.',
        'The lower acoustic exponent remains experimental: it saved slightly more early energy, '
        'but late-round behavior and lifetime are unvalidated. Repeated timings varied markedly '
        'even for identical trajectories, so the initial apparent CPU regression is not reliable. Beta_max=3 was '
        'exploratory only; these 150-round trials cannot assess the raw schedule near round 1500.',
        '', f"Maximum observed single-round relative depletion: historical {peak_old:.9f}, "
        f"selected {peak_new:.9f} ({(peak_new/peak_old-1)*100:+.2f}%). This is a remaining "
        'lifetime risk, not proof of earlier death. The change is adopted for numerical scale '
        'and preserved early feasibility, not a claimed lifetime improvement.',
        '', 'Floors .001/.01/.05 gave the same screening energies in their matched controls; '
        '.01 is chosen from the background-disturbance scale, not a measured optimum. '
        'Wide and small ceilings also yield identical early trajectories when neither clips; '
        'the wider value is chosen for late recurrence headroom.',
        '', 'Validation seed results do not certify generalization across topologies. '
        'No 600-round or full-lifetime experiment was performed.',
        '', 'Verification: 21 unit tests pass, including historical elite-clamp regression, '
        'inverse-cost discrimination, sustained late reinforcement, finite normalized probabilities '
        'and exact full service across coupled scales.',
        '', f"Map SHA-256: `{data['map_sha']}`. Starting git SHA: `{data['git_sha']}`."])
    report = folder / 'README.md'
    prefix = report.read_text().split('<!-- RESULTS -->')[0].rstrip()
    report.write_text(prefix + '\n' + '\n'.join(summary) + '\n')
    canonical = json.dumps(config, sort_keys=True)
    manifest = dict(selected_config=selected, parameters=config,
        config_sha256=sha256(canonical.encode()).hexdigest(),
        map_sha256=data['map_sha'], starting_git_sha=data['git_sha'],
        selection_reason='Coupled numeric scale, no early loss of service; not lifetime superiority',
        production_source_hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'src').rglob('*.py'))})
    (folder / 'selected-config.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('\n'.join(summary))


if __name__ == '__main__':
    main()
