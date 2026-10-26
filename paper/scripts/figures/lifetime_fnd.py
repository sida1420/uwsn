"""First node death (FND) bar charts.

    .venv/bin/python paper/scripts/figures/lifetime_fnd.py [log_dir] [out_dir]

out_dir/lifetime/fnd/<size>_<dist>_N<n>          one figure per configuration (one run per map;
                                                 several maps give mean, sample SD and dots)
out_dir/lifetime/fnd/<size>_N<n>_by_deployment   deployments side by side (when >= 2 exist)
"""
from common import (DEFAULT_LOG, DEFAULT_OUT, SKIPPED, T_MAX, TMAX_HANDLE, any_fnd, describe_all,
                    draw_lifetime_bars, fnd, grouped, one_per_map, panel_by_deployment, run_cli, save, single,
                    t_max_h, thousands)

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình


def draw(runs, out):
    draw_lifetime_bars(runs, out, ["FND"], "fnd", "First node death (FND)")
    _, _, deploy = grouped(one_per_map(runs.values()))
    for (size, n), by_dist in sorted(deploy.items()):
        if len(by_dist) < 2:
            continue
        if not all(any_fnd(g) for g in by_dist.values()):
            SKIPPED.append(f"`lifetime/fnd/{size}_N{n}_by_deployment`: FND not reached in some deployment")
            continue
        fig, ax = single(2.6)
        panel_by_deployment(ax, by_dist, fnd, "FND (rounds)", [TMAX_HANDLE])
        t_max_h(ax)
        ax.set_ylim(0, T_MAX * 1.15)
        ax.yaxis.set_major_formatter(thousands)
        save(fig, out, f"lifetime/fnd/{size}_N{n}_by_deployment", describe_all(by_dist.values()),
             "FND of each algorithm under each deployment (maps averaged, whiskers = sample SD; "
             "≥ marks FND not reached).")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
