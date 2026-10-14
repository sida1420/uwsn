"""Named, spawn-picklable preset for the reported energy-only V2+V6 variant."""
from dataclasses import replace

from algorithms.clustering.ac_aco.parameters import ACACOParameters
from algorithms.research_acaco import ResearchACACO, ResearchOptions


class ACACO_V2_V6(ResearchACACO):
    """Marginal construction and evaporation-only chaos; no parameter retuning."""

    name = "AC-ACO-V2-V6"

    def __init__(self, network, hparameters, seed=None):
        # Same overrides as run-experiments.py make_algorithm('V2+V6', ..., 40).
        # Bounds are explicit because production's current floor differs from the audit.
        params = replace(ACACOParameters(), num_ants=40, load_weight=0.0,
                         tau0=1.0, tau_min=0.01, tau_max=20.0)
        options = ResearchOptions(heuristic="marginal", chaos_policy="evaporation",
                                  evaporation_kappa=0.5)
        super().__init__(network, hparameters, params=params, seed=seed, options=options)
