# Maintained performance analysis

This is the only retained analysis folder under `plans/`. It contains conclusions,
tested parameter vectors and evidence rather than obsolete execution scripts.

- [D-ACO comparisons](daco-performance.md): grid decay, load/density fitness,
  pheromone-only SimpleACO, lighter heuristics, stronger deposits and saturation.
- [AC-ACO comparisons and math](acaco-performance.md): calibration, elite balance,
  chaos mixing and limitations of historical fixed-state analysis.
- [Optimizer results](optimizer-results.md): two maps, measured lifetime/energy,
  complete parameter sets, sample origin and incomplete-trial exclusions.
- [All completed optimizer metrics](optimizer-results.json).
- [Theta scaling](theta-scaling-audit.md) and its algebraic diagnostic CSV.

Important distinctions: first-node death differs from routing-service termination;
reaching the horizon censors lifetime; energy comparisons require identical fully
served workloads; a replayed parameter set is validation rather than a newly
discovered optimum. CPU comparisons across different concurrency/observers are
not controlled runtime evidence. These studies mostly use three seeds on one map.

The runtime optimizer, Windows launchers and its current checks remain in
`optimizer/`. Exact current-study outputs/checkpoints and the prior study used for
warm-start parameters remain in `optimizer/runs/`. Removed plans are in Git history.
