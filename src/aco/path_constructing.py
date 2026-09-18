from evaluate import E_m
import random
from node import Node



def greedy_clustering(sensors, CHs, R_max, dist_matrix, residual_e):
    CH_nodes=[Node(idx,isCH=True) for idx in CHs]


    CHs_lookup=set(CHs)
    CHs_mapping={node.idx:i for i, node in enumerate(CH_nodes)}
    for i, sensos in enumerate(sensors):
        if i in CHs_lookup or residual_e[i]<=0:
            continue

        nearest=CHs[0]
        nearest_dist=dist_matrix[i][nearest]
        for j in CHs:
            dist=dist_matrix[i][j]
            if dist<nearest_dist:
                nearest_dist=dist
                nearest=j
             
        
        idx=CHs_mapping[nearest]
        if nearest_dist>R_max:
            return None
        node=Node(i)
        CH_nodes[idx].branches.append(node)
        node.set_parent(nearest)

    return CH_nodes


def direct_routing(sensors, CHs, R_max, base_dists, dist_matrix, residual_e):
    CH_nodes=greedy_clustering(sensors,CHs, R_max, dist_matrix, residual_e)
    if CH_nodes is None:
        return None
    base=Node(-1)

    for node in CH_nodes:
        dist=base_dists[node.idx]
        if dist<R_max:
            base.branches.append(node)
            node.set_parent(base.idx)
        else:
            return None
    return base


class ACO_routing:
    def __init__(self, n_nodes):
        self.n_nodes=n_nodes
        self.pheromone_matrix=[[0]*(n_nodes+1) for i in range(n_nodes)]
        self.alpha=0
        self.beta=0
        self.time_to_live=10
        self.local_heuristic_min=0
        self.local_heuristic_max=1
        self.base_residual_e=1e6
        self.k_1=1
        self.k_2=1
        self.k_3=1
        self.k_4=1
        self.k_5=1
        self.k_6=1
        self.k_7=1
        self.k_8=1
        self.k_9=1
        self.k_10=1
        self.k_11=1
        self.k_12=1
    
    def route(self,nodes, CHs, R_max, d0, base_pos, hopping_factor, base_dists, dist_matrix, residual_e):
        CH_nodes=clustering(nodes,CHs, R_max,dist_matrix,residual_e)
        if CH_nodes is None:
            return None
        base=Node(-1)

        