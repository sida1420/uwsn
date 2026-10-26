"""Number of alive nodes versus rounds, one figure per map, in three marker variants.

    .venv/bin/python paper/scripts/figures/lifetime_alive.py [log_dir] [out_dir]

out_dir/lifetime/alive_fnd/<run>       FND marked by an enlarged hollow marker
out_dir/lifetime/alive_lnd/<run>       LND marked (or the end of the run when LND is not reached)
out_dir/lifetime/alive_fnd_lnd/<run>   both
Maps in which no node dies (flat curves) are skipped.
"""
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from common import (DEFAULT_LOG, DEFAULT_OUT, MS, SKIPPED, STYLE, algos, describe, fnd, handles,
                    legend_above, line_kw, lnd, one_per_map, round_axis, run_cli, save, single, t_max_v)

LOG = DEFAULT_LOG   # <- đổi thư mục log ở đây (hoặc truyền làm tham số đầu tiên)
OUT = DEFAULT_OUT   # <- thư mục lưu hình
VARIANTS = [(["FND"], "alive_fnd", "FND marked by enlarged hollow markers"),
            (["LND"], "alive_lnd", "LND marked (end of run when not reached)"),
            (["FND", "LND"], "alive_fnd_lnd", "FND and LND (or end of run) marked")]


def panel(ax, r, kinds):
    lo = r["n"]
    for k, a in enumerate(algos(r)):
        alive = r["hist"][a]["alive_nodes"].to_numpy()
        kw = line_kw(a, len(alive), k)
        kw["markevery"] = None
        kw["marker"] = None
        ax.plot(np.arange(1, len(alive) + 1), alive, **kw)
        lo = min(lo, alive.min())
        c = STYLE[a]["color"]
        if "FND" in kinds:
            f, ok = fnd(r, a)
            if ok:
                ax.plot(f, alive[f - 1], marker=STYLE[a]["marker"], ms=MS + 2, mfc="white", mec=c, mew=1.0,
                        zorder=5, ls="none")
        if "LND" in kinds:
            end, ok = lnd(r, a)
            ax.plot(end, alive[end - 1], marker=STYLE[a]["marker"] if ok else "|", ms=MS + 3, mfc=c, mec=c,
                    mew=1.2, zorder=5, ls="none")
    round_axis(ax)
    t_max_v(ax)
    span = max(2, r["n"] - lo)
    ax.set_ylim(lo - 0.25 * span, r["n"] + 0.15 * span)
    ax.yaxis.set_major_locator(MaxNLocator(6, integer=True, steps=[1, 2, 5, 10]))
    ax.set_ylabel("Number of alive nodes")
    items = handles(algos(r))
    if "FND" in kinds:
        items.append(Line2D([], [], ls="none", marker="o", ms=MS + 2, mfc="white", mec="#333333", label="FND"))
    if "LND" in kinds:
        reached = any(lnd(r, a)[1] for a in algos(r))
        items.append(Line2D([], [], ls="none", marker="|", ms=MS + 3, mec="#333333", mew=1.2,
                            label="LND" if reached else "End of run (LND not reached)"))
    legend_above(ax, items)


def draw(runs, out):
    for r in sorted(one_per_map(runs.values()), key=lambda r: r["id"]):
        if not any(r["hist"][a]["alive_nodes"].min() < r["n"] for a in algos(r)):
            SKIPPED.append(f"`lifetime/alive_*/{r['id']}`: no node dies (flat curves)")
            continue
        for kinds, folder, what in VARIANTS:
            fig, ax = single(2.6)
            panel(ax, r, kinds)
            save(fig, out, f"lifetime/{folder}/{r['id']}", describe(r),
                 f"Number of alive nodes versus rounds; {what}.")


if __name__ == "__main__":
    run_cli(draw, LOG, OUT)
