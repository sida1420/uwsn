"""Equal-exposure summaries for higher pheromone caps and deposits."""
import json
from pathlib import Path
from statistics import mean

FOLDER=Path(__file__).parent
SEEDS=(24,25,26)
NEW=('deposit_4x_cap32','deposit_6x_cap8','deposit_6x_cap32')
rows={name:[json.loads((FOLDER/'full'/f'{name}_{seed}.json').read_text()) for seed in SEEDS] for name in NEW}
for name in ('baseline','deposit_4x','heuristic_quarter'):
    rows[name]=[json.loads((FOLDER.parent/'phase11-daco-concentration/full'/f'{name}_{seed}.json').read_text()) for seed in SEEDS]
rows['pheromone']=[json.loads((FOLDER.parent/'phase10-daco-vs-pheromone/full'/f'pheromone_{seed}.json').read_text()) for seed in SEEDS]
ORDER=('baseline','deposit_4x','deposit_4x_cap32','deposit_6x_cap8','deposit_6x_cap32','heuristic_quarter','pheromone')
LABELS=dict(baseline='Current D-ACO',deposit_4x='Deposits ×4, cap 8',
    deposit_4x_cap32='Deposits ×4, cap 32',deposit_6x_cap8='Deposits ×6, cap 8',
    deposit_6x_cap32='Deposits ×6, cap 32',heuristic_quarter='Quarter heuristics, cap 8',
    pheromone='SimpleACO, pheromone only')
all_rows=sum(rows.values(),[])
epoch={key:all_rows[0]['provenance'][key] for key in ('map_sha','sources')}
assert all(all(r['provenance'][key]==value for key,value in epoch.items()) for r in all_rows)
base=rows['baseline'][0]['parameters']
for name in NEW:
    for r in rows[name]:
        changed={key for key,value in r['parameters'].items() if value!=base[key]}
        assert changed==({'Q'} if name=='deposit_6x_cap8' else {'Q','tau_max'})
window=min(r['FND']-1 if r['FND'] is not None else r['completed_rounds'] for r in all_rows)
service_window=min(r['completed_rounds'] for r in all_rows)

def summarize(items):
    result=dict(FND=mean(r['FND'] for r in items) if all(r['FND'] is not None for r in items) else None,
        completed_rounds=mean(r['completed_rounds'] for r in items),
        horizon_count=sum(r['termination_reason']=='horizon' for r in items),
        energy=mean(sum(x['energy'] for x in r['records'][:window]) for r in items),
        energy_equal_service=mean(sum(x['energy'] for x in r['records'][:service_window]) for r in items),
        cpu_per_round=mean(r['cpu']/r['completed_rounds'] for r in items),
        attempts_per_round=mean((r['clustering_attempts']+r['calibration_attempts'])/r['completed_rounds'] for r in items))
    if 'deposits' in items[0]:
        selected=[x for r in items for x in r['records'][:window]]
        total={key:sum(x['deposit'][key] for x in selected) for key in ('updates','clipped','requested','lost')}
        result['diagnostics']=dict(cap_fraction=mean(x['tau_cap_fraction'] for x in selected),
            clipped_updates=total['clipped']/total['updates'],lost_mass=total['lost']/total['requested'],
            mean_tau_range=mean(x['tau_spread'] for x in selected),
            mean_tau_max=mean(x['tau_max'] for x in selected))
    return result

summary={name:summarize(rows[name]) for name in ORDER}
for name,s in summary.items():
    s['percent_vs_baseline']={key:100*(s[key]/summary['baseline'][key]-1) for key in ('completed_rounds','energy')}
    s['percent_vs_simple']={key:100*(s[key]/summary['pheromone'][key]-1) for key in ('completed_rounds','energy')}
comparisons={}
for name,reference in (('deposit_4x_cap32','deposit_4x'),('deposit_6x_cap32','deposit_6x_cap8'),
                       ('deposit_6x_cap32','deposit_4x_cap32')):
    comparisons[f'{name}_vs_{reference}']={key:100*(summary[name][key]/summary[reference][key]-1)
        for key in ('completed_rounds','energy')}
output=dict(all_alive_window=window,equal_service_window=service_window,summary=summary,comparisons=comparisons)
(FOLDER/'summary.json').write_text(json.dumps(output,indent=2))
lines=['# Higher D-ACO pheromone bounds and deposits', '',
    'Nine fresh full trials: deposits ×4 (Q=20) with tau_max=32, deposits ×6 (Q=30) '
    'with tau_max=8, and deposits ×6 with tau_max=32. Three paired seeds per case '
    '(24,25,26), normal 3000-round horizon. Previously completed current D-ACO, '
    '×4/cap-8, quarter-heuristic, and pheromone-only SimpleACO controls are reused '
    'only after verifying exact source/map epoch matches.', '',
    'New variants retain beta=0.9, gamma=0.4, alpha=1, tau_min=tau0=1, the existing '
    'evaporation schedule, fitness formula and parameters, geometric normalization, '
    '40 calibration ants, and live per-ant pheromone. No production defaults changed. '
    'Each physical round has one batch of 40 ants and at most 10 feasibility attempts '
    'per ant, with identical routing and physics.', '',
    'The high cap is 32 versus the current 8. It is held fixed for ×4 and ×6 '
    'so that their difference isolates deposit strength; ×6/cap-8 provides a '
    'matching control for the ceiling change.', '',
    f'Energy below uses the same first **{window} all-alive rounds** across every '
    'case. Completed service stops when no complete route is found or the horizon '
    'is reached; this is distinct from all nodes dying. Horizon-censored results '
    'are flagged in the per-seed table and only give lower bounds on lifetime.', '',
    '| Variant | Q | Upper bound | beta / gamma | Mean first death | Mean completed service | Energy (J) | Energy vs baseline |',
    '|---|---:|---:|---|---:|---:|---:|---:|']
for name in ORDER:
    s=summary[name];p=rows[name][0]['parameters']
    fnd=f"{s['FND']:.2f}" if s['FND'] is not None else 'Unobserved in some trials'
    censor=' *' if s['horizon_count'] else ''
    lines.append(f"| {LABELS[name]} | {p['Q']:g} | {p['tau_max']:g} | {p['beta']:g} / {p['gamma']:g} | {fnd} | {s['completed_rounds']:.2f}{censor} | {s['energy']:.4f} | {s['percent_vs_baseline']['energy']:+.2f}% |")
lines += ['', '## Controlled comparisons', '',
    '| Comparison | Completed service difference | Equal-round energy difference |',
    '|---|---:|---:|']
for name,reference in (('deposit_4x_cap32','deposit_4x'),('deposit_6x_cap32','deposit_6x_cap8'),
                       ('deposit_6x_cap32','deposit_4x_cap32')):
    s=comparisons[f'{name}_vs_{reference}']
    lines.append(f"| {LABELS[name]} vs {LABELS[reference]} | {s['completed_rounds']:+.2f}% | {s['energy']:+.2f}% |")
lines += ['', '## Saturation', '',
    f'Measured over the common first {window} all-alive rounds. Cap fraction '
    'counts live nodes at the upper bound after the round. Clipped updates '
    'count individual node deposits; lost mass is the fraction of requested '
    'deposit discarded by the cap.', '',
    '| Variant | Mean nodes at cap | Clipped updates | Lost deposit mass | Mean maximum tau | Mean tau range |',
    '|---|---:|---:|---:|---:|---:|']
for name in ORDER[:-1]:
    d=summary[name]['diagnostics']
    lines.append(f"| {LABELS[name]} | {100*d['cap_fraction']:.2f}% | {100*d['clipped_updates']:.2f}% | {100*d['lost_mass']:.2f}% | {d['mean_tau_max']:.3f} | {d['mean_tau_range']:.3f} |")
lines += ['', '## Per-seed trajectories', '',
    '| Variant | Seed | First death | Completed service | Alive at stop | Termination |',
    '|---|---:|---:|---:|---:|---|']
for name in ORDER:
    for r in rows[name]:
        fnd=r['FND'] if r['FND'] is not None else 'Unobserved'
        lines.append(f"| {LABELS[name]} | {r['seed']} | {fnd} | {r['completed_rounds']} | {len(r['alive'])} | {r['termination_reason']} |")
lines += ['', 'All selected trees covered exactly the live nodes, every physical '
    'cost was finite/nonnegative with positive total energy, and source/map '
    'hashes remained unchanged through each run. Diagnostic instrumentation '
    'is identical to the phase-11 observer, whose three complete baseline '
    'replays reproduced the original results exactly. The new driver and '
    'underlying runner hashes are recorded in every result.', '',
    'Nine concurrent trial processes ran in this phase. Stored CPU measurements '
    'include diagnostic overhead and are not a controlled speed comparison '
    'against the earlier waves or uninstrumented SimpleACO. Three seeds on '
    'one map support conclusions for this tested deployment, not a universal optimum.', '',
    'Reproduce: `python -B plans/phase12-daco-higher-cap/full_run.py NAME SEED` '
    '(names deposit_4x_cap32, deposit_6x_cap8, deposit_6x_cap32; seeds 24/25/26), '
    'then `python -B plans/phase12-daco-higher-cap/report.py`.']
lines += ['', '## Interpretation', '',
    'Raising the ceiling from 8 to 32 worsens first death, service, and '
    'equal-round energy for every paired seed at both Q=20 and Q=30. At '
    'Q=20, the higher cap loses 128 service rounds (-4.52%) and uses '
    '0.81% more energy. At Q=30, it loses 115.33 service rounds (-4.05%) '
    'and uses 0.61% more energy.', '',
    'The higher ceiling removes most clipping: for Q=20, discarded '
    'deposit mass falls from 30.67% to 1.21%; for Q=30, it falls from '
    '47.93% to 4.14%. Therefore clipping was not simply preventing a '
    'beneficial stronger-deposit policy. Less clipping and a wider '
    'pheromone range do not imply better search in this configuration. '
    'These outcomes support keeping the tested cap at 8; they do not '
    'identify the detailed failure mechanism.', '',
    'Q=30/cap-8 improves mean service by 18.67 rounds (+0.66%) over '
    'Q=20/cap-8, while energy is effectively unchanged (-0.012%). '
    'The paired service differences are -1, +46, and +11 rounds, so '
    'this small mean gain is not a consistent improvement in every seed. '
    'Relative to current D-ACO, Q=30/cap-8 adds 3.70% service and uses '
    '0.56% less all-alive energy.', '',
    'Quarter heuristics remain the best tested D-ACO variant on the '
    'three mean outcomes: first death 2782.67, service 2938, and energy '
    '43.1655 J. In comparison, Q=30/cap-8 gives 2761, 2849, and '
    '43.4038 J. Production defaults remain unchanged; the cap-32 '
    'variants are not adopted.']
(FOLDER/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(output,indent=2))
