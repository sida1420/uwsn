# Excluded screening runs

These initial checkpoint screens shared a mutable pheromone matrix through `long_run.restore`. Later configurations could inherit earlier configurations' updates. Results depended on configuration order and must not be used as evidence.

The restore helper now deep-copies checkpoint fields. All checkpoint screens were rerun from isolated states, with a regression test verifying isolation. Fresh physical trajectories instantiate independent optimizers and were unaffected.
