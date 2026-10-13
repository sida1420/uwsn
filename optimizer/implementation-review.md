# Implementation review — 2026-10-12

PASS: all ten focused checks passed on Windows with Python 3.12 and Optuna 4.6.0 in about 37 seconds; see `smoke-test.log`. The tenth check verifies session and cumulative limits. Physical test trajectories are capped at 2–20 rounds; the concurrency pilot uses three four-round parameter configurations on two seeds, with two workers. No full 3000-round simulation, full optimization campaign, or held-out scientific study was launched.

Budget revision: 32 configurations, 12 startup trials, at most six cumulative active tuning hours, and two-hour resumable sessions. Optional frozen-shortlist validation is limited to one linked study with at most two active hours. The combined allowance is eight hours. Time-based stops reserve shutdown headroom inside the configured limit. Idle gaps between sessions do not consume active budget. The old unstarted initialization is preserved; `runs/ready-short` uses the revised policy.

The budget-revision tests also exposed a transient Windows read-handle collision with atomic status replacement. Atomic outputs now retry replacement for at most half a second before reporting an error; the final stop/resume/concurrency checks pass with this fix.

Verified:

- Independent parameter domains, legal overrides, and strict workload/energy settings.
- Cohort mean feasibility, per-seed violation diagnostics, and positive constraints for noncomparable workload.
- Exact residual-energy/energy/attempt equality after checkpoint pause/resume and an actual killed worker.
- Full-precision historical SimpleACO cap and short deterministic prefixes for current D-ACO, quarter heuristics, and pheromone-only SimpleACO.
- Source/map/config identity checks and duplicate-work avoidance.
- Kernel coordinator exclusivity, graceful stop, coordinator resume, two-worker completion and exhausted-budget resume.
- Actual adaptive multivariate TPE suggestions using synthetic objective values, and constraint metadata stored by the installed Optuna version.
- Complete CSV/JSON/report/plot generation, and suppression of best-config promotion in smoke studies.

Observed API detail: installed Optuna 4.6 invokes the constraint callback on PRUNED trials as well as COMPLETE trials, while FAIL trials do not invoke it. The callback returns a strictly positive constraint if attributes are missing. Incomplete/failed/pruned trials never appear in the scientific feasible leaderboard. This behavior was tested rather than inferred from the plan's API expectation. The implemented study does not use proxy pruning.

The physical runner leaves native T_max=3000 and all production defaults unchanged. Only configured D-ACO parameter overrides affect its search. Diagnostic wrappers restore original methods before checkpointing and add no RNG draws. Calibration energy is hypothetical; physical deduction applies only to the selected full-service tree.

The controller is the sole SQLite/Optuna writer. Simulation workers never write the DB. A crashed coordinator's kernel lock releases; old workers pause on ownership loss. Resume recovers complete outcomes, queued trials, paused cohorts and sampler state; a suggestion interrupted before its durable manifest is marked failed and consumes budget rather than being silently replaced. Hard-killed uncommitted rounds may be recomputed. This preserves physical accounting, not a guarantee that asynchronous future proposal order is identical to an uninterrupted run.

Remaining scope limits: Ubuntu launch is documented but not executed on this Windows host; no multi-hour stress benchmark, full source regression sweep, random-search comparator or independent scientific holdout validation was run. Historical reference artifacts did not record their original NumPy version, and are labeled as fingerprint-matched historical evidence. The tiny historical-prefix checks are not presented as fresh full-trajectory reproduction. Trial/seed resource metrics include diagnostic overhead; no calibrated speed claim is made.

All implementation artifacts are under `optimizer/`. Production source, map, prior experimental evidence, defaults and the sibling checkout were not changed in this task. Generated study data and local verification dependencies are ignored. `PLAN.md` preserves the attached proposal as context; its proposed autonomous-run instructions were not used as authorization to launch a campaign.
