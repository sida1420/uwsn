"""Last node death (LND) bar charts.

    .venv/bin/python paper/scripts/figures/lifetime_lnd.py [log_dir] [out_dir]

out_dir/lifetime/lnd/<size>_<dist>_N<n>, one figure per configuration with at least one node death.
An LND that is not reached is a hatched bar at the last logged round (lower bound).
"""
from common import DEFAULT_LOG, DEFAULT_OUT, draw_lifetime_bars, run_cli

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình


def draw(runs, out):
    draw_lifetime_bars(runs, out, ["LND"], "lnd", "Last node death (LND)")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
