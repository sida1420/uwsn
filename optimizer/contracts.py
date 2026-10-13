from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class StudyContext:
    network_horizon: int = 3500
    adaptive_total_rounds: int = 3500
    energy_reference_window: int = 2611

class AlgorithmAdapter(Protocol):
    name: str
    adapter_version: str
    parameter_space_version: str
    native_fitness_id: str
    def baseline_config(self) -> dict: ...
    def validate_config(self, cfg: dict) -> None: ...
    def make_algorithm(self, network, hparams, cfg: dict, seed: int): ...
    def diagnostics(self, algorithm) -> dict: ...
