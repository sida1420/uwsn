"""Require all twelve full trajectories before comparing grid decay."""
import json
from pathlib import Path
import statistics as st

FOLDER = Path(__file__).parent
SEEDS = (15,16,17)
DECAYS = ('none','linear','quadratic','parabolic')


def main():
    rows = {(s,d):json.loads((FOLDER/'full'/f'{d}_{s}.json').read_text())
            for s in SEEDS for d in DECAYS}
    provenance = rows[15,'none']['provenance']
    for (seed,decay),row in rows.items():
        if decay=='parabolic':
            common = row['provenance'].copy()
            common.pop('adapter_sha')
            common['decays'] = provenance['decays']
            assert common==provenance
        else:
            assert row['provenance']==provenance
        assert row['seed']==seed and row['decay']==decay
        assert len(row['records'])==row['completed_rounds']
        expected = rows[seed,'none']['parameters'].copy()
        expected['density_decay'] = 'none' if decay=='parabolic' else decay
        if decay=='parabolic':
            expected['density_profile'] = 'parabolic'
        assert row['parameters']==expected
    horizon = min(r['completed_rounds'] for r in rows.values())
    summary = dict(provenance=provenance,equal_exposure_rounds=horizon,groups={})
    lines = ['# Full D-ACO grid-distance experiment', '',
        'Twelve full trajectories on the current 100-node map, radius 200 m, paired seeds 15/16/17. '
        'Each runs until no feasible tree, all nodes die, or the 3000-round horizon. '
        'Only grid attenuation changes; 40 ants, one batch, up to ten feasibility attempts per ant, '
        'routing, pheromone, and energy/load-CV fitness remain fixed.', '',
        'The original overlap matrix F has unit weights for fully reachable cells. '
        'Linear multiplies F by `max(1 - d/(R + r_cell), 0)`; quadratic uses its square. '
        'Parabolic instead uses `max(1 - (d/(R + r_cell))^2, 0)`: gentle nearby, steeper farther away. '
        '`d` is sensor-to-cell-center distance and `r_cell` is the cell half-diagonal. '
        'The extended reach preserves partially reachable cells. This factor is applied consistently '
        'to grid density, candidate density, and coverage loss. No sensor-neighbor density is used.', '',
        '| Seed | Grid | First-node death | Completed service | CPU seconds |',
        '| --- | --- | ---: | ---: | ---: |']
    for seed in SEEDS:
        for decay in DECAYS:
            r = rows[seed,decay]
            lines.append(f"| {seed} | {decay} | {r['FND'] if r['FND'] is not None else 'censored'} | {r['completed_rounds']} | {r['cpu']:.1f} |")
    lines += ['',f'Energy comparisons use the same first {horizon} completed rounds for every run.', '',
        '| Grid | Mean FND | Mean service | Equal-round energy | Energy change | CPU per completed round |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    baseline_energy = st.mean(sum(r['energy'] for r in rows[s,'none']['records'][:horizon]) for s in SEEDS)
    for decay in DECAYS:
        group = [rows[s,decay] for s in SEEDS]
        fnds = [r['FND'] for r in group]
        energy = st.mean(sum(x['energy'] for x in r['records'][:horizon]) for r in group)
        metrics = dict(mean_FND=st.mean(fnds) if all(f is not None for f in fnds) else None,
            mean_service=st.mean(r['completed_rounds'] for r in group),energy=energy,
            energy_change_percent=100*(energy/baseline_energy-1),
            cpu_per_round=st.mean(r['cpu']/r['completed_rounds'] for r in group),
            paired_service_changes=[rows[s,decay]['completed_rounds']-rows[s,'none']['completed_rounds'] for s in SEEDS],
            paired_FND_changes=[rows[s,decay]['FND']-rows[s,'none']['FND']
                if rows[s,decay]['FND'] is not None and rows[s,'none']['FND'] is not None else None for s in SEEDS],
            paired_energy_change_percent=[100*(sum(x['energy'] for x in rows[s,decay]['records'][:horizon])/
                sum(x['energy'] for x in rows[s,'none']['records'][:horizon])-1) for s in SEEDS])
        summary['groups'][decay] = metrics
        fnd = f"{metrics['mean_FND']:.2f}" if metrics['mean_FND'] is not None else 'censored'
        lines.append(f"| {decay} | {fnd} | {metrics['mean_service']:.2f} | {energy:.6f} | {metrics['energy_change_percent']:+.3f}% | {metrics['cpu_per_round']:.4f}s |")
    lines += ['', 'Full service means the search found a tree for every surviving sensor. '
        'Failure to find a tree is not equivalent to all sensors dying; HND/LND can be censored. '
        'Energy over equal rounds avoids rewarding an algorithm simply for stopping earlier. '
        'CPU times include the terminal failed search; concurrent runs make wall-time comparisons unsuitable.', '',
        'CPU measurements are indicative: concurrency increased during the later trials, '
        'and hardware load/frequency were not controlled. Do not treat their ratios as precise kernel overhead.', '',
        'Three seeds on one map are a paired comparison, not proof of improvement across deployments. '
        'No density-aware load fitness is enabled in these runs.']
    predeath = min([r['FND']-1 for r in rows.values() if r['FND'] is not None]+[horizon])
    summary['all_alive_comparison_rounds'] = predeath
    summary['all_alive_energy'] = {}
    lines += ['', f'## Energy while all sensors remain alive: first {predeath} rounds', '',
        '| Grid | Mean energy | Change from original | Paired changes by seed |',
        '| --- | ---: | ---: | --- |']
    totals = {d:[sum(x['energy'] for x in rows[s,d]['records'][:predeath]) for s in SEEDS] for d in DECAYS}
    for d in DECAYS:
        changes = [100*(a/b-1) for a,b in zip(totals[d],totals['none'])]
        change = 100*(st.mean(totals[d])/st.mean(totals['none'])-1)
        summary['all_alive_energy'][d] = dict(mean=st.mean(totals[d]),change_percent=change,paired_changes=changes)
        lines.append(f"| {d} | {st.mean(totals[d]):.6f} | {change:+.3f}% | {', '.join(f'{v:+.3f}%' for v in changes)} |")
    summary['all_alive_load'] = {}
    lines += ['', '| Grid | Mean load CV | Mean peak relative depletion |',
        '| --- | ---: | ---: |']
    for d in DECAYS:
        cv = st.mean(st.mean(x['cv'] for x in rows[s,d]['records'][:predeath]) for s in SEEDS)
        risk = st.mean(st.mean(x['peak_depletion'] for x in rows[s,d]['records'][:predeath]) for s in SEEDS)
        summary['all_alive_load'][d] = dict(cv=cv,peak_depletion=risk)
        lines.append(f'| {d} | {cv:.6f} | {risk:.6f} |')
    lines += ['', '## Decision', '',
        'Keep the original grid (`density_decay="none"`) as the default. '
        'Linear improves mean service by 9 rounds (paired changes +4/+8/+15), '
        'but raises all-alive energy by 0.378%. It is the best service tradeoff of these variants. '
        'The fast-drop quadratic curve delays first-node death most, at a 1.176% energy cost. '
        'The gentle-near parabolic curve loses 8 mean service rounds and uses 0.118% more all-alive energy.', '',
        'All three curves are available as explicit production options, including `density_decay="parabolic"`. '
        'The optional parabolic implementation was added after the experiments completed; '
        'a regression test verifies its grid weights, density, and coverage-loss scores exactly match the tested adapter. '
        'Recorded source hashes describe the code used during the runs, not this later addition.', '',
        'Density-aware load fitness remains unchanged because the proposed gentle-near curve did not improve the full comparison. '
        'Any later fitness experiment should use the baseline weighted grid density before CH coverage loss, '
        'rather than the order-dependent remaining-density score.', '',
        'Mean peak relative depletion is sensitive to a nearly exhausted sensor just before first-node death; '
        'its reduction alone does not quantify whole-network balance. Absolute load CV slightly increases for all weighted variants.']
    (FOLDER/'summary.json').write_text(json.dumps(summary,indent=2))
    (FOLDER/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='provenance'},indent=2))


if __name__=='__main__':
    main()
