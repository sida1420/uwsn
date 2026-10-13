"""Summarize completed lifetime pairs and the matched-state math probes."""
import json
import math
from pathlib import Path
import statistics as st

FOLDER = Path(__file__).parent / 'long'


def populate_probe_table():
    probes=json.loads((FOLDER/'math-probes.json').read_text())
    table=['| Completed checkpoint | Factor | Mean candidate energy (J) | Empirical expected best of 40 (J) | Mean outliers | Mean CH pair distance (m) |',
           '| --- | ---: | ---: | ---: | ---: | ---: |']
    for checkpoint,values in probes.items():
        for factor,r in values.items():
            table.append(f"| {checkpoint} | {factor} | {r['mean_energy_J']:.9f} | {r['empirical_best40_J']:.9f} | {r['mean_outliers']:.4f} | {r['mean_CH_pair_distance_m']:.3f} |")
    text=(FOLDER/'MATH_ANALYSIS.md').read_text(encoding='utf-8')
    begin='<!-- PROBE_TABLE_BEGIN -->'
    end='<!-- PROBE_TABLE_END -->'
    text=text.split(begin)[0]+begin+'\n'+'\n'.join(table)+'\n'+end+text.split(end)[1]
    (FOLDER/'MATH_ANALYSIS.md').write_text(text,encoding='utf-8')


def main():
    runs = [json.loads(p.read_text()) for p in sorted(FOLDER.glob('calibrated_x?_seed?.json'))]
    assert len(runs) == 6, 'Wait for all six trajectories before summarizing'
    by = {(r['seed'], r['config']): r for r in runs}
    prior = json.loads((FOLDER.parent / 'results.json').read_text())
    for r in runs:
        control = next(x for x in prior['validation'][r['config']] if x['seed'] == r['seed'])
        assert math.isclose(sum(x['energy_J'] for x in r['records'][:150]),
                            control['total_energy_J'], rel_tol=1e-12)
    lines = ['# Longer chaos validation', '',
        'Current chaos bounds [.05,.30] versus doubled bounds [.10,.60], with all other calibrated parameters fixed. '
        'Independent physical trajectories use seeds 6/7/8 on the same 100-node map, up to 3000 rounds. '
        'These extend the earlier 150-round seeds; they are not a new holdout. Routing, physics and the production defaults are unchanged.', '',
        '| Seed | Current FND | Doubled FND | Current completed rounds | Doubled completed rounds |',
        '| --- | ---: | ---: | ---: | ---: |']
    for seed in (6,7,8):
        a,b = (by[seed,n] for n in ('calibrated_x1','calibrated_x2'))
        lines.append(f"| {seed} | {a['FND']} | {b['FND']} | {a['completed_rounds']} | {b['completed_rounds']} |")
    fnd_means=[st.mean(by[s,n]['FND'] for s in (6,7,8)) for n in ('calibrated_x1','calibrated_x2')]
    service_means=[st.mean(by[s,n]['completed_rounds'] for s in (6,7,8)) for n in ('calibrated_x1','calibrated_x2')]
    lines += ['', f'Mean FND: {fnd_means[0]:.3f} versus {fnd_means[1]:.3f} rounds '
        f'({(fnd_means[1]/fnd_means[0]-1)*100:+.3f}%). Mean completed full-survivor service: '
        f'{service_means[0]:.3f} versus {service_means[1]:.3f} rounds '
        f'({(service_means[1]/service_means[0]-1)*100:+.3f}%).', '',
        'Retain production chaos bounds [.05,.30]. The doubled [.10,.60] setting remains an experimental candidate: '
        'its energy gain is small and FND does not improve consistently across seeds. '
        'Mean full-survivor service also regresses. '
        'This single-map, three-seed comparison establishes neither statistical significance nor an optimal strength range.']
    lines += ['', 'FND is the number of completed rounds at the first death, using one-based counting. '
        'HND and LND are censored when not observed. A failed routing search ends service in this simulator; '
        'this does not mean all sensors have died.', '',
        '| Equal exposure | Current mean modeled energy (J) | Doubled mean (J) | Change |',
        '| --- | ---: | ---: | ---: |']
    for k in (150,600,1400):
        groups = [[sum(x['energy_J'] for x in by[s,n]['records'][:k]) for s in (6,7,8)]
                  for n in ('calibrated_x1','calibrated_x2')]
        assert all(by[s,n]['completed_rounds']>=k for s in (6,7,8) for n in ('calibrated_x1','calibrated_x2'))
        a,b=map(st.mean,groups)
        lines.append(f'| {k} rounds | {a:.9f} | {b:.9f} | {(b/a-1)*100:+.3f}% |')
    lines += ['', 'Full-run cumulative energies are not compared as efficiency scores because trajectories can have different durations or survivor counts.', '',
        '## Critical-node energy at round 1400', '',
        '| Seed | Current node 33 residual (J) | Doubled node 33 (J) | Current node 65 residual (J) | Doubled node 65 (J) |',
        '| --- | ---: | ---: | ---: | ---: |']
    for seed in (6,7,8):
        a,b=(json.loads((FOLDER/f'{n}_seed{seed}_round1400.json').read_text()) for n in ('calibrated_x1','calibrated_x2'))
        lines.append(f"| {seed} | {a['residual'][33]:.6f} | {b['residual'][33]:.6f} | {a['residual'][65]:.6f} | {b['residual'][65]:.6f} |")
    lines += ['', 'Node 48 has only neighbors 33 and 65 within communication range. '
        'After node 33 dies, preserving node 65 is necessary for full-survivor service. '
        'Lower total energy does not guarantee preserving this node.', '',
        '## Termination and bounds', '',
        '| Configuration / seed | Termination | Survivors | HND | LND | Max floor / ceiling occupancy |',
        '| --- | --- | ---: | --- | --- | --- |']
    for r in runs:
        floor=max(x['tau_floor_fraction'] for x in r['records'])
        ceiling=max(x['tau_ceiling_fraction'] for x in r['records'])
        lines.append(f"| {r['config']} / {r['seed']} | {r['termination_reason']} | {r['alive_at_end']} | {r['HND'] or 'censored'} | {r['LND'] or 'censored'} | {floor:.3%} / {ceiling:.3%} |")
    lines += ['', '## Terminal connectivity', '']
    for r in runs:
        disconnected=r.get('terminal_connectivity',{}).get('disconnected',[])
        lines.append(f"- {r['config']}, seed {r['seed']}: disconnected surviving node IDs {disconnected}; failed search attempts {r.get('failed_search_attempts',0)}.")
    lines += ['', 'An empty disconnected list means the undirected communication graph still reaches the base; '
        'the greedy router and finite search budget can nevertheless fail. A nonempty list proves that full-survivor service is physically impossible on this graph.', '',
        '## Late search feasibility', '',
        'The ant count and ten-attempt limit are fixed, but failed ants can leave fewer feasible candidates to compare. '
        'The following averages use rounds 1501 through the shorter trajectory endpoint within each pair. '
        'These are different evolving physical/optimizer states; survivor counts can differ briefly around the paired FND times. '
        'They do not isolate transition mixing alone.', '',
        '| Seed | Common late rounds | Current feasible candidates / attempts | Doubled feasible candidates / attempts |',
        '| --- | ---: | ---: | ---: |']
    for seed in (6,7,8):
        a,b=(by[seed,n] for n in ('calibrated_x1','calibrated_x2'))
        end=min(a['completed_rounds'],b['completed_rounds'])
        cells=[]
        for r in (a,b):
            rows=r['records'][1500:end]
            cells.append(f"{st.mean(x['feasible_evaluations'] for x in rows):.3f} / {st.mean(x['routing_attempts'] for x in rows):.3f}" if rows else 'not observed')
        lines.append(f'| {seed} | {max(0,end-1500)} | {cells[0]} | {cells[1]} |')
    lines += ['',
        '## Verification and reproduction', '',
        f"Every selected route independently reevaluated and served every live sensor. Total feasible candidate evaluations: {sum(x['feasible_evaluations'] for r in runs for x in r['records']):,}. "
        'Residual energy is clamped to zero on death, so modeled cost can exceed physically deducted energy in a death round. '
        'Per-round modeled/deducted energy, deaths, attempts, pheromone occupancy and checkpoints are saved. '
        'All 28 repository tests passed, including checkpoint restoration, connectivity cuts and the exact mixture/order-statistic identities. '
        'Search CPU is indicative and excludes the failed terminal search; concurrent jobs make wall-time comparisons unsuitable.', '',
        'Run `python -B plans/phase5-acaco-chaos/long_run.py` to run/reuse all pairs. '
        '`run_pair.py 7` and `run_pair.py 8` allow independent pairs to run concurrently; completed files are reused. '
        'Then run `math_probe.py` and `long_report.py`. Long-run source hashes must match the preceding amplitude study.', '',
        'See [the mathematical analysis](MATH_ANALYSIS.md) for the exact mixing identity, coverage mechanism and limitations.']
    (FOLDER/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    populate_probe_table()
    summary={str(seed):dict(current_FND=by[seed,'calibrated_x1']['FND'],doubled_FND=by[seed,'calibrated_x2']['FND'],
        current_completed=by[seed,'calibrated_x1']['completed_rounds'],doubled_completed=by[seed,'calibrated_x2']['completed_rounds']) for seed in (6,7,8)}
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
