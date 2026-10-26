"""FND and LND side by side for each algorithm (grouped bar chart).

    .venv/bin/python paper/scripts/figures/lifetime_fnd_lnd.py [log_dir] [out_dir]

out_dir/lifetime/fnd_lnd/<size>_<dist>_N<n>, one figure per configuration with at least one node death.
"""
from common import DEFAULT_LOG, DEFAULT_OUT, draw_lifetime_bars, run_cli

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình


def draw(runs, out):
    draw_lifetime_bars(runs, out, ["FND", "LND"], "fnd_lnd", "First (FND) and last (LND) node death")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
