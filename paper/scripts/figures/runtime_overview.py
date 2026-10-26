"""Four headline runtime panels (a)-(d) in one double-column figure.

    .venv/bin/python paper/scripts/figures/runtime_overview.py [log_dir] [out_dir]

out_dir/runtime/runtime_overview. The configurations shown are chosen below; with another log
folder, set them to configurations that exist there (the script says which one is missing).
"""
import sys

import matplotlib.pyplot as plt

import runtime_by_round
import runtime_cumulative
import runtime_mean
import runtime_vs_nodes
from common import DEFAULT_LOG, DEFAULT_OUT, DOUBLE, grouped, handles, run_cli, save

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình
MEAN = ("500x500x500", "uniform", 100)                 # (a): size, deployment, N
TRACE = "500x500x500_uniform_N100_seed89_2026101400"  # (b), (c): one run id
VS_NODES = ("500x500x500", "clustered")               # (d): size, deployment


def draw(runs, out):
    cfg, sizes, _ = grouped(runs.values())
    missing = [k for k, ok in ((MEAN, MEAN in cfg), (TRACE, TRACE in runs), (VS_NODES, VS_NODES in sizes))
               if not ok]
    if missing:
        print(f"runtime_overview: not in this log folder, edit the choice at the top of {__file__}: {missing}",
              file=sys.stderr)
        return
    fig, axes = plt.subplots(2, 2, figsize=(DOUBLE, 5.0), gridspec_kw=dict(hspace=0.5, wspace=0.26))
    panels = [(runtime_mean.panel, cfg[MEAN]), (runtime_by_round.panel, runs[TRACE]),
              (runtime_cumulative.panel, runs[TRACE]), (runtime_vs_nodes.panel, sizes[VS_NODES])]
    for ax, tag, (panel, arg) in zip(axes.flat, "abcd", panels):
        panel(ax, arg)
        ax.text(0.5, -0.30, f"({tag})", transform=ax.transAxes, ha="center", va="top", fontsize=9)
    fig.subplots_adjust(top=0.9)
    fig.legend(handles=handles(), loc="upper center", bbox_to_anchor=(0.5, 0.985), ncol=5)
    save(fig, out, "runtime/runtime_overview", f"(a) {MEAN}; (b), (c) {TRACE}; (d) {VS_NODES}",
         "Computation runtime: (a) mean over the first 1,000 rounds; (b) per round; (c) cumulative; "
         "(d) versus the number of nodes.")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
