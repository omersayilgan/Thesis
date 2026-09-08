---
title: "Faults in Capability Space"
subtitle: "Study I — what 12 engine faults do to the attainable force and moment sets, and why that does not tell you which ones are survivable"
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

# What this study does

Studies G, H and H-R ask whether a damaged vehicle can still fly a trajectory.
This one asks the question underneath: **what can the damaged vehicle push and
twist with at all**, before any trajectory is planned.

For an actuator set there are two sets in $\mathbb{R}^3$ and one in
$\mathbb{R}^6$:

* the **attainable force set (AFS)** — every net force the actuators can produce;
* the **attainable moment set (AMS)** — every net moment;
* the **attainable wrench set (AWS)** — the 6-D set the other two are
  projections of, and the one an operating point has to lie inside.

Each RCS thruster is a one-sided segment: throttle $f \in [0, F]$ contributing
$f\,d$ to the force and $f\,(r \times d)$ to the moment. Each gimballed engine
sweeps a spherical cap: thrust $T \in [T_{min}, T_{max}]$ along any
direction within $\delta_{max}$ of its axis. The sum is what the vehicle can
do instantaneously; its convex hull is what a support-function sweep recovers
exactly, and that is what is computed here on
1200 directions per set.

The vehicle is the Study H plant: 2 gimballed engines at
$y_{eng} = \pm0.25$ m with a
6° cone, 16 RCS thrusters at
445 N each, 7711 kg.



![What each fault leaves of the vehicle's capability](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I0_capability_grid.png)


# Four things a fault can do to a set

The classification is decided from the numbers, not asserted:


| Effect | Faults | What it means |
|:------------|:----------------------------------|:----------------------------------------------------|
| **shrink** | chugging, $\eta$=0.50, $\eta$=0.15, mixture ratio, engine out | the damaged set is a subset of the healthy one |
| **enlarge** | TVC bias, $\eta$=1.30 | more authority than healthy — and asymmetrically, which buys force and costs trim symmetry |
| **deform** | — | same size, moved: the set points somewhere else |
| **puncture** | stuck open | the origin leaves the set — the vehicle can no longer produce zero net wrench |
| **nothing** | healthy, $\tau_T$=2.5 s, erosion drift, dead time | the static set is identical to healthy; the fault lives entirely in time |


## Why the stuck-open valve is its own category

Everywhere else in this repository an engine can be shut down, so its minimum
throttle does not shape the attainable set: zero is always available and the
hull contains the origin. A valve stuck open removes exactly that. The engine's
contribution becomes the shell $\{T d : T \in [T_{min}, T_{max}]\}$ with
$T_{min} > 0$, whose hull does **not** contain the origin.

This is a qualitative change that no volume metric can see — the force set
keeps 97% of its volume
— and it is visible in the figure below as a set with its top cut off, the
origin marked outside it.


![The attainable force and moment sets under fault](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I1_sets.png)


# What each fault costs



![Capability cost per fault, in three measures](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I2_metrics.png)


The third bar is the one that matters, and it is worth explaining why the first
two are not enough.

**The unconstrained AMS flatters every fault.** It is free to spend the whole
actuator set on one moment and let the vehicle fall. A descending vehicle
cannot: most of its thrust is committed to not hitting the ground, and the
moment authority that counts is what remains *after* that commitment. The
conditional set — moments attainable while producing the
12530 N of vertical force that holds the vehicle up —
is the set an allocator actually draws from, and it separates faults the raw
AMS reports as nearly identical.


| Fault | Effect | AFS | AMS | AMS | hover | Zero wrench | Hover wrench | Study H landings |
|:----------------------|:------------|:--------|:--------|:------------|:------------|:------------|:----------------|
| engine out | shrunk | 0.23× | 0.28× | 0.53× | yes | yes | 73% |
| $\eta$=0.15 | shrunk | 0.30× | 0.36× | 0.65× | yes | yes | 87% |
| stuck open | punctured | 0.97× | 1.00× | 0.68× | **no** | yes | 100% |
| $\eta$=0.50 | shrunk | 0.52× | 0.59× | 0.94× | yes | yes | 93% |
| mixture ratio | shrunk | 0.74× | 0.78× | 1.00× | yes | yes | 100% |
| healthy | unchanged | 1.00× | 1.00× | 1.00× | yes | yes | 100% |
| chugging | shrunk | 0.88× | 0.90× | 1.00× | yes | yes | 100% |
| $\eta$=1.30 | enlarged | 1.39× | 1.30× | 1.00× | yes | yes | 100% |
| $\tau_T$=2.5 s | unchanged | 1.00× | 1.00× | 1.00× | yes | yes | 100% |
| erosion drift | unchanged | 1.00× | 1.00× | 1.00× | yes | yes | 100% |
| dead time | unchanged | 1.00× | 1.00× | 1.00× | yes | yes | 67% |
| TVC bias | enlarged | 1.08× | 1.04× | 1.08× | yes | yes | 100% |


# Capability does not predict survivability

Every fault in the catalogue leaves the hover wrench attainable. Not one of
them costs the vehicle the ability to hold itself up at this engine spacing.
And yet Study H found four of them with injection points from which no
trajectory exists at all.



![Retained moment authority against Study H landing share](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I3_capability_vs_survival.png)


The clearest case is **dead time**. Its capability sets are *identical* to
healthy — same volume, same axes, same origin containment, same hover wrench —
and it is the least survivable fault in the entire Study H campaign, landing
from 67% of injection points and accounting for five of the
nine injections that no relaxation of the trajectory constraints could recover.

A transport delay does not remove authority. It removes the vehicle's ability
to *apply* that authority when the state calls for it, and capability space —
which is a statement about an instant, not about a sequence — cannot represent
that. The same is true of the slow thrust response.


The converse case is **$\eta$=0.15**, which keeps only
65% of its conditional moment authority and still lands from
87% of injection points. Losing half the set is survivable
when what remains still contains everything the trajectory asks for.


**This is the study's main result, and it is a negative one.** An FTC scheme
that reasons only about attainable sets — control-allocation feasibility,
degraded-mode envelopes, reconfigurable allocation limits — will rank the
temporal faults as harmless, because in capability space they are. Capability
space is necessary and not sufficient: it tells you what the vehicle can do at
an instant, and says nothing about whether it can do it *in time*.

The two measures are complementary, not redundant:

* a fault that leaves the required wrench outside the set is unrecoverable for
  a reason no controller can fix — that is a capability failure;
* a fault that leaves it inside may still be unrecoverable for reasons of
  timing, delay, or the state the vehicle happens to be in — that is a
  trajectory failure, and only a campaign like Study H finds it.

# What redundancy buys


![The cost of losing one actuator](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I4_redundancy.png)


Losing any single RCS thruster costs between
88% and
95% of the conditional moment
authority — the worst of the sixteen (RCS 2) leaves
88%. Losing one of the two engines leaves
52%. **Sixteen thrusters are close to
interchangeable; two engines are not**, and that asymmetry is the whole
argument for treating the engine tier and the attitude tier as different
redundancy problems rather than counting actuators.

## The trim threshold, recovered from capability space

Study A derived the engine-out roll-trim limit analytically: a single gimbal
can trim a one-engine-out asymmetry only while
$y_{eng} \le dz_{eng}\tan\delta_{max}$ =
**0.263 m**. That derivation is a statement about one moment
balance. Asking capability space the same question — sweep the engine spacing,
and for each ask the LP whether zero net moment is attainable while holding
hover thrust — reproduces it without being told:



![Engine-out trim against engine half-spacing](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I5_spacing.png)


The gimbal-alone curve leaves zero residual up to
$y_{eng}$ = **0.258 m** and diverges past it, against the
analytic 0.263 m. The agreement is a check on the machinery:
two independent derivations of the same threshold, one algebraic and one from a
linear program over the actuator polytope.

The second curve is the part the analytic result does not cover. With the RCS
tier available the vehicle trims engine-out at **every** spacing tested — the
thrusters quietly cover what the gimbal cannot. That is worth knowing before
concluding that a wide engine layout is disqualifying: it is disqualifying for
the gimbal, not for the vehicle, as long as the attitude tier is healthy and has
propellant. Study F's result that engine-out lands from 0 of 48 initial
conditions at $y_{eng}$ = 1.5 m is therefore not a capability statement
either — the authority is there, and something else is spending it.

# A fault that moves through capability space


![Throat-erosion drift over time](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I6_erosion.png)


Throat-erosion drift is the one fault whose capability set is not a fixed
object. Its efficiency decays from the moment of onset, so the set contracts
continuously: the conditional moment authority falls from
1.00× at onset to 0.96× after
40 s.

**At the instant of onset it is indistinguishable from healthy.** Any
capability-based monitor that samples the set will report a healthy vehicle for
as long as it takes the drift to exceed the monitor's threshold, and the fault
that is easiest to detect in capability space is the one that has already done
its damage. This is the argument for tracking the *rate* rather than the value.

# Limitations

* **Instantaneous sets.** Everything here is a statement about one instant with
  no actuator dynamics. Rate limits, lags and delays are exactly what the
  unchanged-set faults consist of, which is the point of section 4 — but it
  means this study cannot be read as a survivability measure on its own.
* **Convex hulls.** The reported sets are hulls of the achievable set. For the
  RCS tier that is exact (a zonotope); for the engines the cap is sampled, and
  the LP uses an inscribed polytope, so a wrench reported attainable really is
  and a wrench reported unattainable is marginally conservative.
* **The chugging derate is a modelling choice.** A forced oscillation does not
  move the commanded boundary; what is reported is the authority the vehicle can
  hold regardless of ripple phase, which is the useful quantity but not the only
  defensible one.
* **One vehicle, one operating point.** The conditional sets are computed at
  hover thrust. A braking or pitch-over manoeuvre would commit the actuators
  differently and move every conditional number, though not the classification.
* **Fixed mass and inertia**, inherited from the plant.

# Reproducing

```bash
python studies/capability_space/run_capability_study.py   # the sets + LPs
python studies/capability_space/plot_capability.py        # figures
python studies/capability_space/build_report.py           # this document
```
