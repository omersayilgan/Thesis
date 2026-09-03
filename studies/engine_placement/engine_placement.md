---
title: "Where to Put the Two Engines"
subtitle: "Setting the twin-engine Apollo LM's spacing from measured authority instead of by assumption"
date: "26 August 2026"
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

# The parameter that was never justified

Every fault study in this repository flies an imaginary vehicle: the Apollo
LM's single Descent Propulsion System engine split into two half-thrust engines
mounted at $y = \pm y_{eng}$. Mass, inertia, total thrust, gimbal throw and
the entire RCS are the real LM's. Only the placement is invented — and it was
invented twice, both times by assumption: **1.50 m** in Studies A through G,
**0.25 m** in Study H after the one-engine-out roll budget showed 1.50 m could
never be trimmed.

Neither number was ever checked against what an Apollo-class lander's
rotational authority actually is. The fleet actuation-envelope survey now
supplies that reference, and it supplies it for the most relevant vehicle
possible: **the real Apollo LM itself**. This document sets $y_{eng}$ by
measurement.

# What the spacing does and does not change

Both vehicles are built and measured with the same machinery used for the
fleet survey — the support function of the achievable force set and of the
achievable moment set, evaluated on each body axis. Body axes are the flight
model's: $x$ forward, $y$ right, $z$ **down along the thrust line**, so
rotation about $x$ is roll, about $y$ pitch, about $z$ yaw.

The sweep shows immediately that only two of the six quantities are in play:


| Quantity | Real LM | Twin-engine, $y_{eng}$ = 0 → 2 m | Why |
|:----------------------|:--------------|:--------------------------|:--------------------------------------------|
| Linear $a_x, a_y, a_z$ | 0.77, 0.77, 6.07 m/s² | unchanged at every spacing | total thrust and mass are fixed; a moment arm cannot make force |
| Pitch $\alpha_y$ | 148 °/s² | unchanged at every spacing | pitch comes from gimbal deflection against $dz_{eng}$, which $y_{eng}$ does not touch |
| Roll $\alpha_x$ | 148 °/s² | 148 → 564 °/s² | differential throttling between the two engines, arm $y_{eng}$ |
| Yaw $\alpha_z$ | 34 °/s² | 34 → 141 °/s² | pitch-gimbal deflection acting through the lateral offset |


So the question is narrower than it looks. Splitting the engine cannot change
what the vehicle can accelerate at, and cannot change its pitch authority. What
it does is **invent roll and yaw authority that the real vehicle never had** —
and the further apart the engines, the more of it.

# The sweep


![Angular authority against engine spacing](/home/omersayilgan/Desktop/ThesisGit/studies/engine_placement/figures/P1_placement_sweep.png)


| $y_{eng}$ [m] | Roll [°/s²] | Pitch [°/s²] | Yaw [°/s²] | Roll / LM | Pitch / LM | Yaw / LM |
|:------------|:------------|:------------|:------------|:----------|:-----------|:----------|
| 0.00 | 148 | 148 | 34 | 1.00 | 1.00 | 1.00 |
| 0.10 | 148 | 148 | 40 | 1.00 | 1.00 | 1.16 |
| 0.25 | 148 | 148 | 48 | 1.00 | 1.00 | 1.39 |
| 0.50 | 205 | 148 | 61 | 1.38 | 1.00 | 1.78 |
| 0.75 | 265 | 148 | 75 | 1.78 | 1.00 | 2.17 |
| 1.00 | 325 | 148 | 88 | 2.19 | 1.00 | 2.56 |
| 1.50 | 444 | 148 | 115 | 2.99 | 1.00 | 3.33 |
| 2.00 | 564 | 148 | 141 | 3.80 | 1.00 | 4.11 |


# Three constraints, and a threshold that appears twice

**Roll parity.** Roll authority stays *exactly* at the real LM's
148 °/s² up to $y_{eng}$ = **0.260 m**, and climbs from
there. Below that spacing the best roll moment the vehicle can make is still
the one the single-engine LM makes — both gimbals deflected in yaw against the
2.5 m engine-plane offset. Differential throttling is the better
lever only once the arm is longer than that.

**One-engine-out trimmability.** Study A's budget, derived independently and
from entirely different reasoning: a single gimbal can trim the roll asymmetry
left by a dead engine only while
$y_{eng} \le d z_{eng} \tan\delta_{max}$ = **0.263 m**.

Those two numbers are the same, and it is not a coincidence. Both ask the same
question — *is the lateral moment arm longer than the moment arm the gimbal
already commands?* Below $d z_{eng} \tan\delta_{max}$ the gimbal
dominates the roll axis, so the split adds nothing and a surviving gimbal can
undo what a dead engine does. Above it, differential thrust dominates, the
vehicle gains roll authority it never had, and the same arm that gave it that
authority is what the lone gimbal can no longer overcome. **One threshold
governs both the fidelity of the model and the survivability of the fault.**

**Yaw cannot be held at parity at all.** Unlike roll, yaw authority rises from
the very first centimetre of separation — 34 °/s² on the
centreline, 40 at 0.10 m, 48 at
0.25 m — because pitch-gimbal deflection acting through the lateral offset
makes a yaw moment that a centreline engine simply cannot. There is no positive
spacing at which yaw is at parity, so yaw cannot be a criterion: the only
spacing that satisfies it is no split at all.

The reason yaw inflates so readily is that it is the LM's *weakest* axis by a
factor of four (34 °/s² against 148 for roll and
pitch). Almost all of the real vehicle's yaw authority comes from the RCS, so
any engine contribution at all is a large *relative* change while staying small
in absolute terms: at 0.25 m the split adds
13 °/s² to an axis that has
34.

**Nozzle geometry.** Two engines cannot overlap. The real DPS nozzle is about
1.52 m across; at fixed chamber pressure and expansion ratio the
exit area scales with thrust, so a half-thrust engine is $1/\sqrt{2}$ as
wide — 1.07 m. Two of them cannot sit closer than one diameter
centre to centre, giving $y_{eng} \ge$ **0.54 m**.

| Constraint | Requires | Source |
|:----------------------------------------|:----------------|:----------------------------------|
| Roll authority at parity with the real LM | $\le$ 0.260 m | measured from the sweep |
| One-engine-out trimmable at 6° gimbal | $\le$ 0.263 m | Study A roll budget — the same threshold |
| Yaw authority at parity | $\le$ 0.00 m | degenerate; rejected |
| Nozzles do not collide | $\ge$ 0.54 m | estimated from a sqrt(T) nozzle scaling |


**The buildable region and the trimmable region do not overlap.** Anything a
real pair of half-DPS engines could be built at ($\ge$ 0.54 m) is already
past the threshold where one gimbal can trim the other's failure, and past the
point where the split starts inventing roll authority ($\le$ 0.263 m).

That is a finding about the configuration rather than a modelling
inconvenience: **a twin-engine Apollo-class lander with only
6° of gimbal throw cannot be both buildable and
single-engine-out survivable.** The gimbal is the binding parameter, not the
spacing. Making the buildable spacing trimmable needs

$$\delta_{max} \ge \arctan\frac{y_{eng}}{d z_{eng}}
= \arctan\frac{0.54}{2.5} = 12.1°$$

— a little over double the LM's actual throw, which is a large but not absurd
ask for a clean-sheet design.

# Recommendation

**Keep $y_{eng}$ = 0.25 m**, and state it as a *modelling* choice
rather than a design one.

It is the largest round spacing under the 0.263 m threshold, so the
imaginary vehicle has **exactly** the real Apollo LM's roll and pitch
authority, and it is engine-out trimmable — which is what turns engine-out from
an automatic loss into a fault with an answer. The price is
39 % more yaw authority than the real LM,
on the axis where the real LM is weakest and where the absolute difference is
13 °/s². That is the residual, and it
should be quoted rather than hidden.

What the vehicle is not is buildable. Two half-DPS engines 0.50 m
apart centre to centre would overlap, so it should be described as **a device
for splitting the DPS into two independently faultable halves while holding the
real LM's authority fixed** — which is exactly what the fault studies need —
and not as a proposal for a real lander.

Studies A through G, at 1.50 m, should carry the caveat that their vehicle had
3.0x the roll and 3.3x the yaw
authority of a real LM. Their engine-out result is unaffected — that fault was
lost to the trim budget, which 1.50 m misses by a factor of
5.7 — but their gimbal-fault and thrust-asymmetry results were
measured on an over-actuated vehicle.


**The buildable region and the trimmable region do not overlap.** Anything a
real pair of half-DPS engines could be built at ($\ge$ 0.54 m) is already
past the point where one gimbal can trim the other's failure
($\le$ 0.263 m), and past parity with the real LM's authority.

That is a genuine finding about the configuration rather than a modelling
inconvenience: **a twin-engine Apollo-class lander with only 6°
of gimbal throw cannot be both buildable and single-engine-out survivable.**
The gimbal is the binding parameter, not the spacing. Making the buildable
spacing trimmable needs

$$\delta_{max} \ge \arctan\frac{y_{eng}}{d z_{eng}}
= \arctan\frac{0.54}{2.5} = 12.1°$$

— a little over double the LM's actual throw, which is a large but not absurd
ask for a clean-sheet design.

# Recommendation

**Keep $y_{eng}$ = 0.25 m for the fault studies**, and state it as a
*modelling* choice rather than a design one.

At that spacing the imaginary vehicle matches the real Apollo LM's roll
authority exactly and its yaw authority to within
39 %, so the fault campaigns are flying
something with an Apollo-class lander's actual pointing capability rather than
an invented one. It also sits just inside the one-engine-out trim limit, which
is what makes engine-out a fault with an answer instead of an automatic loss.

What it is not is buildable. Two half-DPS engines 0.50 m apart
centre to centre would overlap, so the vehicle should be described as **a
device for splitting the DPS into two independently faultable halves while
holding the real LM's authority fixed** — which is exactly what the fault
studies need it to be — and not as a proposal for a real lander.

Studies A through G, at 1.50 m, should carry the caveat that their vehicle had
3.0x the roll and 3.3x the yaw
authority of a real LM. Their engine-out result is unaffected — that fault was
lost to the trim budget, which 1.50 m fails by a factor of
5.7 — but their gimbal-fault and thrust-asymmetry results were
measured on an over-actuated vehicle.

# Limitations

* **The nozzle constraint is an estimate.** 1.52 m for the DPS
  exit diameter and a $\sqrt{T}$ scaling for the half-thrust engine are both
  approximations. A genuinely optimised half-thrust engine at a different
  expansion ratio could be meaningfully smaller, which would move the
  buildable limit down — though not to 0.263 m.
* **Authority is an upper bound.** As in the fleet survey, every actuator fires
  at once in the optimal direction, and angular acceleration is $M/I_{jj}$
  about principal axes with no gyroscopic coupling.
* **Inertia is held fixed** across the sweep. Moving real engines outboard
  would change $I_{xx}$ slightly; at these masses and arms the effect is well
  below the shape-model uncertainty already present in the inertia itself.
* **Only the spacing is varied.** Engine cant, axial station and differential
  gimbal throw are all fixed at the LM's values, and each is another lever on
  the same trade.

# Reproducing

```bash
python studies/engine_placement/place_engines.py
```
