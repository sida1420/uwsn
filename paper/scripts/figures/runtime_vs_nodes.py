"""Mean computation time per round (first 1,000 rounds) versus the number of sensor nodes.

    .venv/bin/python paper/scripts/figures/runtime_vs_nodes.py [log_dir] [out_dir]

out_dir/runtime/vs_nodes/<size>_<dist>, for every size/deployment with >= 2 values of N.
Repeated runs at the same N give sample-SD whiskers.
"""
from common import (DEFAULT_LOG, DEFAULT_OUT, FIRST, describe_all, grouped, handles, legend_above,
                    panel_vs_nodes, run_cli, runtime_value, save, single)

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình


def panel(ax, by_n):
    panel_vs_nodes(ax, by_n, runtime_value, "Computation time (ms/round)")
    ax.set_ylim(0, None)


def draw(runs, out):
    _, sizes, _ = grouped(runs.values())
    for (size, dist), by_n in sorted(sizes.items()):
        if len(by_n) < 2:
            continue
        fig, ax = single()
        panel(ax, by_n)
        legend_above(ax, handles())
        save(fig, out, f"runtime/vs_nodes/{size}_{dist}", describe_all(by_n.values()),
             f"Mean computation time per round (first {FIRST:,} rounds) versus the number of sensor "
             "nodes; fixed deployment volume, whiskers = sample SD over repeated runs.")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
