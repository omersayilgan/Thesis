# Study H — Faults injected along an Apollo descent

**Question.** Study G asked "from how much of the state space is this fault
survivable". This one asks the question a mission analyst actually has:
**where on the descent can this fault be survived?**

It computes one nominal descent for a healthy vehicle, walks along it, and
injects each fault at 15 points. Every injection point carries a time, an
altitude, a range and a speed, so the answer is a function of *when* rather
than a statistic over a box.

## What changed from Study G

| | Study G | Study H |
|---|---|---|
| Initial conditions | Sobol boxes, 5 regimes | points on one nominal trajectory |
| Engine half-spacing | 1.50 m | **0.25 m** (inside the 0.263 m roll-trim limit) |
| Scenario | near-vertical, 1000 m / 320 m range | Apollo P64 approach, 736 m / 2724 m range |
| Glide cone | 30° | 12° (Apollo's real path is ~15°) |
| Speed limit | per-axis 60 m/s | per-axis **plus** a 60 m/s norm cap |
| Faults | 16 | 12 — the gimbal-actuator faults removed |

The engine move is the substantive one. A single gimbal can trim a
one-engine-out asymmetry only while `y_eng <= dz_eng * tan(gimbal_max)` =
0.263 m. At 1.50 m engine-out was unrecoverable from every state Study G tested,
which measured nothing; at 0.25 m it becomes a fault with an answer.

## The nominal

Anchored on the published Apollo approach-phase (P64) geometry — high gate
(7,500 ft, 4.5 nmi, 500 ft/s) and low gate (500 ft, 2,000 ft, 60 ft/s) —
interpolated along the straight-in path to the point where horizontal speed has
bled to 55 m/s:

```
altitude 736 m   range 2724 m   55 m/s horizontal   15.6 m/s descent
line-of-sight depression 15.13°     flight-path angle 15.87°
```

Those last two agreeing to 0.75° is the consistency check: a vehicle flying the
approach points its velocity vector at the landing site. It is a reconstruction
of the geometry, **not telemetry** from any particular mission.

Two fixes the reference trajectory needed, both recorded in the report:

* **a spherical speed cap.** The model's velocity limit is a per-axis box, so a
  vehicle riding all three axes reaches 104 m/s. Harmless on a near-vertical
  descent; on a 2.7 km shallow approach the first solve accelerated downrange,
  rode the 45° pitch limit, overshot the pad and came back. `OCPConfig` gained
  an optional `V_norm_max`, defaulting to off so earlier studies are unaffected.
* **a fitted horizon.** Surplus planning time gets spent wandering. A probe
  solve times the descent; the trajectory is re-solved on a horizon just long
  enough to contain it.

Result: cruise at the cap down the 15° path, brake from ~40 s, contact at 65 s,
touchdown on the pad with gate margin 0.60.

## Running

```bash
python apollo_nominal.py         # the reference descent  -> results/nominal.npz
python run_injection_study.py    # 12 plants x 15 points  -> H_samples.csv
python harden.py                 # re-attack every no_recovery with 6 seeds
python analyse_injection.py      # figures + headline_H.json
python build_report.py           # fault_injection_case_study.pdf
```

`FAULT_WORKERS` controls parallelism (default 4).

## Outputs

```
results/nominal.npz          the reference trajectory and its anchor
results/H_samples.csv        one row per solve
results/H_trajectories.npz   every recovery path (saved during the campaign)
results/headline_H.json      every number the report quotes
figures/H1_nominal.png       the nominal, with the injection points marked
figures/H2_grid.png          outcome by fault x injection point
figures/H3_survival.png      landing share by fault class against injection time
figures/H4_margin.png        gate margin against injection time, per fault
figures/H5_trajectories.png  the recoveries themselves, against the nominal
fault_injection_case_study.pdf
```
