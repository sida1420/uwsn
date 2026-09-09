from point import Point

import random
import pickle


def gen(
    width,
    height,
    depth,
    num_nodes,
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

    nodes = [random_point() for _ in range(num_nodes)]

    # Tâm cụm cũng phải có đủ 3 tọa độ.
    cluster_points = [random_point() for _ in range(num_cluster_points)]

    if cluster_points:
        for i, node in enumerate(nodes):
            nearest = min(
                cluster_points,
                key=lambda point: abs(point - node),
            )

            # Kéo node về phía tâm cụm gần nhất.
            nodes[i] = node + (nearest - node) * random.uniform(0, 0.5)

    return {
        "width": width,
        "height": height,
        "depth": depth,
        "base_pos": base_pos,
        "nodes": nodes,
        "init_energy": energy,
        "radius": radius,
    }


def new_map():
    map_ = gen(
        width=500,
        height=500,
        depth=500,
        num_nodes=100,
        energy=0.6,
        radius=100,
        num_cluster_points=0,
    )

    with open("map.pkl", "wb") as file:
        pickle.dump(map_, file)

    return map_


if __name__ == "__main__":
    new_map()
