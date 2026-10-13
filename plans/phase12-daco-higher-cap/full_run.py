"""Full deposit/bound ablations using the verified phase-11 observer."""
from dataclasses import replace
from hashlib import sha256
import importlib.util
from pathlib import Path

FOLDER=Path(__file__).resolve().parent
PRIOR=FOLDER.parent/'phase11-daco-concentration/full_run.py'
spec=importlib.util.spec_from_file_location('phase11_runner',PRIOR)
trial=importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)
trial.FOLDER=FOLDER
trial.CONFIGS={
    'deposit_4x_cap32':replace(trial.BASE,Q=20.,tau_max=32.),
    'deposit_6x_cap8':replace(trial.BASE,Q=30.,tau_max=8.),
    'deposit_6x_cap32':replace(trial.BASE,Q=30.,tau_max=32.),
}
prior_provenance=trial.provenance

def provenance():
    return dict(**prior_provenance(),driver_sha=sha256(Path(__file__).read_bytes()).hexdigest())

trial.provenance=provenance

if __name__=='__main__':
    trial.main()
