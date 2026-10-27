# Independent minimal models of the NodeACO/DACO rationale

These are separate finite models, implemented with Python's standard library and exact fractions. There are no imports from src/, no ACO search, no routing decoder, no random seeds, no calibration, and no fitted parameters. Each experiment changes one explicitly defined mechanism. Results establish properties of these simplified models, not superiority of full DACO.

## 1. The nearest next CH can be the wrong clustering choice

Four sensors lie at x = 0, 1, 9, 10. Choose two CHs; fix the first at 0. Every sensor's only cost is squared distance to its nearest head. There is no sink or inter-CH route.

| CH locations | Collection cost |
| --- | ---: |
| (0, 1) | 145 |
| (0, 9) | 2 |
| (0, 10) | 2 |
| (1, 9) | 2 |
| (1, 10) | 2 |
| (9, 10) | 145 |

The nearest transition selects heads (0,1), costing 145; a separated pair costs 2. Under an inverse-distance second-choice rule, the probability of choosing 1 is 90/109 (82.57%). Expected collection cost is 120.073, versus 49.667 for uniform choice.

**General calculation:** for positions (0,1,L,L+1), L >= 2, the close pair costs (L-1)^2 + L^2, whereas either distant second choice costs 2. Inverse-distance weighting gives the close second choice probability greater than 1/3, so its expected cost exceeds uniform selection throughout this family. Exact enumeration checked every integer L from 2 through 30.

**Established:** transition distance and collection cost can prefer opposite CH choices. This isolates the user's clumping concern. **Not established:** edge ACO always clumps or node ACO always finds the best set; real routing or other costs could favor nearby heads.

## 2. Node credit is order-invariant, but is not a complete model of set quality

Holding the selected set {A,B,C}, its reward, and deposit amount fixed, all 6 selection orders give 1 node-credit update and 6 distinct directed-edge updates. The clustering objective above depends only on the head set, so this order dependence is artificial in this model. Node credit matches that symmetry. It also needs N credit entries rather than N(N-1) directed entries.

A limitation can be proved too. To make good pair (0,9) score above bad pair (0,1) with additive node rewards requires a9 > a1. Making good pair (1,10) score above bad pair (9,10) requires a1 > a9. Both cannot hold. Enumeration over all 81 reward vectors in {-1,0,1}^4 finds no solution, consistent with the general contradiction. Context-dependent information is still needed.

**Established:** alignment of node credit with a set objective and a limitation of unary credit. **Not established:** lower complete runtime or universally better search.

## 3. A dense region needs more heads to equalize work

There are two equal-area, noncommunicating regions. Six sensors report in the dense region and two in the sparse one. Four CHs are available, each region needs a local CH, and work is balanced within each region. Minimize the maximum number of reports assigned to a CH.

| CH allocation: dense / sparse | Maximum reports per CH |
| --- | ---: |
| 2 / 2 | 3 |
| 3 / 1 | 2 |

Three heads in the dense region and one in the sparse region attain load 2, whereas two heads in each region give load 3. The lower bound is total work / heads = 8/4 = 2; the 3:1 allocation attains it. This is an optimality proof for the stipulated reporting-load model.

### Does a density preference by itself implement this allocation?

For this separate construction check, each sensor supports only its own region. With h heads already chosen there, its remaining density is n-h. Equal energy and pheromone are omitted. Select four distinct sensors with probabilities proportional to per-node density (exponent 1). All possible outcomes are summed exactly; there is no sampling error.

| Selection rule | Expected dense-region heads | Probability of no sparse-region CH |
| --- | ---: | ---: |
| uniform | 3.0000 | 21.43% |
| density | 3.3968 | 42.97% |
| density_no_subtraction | 3.5159 | 55.69% |

**Established:** denser regions warrant more CH capacity under equal per-report costs; density preference shifts allocations toward them. **Also established:** this preference alone does not guarantee the optimal allocation or service in both regions. An explicit feasibility rule or another mechanism is required in this local-service model. This is not a claim that full DACO drops outliers.

## 4. Proximity resolves a flat coverage interior

One sensor is at x=0. Five equally treated cell centers lie at -1,-1/2,0,1/2,1, all strictly inside radius 2. A flat coverage indicator gives weight 1 at every center. The sole change is multiplication by 1-(distance/2)^2.

| Center | Flat weight | Proximity weight |
| --- | ---: | ---: |
| -1 | 1 | 3/4 |
| -1/2 | 1 | 15/16 |
| 0 | 1 | 1 |
| 1/2 | 1 | 15/16 |
| 1 | 1 | 3/4 |

The flat model has five tied maxima; proximity has a unique maximum at the sensor. For fixed radius R and distances 0 <= d1 < d2 < R, 1-(d1/R)^2 > 1-(d2/R)^2. This proves the ordering for the whole interior, not only these points. With the sensor at x=1/4, the two nearest cell centers (0 and 1/2) tie; finite-grid uniqueness cannot be guaranteed when the sensor is off-center.

**Established:** the localizing property you intended. **Not established:** improved lifetime.

## 5. Protecting a truly indispensable node can extend service

Four nodes each have six battery units. S is indispensable and must spend one unit per served round. Each round also needs one optional duty. Assigning it to S costs two more units; assigning it to any one of three interchangeable dense nodes costs that node three units. Thus using S is cheaper in total energy. Costs never depend on routing or geometry, and whole-round battery feasibility is required.

Three decision rules are compared: minimize total energy; minimize sum of squared fractional drains; or minimize that same sum with density/redundancy divisors (1,3,3,3). There is no mixing coefficient. The last rule is also tested with the divisors incorrectly reversed to (3,1,1,1).

| Rule | Served rounds | Energy spent | Final battery vector |
| --- | ---: | ---: | --- |
| energy_only | 2 | 6 | (0, 6, 6, 6) |
| relative_only | 4 | 15 | (0, 3, 3, 3) |
| relative_with_correct_redundancy | 6 | 24 | (0, 0, 0, 0) |
| relative_with_reversed_density | 4 | 15 | (0, 3, 3, 3) |

All legal action sequences were enumerated by dynamic programming over 45 reachable energy states. The optimum is 6 served rounds. Independently, S's mandatory unit per round gives an upper bound of six rounds. Correctly weighted protection attains this bound.

**Why this extends beyond the selected numbers:** if an indispensable node has budget B and must spend u > 0 per served round, no policy can serve more than floor(B/u) rounds. A schedule that assigns all optional work to other nodes attains this bound whenever their combined usable capacity is sufficient. This proves the conditional benefit of avoiding optional load on that node; the score is separately shown to discover such a schedule in the finite example.

The first decision explains the mechanism exactly: unweighted squared drains are 9/36 when S takes the extra duty, versus 10/36 when a dense worker takes it. With redundancy weighting, the latter becomes (1+9/3)/36 = 4/36, so the expensive duty moves to an interchangeable worker.

**Established:** if low density correctly identifies fewer substitutes, protecting that node can extend service even while increasing energy per round. **Not established:** geometric density always identifies irreplaceability. Reversing that information in the same model shows the failure. The experiment isolates the penalty term, not the full calibrated DACO fitness.

## What can be claimed

The exact calculations support a mismatch between transition proximity and cluster service, order-invariant node credit for set decisions, density-proportional capacity in an equal-load model, localization by proximity, and a conditional benefit from protecting nodes with fewer substitutes. They do not prove that full DACO is optimal, that inverse density is an exact criticality measure, or that all components improve every deployment.

These assumptions are deliberately visible and different from the full simulator. Use these models to justify individual design decisions; use the full simulator to measure their combined outcome.

## Files and reproduction

`minimal_models.py` is the standalone source; `test_minimal_models.py` contains independent checks. `exact_results.json` contains exact rational values, all finite-model results, and complete energy-policy histories. `verification.json` records the executed checks and source hashes. No production code was imported or changed.

```powershell
python -B -m unittest discover -s experiments -p test_minimal_models.py -v
python -B experiments/minimal_models.py --output output/minimal_models_reproduction
```
