# Optimizer results across two maps

## Current rerandomized map

The map hash is b7e43b90e548de14743b4f5361f32484b58a99439451ff866434839849542532.
Energy is measured over the same first 2073 fully alive/served rounds for every
seed and candidate, against the matched SimpleACO cohort. Lifetime is capped at
3500. There are 12 complete three-seed cohorts, including 7 new sampler proposals.
Six new proposals satisfy the +2% energy cap. None of the completed new proposals
beats the supplied rounded baseline on lifetime. Trial 7 improves its mean by
only 2.67 rounds; this small difference does not establish a robust improvement.
Trial 21 is incomplete after source edits interrupted the controller.
Runtime of 173.70 minutes includes finishing active trials after the 150-minute
admission cutoff. This is not a controlled algorithm-speed benchmark.
The machine-readable `optimizer-results.json` retains all complete metrics and
parameter vectors, including new proposals, rather than just the top-five anchors.

# Optimizer campaign results

Stop: controller_error. H=3500, T_max=3500, K=2073 (configured limit 2611).

|Trial|Status|Parameter origin|Service|Energy K|Feasible|
|---|---|---|---:|---:|---|
|14|complete|sampler_proposal|2457.6666666666665|34.070825883758474|True|
|15|complete|sampler_proposal|2447.3333333333335|32.26270676691036|True|
|0|failed|reused_anchor|incomplete||False|
|1|failed|reused_anchor|incomplete||False|
|2|failed|reused_anchor|incomplete||False|
|3|failed|reused_anchor|incomplete||False|
|4|failed|reused_anchor|incomplete||False|
|5|complete|user_rounded_previous_parameters|2640.3333333333335|31.20723880295005|True|
|6|complete|reused_anchor|2617.6666666666665|30.741817015824942|True|
|7|complete|reused_anchor|2643|30.961518049361032|True|
|8|complete|reused_anchor|2566.6666666666665|31.934910349537176|True|
|9|complete|reused_anchor|2604.6666666666665|30.397605822003698|True|
|10|deferred|reused_anchor|incomplete||False|
|11|deferred|reused_anchor|incomplete||False|
|12|deferred|reused_anchor|incomplete||False|
|13|deferred|reused_anchor|incomplete||False|
|16|complete|sampler_proposal|2356.3333333333335|34.46489259987704|False|
|17|complete|sampler_proposal|2395.6666666666665|34.21951746353969|True|
|18|complete|sampler_proposal|2556.6666666666665|31.63578169866338|True|
|19|complete|sampler_proposal|2510.3333333333335|32.532340072328985|True|
|20|complete|sampler_proposal|2490|32.47154734614724|True|
|21|paused|sampler_proposal|incomplete||False|

Completed cohorts: 12. Feasible completed cohorts: 11. Active wall time: 173.70 minutes.

## Best completed trial versus matched SimpleACO

Trial 7: mean service 2643.00 versus 2321.00 rounds (+13.87%).
Mean physical energy over K=2073: 30.961518 versus 33.582774 J (7.81% lower). The +2% cap is 34.254429 J.

|Seed|SimpleACO rounds|D-ACO rounds|SimpleACO energy K (J)|D-ACO energy K (J)|
|---|---:|---:|---:|---:|
|24|2307|2646|33.654114|30.857991|
|25|2324|2668|33.451207|30.950541|
|26|2332|2615|33.643001|31.076021|

## Five best feasible configurations

### Trial 7

```json
{
  "num_ants": 40,
  "max_clustering_attempts": 10,
  "CH_proportion": 0.2,
  "alpha": 1.8,
  "beta": 0.45,
  "gamma": 0.2,
  "density_decay": "parabolic",
  "load_power": 2.6,
  "load_density_weight": 0.84,
  "reference_memory": 0.8,
  "calibration_ants": 40,
  "density_epsilon": 1e-12,
  "hopping_factor": 0.4,
  "rho_min": 0.36,
  "rho_max": 0.52,
  "Q": 9.5,
  "theta": 0.84,
  "tau0": 1.0,
  "tau_min": 1.0,
  "tau_max": 25
}
```

### Trial 5

```json
{
  "num_ants": 40,
  "max_clustering_attempts": 10,
  "CH_proportion": 0.2,
  "alpha": 1.8,
  "beta": 0.04,
  "gamma": 0.6,
  "density_decay": "parabolic",
  "load_power": 2.6,
  "load_density_weight": 0.84,
  "reference_memory": 0.8,
  "calibration_ants": 40,
  "density_epsilon": 1e-12,
  "hopping_factor": 0.4,
  "rho_min": 0.36,
  "rho_max": 0.52,
  "Q": 9.5,
  "theta": 0.84,
  "tau0": 1.0,
  "tau_min": 1.0,
  "tau_max": 25
}
```

### Trial 6

```json
{
  "num_ants": 40,
  "max_clustering_attempts": 10,
  "CH_proportion": 0.2,
  "alpha": 1.8,
  "beta": 0.225,
  "gamma": 0.1,
  "density_decay": "parabolic",
  "load_power": 2.6,
  "load_density_weight": 0.84,
  "reference_memory": 0.8,
  "calibration_ants": 40,
  "density_epsilon": 1e-12,
  "hopping_factor": 0.4,
  "rho_min": 0.36,
  "rho_max": 0.52,
  "Q": 9.5,
  "theta": 0.84,
  "tau0": 1.0,
  "tau_min": 1.0,
  "tau_max": 25
}
```

### Trial 9

```json
{
  "num_ants": 40,
  "max_clustering_attempts": 10,
  "CH_proportion": 0.2,
  "alpha": 1.8443776383168635,
  "beta": 0.04107401092728735,
  "gamma": 0.6060200962856602,
  "density_decay": "parabolic",
  "load_power": 2.5886206172339983,
  "load_density_weight": 0.42607079321081437,
  "reference_memory": 0.8,
  "calibration_ants": 40,
  "density_epsilon": 1e-12,
  "hopping_factor": 0.4,
  "rho_min": 0.36472343993718964,
  "rho_max": 0.5203352372897225,
  "Q": 9.511346558794795,
  "theta": 0.8363876748180215,
  "tau0": 1.0,
  "tau_min": 1.0,
  "tau_max": 25.281955143438616
}
```

### Trial 8

```json
{
  "num_ants": 40,
  "max_clustering_attempts": 10,
  "CH_proportion": 0.2,
  "alpha": 1.8,
  "beta": 0.04,
  "gamma": 0.6,
  "density_decay": "parabolic",
  "load_power": 2.6,
  "load_density_weight": 0.84,
  "reference_memory": 0.8,
  "calibration_ants": 40,
  "density_epsilon": 1e-12,
  "hopping_factor": 0.4,
  "rho_min": 0.36,
  "rho_max": 0.52,
  "Q": 20.0,
  "theta": 0.84,
  "tau0": 1.0,
  "tau_min": 1.0,
  "tau_max": 25
}
```


3500 is right-censored, not observed termination. Partial cohorts are not ranked. No defaults are promoted.


## Previous map and 3000-round campaign

Map hash d9e086fde395ff10a4348122727bc2af6972dffa25d5f92afa37ed0d56ca4b05;
seeds 24/25/26; energy window 2611. Best trial 25 reached the 3000-round horizon
on all seeds (right-censored), using 38.290824 J versus SimpleACO 42.466116 J
(9.83% lower energy). SimpleACO averaged 2936 service rounds. The previous result
must not be compared numerically with the current map's different K or horizon.
Its prior parameters seed future studies; old scores are not imported as new observations.

Best old parameters:

```json
{
  "num_ants": 40,
  "max_clustering_attempts": 10,
  "CH_proportion": 0.2,
  "alpha": 1.8443776383168635,
  "beta": 0.04107401092728735,
  "gamma": 0.6060200962856602,
  "density_decay": "parabolic",
  "load_power": 2.5886206172339983,
  "load_density_weight": 0.42607079321081437,
  "reference_memory": 0.8,
  "calibration_ants": 40,
  "density_epsilon": 1e-12,
  "hopping_factor": 0.4,
  "rho_min": 0.36472343993718964,
  "rho_max": 0.5203352372897225,
  "Q": 9.511346558794795,
  "theta": 0.8363876748180215,
  "tau0": 1.0,
  "tau_min": 1.0,
  "tau_max": 25.281955143438616
}
```
