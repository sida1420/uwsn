# D-ACO optimizer

One optimizer implementation lives directly in `optimizer/`. Historical studies
and checkpoints remain under `runs/`; the old implementation is available in Git.
All five production algorithms support isolated per-instance random seeds.
The current `service3500` campaign is prepared and has not been launched.

After approving a new campaign, double-click **Run-Optimizer-Windows.bat**, choose **1**,
then choose parallel runs (1–4, initially two). Q closes the display; S stops and
saves. Closing the display leaves the background controller running. Resume uses
the same cumulative 90-minute ledger. There is no separate two-hour session limit.

For either an increase or decrease in workers, press **S**, wait until the controller
has stopped, then resume with the new count. Extra unfinished trials stay paused
with their checkpoints and resume when worker slots are free, provided campaign
time remains. They are not deleted. A running controller keeps its existing count.

This is a new campaign budget, not an extension/reset of the previous study.
The outer supervisor includes startup, references, trajectories, flush, reporting
and shutdown. It reserves the last five minutes for stopping/reporting and kills
unfinished child processes at the deadline. Process termination and final atomic
bookkeeping have unavoidable OS scheduling latency; this is not a hard realtime system.
Interrupted trajectories remain incomplete and never enter the final ranking.

The new objective is completed full-service lifetime capped at **3500**, with
**T_max=3500** explicitly applied to algorithm instances. K=2611 fully alive/served
rounds and the +2% cohort mean energy rule remain. Ant count stays40; one D-ACO
batch per network round. Production defaults and physics are not modified.

Previous trials25,30,15,1,2 seed the search, followed by deduplicated baseline and
diversity anchors. Their old scores and checkpoints are NOT imported: changing
T_max changes evaporation from round1. All32 old trials are parameter-only tierC.
The old database is opened read-only and copied to a separate SQLite snapshot.
SimpleACO reference runs are fresh under the new epoch. No held-out seeds are used.

Adapter registry and shared trajectory/controller support D-ACO, PSO, AC-ACO and
SimpleACO reference construction. PSO/AC-ACO are smoke-only; tuning them is refused.
Adapter versions, native fitness identity and requested/effective parameters are
recorded per trajectory. Native fitness, search effort and equations remain intact.
Adapters pass the cohort seed explicitly. Private RNG state is included in
checkpoints; entropy observation uses that same stream without extra draws.
The prepared flat-layout epoch supersedes earlier unstarted preparations, whose
source fingerprints are now stale. Old checkpoints are never migrated.

Efficiency changes: stat-based epoch guards between full hashes at boundaries;
state writes on transitions/every2s; sampler writes on ask/tell; old feasible
settings first; exact-anchor deduplication; conservative measured cohort-time
admission. They reduce bookkeeping, not physical evaluation effort. No speedup
percentage is claimed. High-dimensional TPE with few trials is not an optimality proof.

## Manual commands (repository root, Windows)

```powershell
$py = 'C:/Users/hgtfh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
# Initialization is already prepared; these show how to create another unique campaign.
& $py -B -m optimizer init --config optimizer/config.example.yaml --study optimizer/runs/new-id --legacy optimizer/runs/ready-expanded
# Launch only after approval. The prepared campaign uses this path:
& $py -B -m optimizer run --study optimizer/runs/service3500 --workers 2
& $py -B -m optimizer status --study optimizer/runs/service3500
& $py -B -m optimizer stop --study optimizer/runs/service3500
& $py -B -m optimizer report --study optimizer/runs/service3500
```

Only public `run` uses the outer deadline supervisor; `_run` is an internal child
entry point. Use public run/launcher. No background jobs start during init/audit.

Outputs: immutable config/provenance, legacy compatibility/database snapshot,
anchors, deadline ledger, OptunaDB, checkpoint/RNG states, progress, full per-round
CSV, per-seed physical metrics and connectivity certificates, all-trial exports,
incomplete lists, top-five full params, best feasible YAML and service/energy plot.
The result at3500 is right-censored; failure to find a route is separate from graph disconnection.

## Audits and limitations

See reports/architecture-and-provenance.md, adaptive-horizon-inventory.csv,
schedule-boundaries.csv and theta-scaling-audit.md. Theta is already ant-count
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
`reports/` holds audits and verification logs; `runs/` preserves all old results
and holds the current `service3500` campaign. Historical run files retain their
original provenance and are read-only inputs for parameter reuse. Old optimizer
code is available in Git history. There is no nested optimizer implementation.
