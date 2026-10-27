# Reproduce the rationale experiments

Run commands from `C:/Users/hgtfh/Code/uwsn/review_uwsn` with the bundled Python. Use a new result directory for a new campaign; the runner refuses to overwrite an existing manifest.

```powershell
$rationalePython = 'C:/Users/hgtfh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $rationalePython -B -m unittest discover -s tests -p 'test_d_aco*.py' -v

# Reproduce using the exact frozen sources; this creates a fresh result folder.
& $rationalePython -B output/daco_rationale_20261027/source_snapshot/daco_rationale.py --output output/daco_rationale_reproduction

# Recompute diagnostics and plots from the completed cohort.
& $rationalePython -B experiments/diagnose_daco_termination.py output/daco_rationale_reproduction
& $rationalePython -B experiments/analyze_daco_rationale.py output/daco_rationale_reproduction
```

The frozen runner imports its adjacent `src/` snapshot. `manifest.json` records source hashes, parameters, Python, and NumPy. `maps/` contains explicit coordinates and seeds. `inputs/` identifies every paired variant run, `jobs/` stores histories and endpoints, and `logs/` contains worker output.

The current analyzer can find the existing plotting dependencies in `tmp/plot_deps`. NumPy and matplotlib must be available to render plots on another machine. The first run's controller completed the scientific measurements without matplotlib; the separate analyzer subsequently generated and visually checked the plots using the existing local plotting dependencies. This did not rerun or alter the simulations.

Two workers ran concurrently. CPU and wall times are measured observations on this machine, not portable speed guarantees. All variants receive 40 ants, 40 calibration starts, and at most ten construction attempts per ant; actual feasibility and evaluation counts can differ.

The shortened horizon changes the evaporation timescale as well as limiting observation. Lower initial battery energy accelerates deaths. Preserve these settings when reproducing these numbers; a larger or production-scale campaign is a different study.

`analysis_script.py` and `termination_diagnostic_script.py` preserve the analysis versions beside these results. The primary maintained entry points are in `experiments/`.
