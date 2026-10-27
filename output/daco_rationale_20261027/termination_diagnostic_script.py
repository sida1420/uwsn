"""Replay two saved runs to distinguish physical disconnection from search failure."""
import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser();parser.add_argument("output",type=Path)
    out=parser.parse_args().output.resolve()
    spec=importlib.util.spec_from_file_location("frozen_run",out/"source_snapshot/daco_rationale.py")
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    results=[]
    for variant in ["full","energy_only"]:
        saved=json.loads((out/"jobs"/f"uniform_37_101_{variant}.json").read_text())
        net=m.make_network(m.gen(*m.CONFIG["size"],m.CONFIG["nodes"],m.CONFIG["initial_energy"],
            m.CONFIG["radius"],seed=37,distribution="uniform"))
        hp=m.HyperParameters();hp.T_max=m.CONFIG["horizon"]
        a=m.Variant(net,hp,variant,101)
        residual=[net.init_energy]*net.N;live=list(range(net.N));events=[]
        def reached(nodes):
            nodes=set(nodes);seen={i for i in nodes if net.base_dists[i]<=net.radius};queue=list(seen)
            while queue:
                i=queue.pop()
                for j in nodes-seen:
                    if net.dist_matrix[i][j]<=net.radius:seen.add(j);queue.append(j)
            return seen
        with contextlib.redirect_stdout(io.StringIO()):
            for t in range(hp.T_max):
                tree,costs=a.plan_round(live,residual)
                if tree is None:break
                assert abs(sum(costs.values())-saved["history"][t]["nominal_energy"])<1e-12
                before=live.copy()
                for i,c in costs.items():residual[i]=max(0.,residual[i]-c)
                live=[i for i in live if residual[i]>0]
                dead=set(before)-set(live)
                if dead:
                    reachable_after=reached(live)
                    events.append(dict(round=t+1,dead=sorted(dead),alive=len(live),
                        remaining_disconnected=sorted(set(live)-reachable_after)))
        assert t==saved["completed_rounds"]
        results.append(dict(variant=variant,completed_rounds=t,live_at_failure=len(live),
            physically_sink_reachable=len(reached(live)),
            remaining_disconnected=sorted(set(live)-reached(live)),
            death_events=events,residual=residual))
        print(variant,results[-1]["completed_rounds"],"rounds; alive",len(live),
              "physically reachable",len(reached(live)),flush=True)
    m.dump(out/"termination_replay.json",results)


if __name__=="__main__":main()
