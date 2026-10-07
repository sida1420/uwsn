"""Standalone scientific figures; never pad stopped networks with zero deaths."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_results(results, output):
    variants = ["tuned", "old", "new"]
    labels = ["Tuned ACO", "Old AC-ACO", "Updated AC-ACO"]
    colors = ["#2563eb", "#dc2626", "#059669"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for variant, label, color in zip(variants, labels, colors):
        cases = sorted((d for d in results if d["variant"] == variant), key=lambda d: d["seed"])
        for panel, key, cumulative in ((axes[0, 0], "energy", True),
                                       (axes[0, 1], "alive_nodes", False)):
            for index, case in enumerate(cases):
                values = np.array([r[key] for r in case["rows"]])
                panel.plot(np.arange(1, len(values)+1), np.cumsum(values) if cumulative else values,
                           color=color, alpha=0.5, lw=1.2, label=label if index == 0 else None)
                panel.scatter([len(values)], [np.cumsum(values)[-1] if cumulative else values[-1]],
                              color=color, s=16)
        means = np.array([[r["convergence"] for r in d["rows"][:100]] for d in cases]).mean(axis=(0, 1))
        axes[1, 0].plot(np.arange(1, len(means)+1), means, color=color, label=label)
        energy = [d["common_100_energy"] for d in cases]
        x = variants.index(variant)
        axes[1, 1].bar(x, np.mean(energy), yerr=np.std(energy, ddof=1),
                       color=color, alpha=0.7, capsize=5)
        axes[1, 1].scatter([x]*len(energy), energy, color="black", s=16, zorder=3)
    axes[0, 0].set(title="Modeled energy at unequal service lifetimes", xlabel="Completed rounds", ylabel="Cumulative energy (J)")
    axes[0, 1].set(title="Alive nodes while full-network routing continues", xlabel="Completed rounds", ylabel="Alive nodes")
    axes[1, 0].set(title="Within-round convergence, first 100 rounds", xlabel="Feasible ants evaluated", ylabel="Mean best fitness (J)")
    axes[1, 1].set(title="Matched 100-round energy: five seeds, mean ± SD", ylabel="Energy (J)", xticks=range(3), xticklabels=labels)
    for axis in axes.flat:
        axis.grid(alpha=0.2)
    axes[0, 0].legend()
    axes[1, 0].legend()
    fig.suptitle("Identical 3D map, shared acoustic model, seeds 0–4\nEndpoints mark stopping; stopped runs are not padded", fontsize=14)
    fig.savefig(output, dpi=180)
    plt.close(fig)
