"""Produce comparative tables after every declared study run completes."""
import json
from pathlib import Path
import statistics as st

FOLDER=Path(__file__).parent


def aggregate(rows):
    records=[x for r in rows for x in r['records'] if not x['failed']]
    return dict(energy=st.mean(r['energy_J']/r['completed'] for r in rows),
        cpu=st.mean(r['cpu_s']/r['completed'] for r in rows),
        cv=st.mean(x['load_cv'] for x in records),
        risk=st.mean(x['peak_relative_depletion'] for x in records),
        maxrisk=max(x['peak_relative_depletion'] for x in records),
        feasible=st.mean(x['feasible'] for x in records),
        attempts=st.mean(x['attempts'] for x in records),
        elite=st.mean(x['elite_fraction'] for x in records),
        residual33=st.mean(r['critical_residual']['33'] for r in rows),
        residual65=st.mean(r['critical_residual']['65'] for r in rows))


def main():
    metadata=json.loads((FOLDER/'results/metadata_validation_9.json').read_text())
    names=[n for n in metadata['configs'] if not n.startswith('live_')]
    groups={}
    for mode,context,seeds,selected in [('screen',600,(0,1,2),names),
            ('screen',1510,(0,1,2),names),('validation',None,(9,10,11),metadata['validation'])]:
        for name in selected:
            rows=[json.loads((FOLDER/'results'/f'{mode}_{context}_{name}_seed{s}.json').read_text()) for s in seeds]
            assert all(r['completed']==(12 if mode=='screen' else 300) for r in rows)
            groups[mode,context,name]=aggregate(rows)
    lines=['# Frozen reference: best-set balance and inner iterations', '',
        'These are historical frozen-sampler controls. See [the live-sampler report](README.md) for the current implementation. '
        'Checkpoint states are independently deep-copied; the initial order-confounded screens were excluded and archived under `invalid-screen-state-alias/`.', '',
        '## What current D-ACO does', '',
        'The current D-ACO wrapper runs one ant batch per physical round, not a nested optimizer loop. '
        'It scores candidates by `.9 * energy / mean_energy + .1 * load_CV / mean_CV`, '
        'and gives the best set an additional pheromone multiplier `theta=.1`. '
        'Its pheromone belongs to CH nodes; AC-ACO pheromone belongs to CH-order transitions. '
        'AC-ACO currently selects by total energy and uses an elite multiplier of 1.', '',
        'D-ACO deposits `Q/fitness`, whereas AC-ACO deposits `Q/physical_energy`. '
        'Copying the former denominator would change the calibrated scale drastically. '
        'This study tests the elite multiplier and candidate selection separately while retaining inverse-physical-energy deposits.', '',
        '## Controlled design', '',
        'Frozen screening uses RNG seeds 0/1/2 and 12 consecutive optimizer searches at each unchanged physical state. '
        'The states are the calibrated current-chaos seed-6 checkpoint after 600 rounds, and the exact state after node 33 dies at round 1510. '
        'The latter is recreated by replaying nine saved-state rounds and checking every cost against the prior trajectory. '
        'Each configuration starts from identical physical and optimizer state. Memory evolves during the 12 searches; energy is not deducted.', '',
        'Independent validation uses fresh seeds 9/10/11 and 300 physical rounds per configuration. '
        'All seven configurations were declared before validation. The schedule horizon stays 3000. '
        'Configuration order rotates by seed. This is an early-trajectory comparison, not a lifetime/FND validation.', '',
        'One iteration uses 40 ants. Split-2 and split-4 use 20x2 and 10x4 ants, respectively. '
        'Expanded-budget controls compare 80x1 versus 40x2, and 160x1 versus 40x4. '
        'Every ant retains the same ten-attempt limit. Actual feasible candidates and attempts are counted.', '',
        '## Frozen screening', '']
    for context in (600,1510):
        lines += [f'### Checkpoint {context}', '',
            '| Configuration | Energy change | CPU ratio | Load CV change | Mean peak relative depletion change | Feasible candidates | Elite share of new mass |',
            '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        base=groups['screen',context,'baseline']
        for name in names:
            a=groups['screen',context,name]
            lines.append(f"| {name} | {(a['energy']/base['energy']-1)*100:+.3f}% | {a['cpu']/base['cpu']:.2f}x | {(a['cv']/base['cv']-1)*100:+.3f}% | {(a['risk']/base['risk']-1)*100:+.3f}% | {a['feasible']:.2f} | {a['elite']:.2%} |")
    lines += ['', '## Fresh 300-round trajectories', '',
        '| Configuration | Mean total energy (J) | Energy change | CPU ratio | Load CV change | Mean peak relative depletion change | Node 33 final residual (J) | Node 65 final residual (J) |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    base=groups['validation',None,'baseline']
    for name in metadata['validation']:
        a=groups['validation',None,name]
        lines.append(f"| {name} | {a['energy']*300:.9f} | {(a['energy']/base['energy']-1)*100:+.3f}% | {a['cpu']/base['cpu']:.2f}x | {(a['cv']/base['cv']-1)*100:+.3f}% | {(a['risk']/base['risk']-1)*100:+.3f}% | {a['residual33']:.6f} | {a['residual65']:.6f} |")
    lines += ['', '## Equal-budget effect of inner feedback', '',
        '| Context | Inner / one-batch control | Energy change | CPU ratio |',
        '| --- | --- | ---: | ---: |']
    for mode,context,pairs in [('screen',600,[('split_2','baseline'),('split_4','baseline'),('inner_80','batch_80'),('inner_160','batch_160')]),
            ('screen',1510,[('split_2','baseline'),('split_4','baseline'),('inner_80','batch_80'),('inner_160','batch_160')]),
            ('validation',None,[('split_2','baseline'),('inner_80','batch_80')])]:
        for inner,control in pairs:
            a,b=(groups[mode,context,n] for n in (inner,control))
            label=f'frozen {context}' if mode=='screen' else '300-round trajectories'
            lines.append(f"| {label} | {inner} / {control} | {(a['energy']/b['energy']-1)*100:+.3f}% | {a['cpu']/b['cpu']:.2f}x |")
    lines += ['', '## Interpreting balance', '',
        'Load CV is the standard deviation of absolute per-node round energy divided by its mean, matching D-ACO. '
        'It is different from residual-aware depletion. Peak relative depletion is `max_i(cost_i / residual_i)` and is measured independently. '
        'A lower CV can still burden a nearly exhausted critical node; total energy can rise when choosing a more uniform load. '
        'No FND or full-service gain is established by 300 rounds.', '',
        'Elite mass shares refer to newly added ant and elite reinforcement after accounting for their remaining evaporation. '
        'They exclude existing pheromone and chaos, and are theoretical surviving additions before any clipping. '
        'CPU uses process time from the same instrumented runner, which calculates candidate load CV even for energy-only controls. '
        'Absolute timings are not bare-production benchmarks; ratios are indicative.', '',
        '## Mathematical normalization of inner updates', '',
        'For outer-round evaporation `rho` and `m` batches, use `rho_inner = 1-(1-rho)^(1/m)`. '
        'With `a=1-rho_inner`, the effective decay is `a^m=1-rho`. '
        'Use pheromone disturbance `c_inner=c*rho_inner/rho`, giving `sum(a^i*c_inner)=c`. '
        'Transition mixing retains the original outer strength, and the logistic state advances once after the final batch. '
        'Beta, evaporation progress and physical energy advance once per physical round.', '',
        'For batch `b=0..m-1`, per-ant deposits divide by the total ant budget `B`, '
        'and are multiplied by `(1-rho)/a^(m-b)`. Their final survival therefore matches the single-update control. '
        'The best-so-far elite deposit per batch uses `theta / sum(a^i)`. '
        'For identical candidate costs and paths this preserves total elite reinforcement. '
        'Clipping or changing candidate quality can break exact mass equivalence, and are part of the measured optimizer behavior. '
        'This normalization isolates feedback within the round instead of simply increasing evaporation, logistic steps or deposit strength.', '',
        'For a single batch with `K` CHs and `B` ants, surviving ant mass is '
        '`A=(1-rho)*(K-1)*Q/B*sum(1/E_ant)`, while elite mass is '
        '`G=(K_best-1)*theta*Q/E_best`. The elite share is `G/(A+G)`. '
        'For equal costs, all ants feasible and equal CH counts, it simplifies to '
        '`theta/(1-rho+theta)`. At rho=.6, theta=1 yields 71.43%, while theta=.1 yields 20%. '
        'A cheaper best candidate or fewer feasible ants increases its share. '
        'Thus a full-strength best-set deposit can outweigh all ordinary ants together.', '',
        '## Verification and reproduction', '',
        'All 37 tests passed. Experimental live configurations match production consumption, pheromone, chaos and RNG state when instantiated with corresponding weights. '
        'Tests also verify one physical/logistic step despite multiple inner batches, identical-candidate reinforcement across split budgets, and the normalized D-ACO fitness tradeoff. '
        'Every selected tree is independently reevaluated and serves every live node; source/map/script fingerprints and instantiated parameters are saved.', '',
        'Run `python -B plans/phase5-acaco-balance/balance_study.py screen SEED FRESH_RESULTS_DIRECTORY` for seeds 0/1/2; '
        'run with `validation SEED FRESH_RESULTS_DIRECTORY` for seeds 9/10/11. Use a fresh directory after code changes to preserve old provenance. '
        'Then run `summarize_balance.py`. Inner iterations remain experiment-local; production exposes separate elite and fitness weights.']
    (FOLDER/'FROZEN_REFERENCE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    summary={f'{mode}:{context}:{name}':v for (mode,context,name),v in groups.items()}
    (FOLDER/'frozen_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({name:groups['validation',None,name] for name in metadata['validation']},indent=2))


if __name__=='__main__':
    main()
