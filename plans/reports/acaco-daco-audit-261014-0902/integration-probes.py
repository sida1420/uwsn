"""Tiny diagnostic fixtures; no production source, map or configuration writes."""
import ast
import contextlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
import pandas as pd
from algorithms.clustering.clustering import build_clusters
from algorithms.routing.routing import dropping_member_multi_hop_routing
from evaluate import Evaluator
from hparameter import HyperParameters
from network import NetworkInstance
from node import Node
from point import Point
from simulate import Simulator
from map_gen import gen


def main():
    hp = HyperParameters()
    evaluator = Evaluator(hp)
    net = NetworkInstance([Point(100, 0, 0)], Point(0, 0, 0), .00001, 100, 1, 1, 200)
    sink, head = Node(-1), Node(0, isCH=True)
    sink.add_next(head)
    head.set_previous(sink)
    costs, total = evaluator.energy_consumption(sink, net.dist_matrix, net.base_dists)
    assert total == 2*evaluator.E_tx(100)
    class UnderfundedFixture:
        name = 'underfunded-fixture'
        def plan_round(self, live, residual):
            return sink, costs
    simulator = Simulator(net, hp)
    with contextlib.redirect_stdout(io.StringIO()):
        history = simulator.run(UnderfundedFixture(), verbose=False)
    assert len(history) == 1 and history['alive_nodes'].iloc[0] == 0

    points = [Point(2, 0, 0), Point(2.1, .6, 0), Point(1.3, .9, 0), Point(.6, .4, 0)]
    small = NetworkInstance(points, Point(0, 0, 0), 1, 3, 1, 1, .9)
    live = list(range(4))
    ch, nodes, outliers = build_clusters(live, live, small.dist_matrix, small.radius)
    routed = dropping_member_multi_hop_routing(ch, nodes, live, outliers,
        small.dist_matrix, small.base_dists, [1.]*4, small.radius)
    hops = [small.dist_matrix[i][i+1] for i in range(3)] + [small.base_dists[3]]
    assert max(hops) <= small.radius and routed is None

    notebook = json.loads((ROOT/'src/analyze.ipynb').read_text(encoding='utf-8'))
    function = None
    for cell in notebook['cells']:
        source = ''.join(cell.get('source', []))
        if cell['cell_type'] == 'code' and source.startswith('def mean_alive_percentage_curve'):
            function = ast.parse(source).body[0]
    assert function is not None
    frames = [pd.DataFrame({'round': [0, 1, 2], 'alive_nodes': [100, 99, 98]}),
              pd.DataFrame({'round': [0, 1, 2, 3], 'alive_nodes': [100, 99, 98, 97]})]
    namespace = {'np': np, 'runs': [{'algo': 'fixture', 'history': f} for f in frames]}
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<notebook-function>', 'exec'), namespace)
    curve = namespace['mean_alive_percentage_curve']('fixture').tolist()
    assert curve == [100., 99., 98., 48.5]

    kwargs = dict(width=500, height=500, depth=500, num_sensors=5000, energy=.6, radius=200, seed=7)
    uniform = gen(**kwargs)['sensors']
    normal = gen(**kwargs, distribution='normal')['sensors']
    result = dict(empty_ch_cost=total, empty_ch_tx_packet_equivalents=2,
        underfunded=dict(initial_energy=net.init_energy, reported_energy=float(history['round_energy'].iloc[0]),
            completed_rounds=len(history), alive_after=int(history['alive_nodes'].iloc[0])),
        nonmonotone_connected_path=dict(hop_lengths=hops, router_returned_none=routed is None),
        notebook=dict(actual=curve, terminal_survivor_carry_example_last=97.5,
            caution='After stop, surviving nodes are censored, not simulated at later times.'),
        map_test_drift=dict(uniform_mean_z=float(np.mean([p.z for p in uniform])),
            explicit_normal_mean_z=float(np.mean([p.z for p in normal]))))
    (Path(__file__).parent/'integration-probes.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
