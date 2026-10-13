"""Report all twelve full new-policy runs and six historical references."""
import json
from pathlib import Path
import statistics as st

FOLDER = Path(__file__).parent
ROOT = FOLDER.parents[1]
SEEDS = (15,16,17)
NAMES = ('energy_live','linear_load','power_010','power_025','power_100')


def main():
    rows = {(s,n):json.loads((FOLDER/'full'/f'{n}_{s}.json').read_text()) for s in SEEDS for n in NAMES}
    provenance = rows[15,'energy_live']['provenance']
    for (s,n),r in rows.items():
        if n=='power_100':
            extra = r['provenance'].copy()
            extra.pop('extra_config')
            extra.pop('driver_sha')
            assert extra==provenance
            assert r['parameters']==r['provenance']['extra_config'][n]
        else:
            assert r['provenance']==provenance
            assert r['parameters']==provenance['configs'][n]
        assert r['seed']==s and r['configuration']==n
        assert len(r['records'])==r['completed_rounds']
    for s in SEEDS:
        for name,target in (('baseline','old_baseline'),('density_005','old_max_005')):
            r = json.loads((ROOT/'plans/phase8-daco-tuned/full'/f'{name}_{s}.json').read_text())
            assert r['provenance']['map_sha']==provenance['map_sha']
            rows[s,target] = r
    names = ('old_baseline','old_max_005')+NAMES
    exposure = min(r['completed_rounds'] for r in rows.values())
    predeath = min([r['FND']-1 for r in rows.values() if r['FND'] is not None]+[exposure])
    summary = dict(provenance=provenance,equal_exposure_rounds=exposure,all_alive_rounds=predeath,groups={})
    base_energy = st.mean(sum(x['energy'] for x in rows[s,'old_baseline']['records'][:predeath]) for s in SEEDS)
    lines = ['# Full D-ACO: powered load/density with live pheromone', '',
        'Fifteen new full trials: three paired seeds 15/16/17 for five configurations. '
        'Six completed historical full trajectories supply old baseline and max-penalty references. '
        'All use the current 100-sensor map and 3000-round horizon or normal termination. '
        'Only D-ACO is simulated; all physical rounds use one batch of 40 ants.', '',
        '`P = mean((consumption/residual)^p / max(structural_grid_density, epsilon))`', '',
        '`F = total_energy + weight * E_ref * P/P_ref`', '',
        'Ant and elite use the same cached F and frozen per-round E_ref. '
        'Pheromone is always live. A throwaway initial batch estimates E_ref and P_ref; '
        'it consumes computation and RNG, but no simulated energy, deposits, or physical round. '
        'Reference updates after the round are geometric: previous^0.8 * observed^0.2. '
        'Evaporation occurs once before physical ants; the elite bonus follows their live deposits.', '',
        f'Energy comparisons use the same first {predeath} rounds with all sensors alive. '
        'Historical references did not have the new calibration batch or live policy. '
        'The energy_live control separates that policy change from adding powered load/density.', '',
        '| Configuration | Mean FND | Mean service | All-alive energy change | Mean attempts, including calibration |',
        '| --- | ---: | ---: | ---: | ---: |']
    for name in names:
        group = [rows[s,name] for s in SEEDS]
        fnds = [r['FND'] for r in group]
        energy = st.mean(sum(x['energy'] for x in r['records'][:predeath]) for r in group)
        metrics = dict(mean_FND=st.mean(fnds) if all(f is not None for f in fnds) else None,
            mean_service=st.mean(r['completed_rounds'] for r in group),all_alive_energy=energy,
            energy_change_percent=100*(energy/base_energy-1),
            mean_cpu=st.mean(r['cpu'] for r in group),
            mean_attempts=st.mean(r['clustering_attempts']+r.get('calibration_attempts',0) for r in group),
            calibration_attempts=[r.get('calibration_attempts',0) for r in group],
            paired_FND_changes=[rows[s,name]['FND']-rows[s,'old_baseline']['FND']
                if rows[s,name]['FND'] is not None else None for s in SEEDS],
            paired_service_changes=[rows[s,name]['completed_rounds']-rows[s,'old_baseline']['completed_rounds'] for s in SEEDS],
            paired_energy_changes=[100*(sum(x['energy'] for x in rows[s,name]['records'][:predeath])/
                sum(x['energy'] for x in rows[s,'old_baseline']['records'][:predeath])-1) for s in SEEDS])
        summary['groups'][name] = metrics
        fnd = f"{metrics['mean_FND']:.1f}" if metrics['mean_FND'] is not None else 'censored'
        lines.append(f"| {name} | {fnd} | {metrics['mean_service']:.1f} | {metrics['energy_change_percent']:+.3f}% | {metrics['mean_attempts']:.0f} |")
    lines += ['', 'CPU includes calibration and the terminal failed search, but hardware frequency and '
        'concurrent scheduling are uncontrolled. Attempt counts are a more stable measure of work. '
        'Full-survivor service failure does not mean all sensors died; HND/LND may be censored. '
        'Three seeds on one map are not deployment-wide validation.', '',
        'Q stays fixed when changing the objective multiplier. A larger multiplier also '
        'reduces inverse-fitness deposit magnitudes; these trials measure the complete policy, '
        'not an objective-weight change with total reinforcement mass held constant.', '',
        'The old CV/max objectives and mode switches are removed from production, not deleted from historical evidence. '
        'Their code lives only in archive; its original hashes and first-ten-round replay match the six references. '
        'All grid decay options remain. AC-ACO and the sibling uwsn source are unchanged in this phase.']
    lines += ['', '## Selected production default', '',
        'Use load_power=2, load_density_weight=0.25, reference_memory=0.8. '
        'This is a deliberate energy/lifetime compromise: mean first-node death 1896.7 '
        'and mean service 2318.0, versus 1658.3 and 2190.7 for the old baseline. '
        'Energy rises 0.601% over equal all-alive rounds. '
        'Paired service gains are +101/+135/+146, and paired first-death gains +209/+267/+239.', '',
        'Weight 0.10 gives 2263.7 mean service rounds for +0.466% energy; moving to 0.25 '
        'adds 54.3 rounds at only 0.135 percentage points more energy. '
        'Moving from 0.25 to 1.0 adds a further 48.7 service rounds but raises energy '
        'by another 1.232 percentage points relative to baseline. Weight 1.0 remains available.', '',
        'The old max-penalty reference still gives later first-node death and slightly more '
        'service than the new weight-1.0 case, at a larger energy cost. '
        'The new policy is not uniformly superior to max. The clean p=1 versus p=2 '
        'comparison at weight 0.10 shows the exponent improves lifetime within the new framework.', '',
        'The default was promoted after all runs finished. Raw source hashes describe the '
        'tested prototype default; its explicit power_025 parameter set matches the promoted '
        'default. The experiment base is now explicitly frozen at 0.10 to prevent labels '
        'changing when production defaults change.']
    summary['selection'] = dict(configuration='power_025',load_power=2.,load_density_weight=.25,
                                reference_memory=.8,reason='Energy/lifetime compromise, not an energy-only win')
    (FOLDER/'summary.json').write_text(json.dumps(summary,indent=2))
    (FOLDER/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='provenance'},indent=2))


if __name__=='__main__':
    main()
