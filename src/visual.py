
import matplotlib.pyplot as plt

from node import Node


class Visual:
    def __init__(self, w, h, d, sensors, base_pos):
        self.w = w
        self.h = h
        self.d = d
        self.sensors = sensors
        self.base_pos = base_pos
        self.nodes=[]
        self.lines=[]

        self.plot()

    def plot(self):
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection="3d")

        # Node: màu thể hiện độ sâu.
        self.nodes=self.ax.scatter(
            [p.x for p in self.sensors],  # X coordinates
            [p.y for p in self.sensors],  # Y coordinates
            [p.z for p in self.sensors],  # Z/depth coordinates
            c=[p.z for p in self.sensors],# Color each point by depth
            cmap="viridis_r",              # Reversed Viridis color map
            vmin=0,                        # Color scale minimum
            vmax=self.d,                  # Color scale maximum
            s=35,                         # Marker size
            alpha=0.85,                   # Slight transparency
            label="Sensor nodes",         # Legend label
        )

        # Sink ở trung tâm mặt nước nếu dùng base_pos mặc định.
        self.ax.scatter(
            [self.base_pos.x],
            [self.base_pos.y],
            [self.base_pos.z],
            color="red",
            marker="*",
            s=250,
            edgecolors="black",
            label="Sink",
            depthshade=False,
        )

        self.ax.set_xlim(0, self.w)
        self.ax.set_ylim(0, self.h)

        # z = 0 ở phía trên; độ sâu tăng xuống dưới.
        self.ax.set_zlim(self.d, 0)

        # Giữ đúng tỷ lệ kích thước không gian.
        self.ax.set_box_aspect((self.w, self.h, self.d))

        self.ax.set_xlabel("X (m)")
        self.ax.set_ylabel("Y (m)")
        self.ax.set_zlabel("Depth (m)")
        self.ax.set_title(f"UWSN 3D — {len(self.sensors)} sensor nodes")        
        self.ax.legend(loc="upper left")

        colorbar = self.fig.colorbar(
            self.nodes,
            ax=self.ax,
            shrink=0.6,
            pad=0.12,
            )
        colorbar.ax.invert_yaxis()


        self.ax.view_init(elev=25, azim=-60)

    def route(self, root: Node):
        def draw_lines(node: Node, linewidth):
            for nxt in node.nxts:
                self.lines.append(
                    self.ax.plot(
                        [self.sensors[node.id].x, self.sensors[nxt.id].x],
                        [self.sensors[node.id].y, self.sensors[nxt.id].y],
                        [self.sensors[node.id].z, self.sensors[nxt.id].z],
                        color="blue",
                        linewidth=linewidth,
                    alpha=0.7,
                ))
                draw_lines(nxt, linewidth*0.8)

    def save(self, path):
        self.fig.savefig(path, dpi=300, bbox_inches="tight")

    def show(self):
        self.fig.show()