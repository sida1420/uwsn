import argparse

from algorithms.ac_aco import ACACOClustering, ACACOParameters
from hparameter import HyperParameters
from network import NetworkInstance


def main():
    parser = argparse.ArgumentParser(description="Run one AC-ACO routing plan")
    parser.add_argument("--map", default="map.pkl", help="Network pickle path")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--ants", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=5)
    args = parser.parse_args()

    network = NetworkInstance.from_pickle(args.map)
    params = ACACOParameters(
        num_ants=args.ants,
        num_iterations=args.iterations,
        random_seed=args.seed,
    )
    algorithm = ACACOClustering(network, HyperParameters(), params)
    live_nodes = list(range(network.N))
    residual_e = [network.init_energy] * network.N
    algorithm.plan_round(live_nodes, residual_e)
    solution = algorithm.last_solution
    if solution is None:
        print("No feasible AC-ACO routing solution found.")
        return 1
    print(f"candidate evaluations: {params.num_ants * params.num_iterations}")
    print(f"target CHs: {solution.target_head_count}")
    print(f"selected CHs: {len(solution.cluster_heads)}")
    print(f"acoustic round energy: {solution.cost:.6f}")
    print(f"selected CH path length: {solution.path_length:.3f} m")
    print(f"CH ids: {list(solution.cluster_heads)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
