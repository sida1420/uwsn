# Current changes in review_uwsn

AC-ACO now defaults to `energy_cost_exponent=0.1`, previously 1.
Its transition log weight includes `-gamma * log(E_m)`; this change
reduces that term tenfold. For a candidate whose hop cost is ten times
another's, its relative E_m weight becomes `10^-0.1 = 0.794`, previously
`10^-1 = 0.1`, holding other terms equal. Physical energy evaluation is
unchanged. The separate `(residual_energy / distance)^beta` term remains.

The [AC-ACO paper](https://www.techscience.com/cmc/v84n3/63163/html)
uses gamma for the E_m exponent in equation 20, but calls gamma=0.1 a
chaos disturbance factor in its simulation description. Consequently,
0.1 here implements the requested weak energy-cost heuristic; the paper's
terminology does not establish a consistent mapping of every parameter.

D-ACO in this checkout already uses one batch of up to 40 ants per
physical round, computes density once, and updates pheromone once after
candidate evaluation. Up to ten attempts per ant are feasibility retries.
There is no inner optimization iteration to remove.

Historical balance experiments explicitly retain exponent 1. Their
energy and lifetime measurements do not measure the new exponent 0.1.

## Density-aware load fitness proposal

For an evaluated tree, let `e_i` be each live sensor's consumption,
`r_i` its residual energy before the round, and `d_i` the count of other
live sensors within communication radius. A possible protective cost is

`P = max_i [(e_i / r_i) * (1 + kappa / (1 + d_i))]`.

This penalizes relative depletion most strongly for sparse sensors,
including relays and ordinary members. Count neighbors before construction;
D-ACO's remaining grid coverage depends on the chosen CH sequence and is
not a stable measure of a sensor's alternatives. Low density is only a
proxy: a sensor with many neighbors can still be a critical bridge.

Normalize P across candidate trees before mixing it with normalized total
energy. Both kappa and its objective weight need independent experiments;
this proposal is not enabled in production. It changes selection and
reinforcement after evaluation, which can guide later searches, but adds
no local search operator. A separate bounded CH-swap experiment would test
whether proposals improve at an equal evaluation or runtime budget.
