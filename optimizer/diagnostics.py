"""Physical accounting, connectivity and non-invasive native observers."""
from contextlib import contextmanager
import math, random
import psutil
from optimizer.storage import read
from algorithms.d_aco import DACO

@contextmanager
def observe(algorithm):
    """Observers restore every method before checkpointing; no RNG calls added."""
    counters=dict(evaluations=0,choices=0,entropy_sum=0.,updates=0,clipped=0,
                  requested=0.,lost=0.,repeated_ch_sets=0)
    originals=[];sets=set()
    def wrap(obj,name,factory):
        original=getattr(obj,name);originals.append((obj,name))
        setattr(obj,name,factory(original))
    def energy(original):
        def run(*args,**kwargs):
            result=original(*args,**kwargs);counters['evaluations']+=1;return result
        return run
    def clusters(original):
        def run(*args,**kwargs):
            result=original(*args,**kwargs)
            if result and result[0] is not None:
                key=tuple(sorted(result[0]));counters['repeated_ch_sets']+=int(key in sets);sets.add(key)
            return result
        return run
    def deposit(original):
        def run(chs,fitness,energy_reference,per_ant=True):
            if chs and fitness is not None and fitness>0:
                p=algorithm.params;amount=p.Q*energy_reference/fitness
                amount=amount/p.num_ants if per_ant else amount*p.theta
                for node in chs:
                    lost=max(0.,algorithm.clustering.pheromone[node]+amount-p.tau_max)
                    counters['updates']+=1;counters['clipped']+=int(lost>1e-12)
                    counters['requested']+=amount;counters['lost']+=lost
            return original(chs,fitness,energy_reference,per_ant)
        return run
    original_choices=random.choices
    def choices(population,weights=None,**kwargs):
        if weights is not None:
            total=sum(weights)
            probs=[w/total for w in weights if w>0]
            counters['choices']+=1;counters['entropy_sum']-=sum(p*math.log(p) for p in probs)
        return original_choices(population,weights=weights,**kwargs)
    wrap(algorithm.evaluator,'energy_consumption',energy)
    wrap(algorithm.clustering,'create_clusters',clusters)
    if isinstance(algorithm,DACO): wrap(algorithm.clustering,'deposit',deposit)
    random.choices=choices
    try: yield counters
    finally:
        random.choices=original_choices
        for obj,name in originals: delattr(obj,name)

def owner_alive(folder,token):
    if token is None: return True
    if (folder/'STOP').exists(): return False
    try:
        owner=read(folder/'owner.json')
        process=psutil.Process(owner['pid'])
        return owner['token']==token and process.create_time()==owner['created'] and process.is_running() and process.status()!=psutil.STATUS_ZOMBIE
    except (OSError,ValueError,psutil.Error): return False

def tree_metrics(root,costs):
    ids=set();groups=dict(CH=0.,relay=0.,member=0.);stack=[root]
    while stack:
        node=stack.pop();stack.extend(node.nxts)
        if node.id==-1: continue
        if node.id in ids: raise ValueError('Duplicate node in selected tree')
        ids.add(node.id);groups['CH' if node.isCH else 'relay' if node.isRelay else 'member']+=costs[node.id]
    if ids!=set(costs): raise ValueError('Selected tree does not cover consumption nodes')
    return groups

def reachable(network,live):
    """Certificate only for survivors disconnected in the physical radius graph."""
    remaining=set(live);seen={i for i in live if network.base_dists[i]<=network.radius};queue=list(seen)
    while queue:
        i=queue.pop()
        adjacent={j for j in remaining-seen if network.dist_matrix[i][j]<=network.radius}
        seen.update(adjacent);queue.extend(adjacent)
    return sorted(seen),sorted(remaining-seen)

