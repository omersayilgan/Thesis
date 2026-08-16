# Actuation envelopes — achievable force and moment sets

Per-spacecraft 3-D actuation envelopes for the 21 vehicles in
`ExcelSheets/spacecraft_values.xlsx`, plus a summary workbook of per-axis
maximum linear and angular acceleration.

```
python build_report.py
```

## Outputs

| Path | Contents |
|---|---|
| `figures/<Spacecraft>.png` | 3 panels — actuator layout, achievable force set, achievable moment set |
| `figures/_fleet_comparison.png` | best-vs-worst axis authority across the fleet |
| `actuation_envelope_summary.xlsx` | `Max acceleration`, `Max force-moment`, `Provenance`, `Method` |

## Files

| File | Role |
|---|---|
| `geometry_db.py` | data model, inertia shape models, reusable actuator layouts |
| `vehicles.py` | per-vehicle dimensions, gimbal limits, layout choice, provenance flags |
| `envelopes.py` | support functions, achievable sets, per-axis maxima |
| `plots.py` | figures |
| `build_report.py` | runner |

## The data gap you must know about

`spacecraft_values.xlsx` supplies thrust magnitudes, actuator counts and
masses. It contains **no thruster positions, no thrust direction vectors, no
gimbal limits and no inertia tensors** — all four were checked for and are
absent. They are supplied in `vehicles.py` / `geometry_db.py`.

Every input carries a provenance flag, and the `Provenance` sheet lists all of
them. Currently **87 SOURCED, 82 ESTIMATED, 1 MISSING**.

- **SOURCED** — read from the workbook, or from this repository's validated
  Apollo LM model (`apollo_full.py`).
- **ESTIMATED** — an engineering assumption made here, with its basis written
  into the flag text.

Rows whose geometry is ESTIMATED give **moments and angular accelerations that
are indicative, not authoritative**. Forces and linear accelerations depend
only on thrust and mass and are therefore on much firmer ground than the
moment-derived quantities.

The single most trustworthy row is the **Apollo Lunar Module**: its layout,
gimbal limit and inertia all come from `apollo_full.py`, and the generated
thruster set reproduces that model's 6×16 allocation matrix exactly.

## Method

Each RCS thruster is throttleable in `[0, F]` along a fixed direction, so it
contributes a line segment; summed over thrusters that is a zonotope. Each
gimballed engine contributes `T·d` with `T ∈ [0, T_max]` and `d` sweeping a
spherical cap of half-angle equal to the gimbal limit. The reported set is the
**convex hull** of the total, recovered by a support-function sweep over a
Fibonacci sphere:

```
RCS force     h(u) = Σ F_i · max(0, u·d_i)
RCS moment    h(u) = Σ F_i · max(0, u·(r_i × d_i))
engine        maximise over the cap, using u·(r × d) = d·(u × r)
```

Max force along an axis is the support function evaluated on that axis; `+x`
and `−x` are reported separately because layouts are frequently asymmetric.
Then `a = F/m` and `α_j = M_j / I_jj`.

## Standing caveats

- **Inertia is a shape model.** Uniform-density cylinder or box from mass plus
  an approximate published envelope (except the LM). Uniform density
  understates inertia for a vehicle with heavy peripheral items, and therefore
  **overstates** angular acceleration.
- **`α_j = M_j / I_jj` neglects coupling** — products of inertia and the
  gyroscopic term `ω × (Iω)`. It is an instantaneous, small-rate figure.
- **Moment arms are about the geometric CG.** The real CG moves with
  propellant load, which changes every arm and hence the whole moment set.
- **Three vehicles are excluded** (Sentinel-1A, GOES-16, GOES-19): the
  workbook records `n/d` for both their thrust and their actuator counts.

## Zero-authority axes are real, not bugs

Several vehicles legitimately show zero moment about an axis:

- **Ariane 5 ECA, Vega, Vega-C** — a single gimballed engine on the centreline
  produces pitch and yaw but no roll about its own thrust axis, and the
  workbook lists no vehicle-level RCS. Real launchers get roll authority from
  systems the workbook does not tabulate.
- **Europa Clipper** — 24 rigidly mounted engines on a ring, all axial: pitch
  and roll, no yaw.
- **Juno** — a fixed, non-gimballed main engine and an RCS whose per-unit
  thrust the workbook records as `n/d`, so no moment can be formed at all.

Two earlier zeros *were* generator bugs and are fixed: deriving the cluster
count as `n/4` put 8 thrusters into 2 collinear clusters (no roll), and canting
a thruster ring purely radially gives no tangential component (no yaw). Both
functions now document the trap.
