---
title: "Faults Along an Apollo Descent"
subtitle: "The complete study — 180 injections, a relaxation ladder, and what separates a lost vehicle from a tight corridor"
date: "1 September 2026"
geometry: margin=2.2cm
fontsize: 10.5pt
numbersections: true
toc: true
colorlinks: true
header-includes:
  - \usepackage{booktabs}
  - \usepackage{amsmath}
  - \usepackage{float}
  - \let\origfigure\figure
  - \let\endorigfigure\endfigure
  - \renewenvironment{figure}[1][2]{\expandafter\origfigure\expandafter[H]}{\endorigfigure}
---

# Summary

This document is three campaigns in one argument.

**Study H** flies one Apollo-anchored nominal descent and injects
12 engine plants at 15 points along it — 180
optimal-control solves — to ask *where on the descent is this fault
survivable*. It lands 168 of them and finds
11 injections with no recovery trajectory at all.

**Study H-R** asks whether those failures are the vehicle or the problem
statement, by re-solving each at four progressively weaker corridors.
3 of them recover — all at the first level, the glide cone alone.

**The L5 diagnostic** removes every state constraint that remains, the altitude
floor included, leaving only the dynamics and the actuator bounds.
8 cases fail even there.

The three-line result:


| Result | Count | Reading |
|:----------------------------------------|:----------|:----------------------------------------------|
| Injections that land | 168 of 180 | Study H, inside the design corridor |
| Recoverable once the cone is relaxed | 3 | 2 still land in the Apollo gate |
| Feasible only with no state constraints at all | 1 | flies below the surface — a diagnostic, not a landing |
| Infeasible under every relaxation | 8 | resisted 22 seeds across five corridors |


The headline correction is the third and fourth lines together: Study H's
11 "unrecoverable" injections are really **8**
unrecoverable injections plus 3 that were fighting the corridor and
1 that is short only of the surface.

# The vehicle and the nominal

## Where the initial state comes from

The anchor is the published Apollo approach-phase (P64) geometry rather than an
invented state. Two points of that phase are well documented — high gate at
7,500 ft / 4.5 nmi / 500 ft/s, low gate at 500 ft / 2,000 ft / 60 ft/s — and
the approach between them is flown essentially straight at the landing point.
Interpolating along it to the speed this vehicle model admits with margin
gives:


| Anchor state | SI | Imperial |
|:--------------------------|:--------------|:--------------|
| Altitude | 736 m | 2416 ft |
| Range to pad | 2724 m | 8937 ft |
| Horizontal speed | 55.0 m/s | 180 ft/s |
| Descent rate | 15.6 m/s | 51 ft/s |
| Line-of-sight depression | 15.13° |  |
| Flight-path angle | 15.87° |  |


The last two lines are the consistency check: a vehicle flying the approach
points its velocity vector at the landing site, and these agree to
0.75°. **This is a reconstruction of the geometry,
not telemetry.**

Two properties of the vehicle matter for everything below. The engines sit at
$y = \pm0.25$ m, just inside the roll-trim limit
$y_{eng} \le dz_{eng}\tan\delta_{max}$ = 0.263 m, which is what makes
engine-out a fault with an answer rather than an automatic loss. And the glide
cone is 12°, lowered from the earlier studies' 30° because
Apollo's real approach is a ~15° path that a 30° cone forbids outright.


![The Apollo-anchored nominal descent](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/H1_nominal.png)


The healthy vehicle reaches contact at **t = 65 s** with a
gate margin of **0.60**.

# Study H — the injection campaign

At each injection point the state is read straight off the nominal — all 22 of
them — the plant becomes the damaged plant from that instant, and the vehicle
re-plans over the time the nominal had left plus a reserve. The healthy plant is
run from every point as a control.



![Outcome by fault and injection point](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/H2_grid.png)


This is the study's overview figure, and the one worth reading first: one cell
per solve, no averaging, time running left to right. Three groups fall out of
it immediately.


| Group | Faults | Which |
|:----------------------|:--------|:------------------------------------------------------------|
| Survive everywhere | 7 | TVC bias, chugging, $\eta$=1.30, $\tau_T$=2.5 s, mixture ratio, erosion drift, stuck open |
| Have a boundary | 4 | $\eta$=0.50, $\eta$=0.15, engine out, dead time |
| Never survive | 0 | — |


**The faults that fail do not fail randomly across the descent; they fail
late.** Every fault with a boundary has it in the braking phase, where the
vehicle is low, still fast, and has committed its remaining altitude to the
flare. A fault arriving during the cruise has hundreds of metres to trade for a
re-plan; the same fault arriving during the flare has none. Altitude is the
currency.


![Landing share by fault class against injection time](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/H3_survival.png)


![Gate margin against injection time, per fault](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/H4_margin.png)


# The trajectories in three dimensions

Every figure so far collapses the path into the range-altitude plane — the
plane the glide cone lives in, and therefore the plane the constraints are
argued in. It is not the plane the vehicle flies in. A one-engine-out LM yaws
under asymmetric thrust, the gimbal trims it, and what is left is a cross-range
excursion that a 2-D plot draws as nothing at all.


![Study H — every recovery in 3-D, one panel per plant](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/3D1_baseline_by_fault.png)


The panels are worth comparing against each other rather than read one at a
time. The thrust-magnitude faults stay in the vertical plane and differ from
the nominal mostly in *when* they brake. The asymmetric ones — engine out above
all — bulge sideways and come back, and the failures cluster at the end of the
descent where there is no room left to do that.

# Study H-R — is it the vehicle or the corridor?

## The question

The problem those failed solves could not satisfy carries a corridor of path
constraints, and not all of them are physics:


| Constraint | Study H value | What it actually is |
|:--------------|:--------------------------|:----------------------------------------------------------|
| Glide cone | 12° above horizontal | A scenario choice — it rules out the dive-and-crawl-back trajectory family, not something the vehicle cannot fly. |
| Attitude | 45° per axis | Planner comfort. `hard_loss()` puts real loss of control at 90°. |
| Body rate | 10°/s | Comfort again; `hard_loss()` uses 120°/s. |
| Speed | 60 m/s per axis and as a norm | The model has no aerodynamic or structural speed limit at all. |


So "no trajectory exists" may mean "no trajectory exists **that stays inside
the corridor**" — a very different engineering statement.

## The ladder


| Level | Corridor | Constraints removed outright |
|:--------|:----------------------------------------------|:------------------------------|
| L1 | glide cone 12 to 6 deg | none dropped |
| L2 | + attitude 45 to 60 deg, rate 10 to 20 deg/s | none dropped |
| L3 | + speed 60 to 90 m/s (axis and norm) | none dropped |
| L4 | corridor removed (cone, speed, attitude, rate) | cone, vel, att, rate |
| L5 | all state constraints removed, altitude floor included | cone, vel, att, rate, alt |


Thrust and gimbal bounds stand at every level — they are hardware. The Apollo
gate stands at every level: a relaxed solve still has to touch down inside the
same gate to count as a landing. The altitude floor stands through L4 and is
dropped only at **L5**, where *nothing constrains the state anywhere in the
problem*.

Effort is matched deliberately. Study H spent 7 seeds at up to 1,200 iterations
on each of these cases; each ladder level adds 3 horizon seeds
at 1,200, so a case still infeasible at L5 has resisted
**22 seeds**.

## What the ladder found



![The weakest relaxation that admits a trajectory](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/HR1_ladder.png)


| Fault | Injected | Altitude | Study H | Solved at | Outcome | Gate margin | Binding baseline limit |
|:----------------------|:----------|:----------|:--------------|:----------|:--------------|:------------|:--------------------|
| dead time | 17 s | 419 m | no recovery | — | no recovery | — | n/a |
| dead time | 25 s | 282 m | no recovery | — | no recovery | — | n/a |
| dead time | 30 s | 212 m | no recovery | — | no recovery | — | n/a |
| dead time | 38 s | 109 m | no recovery | — | no recovery | — | n/a |
| dead time | 55 s | 8 m | no recovery | — | no recovery | — | n/a |
| engine out | 38 s | 109 m | gate miss | L1 | gate miss | 6.88 | glide cone |
| engine out | 42 s | 56 m | no recovery | — | no recovery | — | n/a |
| engine out | 46 s | 19 m | no recovery | L5 | subsurface | 0.60 | altitude floor |
| engine out | 51 s | 4 m | no recovery | L1 | land | 0.60 | glide cone |
| $\eta$=0.50 | 46 s | 19 m | no recovery | L1 | land | 0.60 | glide cone |
| $\eta$=0.15 | 42 s | 56 m | no recovery | — | no recovery | — | n/a |
| $\eta$=0.15 | 46 s | 19 m | no recovery | — | no recovery | — | n/a |


**Everything that recovered, recovered at L1.** The attitude, rate and speed
relaxations unlocked nothing at all: no case anywhere in this study was limited
by how hard it was allowed to pitch, spin or fly. The single binding constraint
in the whole campaign is the glide cone, and the recoveries that need it fly a
6.0–6.8°
path against a 12° floor. They are *shallower* approaches, not
more violent ones.


![Peak excursion beyond each baseline limit](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/HR2_excursions.png)


These excursions are measured **after the post-fault transient**, from node
6 onward. `solve_ocp` opens a corridor over the first
6 nodes — up to 3× the rate limit — that shrinks to the nominal
envelope, and the baseline problem opens it too. An excursion inside that window
is something Study H already permitted, so counting it would credit the recovery
to the wrong constraint: measured over the whole trajectory two of these
recoveries look bought by the body-rate limit at ~2×; measured after the ramp
their rate and attitude peaks are exactly 1.00× and only the cone is broken.


![What the relaxation bought, in 3-D](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/3D2_relaxed_by_case.png)


# The L5 diagnostic — removing the state constraints entirely

L5 is not a corridor. With the altitude floor gone there is no constraint on
the state left in the problem; only the dynamics and the actuator bounds remain.
A trajectory found there may pass through the lunar surface, so it is **not a
landing** and is not counted as one. Its job is to split the remaining failures
in two: cases where the state constraints were the obstacle, and cases where the
plant simply cannot do it.

**1 of the 11 found a trajectory at L5**
and it dives as deep as 57 m below the surface.


![The trajectory that exists only without the altitude floor](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/3D3_subsurface.png)


This case is the study's sharpest methodological warning. Its touchdown scores a
clean gate margin of 0.60 — the gate inspects only the final
state — at the end of a path that spent most of its length underground. **A
trajectory that satisfies the terminal criteria is not necessarily a landing**,
and any campaign scoring recoveries on a terminal gate alone needs a path check
to go with it.

The other **8** cases fail even with no state constraints at all.
They are short of control authority outright, and no guidance law, however
permissive, recovers them.

# What the three campaigns mean together

**A solver's "infeasible" is a property of the constraint set, and must be
reported as one.** 11 failures became 8 once the
same states and the same plants were given a wider corridor. Any study that
reports fault survivability from a constrained planner is reporting its
constraints as much as its vehicle, and the only way to know the split is to
vary them deliberately.

**Severity should be quoted with the corridor attached.** "Unrecoverable after
t = X" is incomplete. The defensible form is "unrecoverable after t = X inside a
12° cone, and after t = Y with the cone opened to 6°" — and
the gap between the two numbers is exactly the value of an envelope-expanding
guidance mode.

**The cone is doing more work than any other constraint.** It was chosen for a
near-vertical scenario, inherited into a shallow Apollo approach, and it is the
single limit that decides 3 of these cases. Nothing else in the corridor
mattered anywhere in the campaign. If one number in this problem statement
deserves re-derivation from vehicle and mission requirements rather than
convenience, it is that one.

**Altitude is the currency, and the boundary is a time.** Every fault with a
boundary has it late, in the braking phase. The single number a fault-tolerance
budget should carry is the injection time past which recovery stops existing —
and after this study, two of them: one for the design corridor and one for the
open one.

**8 genuine losses, not 11.** After five corridors
and 22 seeds, the failures that remain are
$\eta$=0.15, dead time, engine out — and all five
dead time injections are among
them. That is a smaller and much better-defended claim than the campaign
originally supported.

# Limitations

* **Local infeasibility is not global.** 22 seeds is strong
  evidence, not proof.
* **Instantaneous, perfect detection.** No isolation, identification or reaction
  delay; every number here is an upper bound. Studies D and E measure the gap.
* **Open loop.** Each result is one solve, not a closed loop re-solving as it
  flies.
* **One nominal.** All 180 solves depart from a single reference
  trajectory; a steeper or faster approach would move the boundaries.
* **The relaxed limits are round numbers**, chosen to bracket the baseline
  rather than derived from vehicle structure. The ladder localises which
  constraint binds, not the exact threshold.
* **Constant mass**, inherited from the base model, understating the propellant
  cost of a partial fault.
* **15 injection points** resolve a boundary to about
  4 s.

# Reproducing

```bash
python studies/fault_injection/apollo_nominal.py           # the reference descent
python studies/fault_injection/run_injection_study.py      # Study H campaign
python studies/fault_injection/harden.py                   # H hardening pass
python studies/fault_injection/analyse_injection.py        # H figures + JSON
python studies/fault_injection/run_relaxed_study.py        # H-R ladder, L1-L4
python studies/fault_injection/run_relaxed_study.py --extend L5   # the L5 diagnostic
python studies/fault_injection/analyse_relaxed.py          # H-R figures + JSON
python studies/fault_injection/plot_trajectories_3d.py     # the 3-D figures
python studies/fault_injection/build_combined_report.py    # this document
```
