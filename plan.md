format:

ALGORITHMS:
2 differnet class structures for Clustering and Routing

example:
aco_routing
pso_clustering
aco_clustering

if the algorithm doesn't have memory (e.g. multi_hop_routing), just leave them as a function in `algorithms/routing.py`

new file structures:
algorithms/
    clustering/
        aco/
            aco.py
            parameters.py
            ...
        pso/
            pso.py
            parameters.py
            ...
        ac_aco/
            ac_aco.py
            parameters.py
            ...

    routing/
        ...
    base/
        base.py
    aco.py
    ac_aco.py
    pso.py
    clustering.py #general clustering
    routing.py #general routing


new class structures
```text
algorithms/clustering/.../
class ...Clustering(ClusteringAlgorithm):
    __init__()

    pre_round()
    create_clusters()
    post_round()
```
```text
algorithms/routing/.../
class ...Routing(RoutingAlgorithm):
    __init__()

    pre_round()
    create_routes()
    post_round()
```
```text
algorithms/
class ...(Algorithm):
    __init__()
    init_params()

    plan_round() -> root_node, energy_consumption
```





