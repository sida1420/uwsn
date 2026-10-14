"""Read-only candidate diagnostics; no random draws or extra tree evaluations."""
from math import isclose, isfinite, log
from time import perf_counter

import numpy as np
from .tree_metrics import describe_tree, stats as _stats


class PoolObserver:
    """Wrap one algorithm instance and reset observations on each physical round.

    ``run(live, residual)`` returns ``(root, consumption, JSON-safe summary)``.
    ``close()`` restores the instance methods. Calibration evaluations count as
    work but never enter the search pool. No shared class/module is patched.
    """

    def __init__(self, algorithm):
        self.algorithm = algorithm
        self.clustering = algorithm.clustering
        self._originals = []
        self.active = False
        self._wrap(self.clustering, "create_clusters", self._clusters)
        self._wrap(algorithm.evaluator, "energy_consumption", self._evaluate)
        self._wrap(self.clustering, "post_round", self._post_round)
        name = "_transition_probabilities"
        if hasattr(self.clustering, name):
            self._wrap(self.clustering, name, self._transition)

    def _wrap(self, obj, name, handler):
        original = getattr(obj, name)
        owned = name in vars(obj)
        self._originals.append((obj, name, original, owned))
        def wrapped(*args, **kwargs):
            result = original(*args, **kwargs)
            if self.active:
                started = perf_counter()
                handler(result, args, kwargs)
                self.diagnostic_seconds += perf_counter() - started
            return result
        setattr(obj, name, wrapped)

    def close(self):
        for obj, name, original, owned in reversed(self._originals):
            if owned:
                setattr(obj, name, original)
            else:
                delattr(obj, name)
        self._originals.clear()

    def _stage(self):
        return ("calibration" if hasattr(self.algorithm, "references")
                and self.algorithm.references is None else "search")

    def _feedback(self):
        feedback = getattr(self.clustering, "feedback", None)
        return None if feedback is None else dict(
            best=float(feedback.best) if isfinite(feedback.best) else None,
            stagnation=int(feedback.stagnation), improvement_ema=float(feedback.improvement_ema),
            coefficient=float(feedback.coefficient()))

    def _clusters(self, result, args, kwargs):
        record = dict(attempt=len(self.attempts) + 1, stage=self._stage(),
                      constructed=result is not None, evaluated=False)
        if result is not None and result[0] is not None:
            heads, nodes, outliers = result
            chs = [int(i) for i in heads]
            distances = [self.algorithm.network.dist_matrix[i][j]
                         for n, i in enumerate(chs) for j in chs[n + 1:]]
            record.update(chs=chs, start=chs[0] if chs else None,
                          outliers=len(outliers), outlier_ids=list(map(int, outliers)),
                          coverage=1 - len(outliers) / max(len(self.live), 1),
                          inter_ch_distance=_stats(distances))
            record["initial_parents"] = {
                int(i): node.prev.id if node.prev is not None else None
                for i, node in nodes.items()}
        else:
            record["constructed"] = False
        self.attempts.append(record)

    def _evaluate(self, result, args, kwargs):
        consumption, total = result
        root, distances, base_distances = args[:3]
        attempt = self.attempts[-1] if self.attempts else {}
        attempt["evaluated"] = True
        record = {k: v for k, v in attempt.items() if k != "initial_parents"}
        finite = isfinite(total) and total > 0
        record.update(evaluation=len(self.records) + 1, stage=self._stage(),
                      feedback_before_observation=self._feedback(),
                      energy=float(total) if isfinite(total) else None,
                      positive_finite=finite, per_node_energy={
                          str(i): float(e) if isfinite(e) else None
                          for i, e in consumption.items()}, node_energy=_stats(list(consumption.values())))
        record.update(describe_tree(root, consumption, total, distances, base_distances,
            self.algorithm.evaluator.hparameter, self.algorithm.network.radius, self.live,
            record.get("chs", ()), attempt.get("initial_parents", {})))
        record["feasible_valid"] = bool(finite and all(record[key] for key in
            ("conservation_valid", "topology_valid", "all_live_present", "radius_valid")))
        attempt["feasible_valid"] = record["feasible_valid"]
        if record["stage"] == "search" and record["feasible_valid"]:
            self.stagnation = 0 if total < self.best else self.stagnation + 1
            self.max_stagnation = max(self.max_stagnation, self.stagnation)
            self.best = min(self.best, total)
            record["best_so_far"] = float(self.best)
            record["stagnation"] = self.stagnation
            record["search_index"] = 1 + sum(r["stage"] == "search" and r["feasible_valid"] for r in self.records)
        self.records.append(record)

    def _transition(self, result, args, kwargs):
        probabilities = np.asarray(result, dtype=float)
        n = len(probabilities)
        valid = bool(np.all(np.isfinite(probabilities)) and np.all(probabilities >= 0)
                     and (n == 0 or isclose(float(probabilities.sum()), 1.0, abs_tol=1e-10)))
        self.invalid_probabilities += not valid
        positive = probabilities[probabilities > 0]
        entropy = -float(np.sum(positive * np.log(positive))) / log(n) if n > 1 else 0.0
        strength = getattr(self.clustering, "last_exploration", None)
        if strength is None and len(args) >= 5 and n:
            c = args[4] * self.clustering.chaos[args[0]]
            strength = n * c / (1 + n * c)
        if isinstance(strength, (float, int, np.floating)):
            self.lambdas.append(float(strength))
        self.entropies.append(entropy)

    def _pheromone(self):
        tau = np.asarray(self.clustering.pheromone, dtype=float)
        live = np.asarray(self.live, dtype=int)
        values = tau[np.ix_(live, live)] if tau.ndim == 2 else tau[live]
        if tau.ndim == 2:
            values = values[~np.eye(len(live), dtype=bool)]
        values = values.ravel()
        if not len(values):
            return dict(count=0, floor_fraction=None, ceiling_fraction=None, concentration_cv=None)
        p = self.algorithm.params
        return dict(count=len(values), floor_fraction=float(np.mean(values <= p.tau_min)),
                    ceiling_fraction=float(np.mean(values >= p.tau_max)),
                    concentration_cv=float(values.std() / values.mean()), **_stats(values))

    def _post_round(self, result, args, kwargs):
        self.pheromone_after = self._pheromone()

    def run(self, live, residual):
        self.live = tuple(live)
        self.records, self.attempts, self.entropies, self.lambdas = [], [], [], []
        self.best, self.invalid_probabilities, self.diagnostic_seconds = float("inf"), 0, 0.0
        self.stagnation, self.max_stagnation = 0, 0
        self.pheromone_before = self._pheromone()
        self.pheromone_after = self.pheromone_before
        counters = ("total_clustering_attempts", "total_routing_attempts", "failed_clustering_attempts", "failed_routing_attempts")
        before = {name: getattr(self.algorithm, name, 0) for name in counters}
        self.active = True
        started = perf_counter()
        try:
            root, consumption = self.algorithm.plan_round(live, residual)
        finally:
            self.active = False
        runtime = perf_counter() - started
        plan_diagnostics = self.diagnostic_seconds
        started = perf_counter()
        pool = [r for r in self.records if r["stage"] == "search" and r["feasible_valid"]]
        sets = [set(r.get("chs", ())) for r in pool]
        diversity = [1 - len(a & b) / len(a | b) if a | b else 0.0
                     for i, a in enumerate(sets) for b in sets[i + 1:]]
        attempts = [a for a in self.attempts if a["stage"] == "search"]
        summary = dict(candidate_records=self.records, attempts_records=self.attempts,
                       energy=_stats([r["energy"] for r in pool]),
                       calibration_energy=_stats([r["energy"] for r in self.records if r["stage"] == "calibration" and r["positive_finite"]]),
                       physical_iteration=int(getattr(self.clustering, "iteration", 0)),
                       evaluation_count=len(self.records), calibration_evaluation_count=sum(r["stage"] == "calibration" for r in self.records),
                       search_evaluation_count=sum(r["stage"] == "search" for r in self.records),
                       feasible_count=len(pool), attempt_count=len(attempts),
                       feasibility_rate=len(pool) / len(attempts) if attempts else None,
                       calibration_attempt_count=len(self.attempts) - len(attempts),
                       failed_routing_attempts=sum(a["constructed"] and not a.get("feasible_valid", False) for a in attempts),
                       unique_ch_sets=len({frozenset(s) for s in sets}),
                       jaccard_diversity=float(np.mean(diversity)) if diversity else None,
                       outliers=_stats([r.get("outliers", 0) for r in pool]),
                       coverage=_stats([r.get("coverage", 0) for r in pool]),
                       best_so_far=[r["best_so_far"] for r in pool],
                       transition_entropy=_stats(self.entropies), effective_lambda=_stats(self.lambdas),
                       transition_count=len(self.entropies),
                       feedback_after_search=self._feedback(), max_stagnation=self.max_stagnation,
                       final_stagnation=self.stagnation,
                       effective_evaporation=_stats(getattr(self.clustering, "effective_rhos", ())),
                       invalid_probability_count=self.invalid_probabilities,
                       pheromone_before=self.pheromone_before, pheromone_after=self.pheromone_after,
                       selected_energy=float(sum(consumption.values())) if root is not None else None,
                       counter_deltas={name: getattr(self.algorithm, name, 0) - value for name, value in before.items()})
        summary_seconds = perf_counter() - started
        self.diagnostic_seconds += summary_seconds
        summary.update(runtime_seconds=runtime, summary_seconds=summary_seconds,
                       total_observer_seconds=runtime + summary_seconds,
                       plan_seconds=runtime, diagnostic_seconds=self.diagnostic_seconds,
                       diagnostic_inside_seconds=plan_diagnostics,
                       algorithm_seconds=max(0.0, runtime - plan_diagnostics))
        return root, consumption, summary
