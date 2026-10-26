"""Computation time per round (100-round block means, logarithmic y-axis), one figure per run.

    .venv/bin/python paper/scripts/figures/runtime_by_round.py [log_dir] [out_dir]

out_dir/runtime/by_round/<run>. Timing spikes are kept and named in the caption.
"""
import numpy as np
from matplotlib.ticker import LogLocator

from common import (DEFAULT_LOG, DEFAULT_OUT, algos, describe, handles, legend_above, line_kw, ms,
                    round_axis, run_cli, save, single, t_max_v)

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình
BLOCK = 100         # rounds per plotted point
SPIKE = 50          # a round slower than SPIKE x the run median is reported as a timing spike


def spikes(r):
    out = []
    for a in algos(r):
        t = ms(r, a)
        for i in np.flatnonzero(t > SPIKE * np.median(t)):
            out.append(f"{a} round {i + 1}: {t[i] / 1e3:,.1f} s")
    return out


def spike_note(r):
    sp = spikes(r)
    return f" Timing spikes retained: {'; '.join(sp)}." if sp else ""


def panel(ax, r):
    lo, hi = np.inf, 0
    for k, a in enumerate(algos(r)):
        t = ms(r, a)
        n = int(np.ceil(len(t) / BLOCK))
        y = np.array([t[i * BLOCK:(i + 1) * BLOCK].mean() for i in range(n)])
        x = np.array([min((i + 0.5) * BLOCK, len(t)) for i in range(n)])
        ax.plot(x, y, **line_kw(a, n, k))
        lo, hi = min(lo, y.min()), max(hi, y.max())
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10)))
    ax.set_ylim(lo / 1.4, hi * 1.8)
    round_axis(ax)
    t_max_v(ax)
    ax.set_ylabel("Computation time (ms/round)")


def draw(runs, out):
    for rid, r in sorted(runs.items()):
        fig, ax = single()
        panel(ax, r)
        legend_above(ax, handles(algos(r)))
        save(fig, out, f"runtime/by_round/{rid}", describe(r),
             f"Computation time per round ({BLOCK}-round block means, logarithmic scale).{spike_note(r)}")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
