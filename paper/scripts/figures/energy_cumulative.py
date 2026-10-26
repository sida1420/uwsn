"""Cumulative network energy consumption versus rounds, one figure per map.

    .venv/bin/python paper/scripts/figures/energy_cumulative.py [log_dir] [out_dir]

out_dir/energy/cumulative/<run>. The curve is the running sum of round_energy. The simulator
clamps a dying sensor's residual at 0 but logs its full last-round demand, so the sum can exceed
the energy actually drawn; the excess (from *_sensor-energy.csv) is stated in the caption.
"""
from common import (DEFAULT_LOG, DEFAULT_OUT, E0, algos, describe, handles, legend_above, one_per_map,
                    panel_cumsum, run_cli, save, single)

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình


def clamp_excess(r):
    return sum(float((r["sensor"][a] - E0).clip(lower=0).sum()) for a in algos(r) if a in r["sensor"])


def panel(ax, r):
    panel_cumsum(ax, r, "round_energy", "Cumulative energy consumption (J)")


def draw(runs, out):
    for r in sorted(one_per_map(runs.values()), key=lambda r: r["id"]):
        fig, ax = single()
        panel(ax, r)
        legend_above(ax, handles(algos(r)))
        ex = clamp_excess(r)
        note = (f" The logged sum exceeds the energy actually drawn by {ex:.3f} J in total (dying sensors "
                "are charged their full last-round demand)." if ex > 1e-6 else "")
        save(fig, out, f"energy/cumulative/{r['id']}", describe(r),
             f"Cumulative network energy consumption versus rounds (E0 = {E0} J per node).{note}")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
