# Engine placement — setting `y_eng` from measured authority

**Question.** Every fault study here flies an imaginary vehicle: the Apollo LM's
single DPS engine split into two half-thrust engines at `y = ±y_eng`. Mass,
inertia, total thrust, gimbal throw and the whole RCS are the real LM's — only
the spacing is invented, and it was invented twice by assumption (1.50 m in
Studies A–G, 0.25 m in Study H). This study sets it by measurement, against the
one reference that matters: **the real Apollo LM's own achievable
accelerations**, computed with the same envelope machinery as the fleet survey.

## What the spacing controls

| | Real LM | Twin-engine, `y_eng` 0 → 2 m |
|---|---|---|
| Linear `a_x, a_y, a_z` | 0.77, 0.77, 6.07 m/s² | **unchanged** — a moment arm cannot make force |
| Pitch `α_y` | 148 °/s² | **unchanged** — pitch is gimbal × `dz_eng` |
| Roll `α_x` | 148 °/s² | 148 → 564 °/s² |
| Yaw `α_z` | 34 °/s² | 34 → 141 °/s² |

Splitting the engine cannot change what the vehicle accelerates at, and cannot
change its pitch authority. What it does is **invent roll and yaw authority the
real vehicle never had**.

## The result

One threshold governs the answer, and it turns up twice from independent
reasoning:

* **roll stays exactly at the real LM's 148 °/s²** up to `y_eng` = 0.263 m,
  because below that the best roll moment is still the gimbal one;
* **one-engine-out is trimmable** only while `y_eng ≤ dz_eng·tan(δ_max)` =
  0.263 m (Study A's roll budget).

Both ask the same question — is the lateral moment arm longer than the arm the
gimbal already commands? Below it the split adds nothing and a surviving gimbal
can undo a dead engine; above it the vehicle gains authority it never had and
the lone gimbal can no longer trim it.

**Recommendation: keep `y_eng` = 0.25 m** as a *modelling* choice. Roll and
pitch are then exactly the real LM's, engine-out stays trimmable, and the price
is +39 % yaw (+13 °/s² on an axis that has 34 — the LM's weakest, served almost
entirely by RCS).

**At 1.50 m, Studies A–G flew a vehicle with 3.0× the roll and 3.3× the yaw
authority of a real Apollo LM.** Their engine-out result is unaffected (that
fault was lost to the trim budget, which 1.50 m misses by 5.7×), but their
gimbal-fault and thrust-asymmetry results were measured on an over-actuated
vehicle.

## The configuration finding

Two half-DPS nozzles cannot sit closer than ~0.54 m half-spacing without
overlapping. That is already past the 0.263 m threshold, so **a twin-engine
Apollo-class lander with only 6° of gimbal throw cannot be both buildable and
single-engine-out survivable.** The gimbal is the binding parameter, not the
spacing: a buildable layout would need δ_max ≥ 12.1°, a little over double the
LM's actual throw.

## Running

```bash
python place_engines.py     # -> engine_placement.pdf, placement_sweep.csv
```

## Outputs

```
engine_placement.pdf            the write-up
placement_sweep.csv             y_eng vs all six accelerations and their ratios
figures/P1_placement_sweep.png  authority and authority-ratio against spacing
```
