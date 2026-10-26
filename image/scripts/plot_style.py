"""Shared Matplotlib style for every figure in image/figures.

Visual reference: image/Pasted image.png -- a plain white 2-D line chart, thin
solid/dashed lines, compact legend in the upper area, serif (Times-like) text,
no background fill, no heavy grid. Every figure script imports this module so
fonts, line widths, colours and line styles stay identical across figures.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Fixed algorithm order and identity. Colours are the Okabe-Ito colour-blind-safe
# set (orange and pink darkened to reach 3:1 contrast on white; black and
# vermillion echo the template's black dashed / red solid pair);
# line style + marker give a second, colour-independent encoding (print / CVD).
ALGORITHM_ORDER = ["D-ACO", "AC-ACO", "SimpleACO", "NodeACO", "PSO"]  # ME-ACO excluded
STYLES = {
    "D-ACO":     {"color": "#000000", "linestyle": "-",             "marker": "o"},
    "ME-ACO":    {"color": "#D55E00", "linestyle": "--",            "marker": "^"},
    "AC-ACO":    {"color": "#0072B2", "linestyle": "-.",            "marker": "s"},
    "SimpleACO": {"color": "#009E73", "linestyle": ":",             "marker": "D"},
    "NodeACO":   {"color": "#A87400", "linestyle": (0, (5, 1, 1, 1, 1, 1)), "marker": "v"},
    "PSO":       {"color": "#A8509A", "linestyle": (0, (8, 2)),     "marker": "x"},
}

LINE_WIDTH = 1.1
MARKER_SIZE = 4.5
SINGLE_COL = (3.5, 2.6)     # inches: one journal column
DOUBLE_COL = (7.0, 3.2)     # inches: full text width
DPI = 300

RC = {
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7.5,
    "axes.linewidth": 0.6,
    "axes.edgecolor": "#222222",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "grid.color": "#e6e6e6",
    "grid.linewidth": 0.4,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "lines.linewidth": LINE_WIDTH,
    "lines.markersize": MARKER_SIZE,
    "legend.frameon": False,
    "legend.handlelength": 2.8,
    "legend.borderaxespad": 0.3,
    "legend.labelspacing": 0.3,
    "savefig.dpi": DPI,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
    "pdf.fonttype": 42,   # embed TrueType: editable text in PDF
    "svg.fonttype": "none",
}


def apply():
    plt.rcParams.update(RC)


def style(algo, markers=True):
    s = dict(STYLES[algo])
    if not markers:
        s.pop("marker")
    s.setdefault("linewidth", LINE_WIDTH)
    s.setdefault("markersize", MARKER_SIZE)
    s["markerfacecolor"] = "white" if s.get("marker") not in (None, "x") else s["color"]
    s["markeredgewidth"] = 0.9
    return s


def light_grid(ax, axis="y"):
    ax.grid(True, axis=axis, color="#e6e6e6", linewidth=0.4)
    ax.set_axisbelow(True)


def save(fig, path, formats=("png", "pdf")):
    """Save PNG (300 DPI) plus vector copies next to it; return written paths."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in formats:
        out = path.with_suffix(f".{ext}")
        fig.savefig(out)
        written.append(out)
    plt.close(fig)
    return written
