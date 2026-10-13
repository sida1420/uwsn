"""Completed full-run comparisons with exact source/map matched controls."""
import json
from pathlib import Path
from statistics import mean

FOLDER=Path(__file__).parent
SEEDS=(24,25,26)
NAMES=('baseline','deposit_2x','deposit_4x','heuristic_half','heuristic_quarter')
rows={name:[json.loads((FOLDER/'full'/f'{name}_{seed}.json').read_text()) for seed in SEEDS]
      for name in NAMES}
rows['pheromone']=[json.loads((FOLDER.parent/'phase10-daco-vs-pheromone/full'/f'pheromone_{seed}.json').read_text()) for seed in SEEDS]
all_rows=sum(rows.values(),[])
epoch={key:all_rows[0]['provenance'][key] for key in ('map_sha','sources')}
assert all(all(r['provenance'][key]==value for key,value in epoch.items()) for r in all_rows)
for name in NAMES:
    for seed,r in zip(SEEDS,rows[name]):
        baseline=json.loads((FOLDER.parent/'phase10-daco-vs-pheromone/full'/f'daco_{seed}.json').read_text())
        changed={key for key,value in r['parameters'].items() if value!=baseline['parameters'][key]}
        assert changed==({'Q'} if name.startswith('deposit') else {'beta','gamma'} if name.startswith('heuristic') else set())
        if name=='baseline':
            assert r['residual']==baseline['residual']
            assert all(all(after[key]==value for key,value in before.items())
                       for before,after in zip(baseline['records'],r['records']))
assert all(r['termination_reason']!='horizon' for r in all_rows), 'Handle horizon censoring explicitly'
assert all(r['FND'] is not None for r in all_rows), 'Handle FND censoring explicitly'
window=min(r['FND']-1 for r in all_rows)
service_window=min(r['completed_rounds'] for r in all_rows)

def summarize(items):
    result=dict(FND=mean(r['FND'] for r in items),
        service=mean(r['completed_rounds'] for r in items),
        energy=mean(sum(x['energy'] for x in r['records'][:window]) for r in items),
        energy_equal_service=mean(sum(x['energy'] for x in r['records'][:service_window]) for r in items),
        cpu_per_round=mean(r['cpu']/r['completed_rounds'] for r in items),
        attempts_per_round=mean((r['clustering_attempts']+r['calibration_attempts'])/r['completed_rounds'] for r in items))
    if 'deposits' in items[0]:
        selected=[x for r in items for x in r['records'][:window]]
        deposit={key:sum(x['deposit'][key] for x in selected) for key in ('updates','clipped','requested','lost')}
        result['diagnostics']=dict(end_round_cap_fraction=mean(x['tau_cap_fraction'] for x in selected),
            clipped_update_fraction=deposit['clipped']/deposit['updates'],
            lost_deposit_fraction=deposit['lost']/deposit['requested'],
            mean_tau_spread=mean(x['tau_spread'] for x in selected),
            score_spreads={key:mean(x['score_spreads'][key] for x in selected)
                           for key in ('pheromone','energy','density')})
    return result

summary={name:summarize(items) for name,items in rows.items()}
for name,s in summary.items():
    s['percent_vs_baseline']={key:100*(s[key]/summary['baseline'][key]-1)
         for key in ('FND','service','energy','cpu_per_round')}
    s['percent_vs_simple']={key:100*(s[key]/summary['pheromone'][key]-1)
         for key in ('FND','service','energy')}
(FOLDER/'summary.json').write_text(json.dumps(dict(all_alive_window=window,
    equal_service_window=service_window,summary=summary),indent=2))

lines=['# Stronger D-ACO pheromone versus lighter heuristics', '',
    'Twelve new full variant runs, three instrumented baseline replays, and three '
    'previously completed pheromone-only SimpleACO controls. Paired seeds: 24, 25, 26. '
    'Every source/map hash matches the phase-10 epoch. Each baseline replay reproduces '
    'the complete previous trajectory and final residual energies exactly.', '',
    'Current D-ACO fitness, load power 2, load/density weight 0.25, reference memory 0.8, '
    '40 calibration ants, evaporation, pheromone bounds [1,8], and all other controls '
    'remain fixed. Both heuristic exponents are scaled together. Q variants retain '
    'beta=0.9, gamma=0.4; heuristic variants retain Q=5. Fitness reference values '
    'continue to adapt normally to the sampled candidates. No production defaults changed.', '',
    'Each round uses one batch of 40 ants, max 10 feasibility attempts per ant, 20% '
    'cluster heads, and the existing shared routing/physical energy model. The full '
    'horizon is 3000 rounds; runs stop normally if no complete tree is found.', '',
    f'Energy uses the same first **{window} rounds**, before any node dies in any trial. '
    'Lifetime numbers are completed service, distinct from all sensors dying.', '',
    '| Variant | Q | beta / gamma | Mean first death | Mean service | Energy (J) | Energy vs baseline | Service vs baseline |',
    '|---|---:|---|---:|---:|---:|---:|---:|']
labels=dict(baseline='Current D-ACO',deposit_2x='Deposits ×2',deposit_4x='Deposits ×4',
    heuristic_half='Heuristics ×0.5',heuristic_quarter='Heuristics ×0.25',pheromone='SimpleACO, pheromone only')
for name,s in summary.items():
    p=rows[name][0]['parameters']
    delta=s['percent_vs_baseline']
    lines.append(f"| {labels[name]} | {p['Q']:g} | {p['beta']:g} / {p['gamma']:g} | {s['FND']:.2f} | {s['service']:.2f} | {s['energy']:.4f} | {delta['energy']:+.2f}% | {delta['service']:+.2f}% |")
lines += ['', '## Paired full results', '', '| Variant | Seed | First death | Service | Terminal alive nodes | Stop |',
          '|---|---:|---:|---:|---:|---|']
for name,items in rows.items():
    for r in items:
        lines.append(f"| {labels[name]} | {r['seed']} | {r['FND']} | {r['completed_rounds']} | {len(r['alive'])} | {r['termination_reason']} |")
lines += ['', '## Pheromone saturation and search cost', '',
    f'Diagnostics below use the same first {window} all-alive rounds. Cap fraction is '
    'the fraction of live nodes at tau_max after the elite deposit. Clipped updates '
    'count individual node deposits that exceeded the bound; lost mass is the fraction '
    'of requested deposit removed by clipping. These describe actual updates, not '
    'just the nominal Q multiplier.', '',
    '| D-ACO variant | Mean nodes at cap | Clipped updates | Lost deposit mass | Mean tau range | CPU s / round | Attempts / round |',
    '|---|---:|---:|---:|---:|---:|---:|']
for name in NAMES:
    s=summary[name];d=s['diagnostics']
    lines.append(f"| {labels[name]} | {100*d['end_round_cap_fraction']:.2f}% | {100*d['clipped_update_fraction']:.2f}% | {100*d['lost_deposit_fraction']:.2f}% | {d['mean_tau_spread']:.3f} | {s['cpu_per_round']:.4f} | {s['attempts_per_round']:.3f} |")
lines += ['', 'Raw trajectories also record within-round log-score component ranges. '
    'Those ranges pool different selection steps and should not be interpreted as '
    'an exact probability concentration or a causal dominance measure.', '',
    'CPU includes constructor/calibration and diagnostic overhead. Concurrent processes '
    'make timing indicative; baseline and D-ACO variants share instrumentation, whereas '
    'the reused SimpleACO timings do not. The deposit/control wave had up to nine '
    'concurrent tasks; the heuristic wave mostly had six. CPU-time differences between '
    'these waves cannot be attributed to the parameter changes. Attempt counts are a more robust search-budget '
    'measure. Three seeds on one map do not establish general deployment performance.', '',
    'Checks: every selected tree covered exactly the live nodes; all physical costs '
    'were finite, nonnegative, and positive in total; source/map hashes remained '
    'unchanged through each run; each variant changes only its declared controls; '
    'the three complete baseline replays match the previously saved outcomes.', '',
    'Reproduce: `python -B plans/phase11-daco-concentration/batch.py SEED GROUP` '
    '(seeds 24/25/26, groups a/b), '
    '`python -B plans/phase11-daco-concentration/replay_baseline.py SEED`, then '
    '`python -B plans/phase11-daco-concentration/report.py`.']
lines += ['', '## Interpretation', '',
    'Quartering the heuristic exponents (beta=0.225, gamma=0.1, Q=5) is the best '
    'tested D-ACO variant on mean first death, service, and equal-round energy. '
    'Against current D-ACO, it delays first death by 107.67 rounds (+4.02%), '
    'adds 190.67 service rounds (+6.94%), and reduces all-alive energy by 1.11%. '
    'Each paired seed improves these three outcomes against the baseline.', '',
    'Against pheromone-only SimpleACO, quarter weights give essentially the same '
    'service: 2938 versus 2936 mean rounds. The paired service differences are '
    '+13, -13, and +6 rounds, so this is not persuasive evidence of better service '
    'than SimpleACO. First death is later by 146.67 rounds (+5.56%), at 1.65% '
    'more all-alive energy.', '',
    'Stronger deposits also help service and energy, but less: Q=10 adds 1.58% '
    'service with 0.47% lower energy; Q=20 adds 3.02% service with 0.55% lower '
    'energy. With Q=20, an average 54.66% of live nodes are at the cap after '
    'a round, and 30.67% of requested deposit mass is clipped over the common '
    'all-alive interval. It still improves outcomes, so saturation does not '
    'make the larger Q ineffective; it limits how much extra deposit is retained.', '',
    'The tested results favor lighter heuristics over increasing Q alone. '
    'They support this parameter direction for this map, without establishing '
    'a universal optimum or proving a local-search mechanism. Production defaults '
    'remain unchanged: beta=0.9, gamma=0.4, Q=5.']
(FOLDER/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(window=window,summary=summary),indent=2))
