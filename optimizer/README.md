# D-ACO optimizer

One optimizer implementation lives directly in `optimizer/`. Historical studies
and checkpoints remain under `runs/`; the old implementation is available in Git.
All five production algorithms support isolated per-instance random seeds.
The selected campaign is recorded in `active-study.json`; each campaign stores
its own frozen `map.pkl` so regenerating the source map cannot change it.

After approving a new campaign, double-click **Run-Optimizer-Windows.bat**, choose **1**,
then choose parallel runs (1–4, initially two). Q closes the display; S stops and
saves. Closing the display leaves the background controller running. Resume uses
the same cumulative 90-minute ledger. There is no separate two-hour session limit.

For either an increase or decrease in workers, press **S**, wait until the controller
has stopped, then resume with the new count. Extra unfinished trials stay paused
with their checkpoints and resume when worker slots are free, provided campaign
time remains. After the admission cutoff, only trials already selected for
completion resume; other queued trials remain paused. A running controller keeps its existing count.

Choose **6** to prepare another campaign for the current map, then **1** to run it.
Each new map gets a separate study; old results remain intact. A disconnected
deployment is rejected during preparation because full-network service is
physically impossible from the start.

This is a new campaign budget, not an extension/reset of the previous study.
The cumulative 90-minute budget is an admission cutoff. At that point no new
trials start; active trials finish every remaining seed and enter the final
ranking normally. Actual elapsed time can exceed 90 minutes and remains recorded
in the ledger. There is no five-minute reserve or timer-triggered termination.
Press S to checkpoint and stop immediately, including during this finishing phase.
Partial cohorts remain excluded. Reports distinguish reused anchors, sampler
proposals, and user-supplied rounded parameter sets; rerunning a known set is
validation on this map, not evidence that the optimizer discovered it.

The objective is completed service lifetime capped at **3500**, with
**T_max=3500** explicitly applied to algorithm instances. The +2% cohort mean
energy rule remains. The reference chooses K once, before any D-ACO proposal:
`min(energy_window, floor(reference_window_fraction * shortest all-alive reference prefix))`,
with a one-round minimum if a usable prefix exists. Defaults are a 2611-round
limit and a 0.9 fraction. Every seed and candidate uses the same frozen K; an
early-dying candidate is infeasible. No candidate changes its own denominator.
Use `energy_window_policy: fixed` to require an exact K instead. If SimpleACO
has no fully alive/served round, the campaign stops with a clear explanation.
Ant count stays40; one D-ACO
batch per network round. Production defaults and physics are not modified.

Exactly one strong previous configuration seeds a new study. Every subsequent
trial gets a new vector from the sampler: random startup draws followed by
adaptive TPE proposals once enough trials complete. The remaining historical
parameter pool is archived as metadata and is not queued. Old scores and
checkpoints are not imported: changing T_max changes evaporation from round1.
All32 old trials are parameter-only tierC.
The old database is opened read-only and copied to a separate SQLite snapshot.
SimpleACO reference runs are fresh under the new epoch. No held-out seeds are used.

Adapter registry and shared trajectory/controller support D-ACO, PSO, AC-ACO and
SimpleACO reference construction. PSO/AC-ACO are smoke-only; tuning them is refused.
Adapter versions, native fitness identity and requested/effective parameters are
recorded per trajectory. Native fitness, search effort and equations remain intact.
Adapters pass the cohort seed explicitly. Private RNG state is included in
checkpoints; entropy observation uses that same stream without extra draws.
Source changes require a new epoch. Algorithm checkpoints are never migrated.
Completed SimpleACO measurements can be imported with `init --reference-from`
only after exact map, simulation sources, runtime, native parameters and cohort
checks. Map-generator-only source changes are allowed because the exact map
bytes still match. Import reconstructs energy from saved round records and
carries over the spent-time ledger; it imports no trial scores or algorithm states.

Efficiency changes: stat-based epoch guards between full hashes at boundaries;
state writes on transitions/every2s; sampler writes on ask/tell; old feasible
settings first; exact-anchor deduplication; budget-based trial
admission. They reduce bookkeeping, not physical evaluation effort. No speedup
percentage is claimed. High-dimensional TPE with few trials is not an optimality proof.

## Manual commands (repository root, Windows)

```powershell
$py = 'C:/Users/hgtfh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
# Initialization is already prepared; these show how to create another unique campaign.
& $py -B -m optimizer init --config optimizer/config.example.yaml --study optimizer/runs/new-id --legacy optimizer/runs/ready-expanded
# Launch only after approval. The prepared campaign uses this path:
& $py -B -m optimizer run --study optimizer/runs/service3500-adaptive --workers 2
& $py -B -m optimizer status --study optimizer/runs/service3500-adaptive
& $py -B -m optimizer stop --study optimizer/runs/service3500-adaptive
& $py -B -m optimizer report --study optimizer/runs/service3500-adaptive
```

Only public `run` uses the outer deadline supervisor; `_run` is an internal child
entry point. Use public run/launcher. No background jobs start during init/audit.

Outputs: immutable config/provenance, legacy compatibility/database snapshot,
anchors, deadline ledger, OptunaDB, checkpoint/RNG states, progress, full per-round
CSV, per-seed physical metrics and connectivity certificates, all-trial exports,
incomplete lists, top-five full params, best feasible YAML and service/energy plot.
The result at3500 is right-censored; failure to find a route is separate from graph disconnection.

## Audits and limitations

See [the maintained performance analysis](../plans/analysis/README.md) and
[theta scaling](../plans/analysis/theta-scaling-audit.md). Regenerate a current
source audit with `python -B -m optimizer audit --output optimizer/reports`.
Theta is already ant-count
normalized on the ordinary deposits. Its effectiveness still depends on feasible
ants, scores, CH overlap and clipping. The27-case scaling table is controlled
algebra, not physical lifetime evidence across new maps. No normalization policy
is promoted. Additional topology experiments and held-out validation remain
separate research phases.

Optuna4.6 ask/tell and enqueue APIs were checked against the
[official Study documentation](https://optuna.readthedocs.io/en/v4.6.0/reference/generated/optuna.study.Study.html).
Queued parameters are reevaluated; `add_trial` is deliberately not used for old scores.

## Folder layout

One implementation lives directly in `optimizer/`. `tests/` holds the short checks;
`reports/` holds generated audits and the latest verification logs. `runs/` keeps
the prior completed study needed for baseline selection (`ready-expanded`), the
completed reference measurements (`service3500`), and the current campaign
(`service3500-adaptive`). Unstarted preparations and stale studies were removed.
Historical run files retain their
original provenance and are read-only inputs for parameter reuse. Old optimizer
code is available in Git history. There is no nested optimizer implementation.
