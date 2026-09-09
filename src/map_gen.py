from point import Point

import random
import pickle
import matplotlib.pyplot as plt


def plot_map_3d(map_, save_path="map_3d.png", show_ids=False):
    nodes = map_["nodes"]
    sink = map_["base_pos"]

    width = map_["width"]
    height = map_["height"]
    depth = map_["depth"]

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    # Node: màu thể hiện độ sâu.
    points = ax.scatter(
        [p.x for p in nodes],
        [p.y for p in nodes],
        [p.z for p in nodes],
        c=[p.z for p in nodes],
        cmap="viridis_r",
        vmin=0,
        vmax=depth,
        s=35,
        alpha=0.85,
        label="Sensor nodes",
    )

    # Sink ở trung tâm mặt nước nếu dùng base_pos mặc định.
    ax.scatter(
        [sink.x],
        [sink.y],
        [sink.z],
        color="red",
        marker="*",
        s=250,
        edgecolors="black",
        label="Sink",
        depthshade=False,
    )

    if show_ids:
        for i, p in enumerate(nodes):
            ax.text(p.x, p.y, p.z, str(i), fontsize=7)

    ax.set_xlim(0, width)
    ax.set_ylim(0, height)

    # z = 0 ở phía trên; độ sâu tăng xuống dưới.
    ax.set_zlim(depth, 0)

    # Giữ đúng tỷ lệ kích thước không gian.
    ax.set_box_aspect((width, height, depth))

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Depth (m)")
    ax.set_title(f"UWSN 3D Map — {len(nodes)} sensor nodes")

    ax.view_init(elev=25, azim=-60)
    ax.legend(loc="upper left")

    fig.colorbar(
        points,
        ax=ax,
        label="Depth (m)",
        shrink=0.6,
        pad=0.12,
    )

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()


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

    plot_map_3d(map_)

    return map_


if __name__ == "__main__":
    new_map()
