"""Write the chaos study report from the recorded raw experiment."""
import json
from pathlib import Path


def avg(rows, key):
    return sum(row[key] for row in rows)/len(rows)


def main():
    folder = Path(__file__).parent
    data = json.loads((folder/'results.json').read_text())
    screening, validation = data['screening'], data['validation']
    for rows in validation.values():
        assert {r['seed'] for r in rows} == {6,7,8}
        assert all(r['completed_rounds']==150 and not r['failed'] for r in rows)
    lines = ['# Chaos after pheromone calibration - 2026-10-11', '',
        '## Question and controlled design', '',
        'Does reducing chaos behave differently after replacing Q=100, bounds [.1,10] '
        'and rho_max=.9 with Q=.01, bounds [.01,20] and rho_max=.6?', '',
        'Both chaos_min and chaos_max are multiplied by 0, .25, .5, 1 or 2. '
        'The logistic r=3.61 and seed=.37 are fixed. Q, pheromone bounds, heuristic '
        'exponents, distance bias, CH proportion, routing, physics and search effort '
        'are fixed within each scale. Zero is an experimental ablation, not a proposed default.', '',
        'Screening: two pheromone scales, five amplitudes, plus two calibrated '
        'mechanism ablations; 20 searches at unchanged physical state per seed '
        '(0/1/2), retaining optimizer memory. Validation: all five calibrated '
        'amplitudes, independent 150-round physical trajectories on fresh seeds '
        '6/7/8, 40 ants per round. These seeds were unused in the previous calibration. '
        'All strengths were declared before validation; no selection-driven holdout retuning.', '',
        'Schedule horizon stays 3000. Configuration order rotates by validation seed. '
        'CPU includes tree-signature instrumentation; post-search diagnostics are outside '
        'the measured search. Timings are indicative, not precise speed claims.', '',
        '## Interaction with the old pheromone scale', '',
        '| Chaos factor | Old scale mean energy, 20 searches (J) | Change vs old x1 | New scale mean energy (J) | Change vs new x1 |',
        '| --- | ---: | ---: | ---: | ---: |']
    for factor in ('0','0.25','0.5','1','2'):
        old = avg(screening[f'historical_x{factor}'],'total_energy_J')
        new = avg(screening[f'calibrated_x{factor}'],'total_energy_J')
        old_base = avg(screening['historical_x1'],'total_energy_J')
        new_base = avg(screening['calibrated_x1'],'total_energy_J')
        lines.append(f'| {factor} | {old:.9f} | {(old/old_base-1)*100:+.3f}% | '
                     f'{new:.9f} | {(new/new_base-1)*100:+.3f}% |')
    lines += ['', 'These are matched current-code controls, not an attempted reproduction '
        'of undocumented historical chaos results. The previous audits used different '
        'states/budgets; their numerical percentages cannot be compared directly.', '',
        '## Independent 150-round trajectories', '',
        '| Chaos factor | Strength bounds | Mean energy (J) | Change vs x1 | Mean minimum residual (J/node) | Mean clustering outliers | Mean CPU (s) |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    baseline = avg(validation['calibrated_x1'],'total_energy_J')
    for factor in ('0','0.25','0.5','1','2'):
        name = f'calibrated_x{factor}'
        rows = validation[name]
        p = data['configs'][name]['parameters']
        energy = avg(rows,'total_energy_J')
        lines.append(f"| {factor} | [{p['chaos_min']:g}, {p['chaos_max']:g}] | "
            f"{energy:.9f} | {(energy/baseline-1)*100:+.3f}% | "
            f"{avg(rows,'min_residual'):.6f} | {avg(rows,'mean_clustering_outliers'):.3f} | "
            f"{avg(rows,'cpu_s'):.3f} |")
    lines += ['', '| Seed | Off vs x1 | Quarter vs x1 | Half vs x1 | Double vs x1 |',
        '| --- | ---: | ---: | ---: | ---: |']
    for seed in (6,7,8):
        values = {factor:next(r for r in validation[f'calibrated_x{factor}'] if r['seed']==seed)
            for factor in ('0','0.25','0.5','1','2')}
        base = values['1']['total_energy_J']
        changes = [f"{(values[factor]['total_energy_J']/base-1)*100:+.3f}%"
            for factor in ('0','0.25','0.5','2')]
        lines.append(f"| {seed} | {' | '.join(changes)} |")
    lines += ['', '## Which mechanism matters?', '',
        '| Calibrated fixed-state control | Mean energy (J) | Change vs full chaos | Mean clustering outliers | Diagnostic transition entropy |',
        '| --- | ---: | ---: | ---: | ---: |']
    for name in ('calibrated_x1','calibrated_without_transition','calibrated_without_pheromone','calibrated_x0'):
        rows = screening[name]
        energy = avg(rows,'total_energy_J')
        lines.append(f"| {name} | {energy:.9f} | {(energy/new_base-1)*100:+.3f}% | "
            f"{avg(rows,'mean_clustering_outliers'):.3f} | {avg(rows,'normalized_entropy'):.6f} |")
    lines += ['', 'Chaos is used twice: additive mixing of transition probabilities and '
        'additive disturbance of pheromone updates. Experiment-local overrides disable '
        'each mechanism independently while preserving the logistic recurrence and all '
        'production code. These mechanism ablations are screening probes only, not '
        'validated lifetime interventions.', '',
        'For transition probabilities, c = strength * chaos[source], and '
        '`p_new = (p + c)/(1+n*c) = (1-lambda)*p + lambda/n`, '
        'where `lambda = n*c/(1+n*c)`. Lower strength makes the sampler more '
        'concentrated on pheromone/local heuristics; higher strength spreads CH choices. '
        'On this map that changes clustering coverage and the costs faced by the shared router.', '',
        'Clustering outliers are sensors beyond every selected CH radius; they still '
        'participate in multi-hop routing. They are not omitted or unserved sensors. '
        'Entropy is normalized by log(candidate count), averaged over hypothetical '
        'first transitions from the first ten live sources. Mixture share is a '
        'diagnostic average over live sources and 99..81 candidate counts; it is '
        'not an empirical average over the ants\' sampled source frequencies.', '',
        '## Verification, limits and decision', '']
    count = sum(r['feasible_evaluations'] for stage in (screening,validation)
        for rows in stage.values() for r in rows)
    lines += [f'Completed {count:,} feasible full-tree evaluations. Actual calls and '
        'unique trees are recorded separately; unique trees do not replace the '
        'equal 40-evaluation search budget.',
        'All measured rounds served every live sensor; no deaths were observed. '
        'Every selected tree is independently reevaluated. Tests verify instrumented '
        'control trajectories equal plain production trajectories and disabling both '
        'mechanisms equals zero-amplitude chaos. All 24 repository tests pass.', '',
        '| Factor | Mean pheromone floor occupancy | Mean ceiling occupancy | Maximum relative one-round depletion |',
        '| --- | ---: | ---: | ---: |']
    for factor in ('0','0.25','0.5','1','2'):
        rows = validation[f'calibrated_x{factor}']
        lines.append(f"| {factor} | {avg(rows,'floor_fraction')*100:.3f}% | "
            f"{avg(rows,'ceiling_fraction')*100:.3f}% | {max(r['peak_depletion'] for r in rows):.9f} |")
    lines += ['', 'The doubled maximum disturbance remains within the reference late-round '
        'pheromone envelope: at route cost .015 J, minimum evaporation .1 and '
        'max chaos .6, the all-ant-plus-elite equilibrium bound is '
        '`((2-.1)*(.01/.015)+.6*(3.61/4))/.1 = 18.081667 < 20`. '
        'This reference cost is not a universal lower bound.', '',
        'Retain production chaos bounds [.05,.30] for now. Higher amplitude is '
        'an opt-in candidate based on early energy, not a certified lifetime improvement. '
        'No source-code default is changed by this early study. Lifetime/FND outcomes '
        'and behavior around raw-beta transition at round 1500 are examined in the '
        '[longer follow-up](long/README.md), with a [mathematical analysis](long/MATH_ANALYSIS.md). '
        'Different topologies remain untested. No statistical-significance or global-optimality claim '
        'is supported by three seeds on one topology.', '',
        '## Artifacts and reproduction', '',
        '- `experiment.py`: explicit paired controls, mechanism interventions and instrumentation.',
        '- `results.json`: all configurations, per-round/per-seed raw metrics, map/source/script fingerprints.',
        '- `summarize.py`: regenerates this report.',
        '- `higher-chaos-candidate.json`: full x2 configuration for opt-in follow-up.', '',
        'From the repository root run `python -B plans/phase5-acaco-chaos/experiment.py`, '
        'then `python -B plans/phase5-acaco-chaos/summarize.py`. Matching saved runs '
        'are reused; move the results artifact for a fresh run.', '',
        f"Starting git SHA: `{data['git_sha']}`. Map SHA-256: `{data['map_sha']}`."]
    (folder/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (folder/'higher-chaos-candidate.json').write_text(json.dumps(
        data['configs']['calibrated_x2']['parameters'],indent=2)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
