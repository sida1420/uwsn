# D-ACO constrained optimizer

All optimizer code, configuration, launch scripts and study outputs live in this folder. D-ACO now defaults to parabolic grid decay; the optimizer evaluates parameter candidates without automatically promoting their values. The attached original plan is archived as `PLAN.md`; subsequent user changes expand the search to theta, load_density_weight and load_power.

The objective is **maximum mean completed service, capped at 3000 rounds**, subject to **mean selected-route physical energy over 2611 full all-alive rounds ≤ 1.02 × matched pheromone-only SimpleACO energy**. First death is a diagnostic, not the objective. Candidates that die within the window or stop early are noncomparable and infeasible, never cheap zero-energy successes. The constraint uses the cohort mean; an individual violating seed does not alone disqualify a mean-feasible cohort.

On the existing map/seeds 24/25/26, the raw reference mean is `42.46611648006099 J`; the full-precision cap is `43.31543880966221 J`. The plan's rounded cap, `43.315422 J`, is retained in metadata with the exact discrepancy. Historical references are reused only when map/source hashes, seeds, effective SimpleACO settings and all-alive workload match. Their original NumPy version was not recorded; they are labeled historical. New cohorts or a mismatched epoch get fresh matched SimpleACO references before any D-ACO suggestions. If the reference cannot supply the full window, the study stops; it never silently shortens K. Different map-specific windows require a separately declared/versioned study.

## Windows: easiest way to run

Double-click **`optimizer/Run-Optimizer-Windows.bat`**. It opens a small menu for the prepared `ready-expanded` study:

1. Run/resume
2. Live progress
3. Graceful stop
4. Report
5. Exit

Choose **1**, then enter the **number of parallel runs (1–32)**; Enter reuses the previous choice (initially two). Each worker evaluates one configuration and its seeds sequentially. **There is no session time limit in the Windows launcher.** It runs until the remaining overall budget/trial limit is reached or you stop it. The controller runs in the background: closing the launcher/display leaves it working. Reopening attaches to an existing run; changing worker count requires stopping it first with **S** or menu option **3**, then resuming. Saved checkpoints and total spent time are preserved.

Concurrency and session stopping are launch controls, recorded in `launch-runtime.json` and its history. The frozen `config.json` remains unchanged for checkpoint compatibility; its legacy `max_session_hours: 2` is ignored by this Windows launch path. Direct `python -m optimizer run` uses the original frozen session policy; use the Windows launcher for the new controls.

A progress window now opens automatically when choosing **1**. To watch an existing run, double-click **`optimizer/Show-Progress-Windows.bat`**, or open a second launcher and choose **2**. The display refreshes every three seconds and shows completed configurations, active hours, each worker's seed, round, live sensors, checkpoint age, CPU time and RAM. Round counts normally update every 25 rounds; CPU time updates between checkpoints. **Q** closes only the display; **S** requests a graceful stop. This monitor reads existing files and does not start another optimizer.

The prepared study is `optimizer/runs/ready-expanded`, with parabolic grid decay and ten search coordinates. The old `ready-short` results/checkpoints are preserved separately; its spent time is deducted from this new study's training allowance, so both studies together still have at most six active tuning hours. Settings are frozen; to change them, create a different study as described below.

## Manual setup and commands

Use Python 3.10+ and install the dependencies into your preferred environment:

```powershell
python -m pip install -r optimizer/requirements.txt
```

Optuna is pinned to the verified 4.6.0 API. During implementation, dependencies were installed locally under ignored `optimizer/.deps/`; the package automatically uses that directory when present. This installation keeps the bundled runtime's NumPy unchanged. If using a different environment, install the requirements normally. Source/config/runtime fingerprints are captured at study initialization and must match at every resume/checkpoint; finish dependency setup before `init`.

On this Windows machine the known Python executable is:

```powershell
$py = 'C:/Users/hgtfh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $py -B -m optimizer init --config optimizer/config.example.yaml --study optimizer/runs/main
```

`init` only audits/fingerprints the checkout and creates the study directory. It does not start workers or a full simulation. Review the example YAML before initialization. Limits are **32 parameter configurations and six cumulative active wall hours for tuning**, including time already spent in the preceding study. Windows sessions have no additional time cap and use the chosen concurrency. Optional validation has a separate maximum of two total hours, for a combined tuning/validation ceiling of eight hours. Shutdown headroom is reserved inside the total limit. Other limits are 4 GiB study storage, 1 GiB RSS per worker, one hour per seed attempt, and at most two retries.

The previous `ready` study preserves the old initialization and cannot run against the updated source/config policy. To change settings, edit the example YAML and initialize a different path.

The target is a useful feasible incumbent within budget, not exhaustive optimization. You can stop and resume voluntarily; cumulative active time is preserved and idle time is not charged. Reaching the total limit prevents further tuning on that study. Only one validation study can be linked to a training study.

Manual commands from the repository root:

```powershell
# Foreground; Ctrl+C checkpoints workers and stops gracefully.
& $py -B -m optimizer run --study optimizer/runs/main

# Or background in a hidden window, with PID and logs.
./optimizer/launch.ps1 -Python $py -Study optimizer/runs/main -Workers 4

& $py -B -m optimizer status --study optimizer/runs/main
& $py -B -m optimizer stop --study optimizer/runs/main
& $py -B -m optimizer report --study optimizer/runs/main

# Resume the same study; already completed seeds/trials are not repeated.
& $py -B -m optimizer run --study optimizer/runs/main
```

Ubuntu uses the same CLI:

```bash
python3 -m pip install -r optimizer/requirements.txt
python3 -B -m optimizer init --config optimizer/config.example.yaml --study optimizer/runs/main
bash optimizer/launch.sh optimizer/runs/main
python3 -B -m optimizer status --study optimizer/runs/main
python3 -B -m optimizer stop --study optimizer/runs/main
python3 -B -m optimizer report --study optimizer/runs/main
```

The cross-platform implementation is tested on Windows; the Ubuntu launch script is supplied but was not executed on this host. Use a local disk, not a network-shared SQLite file.

## Search policy

Independent coordinates are alpha `[0.25,3]`, beta `[0,1.5]`, gamma `[0,1]`, Q `[0.1,60]` (log), tau_max `[4,32]`, rho_min `[0.05,0.4]`, rho_max `[0.4,0.9]`, theta `[0,1]`, load_density_weight `[0,1]`, and load_power `[1,4]`. These are exploratory domains, not proven optimal ranges. Theta spans no elite bonus through a full extra best-ant deposit. The calibrated load/density weight spans no penalty through a penalty comparable to energy at calibration; the exponent spans linear through quartic load sensitivity. Grid decay is fixed to **parabolic**, with multiplier `max(1-(distance/reach)^2,0)`: slow decay near the center and steeper decay farther out. Tau floor/initial value, the combined fitness formula, reference-memory policy, 40 ants, 10 feasibility retries, 40 calibration ants, live updates, physics and routing remain fixed. The physical evaporation schedule keeps its native T_max=3000 even in smoke tests.

The eight initial anchors are current D-ACO with parabolic decay, quarter heuristics, half heuristics, Q20/cap8, Q30/cap8, beta zero with theta/weight/power `0/0/1`, gamma zero with `0.5/0.5/3`, and both heuristics zero with `1/1/4`. All ten coordinates are suggested independently after anchors. SimpleACO is an external reference, never a D-ACO trial. Anchor runs are fresh; matched SimpleACO references are reused only when their fingerprints match. The new source epoch requires fresh SimpleACO references before trials. Twelve startup trials (including anchors) precede adaptive multivariate constrained TPE. A separately initialized random-search control is an additional campaign, not included in this eight-hour tuning/validation allowance; no optimizer advantage over random search is claimed.

Only full valid seed cohorts complete an Optuna trial. No 150/600-round proxy pruning is used. Early-death candidates retain their full measured service but receive a strictly positive workload constraint. Training recommendations rank feasible mean service; equal service uses energy as a tie-break. Smoke studies never produce a scientific best-config file.

## Persistence and failure behavior

One coordinator owns a kernel lock and is the sole Optuna SQLite writer. The Windows launcher accepts 1–32 workers; the original frozen config schema allows up to four. Each worker evaluates its cohort sequentially, with no nested process pool. Launch controls can affect adaptive suggestion order and compute timings, so their history is retained. A checkpoint saves the complete algorithm, residual energies, live set, trajectory, and Python/NumPy RNG states. Resume restores the last committed round; physical energy is not counted twice. Checkpoints are trusted local pickles.

Workers pause at round boundaries on STOP or coordinator ownership loss. A crashed coordinator releases its kernel lock; a new token prevents old workers from continuing against a new controller. Resume waits for prior workers to relinquish checkpoints. Hung workers get bounded termination/retries, and incomplete cohorts are excluded from recommendations. A single pathological round may exceed a budget before the parent monitor terminates it. Source/map/config/runtime changes refuse resume; create a new study rather than editing frozen JSON or extending a completed budget.

The service stop `no_feasible_tree_found` is not asserted to be physical disconnection. A separate radius-graph traversal records unreachable survivors at termination. A horizon endpoint is censored at 3000. Reports show seed-level standard errors and violation fractions without treating rounds as independent replicates. Timing is observational, not a controlled speed benchmark.

## Outputs and independent validation

Each study contains frozen JSON/YAML config, provenance and checkout audit, effective baseline parameters, reference cap, `study.db`, sampler state, manifests/status, per-seed `metrics.json`, compressed round CSVs, checkpoints, failures, cohort aggregates, trial/seed CSV/JSON exports, plots and `final-report.md`. A `best-feasible-config.yaml` is a **training recommendation only**; it never edits production defaults. Plots include service/energy with the cap, incumbent history, parallel coordinates, exploratory parameter associations (not causal importance), censoring endpoints, compute use and energy/depletion/entropy trajectories.

After training, initialize a frozen top-three holdout study:

```powershell
& $py -B -m optimizer validate --study optimizer/runs/main --output optimizer/runs/holdout --top 3
& $py -B -m optimizer run --study optimizer/runs/holdout
& $py -B -m optimizer report --study optimizer/runs/holdout
```

This uses the configured disjoint seeds 40/41/42, obtains fresh matched SimpleACO references, and evaluates exactly the frozen training shortlist. It does not refit or generate a new best-default recommendation from validation outcomes. New topologies are not generated automatically. Default promotion remains a separate decision.

## Small tests only

```powershell
& $py -B -m unittest discover -s optimizer/tests -v
```

The tests use only 2–20-round trajectories, ≤3 tiny configurations, and synthetic TPE objective values. They cover checkpoint equality, actual killed-worker recovery, graceful coordinator stop/resume, two-worker completion, constraints, reference fingerprints, historical short prefixes, strict config locking, reports and smoke isolation. This is infrastructure validation, not a scientific optimization run. See `implementation-review.md` and `smoke-test.log` for the implementation-time results.
