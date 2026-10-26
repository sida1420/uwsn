"""Cumulative recorded computation time (running sum of the round timers), one figure per run.

    .venv/bin/python paper/scripts/figures/runtime_cumulative.py [log_dir] [out_dir]

out_dir/runtime/cumulative/<run>
"""
from common import (DEFAULT_LOG, DEFAULT_OUT, algos, describe, handles, legend_above, panel_cumsum, run_cli,
                    save, single)
from runtime_by_round import spike_note

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình


def panel(ax, r):
    panel_cumsum(ax, r, "time", "Cumulative computation time (s)")


def draw(runs, out):
    for rid, r in sorted(runs.items()):
        fig, ax = single()
        panel(ax, r)
        legend_above(ax, handles(algos(r)))
        save(fig, out, f"runtime/cumulative/{rid}", describe(r),
             f"Cumulative recorded computation time (sum of the per-round timers).{spike_note(r)}")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
