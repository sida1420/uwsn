from point import Point

import random
import pickle


def plot_map_3d(map_, save_path="map_3d.svg", show_ids=False):
    from visual import Visual
    sensors = map_["sensors"]
    sink = map_["base_pos"]

    width = map_["width"]
    height = map_["height"]
    depth = map_["depth"]

    visual = Visual(width, height, depth, sensors, sink)

    visual.save(save_path)


def gen(
    width,
    height,
    depth,
    num_sensors,
    energy,
    radius,
    base_pos=None,
    num_cluster_points=0,
    seed=None,
):
    if seed is None: seed = random.SystemRandom().randint(1, 99)
    if type(seed) is not int or not 1 <= seed <= 99:
        raise ValueError('map seed must be an integer from 01 to 99')
    rng = random.Random(seed)
    # Quy ước z là độ sâu:
    # z = 0 là mặt nước, z = depth là đáy.
    if base_pos is None:
        base_pos = Point(width / 2, height / 2, 0)

    def random_point():
        return Point(
            rng.uniform(0, width),
            rng.uniform(0, height),
            rng.uniform(0, depth),
        )

    sensors = [random_point() for _ in range(num_sensors)]

    # Tâm cụm cũng phải có đủ 3 tọa độ.
    cluster_points = [random_point() for _ in range(num_cluster_points)]

    if cluster_points:
        for i, sensor in enumerate(sensors):
            nearest = min(
                cluster_points,
                key=lambda point: abs(point - sensor),
            )

            # Kéo sensor về phía tâm cụm gần nhất.
            sensors[i] = sensor + (nearest - sensor) * rng.uniform(0, 0.5)

    return {
        "width": width,
        "height": height,
        "depth": depth,
        "base_pos": base_pos,
        "sensors": sensors,
        "init_energy": energy,
        "radius": radius,
        "seed": seed,
        "num_cluster_points": num_cluster_points,
    }


def new_map(seed=None, save_path="map.pkl", plot=True):
    map_ = gen(
        width=500,
        height=500,
        depth=500,
        num_sensors=100,
        energy=0.6,
        radius=200,
        num_cluster_points=0,
        seed=seed,
    )

    with open(save_path, "wb") as file:
        pickle.dump(map_, file)

    print(f"Map seed: {map_['seed']:02d}; saved to {save_path}")
    if plot: plot_map_3d(map_)

    return map_


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, help='Map seed from 01 to 99; omitted chooses randomly')
    parser.add_argument('--output', default='map.pkl')
    parser.add_argument('--no-plot', action='store_true')
    args = parser.parse_args()
    new_map(seed=args.seed, save_path=args.output, plot=not args.no_plot)
