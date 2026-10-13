"""Full equal-scale energy + powered load/density trials, shared runner."""
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import sys
import full_run as study


def main():
    seed = int(sys.argv[1])
    assert seed in study.SEEDS
    name = 'power_100'
    params = replace(study.BASE,load_density_weight=1.)
    expected = study.provenance()
    expected['extra_config'] = {name:asdict(params)}
    expected['driver_sha'] = sha256(Path(__file__).read_bytes()).hexdigest()
    folder = study.FOLDER/'full'
    folder.mkdir(parents=True,exist_ok=True)
    metadata = folder/f'metadata_{name}_{seed}.json'
    if metadata.exists():
        assert json.loads(metadata.read_text())==expected
    else:
        metadata.write_text(json.dumps(expected,indent=2))
    target = folder/f'{name}_{seed}.json'
    if target.exists():
        return
    network = study.NetworkInstance.from_pickle(study.ROOT/'map.pkl')
    print('START',name,seed,flush=True)
    row = study.run(network,params,seed,name)
    current = study.provenance()
    current['extra_config'] = {name:asdict(params)}
    current['driver_sha'] = sha256(Path(__file__).read_bytes()).hexdigest()
    assert current==expected
    row['provenance'] = expected
    target.write_text(json.dumps(row,indent=2))
    print('END',name,seed,row['completed_rounds'],row['FND'],row['termination_reason'],flush=True)


if __name__=='__main__':
    main()
