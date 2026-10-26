"""FND versus the number of sensor nodes.

    .venv/bin/python paper/scripts/figures/lifetime_fnd_vs_nodes.py [log_dir] [out_dir]

out_dir/lifetime/fnd_vs_nodes/<size>_<dist>, for every size/deployment with >= 2 values of N in
which FND is reached in at least half of the (N, algorithm) points. Not-reached points are hollow
markers at the last logged round (lower bound).
"""
from matplotlib.lines import Line2D

from common import (DEFAULT_LOG, DEFAULT_OUT, MS, SKIPPED, T_MAX, TMAX_HANDLE, algos, describe_all, fnd,
                    grouped, handles, legend_above, one_per_map, panel_vs_nodes, run_cli, save, single, t_max_h,
                    thousands)

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình


def panel(ax, by_n):
    panel_vs_nodes(ax, by_n, fnd, "FND (rounds)")
    t_max_h(ax)
    values = [fnd(r, a) for g in by_n.values() for r in g for a in algos(r)]
    lo = min(v for v, _ in values)
    ax.set_ylim(max(0, lo - 0.25 * (T_MAX - lo)), T_MAX * 1.06)
    ax.yaxis.set_major_formatter(thousands)
    items = handles() + [TMAX_HANDLE]
    if not all(ok for _, ok in values):
        items.append(Line2D([], [], ls="none", marker="o", ms=MS + 0.6, mfc="white", mec="#333333",
                            label="Not reached (last round)"))
    legend_above(ax, items)


def draw(runs, out):
    _, sizes, _ = grouped(one_per_map(runs.values()))
    for (size, dist), by_n in sorted(sizes.items()):
        if len(by_n) < 2:
            continue
        reached = [fnd(r, a)[1] for g in by_n.values() for r in g for a in algos(r)]
        if sum(reached) < len(reached) / 2:
            SKIPPED.append(f"`lifetime/fnd_vs_nodes/{size}_{dist}`: FND reached in only {sum(reached)} of "
                           f"{len(reached)} (N, algorithm) points")
            continue
        fig, ax = single(2.6)
        panel(ax, by_n)
        save(fig, out, f"lifetime/fnd_vs_nodes/{size}_{dist}", describe_all(by_n.values()),
             "FND versus the number of sensor nodes (fixed deployment volume). Hollow markers: FND not "
             "reached before the end of the run (plotted at the last logged round, a lower bound).")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
