"""Mean computation time per round over the first 1,000 rounds (bar chart).

    .venv/bin/python paper/scripts/figures/runtime_mean.py [log_dir] [out_dir]

out_dir/runtime/mean/<size>_<dist>_N<n>          one figure per configuration; repeated runs
                                                 give mean, sample-SD whiskers and dots
out_dir/runtime/mean/<size>_N<n>_by_deployment   deployments side by side (when >= 2 exist)
Every run is used: re-runs of a map differ in wall-clock time.
"""
from common import (DEFAULT_LOG, DEFAULT_OUT, FIRST, bars, describe_all, grouped, panel_by_deployment,
                    run_cli, runtime_value, save, single)

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình


def panel(ax, group):
    ymax, _ = bars(ax, group, [("runtime", runtime_value, False)], "Computation time (ms/round)",
                   lambda v: f"{v:.1f}", 0.03)
    ax.set_ylim(0, ymax * 1.3)


def draw(runs, out):
    cfg, _, deploy = grouped(runs.values())
    for (size, dist, n), group in sorted(cfg.items()):
        rep = (f"mean of {len(group)} runs, whiskers = sample SD, dots = individual runs" if len(group) > 1
               else "single run")
        fig, ax = single()
        panel(ax, group)
        save(fig, out, f"runtime/mean/{size}_{dist}_N{n}", describe_all([group]),
             f"Mean computation time per round over the first {FIRST:,} rounds ({rep}).")
    for (size, n), by_dist in sorted(deploy.items()):
        if len(by_dist) < 2:
            continue
        fig, ax = single()
        top = panel_by_deployment(ax, by_dist, runtime_value, "Computation time (ms/round)")
        ax.set_ylim(0, top * 1.2)
        save(fig, out, f"runtime/mean/{size}_N{n}_by_deployment", describe_all(by_dist.values()),
             f"Mean computation time per round over the first {FIRST:,} rounds for each deployment "
             "(repeated runs averaged, whiskers = sample SD).")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
