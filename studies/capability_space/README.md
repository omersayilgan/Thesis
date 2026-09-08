# Study I — fault impacts in capability space

**Question.** Studies G/H/H-R ask whether a damaged vehicle can still fly a
trajectory. This one asks what it can push and twist with *at all*: the
attainable force set (AFS), the attainable moment set (AMS), and the 6-D
wrench set an operating point has to lie inside.

## What it computes

| Object | How |
|---|---|
| AFS / AMS | support-function sweep over 1200 directions, convex hull |
| conditional AMS | LP per direction: moments attainable **while** producing hover thrust |
| operating point | LP: can the vehicle produce the hover wrench, and with what residual |
| trim threshold | the same LP swept over engine half-spacing |
| redundancy | the same measures with one actuator removed, unit by unit |

## The headline

Every fault in the Study H catalogue leaves the hover wrench attainable — and
four of them still have injection points from which no trajectory exists.
Capability space is necessary and not sufficient: transport delay and slow
thrust response leave the sets **identical to healthy** and are the least
survivable faults in the campaign.

The classification the study produces:

| Effect | Faults |
|---|---|
| shrink | thrust loss (η=0.15, η=0.50), mixture-ratio shift, chugging, engine out |
| enlarge | thrust excess (η=1.30), TVC bias |
| puncture | valve stuck open — the origin leaves the set |
| nothing | transport delay, slow thrust response, erosion drift (at onset) |

## Running

```bash
python run_capability_study.py    # -> results/*.csv + headline_I.json
python plot_capability.py         # -> figures/I0..I6
python build_report.py            # -> capability_space_case_study.pdf
```

## Outputs

```
results/I_faults.csv        one row per fault: volumes, axes, origin, LP slacks
results/I_erosion.csv       the drifting fault, sampled in time
results/I_redundancy.csv    one row per actuator removed
results/I_spacing.csv       engine-out trim against engine half-spacing
results/headline_I.json     every number the report quotes
figures/I0_capability_grid.png   overview grid, fault x capability test
figures/I1_sets.png              AFS and AMS, healthy and damaged
figures/I2_metrics.png           what each fault costs, three measures
figures/I3_capability_vs_survival.png   the central negative result
figures/I4_redundancy.png        the price of one actuator
figures/I5_spacing.png           the trim threshold, recovered by LP
figures/I6_erosion.png           a fault moving through capability space
capability_space_case_study.pdf
```

## Validation

The engine-out trim threshold is derived twice by different routes: Study A's
algebraic `y_eng <= dz_eng * tan(gimbal_max)` = 0.263 m, and this study's LP
sweep, which finds the last trimmable spacing at 0.258 m on a grid of 0.005 m.
