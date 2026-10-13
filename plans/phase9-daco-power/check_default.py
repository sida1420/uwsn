"""Check promoted defaults against the explicit full-tested power_025 config."""
from contextlib import redirect_stdout
from dataclasses import asdict
from io import StringIO
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).parent
sys.path.insert(0,str(ROOT/'src'))
from algorithms.d_aco import DACO
from algorithms.clustering.d_aco.parameters import DACOParameters
from network import NetworkInstance
from hparameter import HyperParameters

for seed in (15,16,17):
    row = json.loads((FOLDER/'full'/f'power_025_{seed}.json').read_text())
    assert asdict(DACOParameters())==row['parameters']
    random.seed(seed)
    network = NetworkInstance.from_pickle(ROOT/'map.pkl')
    a = DACO(network,HyperParameters())
    residual = [network.init_energy]*network.N
    with redirect_stdout(StringIO()):
        for record in row['records'][:10]:
            _,costs = a.plan_round(list(range(network.N)),residual)
            assert sum(costs.values())==record['energy']
            assert a.references.energy==record['energy_reference']
            assert a.references.penalty==record['penalty_reference']
            for i,cost in costs.items():
                residual[i]-=cost
print('Promoted defaults match full-tested parameters and all three ten-round replays exactly.')
