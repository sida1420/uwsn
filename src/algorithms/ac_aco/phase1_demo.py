import argparse

from algorithms.ac_aco import ACACOClustering, ACACOParameters
from hparameter import HyperParameters
from network import NetworkInstance


def main():
    parser = argparse.ArgumentParser(description="Run AC-ACO phase-1 clustering")
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
    cluster_heads = algorithm.select_cluster_heads(live_nodes, residual_e)
    solution = algorithm.last_solution
    if solution is None:
        print("No phase-1 clustering solution found.")
        return 1
    max_member_distance = max(
        network.dist_matrix[node_id][ch_id]
        for node_id, ch_id in solution.assignments.items()
    )
    print(f"candidate evaluations: {params.num_ants * params.num_iterations}")
    print(f"target CHs: {solution.target_head_count}")
    print(f"ACO-selected CHs: {len(solution.aco_heads)}")
    print(f"repair-added CHs: {len(cluster_heads) - len(solution.aco_heads)}")
    print(f"selected CHs after coverage repair: {len(cluster_heads)}")
    print(f"objective cost: {solution.cost:.6f}")
    print(f"max member-to-CH distance: {max_member_distance:.3f} m")
    print(f"CH ids: {cluster_heads}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
