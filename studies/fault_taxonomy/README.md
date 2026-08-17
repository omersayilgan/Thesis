# Study G — Fault taxonomy × initial-condition regime

**Question.** The earlier case studies each took one fault and flew it well.
This one takes the fault catalogue of
[`docs/spacecraft_engine_fault_framework.md`](../../docs/spacecraft_engine_fault_framework.md)
and instantiates one plant per dynamic-effect category, then measures the
**landing probability of every fault from five qualitatively different regions
of the state space**.

The deliverable is the landing probability over the product

```
16 fault cases  x  5 initial-condition regimes  x  n initial conditions
```

The regimes were **calibrated**, not guessed: a pilot sweep established that
this recovery planner absorbs almost everything from a high, calm approach, so
regime boxes were tightened until the healthy control itself starts failing.
Without that step the whole matrix saturates at 1.00 and measures nothing.

The initial conditions are **shared across faults**, so any difference within a
regime is attributable to the plant alone (common random numbers), and the
healthy-vs-fault comparison is a within-sample McNemar test.

## The faults

All act on engine 2; engine 1 stays healthy, so every case is an asymmetry to
trim as well as a loss of performance. The column that matters is the FTC fault
structure of framework section 3 — additive / multiplicative / structural — the
classification that decides what a controller has to *do*.

| Fault | Framework § | Structure |
|---|---|---|
| healthy (control) | — | — |
| thrust reduction, η=0.50 / η=0.15 | 2.1 | multiplicative ΔB |
| thrust excess, η=1.30 | 2.2 | multiplicative ΔB |
| valve stuck open (thrust floor) | 2.2 / 1.4 | structural (input set) |
| engine out | 2.1 / 3.1 | structural |
| slow thrust response, τ_T=2.5 s | 2.5 | multiplicative ΔA |
| gimbal bandwidth loss, ω_n=0.6 | 2.5 | multiplicative ΔA |
| gimbal underdamped, ζ=0.25 | 2.3 / 2.8 | multiplicative ΔA |
| gimbal seizure | 1.7 | structural |
| TVC effectiveness loss (35 %) | 2.7 | multiplicative ΔB |
| thrust-vector misalignment (3°, 2°) | 2.7 | additive |
| thrust oscillation (chugging) | 2.3 | additive, forced |
| transport delay (1 interval) | 2.6 | structural |
| mixture-ratio shift (coupled) | 2.4 | coupled ΔB + ΔA |
| throat-erosion drift | 2.10 | time-varying multiplicative |

## The regimes

| Regime | What it is |
|---|---|
| `approach` | high and descending with small dispersions — the fault is the only thing wrong |
| `dispersed` | Study F's wide 22-D box |
| `upset` | already rotating (≥ 10 °/s) or tilted (≥ 15°) with the gimbals deflected |
| `low_late` | 60–200 m and still descending |
| `critical` | below 140 m, descending hard, tilted and rotating — even the healthy vehicle often has no trajectory left |

## Model changes this study required

Four faults needed the vehicle model extended; all additions default to the
healthy plant, so every earlier study is unaffected.

* `LMParams` grew per-engine `tau_T_eng`, `T_min_eng_ovr`, `gimbal_eff_eng`,
  `gimbal_bias_eng`, `gimbal_lock_eng`, `thrust_osc_eng`, `eta_rate_eng`,
  `u_delay_eng`.
* `flat_moon_6dof` takes a trajectory time `t` (default 0), which is what makes
  the time-varying faults — parametric drift and forced oscillation —
  integrable at all. The integrators thread it through their stages.
* `fault_lib.delayed_controls` implements dead time as an exact zero-order-hold
  index shift on the delayed engine's commands, not a Padé approximation.

## Running

```bash
python run_taxonomy_study.py 10      # the campaign  (~2 h on 5 workers)
python analyse.py                    # figures + results/headline_G.json
python build_report.py               # fault_taxonomy_case_study.pdf
```

`FAULT_WORKERS` controls parallelism (default 4; each worker peaks around
1.4 GB).

## Outputs

```
results/G_samples.csv      one row per solve
results/G_states.npz       the sampled initial conditions, per regime
results/headline_G.json    every number the report quotes
figures/G1_heatmap.png     landing probability, fault x regime
figures/G2_forest.png      pooled landing rate per fault, Wilson intervals
figures/G3_paired.png      paired survival against the healthy control
figures/G4_outcomes.png    outcome composition (how the failures fail)
figures/G5_altitude.png    landing rate against initial altitude, by class
figures/G6_margin.png      gate-margin distribution over solved cases
fault_taxonomy_case_study.pdf
```
