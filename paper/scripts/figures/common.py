"""Shared code for the figure scripts in this folder: style, log loading, metrics, helpers.

Each figure script (runtime_*.py, lifetime_*.py, energy_*.py) draws one figure type from a
log folder and runs on its own:

    .venv/bin/python paper/scripts/figures/<script>.py [log_dir] [out_dir]

With no arguments it uses the LOG / OUT set at the top of that script. plot_all.py runs every
script and writes out_dir/README.md (source logs + suggested caption for each figure).

Log format: run.py history CSVs (columns round, alive_nodes, round_energy, time[s]) named
    <W>_<H>_<D>_<N>_<distribution>_<YYYYMMDDHH>_<seed>_<algorithm>.csv
plus the matching *_sensor-energy.csv. Empty logs (no feasible routing in round 1) are skipped.

Run vs. map: a run is one log set (one timestamp). Re-running the same map (same size,
deployment, N, seed) gives identical alive_nodes / round_energy (the simulation is
deterministic) but a different wall-clock time. Runtime figures therefore use every run;
lifetime and energy figures use one run per map (the earliest).

Lifetime (round_number = round + 1):
    FND  first round after which alive_nodes < N
    LND  first round after which alive_nodes == 0
A metric that does not occur in a log is "not reached": it is drawn as a hatched bar /
hollow marker at the last logged round, i.e. a lower bound, never as an observed value.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import to_rgb  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LOG = ROOT / "image" / "log"
DEFAULT_OUT = ROOT / "paper" / "figures"

T_MAX = 3500
E0 = 0.6       # J per sensor (src/map_gen.py default)
FIRST = 1000   # rounds averaged in the runtime mean / vs_nodes / by_deployment figures
NAME = re.compile(r"(\d+)_(\d+)_(\d+)_(\d+)_([a-z]+)_(\d{10})_(\d+)_(.+)\.csv$")

ORDER = ["SimpleACO", "NodeACO", "PSO", "AC-ACO", "D-ACO"]
STYLE = {  # colour + dash + marker: still separable in grayscale print
    "SimpleACO": dict(color="#D62728", ls=(0, (6, 2)), marker="o"),
    "NodeACO":   dict(color="#F28E00", ls=(0, (6, 1.5, 1.5, 1.5)), marker="s"),
    "PSO":       dict(color="#1F6FC5", ls=(0, (1.2, 1.4)), marker="v"),
    "AC-ACO":    dict(color="#8E2C9E", ls=(0, (9, 2.5)), marker="p"),
    "D-ACO":     dict(color="#2E7D32", ls="-", marker="D"),
}
DEPLOY_HATCH = {"clustered": "", "normal": "////", "uniform": "...."}
CENSORED_HATCH = "//////"
EDGE = "#1A1A1A"
LW, LW_OURS, MS = 1.1, 1.7, 3.8
SINGLE, DOUBLE = 3.5, 7.16   # inches: IEEE column / text width

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Nimbus Roman", "Liberation Serif", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8, "axes.labelsize": 8.5, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "axes.linewidth": 0.6, "axes.edgecolor": "#222222",
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.direction": "out", "ytick.direction": "out",
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 3, "ytick.major.size": 3, "ytick.minor.size": 1.6,
    "axes.grid": True, "grid.color": "#D9D9D9", "grid.linestyle": (0, (4, 3)), "grid.linewidth": 0.5,
    "axes.axisbelow": True,
    "legend.frameon": False, "legend.handlelength": 2.6, "legend.columnspacing": 1.2,
    "legend.handletextpad": 0.5,
    "hatch.linewidth": 0.5,
    "pdf.fonttype": 42, "ps.fonttype": 42,   # embed TrueType: required by IEEE PDF eXpress
    "savefig.dpi": 600, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})
thousands = FuncFormatter(lambda v, _: f"{v:,.0f}")

INDEX = []     # (relative path, data description, suggested caption) of every saved figure
SKIPPED = []   # groups a figure type cannot draw, with the reason


# ------------------------------------------------------------------- loading
def load_runs(log_dir):
    """{run id: {...metadata, "hist": {algo: history}, "sensor": {algo: totals}}}, [empty run ids]."""
    runs, empty = {}, set()
    for f in sorted(Path(log_dir).glob("*.csv")):
        m = NAME.match(f.name)
        if not m or f.name.endswith("_sensor-energy.csv"):
            continue
        w, h, d, n, dist, ts, seed, algo = m.groups()
        size = f"{w}x{h}x{d}"
        rid = f"{size}_{dist}_N{n}_seed{seed}_{ts}"
        hist = pd.read_csv(f)
        if hist.empty:
            empty.add(rid)
            continue
        r = runs.setdefault(rid, dict(id=rid, size=size, dist=dist, n=int(n), seed=int(seed), ts=ts,
                                       hist={}, sensor={}))
        r["hist"][algo] = hist
        sensor = f.with_name(f.stem + "_sensor-energy.csv")
        if sensor.exists():
            r["sensor"][algo] = pd.read_csv(sensor)["total_energy"]
    if not runs and not empty:
        sys.exit(f"no log CSV found in {log_dir}")
    return runs, sorted(empty - set(runs))


def one_per_map(runs):
    """Earliest run of each map: re-runs repeat the same deterministic simulation."""
    keep = {}
    for r in sorted(runs, key=lambda r: r["ts"]):
        keep.setdefault((r["size"], r["dist"], r["n"], r["seed"]), r)
    return list(keep.values())


def grouped(runs):
    """(by configuration, by size/deployment then N, by size/N then deployment)."""
    cfg = defaultdict(list)
    size = defaultdict(lambda: defaultdict(list))
    dep = defaultdict(lambda: defaultdict(list))
    for r in runs:
        cfg[(r["size"], r["dist"], r["n"])].append(r)
        size[(r["size"], r["dist"])][r["n"]].append(r)
        dep[(r["size"], r["n"])][r["dist"]].append(r)
    return cfg, size, dep


# ------------------------------------------------------------------- metrics
def algos(r):
    return [a for a in ORDER if a in r["hist"]]


def present(group, a):
    return [r for r in group if a in r["hist"]]


def ms(r, a):
    return r["hist"][a]["time"].to_numpy() * 1e3


def first_mean(r, a):
    return ms(r, a)[:FIRST].mean()


def runtime_value(r, a):
    return first_mean(r, a), True


def fnd(r, a):
    """(round, observed); not observed -> last logged round (lower bound)."""
    alive = r["hist"][a]["alive_nodes"].to_numpy()
    hit = np.flatnonzero(alive < r["n"])
    return (hit[0] + 1, True) if len(hit) else (len(alive), False)


def lnd(r, a):
    alive = r["hist"][a]["alive_nodes"].to_numpy()
    hit = np.flatnonzero(alive == 0)
    return (hit[0] + 1, True) if len(hit) else (len(alive), False)


def any_fnd(group):
    return any(fnd(r, a)[1] for r in group for a in algos(r))


def mean_sd(values):
    v = np.asarray(values, float)
    return v.mean(), (v.std(ddof=1) if len(v) > 1 else 0.0)


def tint(color, k=0.5):
    return tuple(1 - k * (1 - c) for c in to_rgb(color))


# -------------------------------------------------------------- drawing helpers
def line_kw(algo, n_points, offset):
    """Line style with ~7 markers per curve, staggered so they do not stack."""
    s = STYLE[algo]
    step = max(1, n_points // 7)
    return dict(color=s["color"], ls=s["ls"], marker=s["marker"], ms=MS + (0.6 if algo == "D-ACO" else 0),
                lw=LW_OURS if algo == "D-ACO" else LW, mec=s["color"], mew=0.6,
                markevery=(int(offset * step / len(ORDER)), step),
                zorder=3 if algo == "D-ACO" else 2, label=algo, dash_capstyle="butt")


def handles(names=ORDER):
    return [Line2D([], [], color=STYLE[a]["color"], ls=STYLE[a]["ls"], marker=STYLE[a]["marker"],
                   lw=LW_OURS if a == "D-ACO" else LW, ms=MS, label=a) for a in names]


def legend_above(ax, items, ncol=3, **kw):
    ax.legend(handles=items, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=ncol,
              borderaxespad=0, **kw)


TMAX_KW = dict(color="#555555", lw=0.7, ls=(0, (4, 2)))
TMAX_HANDLE = Line2D([], [], label=rf"$T_{{\max}}$ = {T_MAX:,}", **TMAX_KW)


def t_max_v(ax):
    ax.axvline(T_MAX, zorder=1, **TMAX_KW)
    ax.text(T_MAX, 1.0, r"$T_{\max}$", transform=ax.get_xaxis_transform(), ha="right",
            va="bottom", fontsize=7.5, color="#444444")


def t_max_h(ax):
    """Horizontal T_max line; it is named in the legend (TMAX_HANDLE) so it never covers a label."""
    ax.axhline(T_MAX, zorder=1, **TMAX_KW)


def round_axis(ax):
    ax.set_xlim(0, T_MAX + 120)
    ax.set_xticks(range(0, T_MAX + 1, 500))
    ax.xaxis.set_major_formatter(thousands)
    ax.set_xlabel("Round")


def bar_axis(ax, names):
    ax.set_xticks(range(len(names)), names, fontsize=7)
    ax.set_xlim(-0.55, len(names) - 0.45)
    ax.tick_params(axis="x", length=0, pad=3)
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_locator(MaxNLocator(5))


# ----------------------------------------------------------- shared panels
def bars(ax, group, metrics, ylabel, fmt, label_offset):
    """Bar chart per algorithm. metrics: [(name, fn(run, algo) -> (value, observed), light)].
    Repeats in `group` give mean, sample-SD whiskers and dots; any not-observed value makes the
    bar a hatched lower bound labelled with a leading '>='. Returns (max height, any censored)."""
    names = [a for a in ORDER if present(group, a)]
    k = len(metrics)
    width = 0.62 if k == 1 else 0.36
    tops, censored_any = [], False
    for i, a in enumerate(names):
        runs = present(group, a)
        for j, (_, fn, light) in enumerate(metrics):
            vals = [fn(r, a) for r in runs]
            v = [x for x, _ in vals]
            cens = not all(ok for _, ok in vals)
            censored_any |= cens
            m, sd = mean_sd(v)
            xi = i + (j - (k - 1) / 2) * (width + 0.03)
            color = tint(STYLE[a]["color"], 0.45) if light else STYLE[a]["color"]
            ax.bar(xi, m, width=width, color=color, edgecolor=EDGE, linewidth=0.6,
                   hatch=CENSORED_HATCH if cens else None, zorder=2)
            top = m
            if len(v) > 1:
                ax.errorbar(xi, m, yerr=sd, fmt="none", ecolor=EDGE, elinewidth=0.8, capsize=3 if k == 1 else 2,
                            capthick=0.8, zorder=3)
                ax.scatter(xi + np.linspace(-width * 0.23, width * 0.23, len(v)), v, s=11 if k == 1 else 8,
                           facecolor="white", edgecolor=EDGE, linewidth=0.6, zorder=4)
                top = max(m + sd, max(v))
            tops.append((xi, top, m, sd, len(v), cens))
    ymax = max(t[1] for t in tops)
    for xi, top, m, sd, nv, cens in tops:
        text = ("≥" if cens else "") + fmt(m) + (f"\n±{fmt(sd)}" if nv > 1 and k == 1 else "")
        ax.text(xi, top + ymax * label_offset, text, ha="center", va="bottom", fontsize=7 if k == 1 else 6.3,
                linespacing=1.05, rotation=0 if k == 1 else 90, zorder=5,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.4))
    bar_axis(ax, names)
    ax.set_ylabel(ylabel)
    return ymax, censored_any


LIFETIME = {"FND": ("FND", fnd, False), "LND": ("LND", lnd, True)}   # LND bars drawn in a lighter tint


def panel_lifetime(ax, group, kinds):
    """FND / LND bars (kinds = ["FND"], ["LND"] or ["FND", "LND"]) with the T_max line."""
    ylabel = f"{kinds[0]} (rounds)" if len(kinds) == 1 else "Lifetime (rounds)"
    ymax, cens = bars(ax, group, [LIFETIME[k] for k in kinds], ylabel, lambda v: f"{v:,.0f}", 0.03)
    t_max_h(ax)
    ax.set_ylim(0, max(ymax, T_MAX) * (1.22 if len(kinds) == 1 else 1.32))
    ax.yaxis.set_major_formatter(thousands)
    items = [TMAX_HANDLE]
    if len(kinds) > 1:
        items += [Patch(facecolor="#555555", edgecolor=EDGE, lw=0.6, label="FND"),
                  Patch(facecolor=tint("#555555", 0.45), edgecolor=EDGE, lw=0.6, label="LND")]
    if cens:
        items.append(Patch(facecolor="white", edgecolor=EDGE, lw=0.6, hatch=CENSORED_HATCH,
                           label="Not reached (last logged round)"))
    legend_above(ax, items, ncol=len(items) if len(items) < 4 else 2, handlelength=1.8)


def draw_lifetime_bars(runs, out, kinds, folder, what):
    """One lifetime bar figure per configuration (one run per map) in out/lifetime/<folder>/."""
    cfg, _, _ = grouped(one_per_map(runs.values()))
    for (size, dist, n), group in sorted(cfg.items()):
        tag = f"{size}_{dist}_N{n}"
        if not any_fnd(group):
            SKIPPED.append(f"`lifetime/{folder}/{tag}`: no node dies within the logged rounds "
                           "(FND and LND not reached)")
            continue
        rep = (f"mean of {len(group)} maps, whiskers = sample SD, dots = individual maps" if len(group) > 1
               else "single map")
        fig, ax = single(2.6)
        panel_lifetime(ax, group, kinds)
        save(fig, out, f"lifetime/{folder}/{tag}", describe_all([group]),
             f"{what} of each algorithm ({rep}); dashed line = $T_{{max}}$ = {T_MAX:,}. Hatched bars mark "
             "a metric not reached before the end of the run; their height is the last logged round "
             "(lower bound).")


def panel_by_deployment(ax, by_dist, fn, ylabel, extra=()):
    """Grouped bars, one per deployment within each algorithm; repeats averaged (SD whiskers)."""
    dists = sorted(by_dist)
    width = 0.8 / len(dists)
    top = 0
    for j, dist in enumerate(dists):
        for i, a in enumerate(ORDER):
            vals = [fn(r, a) for r in present(by_dist[dist], a)]
            if not vals:
                continue
            m, sd = mean_sd([v for v, _ in vals])
            xi = i + (j - (len(dists) - 1) / 2) * width
            ax.bar(xi, m, width=width * 0.92, color=STYLE[a]["color"], edgecolor=EDGE, linewidth=0.6,
                   hatch=DEPLOY_HATCH.get(dist, "xx"), zorder=2)
            if len(vals) > 1:
                ax.errorbar(xi, m, yerr=sd, fmt="none", ecolor=EDGE, elinewidth=0.7, capsize=2,
                            capthick=0.7, zorder=3)
            if not all(ok for _, ok in vals):
                ax.text(xi, m + sd, "≥", ha="center", va="bottom", fontsize=6.5)
            top = max(top, m + sd)
    bar_axis(ax, ORDER)
    ax.set_ylabel(ylabel)
    legend_above(ax, [Patch(facecolor="white", edgecolor=EDGE, lw=0.6, hatch=DEPLOY_HATCH.get(d, "xx"),
                            label=d.capitalize()) for d in dists] + list(extra),
                 ncol=len(dists) + len(extra), handlelength=1.6)
    return top


def panel_cumsum(ax, r, column, ylabel):
    for k, a in enumerate(algos(r)):
        y = np.cumsum(r["hist"][a][column].to_numpy())
        ax.plot(np.arange(1, len(y) + 1), y, **line_kw(a, len(y), k))
    round_axis(ax)
    t_max_v(ax)
    ax.set_ylim(0, None)
    ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 100 or v == 0 else f"{v:g}"))
    ax.set_ylabel(ylabel)


def panel_vs_nodes(ax, by_n, fn, ylabel):
    """Metric vs. N; repeats averaged (SD whiskers); a not-reached value is a hollow marker."""
    nodes = sorted(by_n)
    for k, a in enumerate(ORDER):
        pts = []
        for n in nodes:
            vals = [fn(r, a) for r in present(by_n[n], a)]
            if vals:
                m, sd = mean_sd([v for v, _ in vals])
                pts.append((n, m, sd, all(ok for _, ok in vals)))
        if not pts:
            continue
        x, y, sd, ok = map(np.array, zip(*pts))
        kw = line_kw(a, len(x), k)
        kw["markevery"] = None
        kw["marker"] = None
        ax.plot(x, y, **kw)
        c = STYLE[a]["color"]
        size = kw["ms"] + 0.6
        ax.plot(x[ok], y[ok], ls="none", marker=STYLE[a]["marker"], ms=size, mfc=c, mec=c, zorder=kw["zorder"] + 1)
        ax.plot(x[~ok], y[~ok], ls="none", marker=STYLE[a]["marker"], ms=size, mfc="white", mec=c, mew=0.9,
                zorder=kw["zorder"] + 1)
        if sd.any():
            ax.errorbar(x, y, yerr=sd, fmt="none", ecolor=c, elinewidth=0.7, capsize=2, capthick=0.7,
                        zorder=kw["zorder"])
    pad = (nodes[-1] - nodes[0]) * 0.07
    ax.set_xticks(nodes)
    ax.set_xlim(nodes[0] - pad, nodes[-1] + pad)
    ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.set_xlabel("Number of sensor nodes")
    ax.set_ylabel(ylabel)


# ------------------------------------------------------------------- output
def single(height=2.45):
    return plt.subplots(figsize=(SINGLE, height))


def save(fig, out, rel, data, caption):
    path = Path(out) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(path.with_suffix(f".{ext}"))
    plt.close(fig)
    INDEX.append((rel, data, caption))
    print("wrote", path.with_suffix(".pdf"), "+ .png")


def describe(r):
    return f"{r['size']} m, {r['dist']}, N = {r['n']}, seed {r['seed']}, run {r['ts']}"


def describe_all(groups):
    return "; ".join(describe(r) for g in groups for r in g)


def run_cli(draw, log=DEFAULT_LOG, out=DEFAULT_OUT):
    """Entry point of every figure script: `script.py [log_dir] [out_dir]` overrides LOG / OUT."""
    log = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(log)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(out)
    runs, empty = load_runs(log)
    draw(runs, out)
    for s in SKIPPED:
        print("skipped:", s)
    for rid in empty:
        print(f"skipped: {rid} (empty log)")
