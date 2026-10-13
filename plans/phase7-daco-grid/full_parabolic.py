"""Full trials for gentle-near, steep-far grid decay: 1-u^2.

Experimental adapter keeps production source fixed during existing trials.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys
import numpy as np
import full_run as study
from algorithms.clustering.d_aco.d_aco import Grid


class ParabolicGrid(Grid):
    def compute_density(self, live_sensors, residual_e=None):
        # The underlying overlap computation remains exactly the original grid.
        super().compute_density(live_sensors,residual_e)
        points = np.array([[p.x,p.y,p.z] for p in self.network.sensors])
        distance = np.linalg.norm(points[:,None,:]-self._center[None,:,:],axis=2)
        u = distance/(self.network.radius+self._cell_radius)
        self.F *= np.maximum(1.-u**2,0.)
        live = np.zeros(self.network.N)
        live[live_sensors] = 1.
        self.density = (self.F.T@live).reshape(self.density.shape)
        self.reset_loss()
        return self.density


class ParabolicDACO(study.DACO):
    def init_params(self):
        self._aco_params.density_decay = 'none'
        self._aco_params.density_profile = 'parabolic'
        super().init_params()
        self.clustering.grid = ParabolicGrid(self.network,self.params)


def main():
    seed = int(sys.argv[1])
    assert seed in study.SEEDS
    study.FOLDER.mkdir(parents=True,exist_ok=True)
    expected = study.provenance()
    expected['adapter_sha'] = sha256(Path(__file__).read_bytes()).hexdigest()
    expected['decays'] = ['parabolic']
    metadata = study.FOLDER/f'metadata_parabolic_{seed}.json'
    if metadata.exists():
        assert json.loads(metadata.read_text())==expected
    else:
        metadata.write_text(json.dumps(expected,indent=2))
    target = study.FOLDER/f'parabolic_{seed}.json'
    if target.exists():
        return
    network = study.NetworkInstance.from_pickle(study.ROOT/'map.pkl')
    study.DACO = ParabolicDACO
    print('START parabolic',seed,flush=True)
    row = study.run(network,'parabolic',seed)
    current = study.provenance()
    current['adapter_sha'] = sha256(Path(__file__).read_bytes()).hexdigest()
    current['decays'] = ['parabolic']
    assert current==expected
    row['provenance'] = expected
    target.write_text(json.dumps(row,indent=2))
    print('END parabolic',seed,row['completed_rounds'],row['FND'],row['termination_reason'],flush=True)


if __name__=='__main__':
    main()
