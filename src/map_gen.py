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
    num_cluster_points=5,
    seed=None,
    distribution="normal",
):
    distribution = distribution.lower()
    if distribution not in {"normal", "clustered", "uniform"}:
        raise ValueError("distribution must be 'normal', 'clustered', or 'uniform'")
    if min(width, height, depth) <= 0:
        raise ValueError("map dimensions must be positive")
    if distribution == "clustered" and (
        type(num_cluster_points) is not int or num_cluster_points < 1
    ):
        raise ValueError("clustered distribution requires a positive integer cluster count")
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

    def bounded_normal(mean, spread, limit, underwater=False):
        # Reject out-of-bounds draws instead of piling sensors onto map edges.
        while True:
            value = rng.gauss(mean, spread)
            if (0 < value if underwater else 0 <= value) and value <= limit:
                return value

    if distribution == "normal":
        if not (0 <= base_pos.x <= width and 0 <= base_pos.y <= height
                and 0 <= base_pos.z <= depth):
            raise ValueError("normal distribution requires the sink inside the map bounds")
        # Sink-centered Gaussian: one sixth of each dimension as the standard
        # deviation, with depth stretched by 1.5. Truncate to the water volume;
        # a surface sink therefore has all sensors below it.
        sensors = [
            Point(
                bounded_normal(base_pos.x, width / 6, width),
                bounded_normal(base_pos.y, height / 6, height),
                bounded_normal(base_pos.z, depth / 6 * 1.5, depth, underwater=True),
            )
            for _ in range(num_sensors)
        ]
    else:
        sensors = [random_point() for _ in range(num_sensors)]

    # Tâm cụm cũng phải có đủ 3 tọa độ.
    cluster_points = (
        [random_point() for _ in range(num_cluster_points)]
        if distribution == "clustered" else []
    )

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
        "distribution": distribution,
        "num_cluster_points": len(cluster_points),
    }


def new_map(seed=None, save_path="map.pkl", plot=True,
            distribution="normal", num_cluster_points=5):
    map_ = gen(
        width=500,
        height=500,
        depth=500,
        num_sensors=100,
        energy=0.6,
        radius=200,
        distribution=distribution,
        num_cluster_points=num_cluster_points,
        seed=seed,
    )

    with open(save_path, "wb") as file:
        pickle.dump(map_, file)

    print(f"Map seed: {map_['seed']:02d}; saved to {save_path}")
    if plot: plot_map_3d(map_)

    return map_


if __name__ == "__main__":
    # Configure the map here: normal, clustered, or uniform.
    new_map(distribution="normal", num_cluster_points=5)
