"""Summarize six completed fresh trajectories without mixing map epochs."""
import json
from pathlib import Path
from statistics import mean

FOLDER = Path(__file__).parent
SEEDS = (24, 25, 26)
rows = {name:[json.loads((FOLDER/'full'/f'{name}_{seed}.json').read_text())
               for seed in SEEDS] for name in ('daco', 'pheromone')}
all_rows = sum(rows.values(), [])
assert all(r['provenance'] == all_rows[0]['provenance'] for r in all_rows)
window = min(r['FND']-1 if r['FND'] is not None else r['completed_rounds'] for r in all_rows)
service_window = min(r['completed_rounds'] for r in all_rows)

def summary(items):
    return dict(FND=mean(r['FND'] for r in items) if all(r['FND'] is not None for r in items) else None,
        service_rounds=mean(r['completed_rounds'] for r in items),
        energy_all_alive=mean(sum(x['energy'] for x in r['records'][:window]) for r in items),
        energy_equal_service=mean(sum(x['energy'] for x in r['records'][:service_window]) for r in items),
        cpu=mean(r['cpu'] for r in items),
        cpu_per_round=mean(r['cpu']/r['completed_rounds'] for r in items),
        attempts_per_round=mean((r['clustering_attempts']+r['calibration_attempts'])/r['completed_rounds'] for r in items),
        routing_per_round=mean((r['routing_attempts']+r['calibration_routing_attempts'])/r['completed_rounds'] for r in items))

summaries = {name:summary(items) for name,items in rows.items()}
d, a = summaries['daco'], summaries['pheromone']
differences = {key:100*(d[key]/a[key]-1) if d[key] is not None and a[key] is not None else None for key in d}
output = dict(all_alive_window=window, equal_service_window=service_window,
              summaries=summaries, daco_percent_vs_pheromone=differences)
(FOLDER/'summary.json').write_text(json.dumps(output, indent=2))
lines = ['# Current D-ACO versus pheromone-only SimpleACO', '',
    'Six fresh full trajectories on the current map; paired seeds 24, 25, 26. '
    'Both use 40 ants, at most 10 feasibility attempts per ant, one batch per round, '
    '20% cluster heads, and the same multi-hop routing and physical energy evaluator.', '',
    'Map: 100 sensors, 500 × 500 × 500 m, radius 200 m, initial energy 0.6 J/node, '
    'sink (250, 250, 0). Map SHA-256: `'+all_rows[0]['provenance']['map_sha']+'`.', '',
    'D-ACO uses the current defaults: quadratic relative depletion divided by structural '
    'grid density, weight 0.25, geometric reference memory 0.8, live node pheromone, '
    'and 40 initial throwaway calibration ants. SimpleACO explicitly uses beta=gamma=0: '
    'its cluster-head sampling weights are pheromone^alpha. Its candidate selection '
    'and pheromone reinforcement still use evaluated physical energy. Routing also '
    'retains its ordinary distance and residual-energy inputs.', '',
    'All other algorithm parameters retain their own current defaults. This compares '
    'the two implementations; it does not isolate a single heuristic or fitness change.', '',
    '| Metric (mean of 3 seeds) | D-ACO | SimpleACO, pheromone only | D-ACO difference |',
    '|---|---:|---:|---:|']
labels = dict(FND='First node death (round)',service_rounds='Completed service rounds',
    energy_all_alive=f'Energy, first {window} rounds (J; all nodes alive)',
    energy_equal_service=f'Energy, first {service_window} rounds (J; includes deaths)',
    cpu='Process CPU time (s)', cpu_per_round='Process CPU seconds / completed round', attempts_per_round='Clustering attempts / completed round',
    routing_per_round='Routing attempts / completed round')
for key,label in labels.items():
    left = f'{d[key]:.3f}' if d[key] is not None else 'Censored; see per-seed results'
    right = f'{a[key]:.3f}' if a[key] is not None else 'Censored; see per-seed results'
    delta = f'{differences[key]:+.2f}%' if differences[key] is not None else 'Not estimable'
    lines.append(f'| {label} | {left} | {right} | {delta} |')
lines += ['', '| Seed | D-ACO FND | SimpleACO FND | D-ACO service | SimpleACO service |',
          '|---|---:|---:|---:|---:|']
for x,y in zip(rows['daco'],rows['pheromone']):
    xf = x['FND'] if x['FND'] is not None else f">{x['completed_rounds']} (censored)"
    yf = y['FND'] if y['FND'] is not None else f">{y['completed_rounds']} (censored)"
    xs = str(x['completed_rounds']) + (' (horizon)' if x['termination_reason']=='horizon' else '')
    ys = str(y['completed_rounds']) + (' (horizon)' if y['termination_reason']=='horizon' else '')
    lines.append(f"| {x['seed']} | {xf} | {yf} | {xs} | {ys} |")
lines += ['', 'The configured horizon is 3000 rounds. Horizon runs give only a lower bound '
    'on service lifetime. A stop for no feasible complete routing tree is distinct from '
    'every sensor dying. FND/HND/LND remain censored when absent in raw trajectories.', '',
    'Runtime includes constructor work and calibration. Three seed processes ran concurrently, '
    'so CPU measurements are indicative; attempt counts are the more robust search-cost comparison. '
    'Seeds share starting randomness, but different algorithms consume the RNG differently. '
    'Three seeds on one map do not establish performance across deployments.', '',
    'Checks: every selected tree covered exactly the live nodes, all costs were finite and '
    'nonnegative with positive total energy, and source/map hashes stayed unchanged through '
    'each run. Raw results contain parameters, trajectories, death rounds, attempts, residual '
    'energy, and provenance. Production settings were not changed.', '',
    'Run: `python -B plans/phase10-daco-vs-pheromone/full_run.py SEED` (24, 25, or 26), '
    'then `python -B plans/phase10-daco-vs-pheromone/report.py`.']
lines += ['', '## Interpretation', '',
    'On this map, pheromone-only SimpleACO has lower energy cost and longer service in '
    'all three paired seeds. D-ACO postpones first death in all three seeds, but the '
    'mean improvement is only 39 rounds (+1.48%), while service is 188.67 rounds '
    'shorter (-6.43%) and all-alive energy is 2.78% higher. D-ACO uses fewer feasibility '
    'attempts per round, yet more CPU per round (+13.18%); its additional fitness and '
    'grid computations do not pay off in these outcomes. This is a comparison of '
    'the current complete policies, so it does not identify which individual '
    'D-ACO component causes the difference. No default was changed.']
(FOLDER/'RESULTS.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(json.dumps(output, indent=2))
