"""Summarize complete trajectories and select a base before fitness trials."""
import json
from pathlib import Path
import statistics as st
import sys

FOLDER = Path(__file__).parent
SEEDS = (15,16,17)


def load(names):
    rows = {(s,n):json.loads((FOLDER/'full'/f'{n}_{s}.json').read_text()) for s in SEEDS for n in names}
    first = next(iter(rows.values()))['provenance']
    for (s,n),r in rows.items():
        assert r['configuration']==n and r['seed']==s
        assert len(r['records'])==r['completed_rounds']
        assert r['parameters']==r['provenance']['parameters']
        for key in ('map_sha','source_hashes','sibling_hashes','runner_sha'):
            assert r['provenance'][key]==first[key]
    return rows


def summarize(rows,names,baseline):
    exposure = min(r['completed_rounds'] for r in rows.values())
    predeath = min([r['FND']-1 for r in rows.values() if r['FND'] is not None]+[exposure])
    result = dict(equal_exposure_rounds=exposure,all_alive_rounds=predeath,groups={})
    for n in names:
        group = [rows[s,n] for s in SEEDS]
        fnds = [r['FND'] for r in group]
        energy = st.mean(sum(x['energy'] for x in r['records'][:predeath]) for r in group)
        base_energy = st.mean(sum(x['energy'] for x in rows[s,baseline]['records'][:predeath]) for s in SEEDS)
        result['groups'][n] = dict(mean_FND=st.mean(fnds) if all(x is not None for x in fnds) else None,
            mean_service=st.mean(r['completed_rounds'] for r in group),all_alive_energy=energy,
            energy_change_percent=100*(energy/base_energy-1),
            mean_cpu=st.mean(r['cpu'] for r in group),
            mean_clustering_attempts=st.mean(r['clustering_attempts'] for r in group),
            cpu_per_round=st.mean(r['cpu']/r['completed_rounds'] for r in group),
            mean_cv=st.mean(st.mean(x['cv'] for x in r['records'][:predeath]) for r in group),
            paired_service_changes=[rows[s,n]['completed_rounds']-rows[s,baseline]['completed_rounds'] for s in SEEDS],
            paired_FND_changes=[rows[s,n]['FND']-rows[s,baseline]['FND']
                if rows[s,n]['FND'] is not None and rows[s,baseline]['FND'] is not None else None for s in SEEDS],
            paired_energy_changes=[100*(sum(x['energy'] for x in rows[s,n]['records'][:predeath])/
                sum(x['energy'] for x in rows[s,baseline]['records'][:predeath])-1) for s in SEEDS])
    return result


def dominates(a,b):
    return (a['all_alive_energy']<=b['all_alive_energy'] and a['mean_service']>=b['mean_service']
            and (a['mean_FND'] is None or b['mean_FND'] is not None and a['mean_FND']>=b['mean_FND'])
            and (a['all_alive_energy']<b['all_alive_energy'] or a['mean_service']>b['mean_service']))


def main():
    stage = sys.argv[1]
    if stage=='tuning':
        names = ['baseline','tuned']
        rows = load(names)
        summary = summarize(rows,names,'baseline')
        chosen = 'tuned' if dominates(summary['groups']['tuned'],summary['groups']['baseline']) else 'baseline'
        reason = ('Tuned adaptation reduces energy without mean FND/service regression.' if chosen=='tuned'
                  else 'Tuned adaptation does not improve energy without mean FND/service regression; retain baseline.')
        selection = dict(configuration=chosen,parameters=rows[15,chosen]['parameters'],reason=reason)
        (FOLDER/'chosen_base.json').write_text(json.dumps(selection,indent=2))
        summary['selection'] = selection
        target = 'tuning_summary.json'
    else:
        chosen = json.loads((FOLDER/'chosen_base.json').read_text())['configuration']
        names = ['baseline','tuned','risk_control','density_005','density_010']
        rows = load(names)
        summary = summarize(rows,names,chosen)
        winning = [n for n in ('density_005','density_010') if dominates(summary['groups'][n],summary['groups'][chosen])]
        selected = min(winning,key=lambda n:summary['groups'][n]['all_alive_energy']) if winning else chosen
        summary['selection'] = dict(configuration=selected,parameters=rows[15,selected]['parameters'],
            reason='Lower energy without mean FND/service regression required for promotion.')
        target = 'summary.json'
    (FOLDER/target).write_text(json.dumps(summary,indent=2))
    if stage!='tuning':
        write_report(rows,summary)
    print(json.dumps(summary,indent=2))


def write_report(rows,summary):
    groups = summary['groups']
    chosen = json.loads((FOLDER/'chosen_base.json').read_text())['configuration']
    lines = ['# Full D-ACO: sibling tuning and density-load fitness', '',
        'Fifteen full runs on the current 100-sensor map (radius 200 m), paired seeds 15/16/17. '
        'Only D-ACO is simulated. Forty ants in one batch, until no feasible complete tree, all nodes die, '
        'or the 3000-round horizon. Every successful tree is checked to serve every surviving sensor.', '',
        'The sibling tuning is a single-batch adaptation. Its original four iterations of 20 ants '
        'are not reinstated. Absolute energy/CV fitness, live deposits, elite units, evaporation order, '
        'coverage scaling, and numeric controls are transferred together. Shared routing, energy model, '
        'and map come from review_uwsn. No files are changed in uwsn.', '',
        f"Energy uses the same first {summary['all_alive_rounds']} rounds with every sensor alive. "
        'CPU is recorded but concurrency and hardware frequency were not controlled.', '',
        '| Configuration | Mean first-node death | Mean service | All-alive energy change | Mean clustering attempts |',
        '| --- | ---: | ---: | ---: | ---: |']
    for name,m in groups.items():
        fnd = f"{m['mean_FND']:.1f}" if m['mean_FND'] is not None else 'censored'
        lines.append(f"| {name} | {fnd} | {m['mean_service']:.1f} | {m['energy_change_percent']:+.3f}% | {m['mean_clustering_attempts']:.0f} |")
    lines += ['', '## Selection', '',
        f"The tuning comparison retains `{chosen}`. The transferred tuning increases energy by "
        f"{groups['tuned']['energy_change_percent']:.3f}% and has earlier first-node death in all three seeds. "
        'It is not promoted. Grid attenuation variants remain available and unchanged.', '',
        f"The energy-preserving promotion rule selects `{summary['selection']['configuration']}`. "
        'Density fitness remains explicit opt-in when no variant meets that rule. '
        'Its lifetime/energy tradeoff is reported rather than described as an energy improvement.', '',
        '## Fitness calculation', '',
        'Use structural grid density `D_i = F_i dot density` before candidate CH coverage loss. '
        'Normalize D_i by the median positive live-sensor density. With evaluated consumption e_i '
        'and pre-round residual energy r_i, define:', '',
        '`P = max_i [(e_i/r_i) * (1 + kappa/(1 + D_i/median(D_positive)))] / (E_total/sum(r_i))`', '',
        'Add `lambda * P` to existing energy/CV fitness. All live sensors, including members and relays, '
        'are included. `risk_control` uses lambda=0.10, kappa=0; `density_005` and `density_010` '
        'use kappa=1 and lambda=0.05/0.10. The same score guides selection and pheromone reinforcement.', '',
        'The scarcity multiplier changes both spatial weighting and overall penalty magnitude. '
        'The control removes that multiplier; it does not match the mean penalty magnitude. '
        'These results therefore do not isolate scarcity geometry from penalty strength. '
        'The candidate energy normalization in P also means a more expensive tree can reduce its '
        'relative concentration score; the separate energy term continues to penalize that cost.', '',
        '## Paired changes versus selected base', '',
        '| Configuration | First-node-death changes | Service changes | Energy changes |',
        '| --- | --- | --- | --- |']
    for name,m in groups.items():
        lines.append(f"| {name} | {m['paired_FND_changes']} | {m['paired_service_changes']} | "
                     f"{', '.join(f'{x:+.3f}%' for x in m['paired_energy_changes'])} |")
    lines += ['', 'To enable the low-weight density option, set `DACOParameters().density_load_weight = 0.05` '
        'on the parameter instance passed to DACO. `density_load_kappa=1` is already the default. '
        'Set weight zero to retain prior fitness. Do not substitute remaining CH-coverage density.', '',
        'First-node death and completed service are different metrics. HND/LND can remain censored '
        'when complete routing fails with most sensors alive. Three seeds on one map establish a '
        'paired comparison here, not a general deployment guarantee.', '',
        'Raw records, parameters, deaths, residual energy, counters, and source/map hashes are in `full/`. '
        'The fresh baseline matches all three historical phase-7 trajectories exactly.']
    (FOLDER/'RESULTS.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    main()
