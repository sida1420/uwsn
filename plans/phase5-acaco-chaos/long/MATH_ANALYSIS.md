# Why increasing chaos can help this AC-ACO implementation

Historical scope: these measurements used the frozen per-round pheromone sampler. Production now reads live deposits from earlier ants. The conditional transition-mixture identity still holds, but candidates are dependent and the independent-sampling order-statistic argument is not exact for the live sampler. See [the live balance study](../../phase5-acaco-balance/README.md) for matched-state comparisons after this change.

This is a derivation from the current code and a controlled empirical check. It explains a plausible mechanism for the observed energy improvement; it does not prove that every increase improves energy or lifetime. The [long-run report](README.md) contains the paired lifetime results. No production chaos default is changed by these experiments.

After pheromone calibration, removing chaos raised frozen-state energy by 5.801%, compared with 17.333% under the legacy parameter scale. Doubling chaos still improved the calibrated 150-round energy by .463% on average across three seeds. The calibration changes deposit size, evaporation and bounds together, so these controls show an interaction with the overall calibration rather than identifying one parameter as the cause. The transition-mixture identity below holds under both scales; the baseline probabilities being mixed have changed.

The completed follow-up finds a .164% mean energy saving through 1400 rounds. Mean first-node death moves from 1494.333 to 1499.333 rounds, with paired changes of 0, -2 and +17. Mean full-survivor service falls from 2184.667 to 2167.667 rounds, a .778% regression; paired changes are -23, -29 and +1. Thus the observed energy benefit does not justify promoting doubled chaos as a lifetime improvement. Current bounds [.05,.30] remain in production.

Implementation sources: [clustering and probabilities](../../../src/algorithms/clustering/ac_aco/ac_aco.py), [ant orchestration](../../../src/algorithms/ac_aco.py), [physical energy evaluator](../../../src/evaluate.py). All formulas below use these implemented rules.

## 1. Chaos is an exact mixture with uniform sampling

For a given source CH, let `n` be the number of available candidates and `p_j` the normalized pheromone/heuristic probability of candidate `j`. The implementation adds the same scalar `c = strength * chaos[source]` to every candidate:

$$q_j(c)=\frac{p_j+c}{1+nc}=(1-\lambda)p_j+\frac{\lambda}{n},\qquad \lambda=\frac{nc}{1+nc}.$$

Thus increasing strength increases a **uniform exploration mixture**, conditional on the same optimizer state. The first CH is already sampled uniformly; this expression applies to subsequent CH selections.

$$\frac{d\lambda}{dc}=\frac{n}{(1+nc)^2}>0,\qquad
\frac{dq_j}{dc}=\frac{1-np_j}{(1+nc)^2}.$$

Candidates with below-uniform baseline probability gain probability. Above-uniform candidates lose probability. Rankings remain unchanged, while their differences contract:

$$q_i-q_j=\frac{p_i-p_j}{1+nc}.$$

At an identical state, doubling strength gives

$$\lambda_2=\frac{2\lambda_1}{1+\lambda_1},\qquad
q_j(2c)-\frac1n=\frac{1}{1+\lambda_1}\left(q_j(c)-\frac1n\right).$$

For example, with `n=90`, logistic value `.6` and strength `.05`, `nc=2.7` and `lambda=.729730`. Doubling strength raises lambda to `.843750`. Deviation from uniform falls from `.270270` to `.156250` times the original baseline deviation. Doubling amplitude therefore does not double exploration; the effect has diminishing returns and depends strongly on candidate count.

The earlier trajectory diagnostics averaged lambda about `.770` for current chaos and `.883` for doubled chaos. These averages involve different adaptive histories and hypothetical source distributions; the exact doubling identity applies to individual matched states, not to those two averages.

For interpreting a reasonable strength range, invert the identity:

$$s=\frac{\lambda}{nz(1-\lambda)},\qquad z=\text{chaos[source]}.$$

With `n=90` and `z=.6`, uniform-mixture fractions `.8` and `.9` correspond to strengths `.074074` and `.166667`. Nominal strength is not itself an exploration percentage. A fixed amplitude also mixes more strongly on larger networks; these tuned bounds should not be treated as topology-independent constants.

## 2. The baseline strongly favors nearby CHs

The implemented unnormalized weight is

$$w_j=\tau_{ij}^{\alpha}\,e_j^{\beta}\,d_{ij}^{-\beta\omega}\,E_m(d_{ij})^{-\gamma}.$$

Here `e_j` is residual energy, `omega` is `distance_weight`, and `E_m=E_tx+E_rx+E_da`. Both the explicit distance term and the acoustic energy term penalize distant candidates. Holding pheromone and residual energy fixed, the exact local distance elasticity is

$$-\frac{d\log w}{d\log d}=\beta\omega+
\gamma\frac{E_{tx}}{E_m}\left(k+\frac{d}{1000}\log a\right),$$

because `E_tx(d)=C*(d/1000)^k*a^(d/1000)`. With the current positive exponents, every term is nonnegative. The raw beta schedule rises sharply from approximately 1 to approximately 5 around iteration 1500, making the explicit distance penalty much stronger late in the run.

For equal pheromone and residual energy, compare candidates 50 m and 200 m from the current CH. The production evaluator gives `E_m(50)=0.0000355972691 J` and `E_m(200)=0.0002729283743 J`. With gamma=omega=1, the closer candidate's baseline weight is **30.668 times** larger at beta=1, and **7851.126 times** larger at beta=5. This is an illustration using two distances, not the measured distribution over all candidates.

The CH sequence is a construction order, not the actual physical routing path. Favoring a short step to the next CH can produce many CHs in one region. That local preference need not minimize the final tree's reception, aggregation and relay costs. Uniform mixing gives remote regions a larger chance to receive a CH, which can reduce the burden subsequently faced by the shared router.

## 3. Coverage explains when the mixture helps

Let `H` be an available subset of `h` nodes whose selection would cover a poorly covered region. Summing the probabilities gives

$$q(H)=(1-\lambda)p(H)+\lambda\frac{h}{n},\qquad
\frac{dq(H)}{d\lambda}=\frac{h}{n}-p(H).$$

Increasing chaos improves the probability of selecting that region **if the baseline underweights it**, `p(H)<h/n`. This condition is essential. A well-targeted heuristic can instead lose useful preference when mixing increases.

In a simplified model with constant independent probability `q(H)` over `K` choices, the chance of missing the region is `(1-q(H))^K`, which decreases as `q(H)` increases. For exactly uniform selection of `K` distinct CHs from `N` nodes, the exact miss probability is

$$P(\text{no CH in }H)=\frac{\binom{N-h}{K}}{\binom{N}{K}}.$$

The actual sequential sampler removes selected nodes and changes its source, so the independent approximation is not an exact prediction for this implementation. Both expressions explain the direction of the coverage mechanism under their stated assumptions.

Observed clustering outliers fell from 5.063 to 4.572 per round in the earlier 150-round comparison. Outliers are nodes outside all CH communication radii. They still participate in routing and are served; these are coverage counts, not packet loss or discarded sensors.

## 4. The objective depends on the low-cost tail

AC-ACO selects the lowest-cost feasible tree from up to 40 ants. Conditional on a fixed round state, candidates sample the same probability model; pheromone deposits are not reflected in the round's probability snapshot. If feasible candidate costs have CDF `F_s(E)` and 40 independent feasible candidates are obtained, then

$$P(E_{best}>E)=(1-F_s(E))^{40},\qquad
\mathbb E[E_{best}]=\int_0^\infty(1-F_s(E))^{40}\,dE.$$

Stronger chaos helps selection when it improves the low-cost tail at the energies relevant to this minimum. Higher entropy or lower mean candidate cost alone does not establish that. Late failures can leave fewer than 40 feasible candidates; then, conditional on the count and independent conditional feasible costs, the exponent is the actual candidate count. The ten attempts per ant impose a finite search budget.

Let `f` be the fixed-state probability that one attempt produces a feasible tree, and let `A=10`. Under independent attempts, one ant succeeds with probability `h=1-(1-f)^A`; the expected number of feasible candidates is `40h`. Thus increasing feasibility from `.05` to `.10` would increase expected candidates from `16.051` to `26.053`, without changing the 40-ant budget. These illustrative feasibility values are not measurements. More generally, using the conditional feasible-energy CDF `F`, the probability that none of the 40 ants produces a route costing at most `E` is

$$P(\text{no candidate}\le E)=[1-hF(E)]^{40}.$$

This exposes two potential benefits: improving feasibility `h`, and improving the feasible low-energy tail `F(E)`. Increasing chaos guarantees neither, but reduced spatial clustering can improve both. The long-run report measures actual feasible candidate counts and attempts after iteration 1500.

The matched-state probe restores the current-chaos seed-6 physical and optimizer checkpoints, doubles only transition strength, and samples 400 candidates for each factor with the same RNG seed. Pheromone, energy, logistic values, beta and cost window are held fixed. No deposits or optimizer evolution occur between samples. This isolates transition mixing; the full trajectories additionally change pheromone evolution and future states. All these probe candidates were feasible. The next-round beta values for checkpoints 600, 1499 and 1501 are approximately 1, 3 and 4.999818, respectively.

<!-- PROBE_TABLE_BEGIN -->
| Completed checkpoint | Factor | Mean candidate energy (J) | Empirical expected best of 40 (J) | Mean outliers | Mean CH pair distance (m) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 600 | 1.0 | 0.018144373 | 0.015651759 | 4.9100 | 311.808 |
| 600 | 2.0 | 0.017996195 | 0.015743482 | 4.5950 | 313.509 |
| 1499 | 1.0 | 0.019136835 | 0.016271718 | 5.8375 | 308.419 |
| 1499 | 2.0 | 0.018812734 | 0.016189654 | 4.8225 | 312.242 |
| 1501 | 1.0 | 0.019258399 | 0.016334099 | 5.6800 | 310.249 |
| 1501 | 2.0 | 0.018909420 | 0.016061968 | 4.7875 | 314.256 |
<!-- PROBE_TABLE_END -->

The empirical expected minimum is calculated exactly for sampling 40 times from the empirical distribution, not by selecting one lucky group of 40. For sorted sample costs `E_(i)`, `i=0..M-1`, its value is

$$\sum_{i=0}^{M-1}E_{(i)}\left[\left(1-\frac{i}{M}\right)^{40}-\left(1-\frac{i+1}{M}\right)^{40}\right].$$

At checkpoint 600, doubled chaos lowers mean candidate cost but slightly raises the estimated best-of-40 cost by .586%. At checkpoints 1499 and 1501, it lowers both, with estimated best-of-40 improvements of .504% and 1.666%, respectively. At 1501, the fraction of candidates at or below the current-chaos 10th-percentile cost rises from 10% to 14.25%. These observations support a better low-cost tail near the stronger late-beta locality, while the 600 result shows why a universal claim would be wrong. There are only 400 samples per state and one checkpoint trajectory; no statistical significance is established. Adjacent checkpoints do not isolate beta by themselves because residual and optimizer states also change.

## 5. Pheromone disturbance also flattens preferences

The second chaos mechanism adds a common source-row offset after evaporation and accumulated ant deposits, before the elite deposit. For two positive pre-offset values `a>b`,

$$\frac{d}{dc}\frac{a+c}{b+c}=\frac{b-a}{(b+c)^2}<0.$$

Thus the offset reduces pheromone ratios toward 1, while the elite deposit subsequently reinforces selected edges. The earlier frozen-state ablation found removing transition chaos increased energy by 6.581%; removing pheromone disturbance increased it by only .087%. Those controls support transition mixing as the main observed early mechanism, rather than proving its dominance at all ages.

For a conservative shared-edge recurrence, let `D=Q/E_ref` bound all-ant deposits and the elite deposit separately:

$$\tau_{t+1}\le(1-\rho)(\tau_t+D)+c+D,
\quad \tau_*\le\frac{(2-\rho)D+c}{\rho}.$$

The logistic update has `z<=r/4` for values in `[0,1]`. At doubled maximum strength `.6`, `r=3.61`, reference route cost `.015 J`, `Q=.01` and minimum evaporation `.1`, this envelope is `18.081667`, below `tau_max=20`. The reference route cost is a scenario, not a guaranteed lower bound; actual floor and ceiling occupancy must still be measured. The lifetime report supplies those observations.

## 6. Energy savings do not imply longer life

Total tree energy and first-node death are different objectives:

$$E_{total}(t)=\sum_i E_i(t),\qquad
T_{FND}=\min_i\inf\left\{T:\sum_{t=1}^{T}E_i(t)\ge e_i(0)\right\}.$$

A lower sum can still exhaust one heavily used relay earlier. Greater CH dispersion can improve coverage without removing a relay bottleneck near the base. In addition, `q_j >= lambda/n`: even a depleted node with baseline probability approaching zero retains a positive CH-selection probability. Increasing exploration therefore weakens the protection supplied by the residual-energy heuristic as well as weakening the distance bias. The final selection minimizes total energy and has no explicit minimax-depletion constraint.

The round-1400 checkpoints demonstrate the objective tradeoff. Mean total energy falls from 22.375407325 J to 22.338751565 J across seeds. Yet node 65's residual energy falls from .297619 J to .292228 J in seed 6, and from .300493 J to .292961 J in seed 7. In seed 8 it rises from .296040 J to .300746 J. Saving total energy therefore does not uniformly preserve the node that later controls connectivity.

Full-survivor service can also end while many sensors retain energy if a required connection disappears or the finite greedy routing search fails. On this map, node 48 has only two communication neighbors within the 200 m radius: node 33 at 91.519 m and node 65 at 185.485 m. In the current-chaos seed-6 trajectory, node 33 dies at completed round 1510; node 65 dies at 2192, disconnecting surviving node 48. Service stops after 2192 successful rounds while 98 nodes are alive. Once both neighbors die, no CH sampler can reconnect node 48. This is a physical connectivity limit for serving every survivor, not an all-node-death time. Hence the paired FND and service-duration results must govern any lifetime claim.

Increasing chaos indefinitely sends `lambda` toward 1 and suppresses useful residual-energy and pheromone preferences. These experiments establish neither an optimal amplitude nor a requirement for a chaotic logistic sequence specifically: positive uniform mixing itself explains the probability mechanism. Different maps, constant disturbances, other schedules and larger amplitudes require separate comparisons.
