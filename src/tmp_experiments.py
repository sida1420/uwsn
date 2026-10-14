"""One-off experiment batch. Run from any directory:

    python src/tmp_experiments.py --dry-run
    python src/tmp_experiments.py

Each configuration runs all algorithms in run.py once. The original map.pkl
is preserved; generated maps go in runs/experiment_maps and CSVs in runs.
"""

import argparse
from itertools import product
import os
from pathlib import Path
import pickle

from map_gen import gen
from point import Point


ROOT = Path(__file__).resolve().parents[1]
MAP_SIZES = [(300, 300, 300), (500, 500, 500), (800, 800, 800)]
SENSOR_COUNTS = [50, 100, 200]


def configurations(current):
    baseline_size = (current["width"], current["height"], current["depth"])
    baseline_count = len(current["sensors"])
    distribution = current["distribution"]
    cluster_points = current["num_cluster_points"] if distribution == "clustered" else 0
    baseline_done = distribution == "uniform" or (
        distribution == "clustered" and cluster_points == 5
    )

    configs = [
        (size, count, distribution, cluster_points)
        for size, count in product(MAP_SIZES, SENSOR_COUNTS)
        if not (baseline_done and size == baseline_size and count == baseline_count)
    ]
    # Distribution comparison uses only the current size and sensor count.
    normal = (baseline_size, baseline_count, "normal", 0)
    if normal not in configs:
        configs.append(normal)
    return configs


def configuration_name(config):
    (width, height, depth), count, distribution, cluster_points = config
    name = f"{width}_{height}_{depth}_{count}_{distribution}"
    if distribution == "clustered":
        name += f"_{cluster_points}clusters"
    return name


def run_batch(current, configs, seed):
    # The existing runner uses relative output paths and multiprocessing spawn.
    # Agg keeps this unattended batch from opening plot windows in its workers.
    os.environ["MPLBACKEND"] = "Agg"
    from run import main as run_experiment

    previous_cwd = Path.cwd()
    os.chdir(ROOT)
    try:
        map_dir = ROOT / "runs" / "experiment_maps"
        map_dir.mkdir(parents=True, exist_ok=True)
        for index, config in enumerate(configs, start=1):
            size, count, distribution, cluster_points = config
            width, height, depth = size
            # Preserve the sink's relative position when resizing the field.
            sink = current["base_pos"]
            base_pos = Point(
                sink.x * width / current["width"],
                sink.y * height / current["height"],
                sink.z * depth / current["depth"],
            )
            name = configuration_name(config)
            generated = gen(
                width=width, height=height, depth=depth, num_sensors=count,
                energy=current["init_energy"], radius=current["radius"],
                base_pos=base_pos, distribution=distribution,
                num_cluster_points=cluster_points, seed=seed,
            )
            map_path = map_dir / f"{name}_seed{seed:02d}.pkl"
            with map_path.open("wb") as file:
                pickle.dump(generated, file)
            print(f"\n[{index}/{len(configs)}] {name}", flush=True)
            run_experiment(map_path=str(map_path), seed=seed)
    finally:
        os.chdir(previous_cwd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print configurations only")
    parser.add_argument("--seed", type=int, help="Map/run seed, 1-99; defaults to current map seed")
    args = parser.parse_args()
    with (ROOT / "map.pkl").open("rb") as file:
        current = pickle.load(file)
    seed = current["seed"] if args.seed is None else args.seed
    if not 1 <= seed <= 99:
        parser.error("seed must be between 1 and 99")

    configs = configurations(current)
    print(f"{len(configs)} configurations; one run per algorithm per configuration; seed {seed:02d}")
    print(f"Initial energy: {current['init_energy']}; radius: {current['radius']} m")
    for config in configs:
        print(f"  {configuration_name(config)}")
    if not args.dry_run:
        run_batch(current, configs, seed)


if __name__ == "__main__":
    main()
