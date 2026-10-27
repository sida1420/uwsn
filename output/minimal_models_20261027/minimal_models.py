"""Independent finite models for the NodeACO/DACO rationale.

Standard library only. No production imports, random numbers, optimizer,
routing decoder, calibration, or simulator. Fractions keep calculations exact.
Each model states its own assumptions; none establishes full DACO superiority.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from functools import lru_cache
from fractions import Fraction as F
from itertools import combinations, permutations, product
import json
from math import ceil
from pathlib import Path


def collection_cost(points, heads):
    """Every sensor reports to its nearest CH; cost is squared distance.

    CHs incur zero own-distance cost. No sink/relay/other energy terms.
    """
    return sum(min((x - points[h]) ** 2 for h in heads) for x in points)


def short_transition_model(gap=9):
    """Four sensors at 0,1,L,L+1; two CHs, first head fixed at 0."""
    assert gap >= 2
    points = (0, 1, gap, gap + 1)
    pairs = {pair: collection_cost(points, pair) for pair in combinations(range(4), 2)}
    next_cost = {j: pairs[(0, j)] for j in (1, 2, 3)}
    weights = {j: F(1, points[j]) for j in (1, 2, 3)}
    normalizer = sum(weights.values())
    probabilities = {j: w / normalizer for j, w in weights.items()}
    expected_inverse = sum(probabilities[j] * next_cost[j] for j in (1, 2, 3))
    expected_uniform = F(sum(next_cost.values()), 3)
    return dict(points=points, all_pairs=pairs, nearest_pair=(0, 1),
        nearest_pair_cost=pairs[(0, 1)], optimal_cost=min(pairs.values()),
        next_probabilities=probabilities, expected_inverse=expected_inverse,
        expected_uniform=expected_uniform)


def memory_model():
    """Hold the selected set, evaluation, and deposit amount fixed.

    This tests credit-assignment invariance, not search performance or runtime.
    """
    orders = list(permutations((0, 1, 2)))
    node_updates = [tuple(sorted(order)) for order in orders]
    edge_updates = [tuple(sorted(zip(order, order[1:]))) for order in orders]
    # For the line example, can additive node scores make every good pair
    # strictly better than both within-region pairs? Exhaust the small score box.
    good = ((0, 2), (0, 3), (1, 2), (1, 3))
    bad = ((0, 1), (2, 3))
    successes = []
    for scores in product((-1, 0, 1), repeat=4):
        if min(sum(scores[i] for i in pair) for pair in good) > max(
                sum(scores[i] for i in pair) for pair in bad):
            successes.append(scores)
    return dict(permutations=len(orders), distinct_node_updates=len(set(node_updates)),
        distinct_edge_updates=len(set(edge_updates)),
        additive_score_assignments_examined=3**4,
        additive_strict_separations=len(successes),
        explanation="The general additive impossibility also follows from opposing strict inequalities; enumeration is a finite check.")


def allocation_probabilities(populations=(6, 2), heads=4, mode="uniform"):
    """Exact sampling distribution, using counts instead of random trials.

    Each node supports only its own region (one-hot support). With equal energy
    and memory, per-node density is the number of unselected nodes in its region.
    The exponent is fixed to 1 so all path probabilities are rational.
    """
    states = {(0, 0): F(1)}
    for _ in range(heads):
        next_states = defaultdict(F)
        for chosen, probability in states.items():
            remaining = [populations[i] - chosen[i] for i in (0, 1)]
            if mode == "uniform":
                weights = remaining
            elif mode == "density":
                weights = [m*m for m in remaining]
            elif mode == "density_no_subtraction":
                weights = [remaining[i]*populations[i] for i in (0, 1)]
            else:
                raise ValueError(mode)
            denominator = sum(weights)
            for i, w in enumerate(weights):
                if not w:
                    continue
                update = list(chosen); update[i] += 1
                next_states[tuple(update)] += probability * F(w, denominator)
        states = dict(next_states)
    assert sum(states.values()) == 1
    return states


def density_model():
    """Two equal-area regions with 6 and 2 unit-reporting sensors.

    A region needs at least one local head. Work is balanced as evenly as possible
    within each region. The objective is maximum per-head reporting load.
    No relay, memory, spatial kernel, energy depletion, or parameter fitting.
    """
    feasible = {}
    for dense_heads in range(5):
        sparse_heads = 4 - dense_heads
        if 1 <= dense_heads <= 6 and 1 <= sparse_heads <= 2:
            feasible[(dense_heads, sparse_heads)] = max(ceil(F(6,dense_heads)), ceil(F(2,sparse_heads)))
    sampling = {}
    for mode in ("uniform", "density", "density_no_subtraction"):
        probabilities = allocation_probabilities(mode=mode)
        sampling[mode] = dict(probabilities=probabilities,
            expected_dense_heads=sum(F(state[0])*prob for state, prob in probabilities.items()),
            probability_no_sparse_head=sum(prob for state, prob in probabilities.items() if state[1] == 0))
    return dict(populations=(6, 2), CH_budget=4, feasible_loads=feasible,
        uniform_space_allocation=(2, 2), uniform_space_max_load=feasible[(2, 2)],
        optimal_allocations=[state for state, load in feasible.items() if load == min(feasible.values())],
        lower_bound=F(8, 4), optimal_max_load=min(feasible.values()), sampling=sampling)


def proximity_model(sensor=F(0)):
    """One sensor, five cell centers strictly inside a fixed radius of 2.

    Equal geometry/coverage; only the interior proximity factor changes.
    """
    centers = tuple(map(F, (-1, F(-1, 2), 0, F(1, 2), 1)))
    radius = F(2)
    flat = [F(1) for x in centers]
    proximity = [1 - ((x-sensor)/radius)**2 for x in centers]
    return dict(sensor=sensor, centers=centers, flat=flat, proximity=proximity,
        flat_maximizers=[x for x,w in zip(centers,flat) if w==max(flat)],
        proximity_maximizers=[x for x,w in zip(centers,proximity) if w==max(proximity)])


def actions(state):
    """One mandatory node S and three substitutable optional workers.

    Each served round costs S one unit, plus one optional duty:
    perform it at S for 2 extra units, or at one dense worker for 3 units.
    All four nodes start with six battery units. Whole-round energy feasibility
    is required. A round is impossible without S or without a legal duty choice.
    """
    possibilities = [(3, 0, 0, 0)]
    for i in (1, 2, 3):
        costs = [1, 0, 0, 0]; costs[i] = 3
        possibilities.append(tuple(costs))
    return [(i, c) for i, c in enumerate(possibilities) if all(e >= use for e,use in zip(state,c))]


def depletion_score(cost, state, densities):
    return sum(F(c, e)**2 / d for c,e,d in zip(cost,state,densities) if c)


def run_policy(rule, densities=(1, 3, 3, 3)):
    state=(6, 6, 6, 6); history=[]
    while actions(state):
        choices=actions(state)
        def score(item):
            action,cost=item
            if rule == "energy": return sum(cost)
            return depletion_score(cost,state,(1, 1, 1, 1) if rule == "relative" else densities)
        action,cost=min(choices,key=lambda item:(score(item),item[0]))
        before=state
        state=tuple(e-c for e,c in zip(state,cost))
        assert all(e>=0 for e in state)
        history.append(dict(action=action,before=before,cost=cost,after=state))
    return dict(rounds=len(history), total_spent=sum(sum(h["cost"]) for h in history),
        final_energy=state, history=history)


@lru_cache(None)
def exact_best_service(state):
    """Exhaust all legal choices, not only the policies being compared."""
    return max([0]+[1+exact_best_service(tuple(e-c for e,c in zip(state,cost)))
                    for _,cost in actions(state)])


def protection_model():
    policies={"energy_only":run_policy("energy"),
        "relative_only":run_policy("relative"),
        "relative_with_correct_redundancy":run_policy("weighted"),
        "relative_with_reversed_density":run_policy("weighted",(3, 1, 1, 1))}
    best=exact_best_service((6, 6, 6, 6))
    return dict(initial_energy=(6, 6, 6, 6), densities=(1, 3, 3, 3),
        policies=policies, all_policy_optimum=best, obligatory_node_upper_bound=6,
        reachable_states_exhausted=exact_best_service.cache_info().currsize,
        initial_scores={name:{str(i):depletion_score(cost,(6,6,6,6),density)
                       for i,cost in actions((6,6,6,6))} for name,density in
                       [("relative",(1,1,1,1)),("correct_redundancy",(1,3,3,3)),("reversed",(3,1,1,1))]})


def serializable(value):
    if isinstance(value,F):return dict(exact=str(value), decimal=float(value))
    if isinstance(value,dict):return {str(k):serializable(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [serializable(v) for v in value]
    return value


def report(results):
    line,mem,dens,kernel,protect=[results[k] for k in ("distance","memory","density","proximity","protection")]
    s=["# Independent minimal models of the NodeACO/DACO rationale", "",
       "These are separate finite models, implemented with Python's standard library and exact fractions. "
       "There are no imports from src/, no ACO search, no routing decoder, no random seeds, no calibration, "
       "and no fitted parameters. Each experiment changes one explicitly defined mechanism. "
       "Results establish properties of these simplified models, not superiority of full DACO.", "",
       "## 1. The nearest next CH can be the wrong clustering choice", "",
       "Four sensors lie at x = 0, 1, 9, 10. Choose two CHs; fix the first at 0. "
       "Every sensor's only cost is squared distance to its nearest head. There is no sink or inter-CH route.", "",
       "| CH locations | Collection cost |", "| --- | ---: |"]
    for pair,cost in line["all_pairs"].items():s.append(f"| {tuple(line['points'][i] for i in pair)} | {cost} |")
    s += ["",f"The nearest transition selects heads (0,1), costing {line['nearest_pair_cost']}; "
          f"a separated pair costs {line['optimal_cost']}. Under an inverse-distance second-choice rule, "
          f"the probability of choosing 1 is {line['next_probabilities'][1]} "
          f"({float(line['next_probabilities'][1]):.2%}). Expected collection cost is "
          f"{float(line['expected_inverse']):.3f}, versus {float(line['expected_uniform']):.3f} for uniform choice.", "",
          "**General calculation:** for positions (0,1,L,L+1), L >= 2, the close pair costs "
          "(L-1)^2 + L^2, whereas either distant second choice costs 2. Inverse-distance weighting "
          "gives the close second choice probability greater than 1/3, so its expected cost exceeds uniform "
          "selection throughout this family. Exact enumeration checked every integer L from 2 through 30.", "",
          "**Established:** transition distance and collection cost can prefer opposite CH choices. "
          "This isolates the user's clumping concern. **Not established:** edge ACO always clumps or "
          "node ACO always finds the best set; real routing or other costs could favor nearby heads.", "",
          "## 2. Node credit is order-invariant, but is not a complete model of set quality", "",
          f"Holding the selected set {{A,B,C}}, its reward, and deposit amount fixed, all {mem['permutations']} "
          f"selection orders give {mem['distinct_node_updates']} node-credit update and "
          f"{mem['distinct_edge_updates']} distinct directed-edge updates. The clustering objective above "
          "depends only on the head set, so this order dependence is artificial in this model. "
          "Node credit matches that symmetry. It also needs N credit entries rather than N(N-1) directed entries.", "",
          "A limitation can be proved too. To make good pair (0,9) score above bad pair (0,1) with additive "
          "node rewards requires a9 > a1. Making good pair (1,10) score above bad pair (9,10) requires "
          "a1 > a9. Both cannot hold. Enumeration over all 81 reward vectors in {-1,0,1}^4 finds no solution, "
          "consistent with the general contradiction. Context-dependent information is still needed.", "",
          "**Established:** alignment of node credit with a set objective and a limitation of unary credit. "
          "**Not established:** lower complete runtime or universally better search.", "",
          "## 3. A dense region needs more heads to equalize work", "",
          "There are two equal-area, noncommunicating regions. Six sensors report in the dense region and two "
          "in the sparse one. Four CHs are available, each region needs a local CH, and work is balanced "
          "within each region. Minimize the maximum number of reports assigned to a CH.", "",
          "| CH allocation: dense / sparse | Maximum reports per CH |", "| --- | ---: |"]
    for state,cost in dens["feasible_loads"].items():s.append(f"| {state[0]} / {state[1]} | {cost} |")
    s += ["", "Three heads in the dense region and one in the sparse region attain load 2, "
          "whereas two heads in each region give load 3. The lower bound is total work / heads = 8/4 = 2; "
          "the 3:1 allocation attains it. This is an optimality proof for the stipulated reporting-load model.", "",
          "### Does a density preference by itself implement this allocation?", "",
          "For this separate construction check, each sensor supports only its own region. With h heads "
          "already chosen there, its remaining density is n-h. Equal energy and pheromone are omitted. "
          "Select four distinct sensors with probabilities proportional to per-node density (exponent 1). "
          "All possible outcomes are summed exactly; there is no sampling error.", "",
          "| Selection rule | Expected dense-region heads | Probability of no sparse-region CH |",
          "| --- | ---: | ---: |"]
    for name,row in dens["sampling"].items():s.append(f"| {name} | {float(row['expected_dense_heads']):.4f} | {float(row['probability_no_sparse_head']):.2%} |")
    s += ["", "**Established:** denser regions warrant more CH capacity under equal per-report costs; density "
          "preference shifts allocations toward them. **Also established:** this preference alone does not "
          "guarantee the optimal allocation or service in both regions. An explicit feasibility rule or another "
          "mechanism is required in this local-service model. This is not a claim that full DACO drops outliers.", "",
          "## 4. Proximity resolves a flat coverage interior", "",
          "One sensor is at x=0. Five equally treated cell centers lie at -1,-1/2,0,1/2,1, all strictly inside "
          "radius 2. A flat coverage indicator gives weight 1 at every center. The sole change is multiplication "
          "by 1-(distance/2)^2.", "",
          "| Center | Flat weight | Proximity weight |", "| --- | ---: | ---: |"]
    for x,a,b in zip(kernel["centers"],kernel["flat"],kernel["proximity"]):s.append(f"| {x} | {a} | {b} |")
    s += ["", "The flat model has five tied maxima; proximity has a unique maximum at the sensor. "
          "For fixed radius R and distances 0 <= d1 < d2 < R, "
          "1-(d1/R)^2 > 1-(d2/R)^2. This proves the ordering for the whole interior, not only these points. "
          "With the sensor at x=1/4, the two nearest cell centers (0 and 1/2) tie; finite-grid uniqueness "
          "cannot be guaranteed when the sensor is off-center.", "",
          "**Established:** the localizing property you intended. **Not established:** improved lifetime.", "",
          "## 5. Protecting a truly indispensable node can extend service", "",
          "Four nodes each have six battery units. S is indispensable and must spend one unit per served round. "
          "Each round also needs one optional duty. Assigning it to S costs two more units; assigning it to "
          "any one of three interchangeable dense nodes costs that node three units. Thus using S is cheaper "
          "in total energy. Costs never depend on routing or geometry, and whole-round battery feasibility is required.", "",
          "Three decision rules are compared: minimize total energy; minimize sum of squared fractional drains; "
          "or minimize that same sum with density/redundancy divisors (1,3,3,3). There is no mixing coefficient. "
          "The last rule is also tested with the divisors incorrectly reversed to (3,1,1,1).", "",
          "| Rule | Served rounds | Energy spent | Final battery vector |", "| --- | ---: | ---: | --- |"]
    for name,r in protect["policies"].items():s.append(f"| {name} | {r['rounds']} | {r['total_spent']} | {r['final_energy']} |")
    s += ["",f"All legal action sequences were enumerated by dynamic programming over "
          f"{protect['reachable_states_exhausted']} reachable energy states. The optimum is "
          f"{protect['all_policy_optimum']} served rounds. Independently, S's mandatory unit per round gives "
          "an upper bound of six rounds. Correctly weighted protection attains this bound.", "",
          "**Why this extends beyond the selected numbers:** if an indispensable node has budget B "
          "and must spend u > 0 per served round, no policy can serve more than floor(B/u) rounds. "
          "A schedule that assigns all optional work to other nodes attains this bound whenever their "
          "combined usable capacity is sufficient. This proves the conditional benefit of avoiding optional "
          "load on that node; the score is separately shown to discover such a schedule in the finite example.", "",
          "The first decision explains the mechanism exactly: unweighted squared drains are 9/36 when "
          "S takes the extra duty, versus 10/36 when a dense worker takes it. With redundancy weighting, "
          "the latter becomes (1+9/3)/36 = 4/36, so the expensive duty moves to an interchangeable worker.", "",
          "**Established:** if low density correctly identifies fewer substitutes, protecting that node can "
          "extend service even while increasing energy per round. **Not established:** geometric density "
          "always identifies irreplaceability. Reversing that information in the same model shows the failure. "
          "The experiment isolates the penalty term, not the full calibrated DACO fitness.", "",
          "## What can be claimed", "",
          "The exact calculations support a mismatch between transition proximity and cluster service, "
          "order-invariant node credit for set decisions, density-proportional capacity in an equal-load model, "
          "localization by proximity, and a conditional benefit from protecting nodes with fewer substitutes. "
          "They do not prove that full DACO is optimal, that inverse density is an exact criticality measure, "
          "or that all components improve every deployment.", "",
          "These assumptions are deliberately visible and different from the full simulator. Use these models "
          "to justify individual design decisions; use the full simulator to measure their combined outcome.", "",
          "## Files and reproduction", "",
          "`minimal_models.py` is the standalone source; `test_minimal_models.py` contains independent checks. "
          "`exact_results.json` contains exact rational values, all finite-model results, and complete energy-policy histories. "
          "`verification.json` records the executed checks and source hashes. No production code was imported or changed.", "",
          "```powershell",
          "python -B -m unittest discover -s experiments -p test_minimal_models.py -v",
          "python -B experiments/minimal_models.py --output output/minimal_models_reproduction",
          "```"]
    return "\n".join(s)+"\n"


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True)
    results=dict(distance=short_transition_model(),memory=memory_model(),density=density_model(),
                 proximity=proximity_model(),proximity_off_grid=proximity_model(F(1,4)),
                 protection=protection_model())
    for gap in range(2,31):
        r=short_transition_model(gap)
        assert r["nearest_pair_cost"]>r["optimal_cost"]==2
        assert r["expected_inverse"]>r["expected_uniform"]
    (out/"exact_results.json").write_text(json.dumps(serializable(results),indent=2)+"\n",encoding="utf-8")
    (out/"MODEL_REPORT.md").write_text(report(results),encoding="utf-8")
    print(report(results))


if __name__=="__main__":main()
