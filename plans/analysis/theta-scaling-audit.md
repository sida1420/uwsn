# Theta source and scaling audit

`d_aco.py:deposit` requests `Q * energy_reference / fitness / num_ants` per ant and
`Q * energy_reference / fitness * theta` for the best set, depositing on each CH.
Both use the same cached fitness, in joules; energy_reference/fitness is dimensionless.
Evaporation/clamp occurs in pre_round before construction. Live per-ant clipping
occurs during search; the elite deposit follows in post_round. There is no second evaporation.
The literal theta is already a ratio to the full equal-quality ant batch, not one ant.
Elite/one-ant = theta*A; elite/batch = theta when all A ants contribute equal quality.
With fewer feasible ants, unequal costs, differing CHs and clipping the effective ratio varies.
Total requested mass also scales with rewarded CH count. Multiplying both fitness and reference
by a common unit scale leaves deposits unchanged; multiplying only fitness does not.

No normalization policy is promoted. Raw theta remains the reproducible control.
The accompanying 27-case table is an algebraic diagnostic, not a claim of geometry invariance.
N/ant-count physical scaling tests are separate research work; no 50/200-node lifetime runs occurred.
Transition entropy, requested/lost deposit, saturation and native counts are recorded per round.
