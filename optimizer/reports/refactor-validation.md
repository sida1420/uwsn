# V2 implementation and validation

Nine tests passed in36.978s; see ../test-results.log. Tests used only2–10 physical
rounds, never a3500-round scientific cohort. Windows scripts passed PowerShell
AST parsing and the CLI init/audit/help commands executed successfully.

Verified:

- D-ACO, PSO and AC-ACO execute five-round trajectories through the same runner.
- D-ACO physical residuals and K-energy exactly match the legacy runner with
  identical parameters, seed, map and T_max3000.
- A paused or actually killed worker resumes RNG/algorithm/physical checkpoints
  and matches uninterrupted results at ten rounds.
- Changing T_max changes rho at round1; schedules are logged at1,600,1500,1750,
  2611,2999,3000,3500 for both clocks. No previous checkpoint continuation is valid.
- All32 old configurations are tierC; priority starts with trial25, and no old
  scores enter Optuna objective observations. SQLite is read-only and backed up.
- The engine completes and resumes a tiny two-worker study without duplicate trials.
- Public run exercises the outer supervisor: startup/report costs enter the ledger,
  resume increases cumulative spending, and an exhausted ledger launches nothing.
- 100 unchanged epoch checks invoke only one full hash; forced boundary validation
  invokes the second. This is measured call reduction, not a claimed runtime speedup.
- Physical deduction uses only the selected fully covered routing tree. Native
  algorithm candidate evaluations and calibration do not reduce residual energy.

The final prepared service3500-v2-ready campaign has spent_wall0, jobs{}, stop_reason not_started.
Three additional controller checks passed after strengthening duplicate-supervisor
protection and estimating the first cohort's cost from measured SimpleACO throughput;
see ../final-controller-check.log. The preliminary service3500-v2 initialization is
preserved as an unstarted preflight snapshot and is not the launcher's target.
No scientific tuning, holdout validation or production default promotion occurred.
No existing optimizer/source files were edited during this v2 implementation.

Limitations: the deadline supervisor is tested with small real workloads and
exhaustion, not a90-minute stress run. OS termination/atomic bookkeeping can incur
small scheduling latency at the deadline. Scaling diagnostics for50/100/200nodes
and20/40/80ants are algebraic equal-quality cases, not matched physical topology
benchmarks; no topology-aware theta normalization is implemented or claimed.
The occurrence inventory annotates temporal groups and points to exact schedule
boundary values; non-temporal statements retain their source expression rather
than assigning an invented numerical meaning.

Production PSO/AC-ACO controls/equations remain unchanged. Their adapters are
registered for smoke evaluation, not full tuning. Existing report/launch paths
remain operational; v2 has separate versioned sources, DB, config and launcher.
