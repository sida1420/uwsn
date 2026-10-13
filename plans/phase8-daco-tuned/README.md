# D-ACO tuning transfer and density-load fitness

Historical implementation: the user subsequently replaced max/CV fitness with
the phase-9 powered load/density model. The old parameter names and enabling
instructions below describe that archived implementation, not current production.
The runner now explicitly imports frozen legacy D-ACO.

Completed: all 15 full trajectories. See [RESULTS.md](RESULTS.md) for the
paired comparison and [summary.json](summary.json) for the metrics.
The sibling tuning is not promoted. The density penalty is implemented
as an opt-in: weight 0.05 improves mean service by 195 rounds (+8.90%)
and mean first-node death by 645 rounds (+38.89%), with a 2.38% all-alive
energy cost. Weight 0.10 costs more energy and gives less service than
0.05. Original tuning and all grid variants are retained.

Work is in review_uwsn. The sibling uwsn checkout is read only. All grid
attenuation variants from phase 7 remain available; these trials use the
original grid to isolate tuning and fitness changes.

Stage 1: full baseline and transferred tuning trials, fresh paired seeds
15/16/17, current 100-sensor map, 3000-round horizon or normal termination.
Both use one batch of 40 ants. The sibling's four iterations of 20 ants
are not restored. The transfer preserves its absolute fitness, live
per-ant deposits, elite contribution in per-ant units, evaporation order,
partial-grid coverage scaling, and tuned numeric controls. It is a
single-batch adaptation, not a reproduction of the sibling's 80-ant run.
The source values and both checkouts' hashes are recorded in each run.

Promotion rule: require lower energy over the same all-alive rounds,
with no regression in mean first-node death or completed service. A
lifetime/energy tradeoff is reported rather than automatically promoted.
CPU time is recorded but concurrency/hardware frequency are not controlled.

Stage 2: keep the better baseline from stage 1 and test a density-free
relative-depletion control, plus density-aware penalties weighted 0.05
and 0.10. Every trial runs to normal termination.

For each live sensor i, use grid density D_i = F_i dot grid_density,
without CH coverage loss. Let D_scale be the median positive D_i. Define

P = max_i [(e_i / r_i) * (1 + kappa / (1 + D_i / D_scale))]
    / (total_energy / sum_i r_i).

Here e_i is evaluated consumption, r_i is pre-round residual energy,
and kappa=1 weights sparse sensors more strongly. Kappa=0 is the
density-free control. Density scaling makes the scarcity factor
comparable across grid overlap magnitudes. The denominator is ideal
equal relative depletion, making P dimensionless like load CV.
Add lambda * P to the existing fitness; retain energy and CV terms.
All sensors, including members and relays, contribute to the penalty.

The lambda=0 branch preserves the prior algorithm. Nonzero lambda affects
both candidate selection and pheromone reinforcement. No search operator,
inner iteration, routing change, or other algorithm is included.
