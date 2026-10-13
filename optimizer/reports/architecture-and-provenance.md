# Architecture and provenance

Current orchestration is directly under optimizer/; legacy studies are preserved.
Production algorithms now accept explicit per-instance seeds, and adapters pass them.
Private RNG streams are pickled with the native state; observation consumes no extra draws.
Adapter registry owns native construction, parameter validation/search space and diagnostics.
Shared trajectory runner owns selected-route accounting, checkpoints and energy eligibility.
Shared engine owns Optuna ask/tell, seed cohorts, worker isolation and the wall-time ledger.
PSO and AC-ACO use this runner in smoke tests only. No PSO/AC-ACO tuning is enabled.

Clock inventory: D-ACO rho is rho_max-min(t/T_max,1)*(rho_max-rho_min), one increment
per network round. Beta/gamma/theta are constants. Grid decay is spatial, not temporal.
AC-ACO rho uses the same round clock; raw beta centers at T_max/2 (1500 becomes1750),
normalized beta uses t/T_max-.5; chaos uses the native cost window and logistic sequence.
PSO inertia uses inner_iteration/(iterations-1), not network T_max; warm starts persist
across network rounds. Ant/particle counts and PSO inner iterations are not set to3500.
    All source occurrences are retained in adaptive-horizon-inventory.csv; exact boundary
values for both horizons are in schedule-boundaries.csv. Experiment scripts are legacy
provenance and are not executed or rewritten for this campaign.

Old 3000 trials are tier C parameter-only. Prefix identity fails at round1 when rho changes.
No old objective observations or checkpoint state enter the new surrogate/ranking.
SimpleACO is freshly rerun with matched hparameters; K2611 and the exact mean*1.02 cap remain.
The earlier plan's rounded absolute cap is metadata only. Density decay was fixed parabolic,
not tuned, in the previous expanded study.

Performance changes: hash sources at entry/completion and on file-stat changes between
checkpoints; persist state on transitions or every2s; pickle sampler on ask/tell only;
prioritize old feasible settings, deduplicate exact configs, and admit new trials based
on a conservative observed full-cohort duration. No proxy scores enter final ranking.
Concurrent suggestion order can differ; native RNG/physical state checkpoints remain exact.
