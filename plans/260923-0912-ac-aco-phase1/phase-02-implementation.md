# Phase 02: Implementation

## Todo

- [x] Create AC-ACO package and exports.
- [x] Implement finite/range-validated parameters with ten ants by default.
- [x] Implement adaptive chaotic schedules over internal iterations.
- [x] Implement seeded edge-pheromone CH construction and radius coverage repair.
- [x] Implement normalized energy-distance-load phase-1 cost.
- [x] Implement all-ant pheromone deposit, evaporation, and chaotic perturbation.
- [x] Build a compatible `Node` tree with safe sink-range default.
- [x] Correct CH energy classification in `Evaluator`.

## Success Criteria

- Selects unique live CHs deterministically for a fixed seed.
- Every live sensor lies within `radius` of its assigned CH.
- Current map returns a phase-1 CH solution without changing map dimensions or radius.
- Default adapter rejects physically invalid CH-to-sink edges until phase 2 exists.
- No file in the new package exceeds 200 lines.
