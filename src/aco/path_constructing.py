from evaluate import E_m
import random
from node import Node

def make_path(num_CHs, start_node_idx, live_nodes, pheromone_matrix, dist_matrix, E_m_heuristic_matrix, residual_e, pheromone_w, beta, alpha):
    

    curr_node_idx=start_node_idx
    CH_list=[curr_node_idx]
    CH_set=set([curr_node_idx,])

    while len(CH_list)<num_CHs:
        allowed_nodes=[node_i for node_i in live_nodes if node_i not in CH_set]

        if len(allowed_nodes)==0:
            return None

        vals=[(
            pheromone_matrix[curr_node_idx][node_i]**pheromone_w
            *(residual_e[node_i]/dist_matrix[curr_node_idx][node_i])**beta
            * E_m_heuristic_matrix[curr_node_idx][node_i]
        ) for node_i in allowed_nodes]

        sum_vals=sum(vals)

        probs=[val/sum_vals for val in vals]
        probs=[prob+chaos[curr_node_idx]*alpha for prob in probs]
        # sum_probs=sum(probs)
        # probs=[prob/sum_probs for prob in probs]

        curr_node_idx=random.choices(allowed_nodes, weights=probs,k=1)[0]
        CH_list.append(curr_node_idx)
        CH_set.add(curr_node_idx)

    return CH_list

def clustering(nodes, CHs, R_max, dist_matrix, residual_e):
    CH_nodes=[Node(idx,isCH=True) for idx in CHs]

    tree=kdtree.KDTree(True,sorted(CHs, key=lambda idx: nodes[idx].x), sorted(CHs,key=lambda idx: nodes[idx].y))

    CHs_lookup=set(CHs)
    CHs_mapping={node.idx:i for i, node in enumerate(CH_nodes)}
    for i, node in enumerate(nodes):
        if i in CHs_lookup or residual_e[i]<=0:
            continue
        best,_=tree.nearest(nodes,i,None,1e9)
        
        idx=CHs_mapping[best]
        if dist_matrix[best][i]>R_max:
            return None
        node_node=Node(i)
        CH_nodes[idx].branches.append(node_node)
        node_node.set_parent(best)

    return CH_nodes


def network_config(nodes, CHs, R_max, d0, base_pos, hopping_factor, base_dists, dist_matrix, residual_e):
    CH_nodes=clustering(nodes,CHs, R_max, dist_matrix, residual_e)
    if CH_nodes is None:
        return None
    base=Node(-1)

    for node in CH_nodes:
        dist=base_dists[node.idx]
        if dist<R_max:
            base.branches.append(node)
            node.set_parent(base.idx)
        else:
            #list all nodes closer to base and in communication range
            candidates=[cnode for cnode in CH_nodes if cnode.idx!=node.idx and dist_matrix[node.idx][cnode.idx]<R_max and dist>base_dists[cnode.idx] and residual_e[cnode.idx]>0]

            if len(candidates)==0:
                # if dist<R_max:
                #     base.branches.append(node)
                #     node.set_parent(base.idx)

                return None
                # base.branches.append(node)
                # node.set_parent(base.idx)
                # continue

            sum_candidates_e=sum([residual_e[cnode.idx] for cnode in candidates])

            
            costs=[hopping_factor*sum_candidates_e/residual_e[cnode.idx]
                +(1-hopping_factor)*(dist_matrix[node.idx][cnode.idx]**2+base_dists[cnode.idx]**2)/base_dists[node.idx]**2 for cnode in candidates]

            optimal_node_i=0

            for i, cost in enumerate(costs):
                if costs[optimal_node_i]>cost:
                    optimal_node_i=i

            candidates[optimal_node_i].branches.append(node)
            node.set_parent(candidates[optimal_node_i].idx)

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

        