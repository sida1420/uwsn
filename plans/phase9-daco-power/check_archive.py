"""Verify archived baseline/max reference records against preserved code."""
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).parent
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(FOLDER/'archive'))
from legacy_daco_algorithm import DACO
from legacy_daco_parameters import DACOParameters
from network import NetworkInstance
from hparameter import HyperParameters

manifest = json.loads((FOLDER/'archive/manifest.json').read_text())
for seed in (15,16,17):
    for name in ('baseline','density_005'):
        row = json.loads((ROOT/'plans/phase8-daco-tuned/full'/f'{name}_{seed}.json').read_text())
        assert row['provenance']['map_sha']==manifest['map_sha']
        recorded = {k.replace('\\','/'):v for k,v in row['provenance']['source_hashes'].items()}
        for source,digest in manifest['original_source_hashes'].items():
            assert recorded[source]==digest
        for source,digest in recorded.items():
            if source not in manifest['original_source_hashes']:
                assert sha256((ROOT/source).read_bytes()).hexdigest()==digest,source
        params = DACOParameters()
        for key,value in row['parameters'].items():
            setattr(params,key,value)
        random.seed(seed)
        network = NetworkInstance.from_pickle(ROOT/'map.pkl')
        algorithm = DACO(network,HyperParameters(),params)
        residual = [network.init_energy]*network.N
        with redirect_stdout(StringIO()):
            for record in row['records'][:10]:
                _,costs = algorithm.plan_round(list(range(network.N)),residual)
                assert sum(costs.values())==record['energy']
                for i,cost in costs.items():
                    residual[i]-=cost
print('Archive hashes and first ten rounds match six completed full reference runs.')
