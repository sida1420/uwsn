from point import Point

import random
import pickle
import matplotlib.pyplot as plt
from visual import Visual


def plot_map_3d(map_, save_path="map_3d.svg", show_ids=False):
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
):
    # Quy ước z là độ sâu:
    # z = 0 là mặt nước, z = depth là đáy.
    if base_pos is None:
        base_pos = Point(width / 2, height / 2, 0)

    def random_point():
        return Point(
            random.uniform(0, width),
            random.uniform(0, height),
            random.uniform(0, depth),
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
            sensors[i] = sensor + (nearest - sensor) * random.uniform(0, 0.5)

    return {
        "width": width,
        "height": height,
        "depth": depth,
        "base_pos": base_pos,
        "sensors": sensors,
        "init_energy": energy,
        "radius": radius,
    }


def new_map():
    map_ = gen(
        width=500,
        height=500,
        depth=500,
        num_sensors=100,
        energy=0.6,
        radius=200,
        num_cluster_points=0,
    )

    with open("map.pkl", "wb") as file:
        pickle.dump(map_, file)

    plot_map_3d(map_)

    return map_


if __name__ == "__main__":
    new_map()
