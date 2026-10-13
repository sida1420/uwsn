"""Summarize six full lifetime runs; never substitute partial progress files."""
import json
from pathlib import Path
import statistics as st

FOLDER = Path(__file__).parent/'full'
SEEDS = (15,16,17)
NAMES = ('elite_1','elite_01')


def main():
    rows = {(s,n):json.loads((FOLDER/f'{n}_seed{s}.json').read_text())
        for s in SEEDS for n in NAMES}
    provenance = next(iter(rows.values()))['provenance']
    for (seed,name),r in rows.items():
        assert r['provenance'] == provenance
        assert r['parameters'] == provenance['configs'][name]
        assert r['seed'] == seed and r['config'] == name
        assert len(r['records']) == r['completed_rounds']
        assert all(x['served'] >= x['alive'] for x in r['records'])
    p1,p01 = (provenance['configs'][n] for n in NAMES)
    assert {k for k in p1 if p1[k] != p01[k]} == {'elite_weight'}
    lines = ['# Full lifetime test: best-set weight 1 versus 0.1', '',
        'Historical scope: all six runs use `energy_cost_exponent=1`. They do not measure the subsequent production change to 0.1.', '',
        'Six independent production trajectories use fresh paired seeds 15/16/17 on the same 100-node map. '
        'Each physical round has one batch of 40 ants and ten routing attempts per ant. '
        'Pheromone is live, so later ants see earlier deposits. There are no inner iterations. '
        'Only `elite_weight` changes; `load_weight=0`, chaos [.05,.30], Q=.01, evaporation [.1,.6], '
        'and pheromone bounds [.01,20] are fixed. The horizon is 3000 rounds.', '',
        '| Seed | Weight 1 FND | Weight 0.1 FND | Paired FND change | Weight 1 service rounds | Weight 0.1 service rounds | Paired service change |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    fnd_deltas, service_deltas = [],[]
    for s in SEEDS:
        a,b = (rows[s,n] for n in NAMES)
        delta = b['FND']-a['FND'] if a['FND'] is not None and b['FND'] is not None else None
        if delta is not None:
            fnd_deltas.append(delta)
        service_delta = b['completed_rounds']-a['completed_rounds']
        service_deltas.append(service_delta)
        lines.append(f"| {s} | {a['FND'] or 'censored'} | {b['FND'] or 'censored'} | {delta if delta is not None else 'censored'} | {a['completed_rounds']} | {b['completed_rounds']} | {service_delta:+d} |")
    summary = dict(provenance=provenance, paired_FND_changes=fnd_deltas,
        paired_service_changes=service_deltas)
    if len(fnd_deltas) == len(SEEDS):
        a,b = (st.mean(rows[s,n]['FND'] for s in SEEDS) for n in NAMES)
        summary['mean_FND'] = dict(weight1=a, weight01=b, change_percent=100*(b/a-1))
        lines += ['', f'Mean first-node death: {a:.3f} → {b:.3f} rounds ({100*(b/a-1):+.3f}%).']
    a,b = (st.mean(rows[s,n]['completed_rounds'] for s in SEEDS) for n in NAMES)
    summary['mean_service'] = dict(weight1=a,weight01=b,change_percent=100*(b/a-1))
    lines += ['', f'Mean completed service: {a:.3f} → {b:.3f} rounds ({100*(b/a-1):+.3f}%).', '',
        'For these completed runs, reducing the best-set weight provides no demonstrated lifetime gain: '
        'FND changes are mixed, and service ends two rounds earlier in every pair. '
        'Weight 0.1 remains the deliberate reinforcement-balance setting from the earlier study; '
        'it should not be described as an energy or lifetime improvement. '
        'One batch of 40 ants remains the production round structure.', '',
        'FND uses one-based completed-round counting. Service ends when the production search cannot find a tree '
        'that serves all surviving nodes, when all nodes die, or at the horizon. It is not equivalent to last-node death. '
        'HND/LND are censored if service stops before those events.', '',
        '## Energy at equal exposure', '',
        '| Completed rounds | Weight 1 mean energy (J) | Weight 0.1 mean energy (J) | Change |',
        '| --- | ---: | ---: | ---: |']
    summary['equal_exposure_energy'] = {}
    for k in (150,600,1400):
        if not all(r['completed_rounds'] >= k for r in rows.values()):
            continue
        a,b = (st.mean(sum(x['energy_J'] for x in rows[s,n]['records'][:k]) for s in SEEDS) for n in NAMES)
        summary['equal_exposure_energy'][str(k)] = dict(weight1=a,weight01=b,change_percent=100*(b/a-1))
        lines.append(f'| {k} | {a:.9f} | {b:.9f} | {100*(b/a-1):+.3f}% |')
    lines += ['', 'Energy after survivor counts diverge includes different physical states and cannot isolate efficiency. '
        'Whole-run cumulative energy is not used to rank efficiency because service durations differ.', '',
        '## Death events and terminal topology', '',
        '| Weight / seed | Deaths (completed round: node IDs) | Termination | Survivors | Disconnected survivor IDs | HND | LND |',
        '| --- | --- | --- | ---: | --- | --- | --- |']
    for s in SEEDS:
        for n in NAMES:
            r = rows[s,n]
            deaths = '; '.join(f"{e['completed_round']}: {e['dead']}" for e in r['death_events']) or 'none'
            disconnected = r.get('terminal_connectivity',{}).get('disconnected',[])
            lines.append(f"| {r['parameters']['elite_weight']} / {s} | {deaths} | {r['termination_reason']} | {r['alive_at_end']} | {disconnected} | {r['HND'] or 'censored'} | {r['LND'] or 'censored'} |")
    lines += ['', 'A nonempty disconnected list proves that a full-survivor route is impossible in the communication graph. '
        'An empty list at failure instead indicates that finite ant sampling/greedy routing could not find a feasible route.', '',
        '## Critical-node residuals after round 1400', '',
        '| Seed | Weight 1 node 33 (J) | Weight 0.1 node 33 (J) | Weight 1 node 65 (J) | Weight 0.1 node 65 (J) |',
        '| --- | ---: | ---: | ---: | ---: |']
    for s in SEEDS:
        paths = [FOLDER/f'{n}_seed{s}_round1400.json' for n in NAMES]
        if all(p.exists() for p in paths):
            a,b = (json.loads(p.read_text()) for p in paths)
            lines.append(f"| {s} | {a['residual'][33]:.6f} | {b['residual'][33]:.6f} | {a['residual'][65]:.6f} | {b['residual'][65]:.6f} |")
    lines += ['', 'Node 48 has only nodes 33 and 65 as communication-range neighbors on this map. '
        'Their deaths can isolate it even while most other sensors still have energy.', '',
        '## Late search and pheromone bounds', '',
        '| Seed | Weight | Common late rounds | Mean feasible candidates | Mean routing attempts | Maximum floor occupancy | Maximum ceiling occupancy |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for s in SEEDS:
        end = min(rows[s,n]['completed_rounds'] for n in NAMES)
        for n in NAMES:
            r = rows[s,n]
            late = r['records'][1500:end]
            feasible = f"{st.mean(x['feasible_evaluations'] for x in late):.3f}" if late else 'unobserved'
            attempts = f"{st.mean(x['routing_attempts'] for x in late):.3f}" if late else 'unobserved'
            floor = max(x['tau_floor_fraction'] for x in r['records'])
            ceiling = max(x['tau_ceiling_fraction'] for x in r['records'])
            lines.append(f"| {s} | {r['parameters']['elite_weight']} | {max(0,end-1500)} | {feasible} | {attempts} | {floor:.3%} | {ceiling:.3%} |")
    lines += ['', 'Late averages use equal round exposure within each seed pair, beginning at round 1501. '
        'Physical states evolve separately and may have different survivor counts briefly around their respective first deaths.', '',
        '## Validation and limitations', '',
        'Elite weight changes reinforcement on the ordered CH path, not relay edges or a residual-aware lifetime objective. '
        'Selection still minimizes total round energy. A smaller best-set bonus balances ant versus elite reinforcement, '
        'but it does not explicitly protect the critical relays that determine service termination.', '',
        f"Every selected tree was independently reevaluated and served every live node. Across all runs, {sum(x['feasible_evaluations'] for r in rows.values() for x in r['records']):,} feasible candidates were evaluated. "
        'Search leaves physical residual energy unchanged, energy is deducted once per completed round, '
        'and all pheromone entries are checked for finite values and calibrated bounds. '
        'Raw per-round costs, death events, routing attempts, snapshots and terminal connectivity are saved. '
        'Source/map/helper/runner hashes and explicit parameter values are stored per run; the runner rejects source changes during execution.', '',
        'These seeds are fresh relative to the early balance study, but this remains one map and three paired seeds. '
        'No statistical significance or universal optimum is established. '
        'Search CPU excludes the failed terminal search and comes from concurrent runs; it is not a dedicated timing benchmark.', '',
        'Reproduce each trajectory with `python -B plans/phase5-acaco-balance/full_lifetime.py SEED elite_1` '
        'or `elite_01`, for seeds 15/16/17. Existing completed runs are reused only with matching provenance. '
        'Then run `full_report.py`.']
    (FOLDER/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (FOLDER/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='provenance'},indent=2))


if __name__ == '__main__':
    main()
