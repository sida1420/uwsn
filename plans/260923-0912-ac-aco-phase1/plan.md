---
title: "AC-ACO phase 1 clustering"
description: "Implement PPTX-derived adaptive chaotic ACO cluster-head selection and connect it to the UWSN simulator."
status: complete
priority: P1
effort: 5h
branch: main
tags: [feature, algorithms, metaheuristic, clustering]
created: 2026-09-23
---

# AC-ACO Phase 1 Plan

## Overview

Add an importable `src/algorithms/ac_aco` package based on slides 25-45 of
`IT4906_WSN_final.pptx`. Scope is cluster-head selection and cluster assignment;
multi-hop routing remains phase 2.

## Phases

| # | Phase | Status | Link |
|---|---|---|---|
| 1 | Model and integration design | Complete | [phase 01](./phase-01-design.md) |
| 2 | AC-ACO implementation | Complete | [phase 02](./phase-02-implementation.md) |
| 3 | Tests, documentation, review | Complete | [phase 03](./phase-03-validation.md) |

## Decisions

- `num_ants=10`: ten candidate CH sets per simulation round.
- Edge pheromone follows `tau[i][j]`; the ordered ant path is decoded to an unordered CH set.
- Ten ants and five internal iterations evaluate 50 candidates per clustering run.
- Keep the repo acoustic energy model. Do not import the deck's 2D radio model.
- Enforce member-to-CH radius with deterministic coverage repair.
- Sink-range enforcement is safe by default; direct-to-sink simulation is explicit opt-in until phase 2 multi-hop exists.
