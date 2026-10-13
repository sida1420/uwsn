"""Run one independent seed pair; useful for concurrent lifetime validation."""
import json
from hashlib import sha256
from pathlib import Path
import sys

from long_run import ACACOParameters, NetworkInstance, ROOT, run


if __name__ == '__main__':
    seed = int(sys.argv[1])
    folder = Path(__file__).parent / 'long'
    prior = json.loads((folder.parent / 'results.json').read_text())
    hashes = {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
              for p in sorted((ROOT / 'src').rglob('*.py'))}
    assert hashes == prior['source_hashes'], 'Production source changed since the amplitude study'
    network = NetworkInstance.from_pickle(ROOT / 'map.pkl')
    names = ['calibrated_x2', 'calibrated_x1'] if seed % 2 else ['calibrated_x1', 'calibrated_x2']
    if len(sys.argv) > 2:
        assert sys.argv[2] in names
        names = [sys.argv[2]]
    for name in names:
        target = folder / f'{name}_seed{seed}.json'
        if target.exists():
            continue
        params = ACACOParameters(**prior['configs'][name]['parameters'])
        print('START', name, seed, flush=True)
        result = run(network, params, seed, name, folder)
        target.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print('END', name, seed, result['completed_rounds'], result['FND'], flush=True)
