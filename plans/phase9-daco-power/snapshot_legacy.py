"""Preserve the pre-cleanup D-ACO solely for historical experiments."""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).parent/'archive'
manifest = FOLDER/'manifest.json'
if manifest.exists():
    raise SystemExit('Historical snapshot already exists; preserve it.')
FOLDER.mkdir(parents=True,exist_ok=True)
files = {
    'src/algorithms/d_aco.py':'legacy_daco_algorithm.py',
    'src/algorithms/clustering/d_aco/d_aco.py':'legacy_daco_clustering.py',
    'src/algorithms/clustering/d_aco/parameters.py':'legacy_daco_parameters.py',
}
hashes = {}
for source,target in files.items():
    body = (ROOT/source).read_text()
    hashes[source] = sha256((ROOT/source).read_bytes()).hexdigest()
    body = body.replace('from algorithms.clustering.d_aco.d_aco import DACOClustering',
                        'from legacy_daco_clustering import DACOClustering')
    body = body.replace('from algorithms.clustering.d_aco.parameters import DACOParameters',
                        'from legacy_daco_parameters import DACOParameters')
    (FOLDER/target).write_text(body)
manifest.write_text(json.dumps(dict(original_source_hashes=hashes,
    map_sha=sha256((ROOT/'map.pkl').read_bytes()).hexdigest()),indent=2))
