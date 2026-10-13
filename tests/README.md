# Maintained regression tests

These checks target production code and do not import historical experiment drivers.
Run `python -B -m unittest discover -s tests -v` from the repository root.

Coverage: algorithm RNG isolation/checkpointing, reproducible map generation and
run names, D-ACO load/density fitness and geometric references, grid decay and
live deposits, PSO search/state behavior, and AC-ACO equations, calibrated bounds
and vectorized selection. Fixtures exercise synthetic networks or compare paired
instances; they avoid hardcoded energy totals from an old random map.

The optimizer's controller, sampling, report export, map snapshots and recovery
checks live in `optimizer/tests/`. Run
`python -B -m unittest discover -s optimizer/tests -v` separately.
