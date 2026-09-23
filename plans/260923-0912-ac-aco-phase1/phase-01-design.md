# Phase 01: Design

## Status

- [x] Read all 62 PPTX slides.
- [x] Extract equations for logistic chaos, adaptive rho/beta/chaos, transition probability, and fitness.
- [x] Map `M` to `num_ants=10` and distinguish it from simulator `T_max`.
- [x] Inspect `ClusteringAlgorithm`, `Simulator`, `Node`, `Evaluator`, and current ACO integration.
- [x] Confirm current map requires coverage repair when `radius=100`.

## Architecture

- `parameters.py`: validated immutable configuration.
- `adaptive.py`: logistic map and adaptive schedules.
- `optimizer.py`: construct, repair, score, and reinforce CH sets.
- `ac_aco.py`: repository adapter implementing `ClusteringAlgorithm`.
- `README.md`: equations, configuration, connection, caveats.

