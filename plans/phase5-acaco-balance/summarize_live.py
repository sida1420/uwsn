"""Summarize independently restored screens and fresh live trajectories."""
import json
from pathlib import Path
from summarize_balance import aggregate

FOLDER = Path(__file__).parent


def main():
    meta = json.loads((FOLDER/'results/metadata_live_screen_0.json').read_text())
    names = meta['live_validation']
    groups, raw = {}, {}
    for mode, context, seeds in [('live_screen',600,(0,1,2)),
            ('live_screen',1510,(0,1,2)),('live_validation',None,(12,13,14))]:
        for name in names:
            rows = [json.loads((FOLDER/'results'/f'{mode}_{context}_{name}_seed{s}.json').read_text()) for s in seeds]
            assert all(r['completed'] == (12 if mode == 'live_screen' else 150) for r in rows)
            raw[mode,context,name] = rows
            groups[mode,context,name] = aggregate(rows)
    lines = ['# Live AC-ACO: elite balance, load fitness and inner iterations', '',
        'Historical scope: these measurements use `energy_cost_exponent=1`. Production now defaults to 0.1; the results below do not measure that change.', '',
        'The production sampler now reads live pheromone rows: each later ant sees deposits from earlier feasible ants. '
        'The frozen per-round pheromone snapshot was removed. Residual-energy state still stays fixed during search because only the selected tree consumes physical energy.', '',
        'Separate `elite_weight` and `load_weight` parameters implement the two D-ACO-inspired interventions. '
        'The following tests isolate each intervention and also test their combination. '
        'The resulting production defaults are elite weight 0.1, load weight 0, and one batch of 40 ants. '
        'The study controls explicitly retain elite weight 1; `live_elite_01` tests elite weight 0.1 with the historical energy-cost exponent.', '',
        '## Decision', '',
        'Reduce the best-set multiplier to 0.1 to balance reinforcement, matching D-ACO. '
        'Its measured elite share falls from 73.59% to 21.81% in fresh validation. '
        'Mean early energy rises 0.180%, while matched checkpoint energy falls 0.404% at round 600 and 0.279% at round 1510. '
        'This is a deliberate reinforcement-balance choice, not a demonstrated lifetime optimization.', '',
        'Keep load fitness opt-in: `ACACOParameters(load_weight=0.1)` combines it with the new elite default. '
        'Tested alone against theta=1, it reduces load CV by 2.234% and mean peak relative depletion by 4.916%, '
        'with a 0.348% energy cost in fresh validation. Both combined give a 0.358% energy cost, '
        '1.877% lower CV and 3.568% lower mean peak relative depletion. '
        'The critical-node residuals and per-seed outcomes are mixed; these measurements do not establish longer service.', '',
        'Keep one batch of 40 ants. Two batches of 20 use 0.157% more energy than one batch of 40 in fresh validation. '
        'Two batches of 40 versus one batch of 80 differ by only -0.003% energy. '
        'Increasing to 80 ants saves about 1.33% energy but uses roughly twice the CPU. '
        'There is no compelling energy benefit from extra inner iterations at equal ant budget.', '',
        '## D-ACO comparison and design', '',
        'The D-ACO implementation in this checkout runs one ant batch per simulator round. '
        'It uses elite multiplier theta=.1 and candidate fitness `.9*E/mean(E)+.1*CV/mean(CV)`. '
        'CV is the standard deviation of absolute per-node round costs divided by their mean. '
        'AC-ACO uses ordered-CH transition pheromone rather than D-ACO node pheromone. '
        'This study retains AC-ACO deposits `Q/physical_energy`; copying D-ACO\'s `Q/fitness` would alter the calibrated deposit scale.', '',
        'Each checkpoint screen uses three seeds and 12 optimizer searches at a fixed physical state: '
        'after round 600 and immediately after node 33 dies at round 1510 in the earlier frozen trajectory. '
        'The late state is replayed from its saved checkpoint and checked against archived costs. '
        'Every configuration starts from an independent deep copy of physical and optimizer state. '
        'The original screens had shared-state aliasing, were excluded, and remain in `invalid-screen-state-alias/` for audit.', '',
        'Fresh validation uses seeds 12/13/14 and 150 physical rounds per configuration. '
        'All eight configurations share the calibrated bounds and current chaos amplitudes. '
        'The schedule horizon remains 3000. This is an early-trajectory comparison, not a lifetime/FND validation. '
        'The earlier frozen study has three separate 300-round trajectories per configuration in [FROZEN_REFERENCE.md](FROZEN_REFERENCE.md).', '',
        '| Configuration | Elite weight | Load weight | Batches x ants |',
        '| --- | ---: | ---: | --- |']
    for name in names:
        cfg = meta['configs'][name]
        lines.append(f"| {name} | {cfg['theta']} | {cfg['load_weight']} | {cfg['batches']} x {cfg['ants']} |")
    lines += ['', '`baseline` alone retains the old frozen sampler as a control. All `live_` configurations use live pheromone. '
        'Percentages below use `live_baseline` as the reference unless stated otherwise.', '']
    for mode, context, label, rounds in [('live_screen',600,'Checkpoint 600',12),
            ('live_screen',1510,'Checkpoint 1510',12),('live_validation',None,'Fresh 150-round trajectories',150)]:
        lines += [f'## {label}', '',
            '| Configuration | Mean total energy (J) | Energy change | CPU ratio | Load CV change | Mean peak relative depletion change | Elite share of new mass |',
            '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        base = groups[mode,context,'live_baseline']
        for name in names:
            a = groups[mode,context,name]
            lines.append(f"| {name} | {a['energy']*rounds:.9f} | {(a['energy']/base['energy']-1)*100:+.3f}% | {a['cpu']/base['cpu']:.2f}x | {(a['cv']/base['cv']-1)*100:+.3f}% | {(a['risk']/base['risk']-1)*100:+.3f}% | {a['elite']:.2%} |")
    lines += ['', '## Equal-budget inner feedback and snapshot removal', '',
        '| Context | Comparison | Energy change | CPU ratio |',
        '| --- | --- | ---: | ---: |']
    for mode,context,label in [('live_screen',600,'600'),('live_screen',1510,'1510'),('live_validation',None,'150 physical rounds')]:
        for inner, control in [('live_baseline','baseline'),('live_split_2','live_baseline'),('live_inner_80','live_batch_80'),('live_batch_80','live_baseline')]:
            a,b = (groups[mode,context,n] for n in (inner,control))
            lines.append(f"| {label} | {inner} / {control} | {(a['energy']/b['energy']-1)*100:+.3f}% | {a['cpu']/b['cpu']:.2f}x |")
    lines += ['', '## Per-seed validation and critical nodes', '',
        '| Configuration | Seed | Energy change | Mean peak relative depletion change | Node 33 residual (J) | Node 65 residual (J) |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    bases = raw['live_validation',None,'live_baseline']
    for name in names:
        for row, base in zip(raw['live_validation',None,name],bases):
            a,b = aggregate([row]),aggregate([base])
            lines.append(f"| {name} | {row['seed']} | {(a['energy']/b['energy']-1)*100:+.3f}% | {(a['risk']/b['risk']-1)*100:+.3f}% | {a['residual33']:.6f} | {a['residual65']:.6f} |")
    lines += ['', '## Why best-set influence is large', '',
        'For one batch, let B be the ant budget and K the CH count. Ant deposits happen before evaporation, '
        'while the elite deposit happens after it. For equal candidate costs E, equal K and all ants feasible, '
        'surviving ant reinforcement is `(1-rho)*(K-1)*Q/E` and elite reinforcement is `theta*(K-1)*Q/E`. '
        'The elite share of new reinforcement is therefore `theta/(1-rho+theta)`. '
        'At rho=.6, theta=1 gives 71.43%; theta=.1 gives 20%. '
        'A cheaper elite or fewer feasible ants increases its share. '
        'This quantifies why the old best-set bonus can outweigh all ordinary ants together. '
        'It does not imply that reducing it always improves routing. Tables measure surviving additions before clipping, excluding old pheromone and chaos.', '',
        'For the load-fitness comparison, a higher-energy candidate wins over a lower-energy candidate only if '
        '`w*(CV_low-CV_high)/mean(CV) > (1-w)*(E_high-E_low)/mean(E)`. '
        'At w=.1, a CV advantage must offset nine times the normalized energy disadvantage. '
        'This permits an energy/load tradeoff but does not account for residual energy or critical-node topology. '
        'Peak relative depletion, `max_i(cost_i/residual_i)`, is measured separately; a lower absolute CV can still exhaust a vulnerable node sooner.', '',
        '## How multiple batches are controlled', '',
        'For m batches use `rho_inner=1-(1-rho)^(1/m)` and `a=1-rho_inner`, so `a^m=1-rho`. '
        'Disturbance is `c_inner=c*rho_inner/rho`, so its final geometric sum remains c. '
        'For batch b (zero-based), divide ant deposits by the total budget B and multiply by `(1-rho)/a^(m-b)`. '
        'Each batch deposits its best-so-far elite with multiplier `theta/sum(a^i, i=0..m-1)`. '
        'Identical candidates thus produce equal final reinforcement across batch counts before clipping. '
        'One physical round advances beta/rho schedules and logistic chaos exactly once; energy is deducted once. '
        'This separates inner feedback from simply using more ants or applying extra evaporation.', '',
        'Live ants already receive within-round feedback, so extra batches add intermediate evaporation, disturbance and elite reinforcement. '
        'Their benefit must be assessed against an equal total ant budget. The 80-ant batch versus two 40-ant batches comparison provides that control.', '',
        '## Verification and practical limits', '',
        'All 37 tests pass. Checks cover live deposits changing later probabilities, production/experimental equivalence, '
        'independent checkpoint restoration, valid parameter ranges, one physical/logistic step, and equal reinforcement for forced identical candidates. '
        'Every selected tree is independently reevaluated, serves every live node, and leaves residual energy unchanged during search. '
        'All pheromone entries remain finite and within calibrated bounds.', '',
        'CPU is process time from the instrumented runner, which calculates CV for every candidate. '
        'Absolute time and ratios are indicative: these are short concurrent jobs, not a dedicated production benchmark. '
        'Three seeds and early trajectories cannot establish FND or full-service gains. '
        'Checkpoint states are from the old frozen trajectory, so they test the new sampler at matched states rather than predict its eventual late trajectory.', '',
        'Reproduce with `python -B plans/phase5-acaco-balance/balance_study.py live_screen SEED FRESH_RESULTS_DIRECTORY` for seeds 0/1/2 '
        'and `live_validation SEED FRESH_RESULTS_DIRECTORY` for seeds 12/13/14. '
        'Use a fresh directory after source/script changes; the runner refuses to overwrite metadata with different provenance. '
        '`summarize_live.py` reads the archived study results in this folder. '
        'Raw records retain effective experimental configuration, parameters, routing counts, source/map/script hashes and per-round metrics.']
    (FOLDER/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lifetime = FOLDER/'full/summary.json'
    if lifetime.exists():
        followup = json.loads(lifetime.read_text())
        fnd = followup['mean_FND']
        service = followup['mean_service']
        energy = followup['equal_exposure_energy']['1400']
        note = ('## Completed full lifetime follow-up\n\n'
            'Fresh paired seeds 15/16/17 tested production weights 1 and 0.1 with one batch of 40 ants. '
            f"Mean FND was {fnd['weight1']:.3f} versus {fnd['weight01']:.3f} rounds; "
            f"mean service was {service['weight1']:.3f} versus {service['weight01']:.3f} rounds "
            f"({service['change_percent']:+.3f}%). Weight 0.1 lost two service rounds in every pair "
            f"and used {energy['change_percent']:.3f}% more energy through round 1400. "
            'All runs stopped when node 65 died and isolated node 48, with 98 survivors. '
            'The lower weight balances reinforcement but does not improve lifetime on these seeds. '
            'See [full results and terminal topology](full/README.md).\n\n')
        lines[6:6] = [note]
        (FOLDER/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    summary = {f'{m}:{c}:{n}':a for (m,c,n),a in groups.items()}
    (FOLDER/'live_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({n:groups['live_validation',None,n] for n in names},indent=2))


if __name__ == '__main__':
    main()
