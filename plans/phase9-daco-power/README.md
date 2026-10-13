# D-ACO unified powered fitness

Completed: all 15 new full trials. [RESULTS.md](RESULTS.md) contains the
comparison with six completed historical references. Selected default weight
0.25 gives mean first death 1896.7 and service 2318.0, up 14.37% and 5.81%
from the old baseline, at 0.60% more energy over equal all-alive rounds.
The old max reference still has longer lifetime at higher energy cost;
the new policy is a tradeoff, not a universal improvement.

Active implementation replaces CV/max penalties and legacy objective/deposit
modes with one fitness. Pheromone is always live. Existing grid decay options
remain. Load means evaluated consumption divided by pre-round residual energy.

`P = mean_i [(consumption_i / residual_i)^p / max(grid_density_i, epsilon)]`

`F = total_energy + weight * E_ref * P / P_ref`

The combined load/density term is calibrated as one quantity, not separated
into independent load and density objectives. The selected default is p=2,
weight=0.25, reference_memory=0.8. The initial prototype used weight=0.10.
One throwaway batch of up to 40 ants estimates initial mean E and P without
physical energy, pheromone deposits, or schedule advancement. It is recorded
separately and included in runtime. Score references remain fixed through each
physical round; each successful ant deposits immediately using its cached F.
The best-ant bonus uses that same cached F and reference, with only its bonus
multiplier changed. Deposits are `Q * E_ref / F / num_ants`, elite `theta * Q * E_ref / F`.
Evaporation occurs once before ants, then their live deposits and the elite bonus.

After the physical round, mean observed E and P update the references:
`ref_new = ref_previous^0.8 * ref_observed^0.2`, implemented in log space.
The discarded calibration costs no simulated energy but is not free computation.

Full tests: three paired seeds 15/16/17 on the current map, for energy-only live
feedback, linear-load p=1, powered p=2 at weights 0.10 and 0.25. One batch of 40
ants per physical round, through normal termination or 3000 rounds. An additional
weight-1.0 squared-load trial tests equal typical energy and penalty scales.
Earlier
baseline and max-penalty full runs remain historical reference controls; their
source is frozen under archive and first-ten-round replay is checked for all six.

Removed from production: fitness_mode, deposit_mode, elite_per_ant,
coverage_strength, energy_weight, load_weight, density_load_weight,
density_load_kappa, CV selection branches, and max-depletion fitness functions.
Historical runners explicitly import the archive instead of silently using new
production semantics. No AC-ACO or sibling uwsn source is changed in this phase.
