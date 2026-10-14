"""One physical round through the production spawn worker; isolated new CSVs."""
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, str(ROOT / "src"))
from algorithms.ac_aco_v2_v6 import ACACO_V2_V6
from hparameter import HyperParameters
from network import NetworkInstance
from run import run_algorithm


def main():
    output = Path(__file__).resolve().parent / "smoke-output"
    output.mkdir(exist_ok=False)  # Never overwrite a prior smoke or production CSV.
    network = NetworkInstance.from_pickle(ROOT / "map.pkl")
    hp = HyperParameters()
    hp.T_max = 1  # Smoke-only limit; src/run.py still uses the production horizon.
    with ProcessPoolExecutor(max_workers=1, mp_context=get_context("spawn")) as pool:
        name, history = pool.submit(run_algorithm, ACACO_V2_V6, network, hp,
                                    24, output, "integration-smoke").result(timeout=60)
    assert name == "AC-ACO-V2-V6" and len(history) == 1
    result = dict(algorithm=name, seed=24, smoke_T_max=1, physical_rounds=len(history),
                  alive_nodes=int(history.iloc[0]["alive_nodes"]),
                  round_energy=float(history.iloc[0]["round_energy"]))
    (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
