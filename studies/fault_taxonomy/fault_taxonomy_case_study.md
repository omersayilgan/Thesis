---
title: "A Fault Taxonomy for the Apollo LM Landing Problem"
subtitle: "Study G — landing probability across 16 engine faults and 5 initial-condition regimes"
date: "17 August 2026"
geometry: margin=2.4cm
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

# What this study adds

The earlier case studies each took **one** fault and flew it as well as it can
be flown: an engine out (Study A), a thrust-efficiency sweep (Study B), a gimbal
bandwidth sweep (Study C), fault onset time (Studies D/E), and whether a fault
is expressible as an initial condition (Study F, which found that it is not —
the state is recoverable information, the *plant change* is not).

Between them they cover three of the eleven dynamic-effect categories in
`docs/spacecraft_engine_fault_framework.md`. This study covers the rest. It
instantiates **15 distinct faults** drawn from that framework — one per
dynamic-effect category, with severity variants where the category spans a wide
range — as 15 *plants*, and measures the landing probability of each from
**5 qualitatively different regions of the state space**.

The two axes are the ones the framework itself insists on:

* **What the fault is.** Framework section 3 classifies every fault as
  *additive* (an unknown disturbance, independent of state and input),
  *multiplicative* (a change to $A$ or $B$, scaling with the operating point),
  or *structural* (a change to the model's order or topology). This is the
  classification that decides what a fault-tolerant architecture has to *do*,
  so it is the one the figures colour by.
* **Where the vehicle is when it gets it.** A fault that is survivable on a
  high, calm approach is not the same fault at 300 m with the vehicle already
  rolling. Reporting a single landing rate per fault would average those two
  situations into a number describing neither.

The deliverable is therefore the landing probability over the **product** of the
two: 16 faults $\times$ 5 regimes $\times$ 10
initial conditions = **800 nonlinear programmes**
(15.6 core-hours of IPOPT).

## The experiment, in one paragraph

Initial conditions are drawn once per regime, as scrambled Sobol points in the
same 22-dimensional box Study F used (12 rigid-body states plus all 10 actuator
states), and **reused for every fault**. Each sample is then handed to the
recovery planner of `fault_lib.recover`: given the state the vehicle is in and
the plant it has become, plan a landing to the 80 s deadline or refuse. There is
no nominal trajectory and no fault onset time — Study F established that the
post-fault problem is fully specified by (state, plant), and the fault enters
here only through the plant, which is precisely the part that is *not* an
initial condition. The resulting trajectory is flown to the contact altitude,
the engine is cut, the vehicle settles ballistically, and the touchdown state is
scored against the Apollo landing gate (vertical speed $\le$ 3.0 m/s,
horizontal $\le$ 1.2 m/s, tilt $\le$ 6°, 15 m of the pad, rates $\le$ 5°/s).

Because the initial conditions are shared across plants, the healthy
configuration is a genuine control: any difference within a regime column is
attributable to the plant alone, and the healthy-vs-fault comparison is a
within-sample McNemar test rather than two independent proportions.

# The fault catalogue

Every fault acts on engine 2; engine 1 stays healthy, so each case is an
*asymmetry* the vehicle must trim as well as a loss of performance. Severity is
chosen to span the interesting range rather than the survivable one — a taxonomy
in which everything lands measures nothing.


| Fault | § | FTC structure | Temporal | What the plant becomes |
|:----------------|:-:|:-------------|:----------|:----------------------------------------------------------|
| Healthy (control) | — | none | — | nominal plant; measures what the state dispersion alone costs |
| Thrust-vector misalignment (3°, 2°) | 2.7 | additive | incipient | asymmetric nozzle erosion leaves engine 2 pointing 3° in pitch and 2° in yaw off its commanded axis, independent of command |
| Thrust oscillation (chugging) | 2.3 | additive | intermittent / forced | feed-coupled instability: engine 2 thrust rings at 0.25 Hz with an amplitude of 20 % of its hover share, regardless of throttle |
| Thrust reduction, $\eta$=0.50 | 2.1 | multiplicative | abrupt / incipient | engine 2 delivers half of its internal thrust (turbopump degradation, injector blockage, throat erosion) |
| Thrust reduction, $\eta$=0.15 | 2.1 | multiplicative | abrupt | engine 2 delivers 15 % — near-total gain loss with the gimbal alive |
| Thrust excess, $\eta$=1.30 | 2.2 | multiplicative | abrupt | pressurant regulator runaway: engine 2 delivers 130 % of its commanded thrust |
| Slow thrust response, $\tau_T$=2.5 s | 2.5 | multiplicative | incipient | engine 2 thrust lag grows from 0.4 s to 2.5 s (valve friction, coking, actuator supply loss) with the gain untouched |
| Gimbal bandwidth loss, $\omega_n$=0.6 | 2.5 | multiplicative | incipient | engine 2 gimbal actuator slowed from 4.0 to 0.6 rad/s |
| Gimbal underdamped, $\zeta$=0.25 | 2.3 / 2.8 | multiplicative | incipient | engine 2 gimbal at $\omega_n$=1.0 rad/s with damping down to 0.25 — a lightly damped TVC mode |
| TVC effectiveness loss (35 %) | 2.7 | multiplicative | incipient | engine 2 gimbal reaches only 35 % of the commanded deflection |
| Mixture-ratio shift (coupled) | 2.4 | multiplicative (coupled) | incipient | oxidiser-side erosion on engine 2: gain falls to 0.75 *and* the combustion time constant grows to 1.2 s — the framework's coupled ΔB + ΔA case, where the gain change drags the dynamics with it |
| Throat-erosion drift | 2.10 | time-varying multiplicative | incipient | engine 2 efficiency decays at 1.2 %/s from the moment the planner starts: healthy at t=0, eta=0.52 forty seconds later. The vehicle it plans with is not the vehicle it lands with |
| Valve stuck open (thrust floor) | 2.2 / 1.4 | structural | abrupt | engine 2 cannot be throttled below 8458 N (1.35x its hover share) — the input set itself is cut |
| Engine out | 2.1 / 3.1 | structural | abrupt | engine 2 dead: thrust and both gimbals pinned to zero for the rest of the flight |
| Gimbal seizure | 1.7 | structural | abrupt | engine 2 gimbal bearing seizes: the deflection freezes at whatever it held at the fault and no longer answers the command |
| Transport delay (1 interval) | 2.6 | structural | abrupt / intermittent | a vapour pocket in engine 2's feed line delays every command by one full control interval (1 s) — exact on a zero-order-hold grid, so no Pade approximation is involved |

Four of these required extending the vehicle model, because the earlier studies
only ever needed thrust efficiency and gimbal bandwidth. The additions are all
in `LMParams` and `flat_moon_6dof`, and all default to the healthy plant:

* **transport delay** is exact rather than a Padé approximation — on a
  zero-order-hold control grid, a delay of one interval is a pure index shift
  of the engine's command, which is what the OCP builder now applies;
* **parametric drift** and **forced oscillation** required threading trajectory
  time through the integrator, so a time-varying plant can be integrated at all;
* **thrust-vector misalignment** enters as a bias on the delivered thrust axis
  that no command can null — the planner can only aim the sum somewhere useful;
* **valve stuck open** is not a parameter change but a cut to the *input set*:
  the engine's lower thrust bound is raised above its own hover share;
* **gimbal seizure** freezes the deflection where the fault caught it. The
  seizure arrests the motion, so the gimbal *rate* states are zeroed in the
  initial condition and the acceleration is identically zero thereafter. A
  first attempt instead bled the rate off with a fast decay term, which looks
  more physical and is numerically wrong: a decay fast enough to read as a
  seizure sits far outside RK4's stability region on this grid, so the rate
  state diverged and every seizure solve came back infeasible for reasons that
  had nothing to do with the vehicle.

# The initial-condition regimes

The regimes were **calibrated rather than guessed**. A pilot sweep established
that this recovery planner, handed the damaged plant exactly and a free choice
of trajectory, absorbs almost every single-engine fault from a high, calm
approach — the healthy control and most of the catalogue all land, and the
matrix saturates at 1.00. Regime boxes were therefore tightened until the
*healthy* vehicle itself starts failing, which is the only condition under which
the fault differences are measurable at all. That saturation is itself a result,
and it is reported below rather than tuned away: the first three regimes are
kept precisely because they show where the ceiling is.


| Regime | What it is | Landing rate, all faults pooled | n |
|:------------|:----------------------------------------------------|:-:|:-:|
| On approach | high, descending, small dispersions — the vehicle is where a healthy descent would have put it, and the fault is the only thing wrong | **0.88** [0.81, 0.92] | 140/160 |
| Dispersed | Study F's wide box: position, velocity, attitude, rates and both sets of actuator states drawn over their full admissible ranges | **0.78** [0.70, 0.83] | 124/160 |
| Upset | the corner of the box where the vehicle is already rotating or tilted (>= 10 deg/s on some axis, or >= 15 deg of tilt) with the gimbals deflected — the states a fault transient actually produces | **0.75** [0.68, 0.81] | 120/160 |
| Low and late | between 60 m and 200 m and still descending: the fault arrives when there is very little altitude left to trade for time | **0.66** [0.58, 0.73] | 105/160 |
| Critical | below 140 m, descending hard, tilted and rotating — the regime where even the healthy vehicle frequently has no trajectory left, so the fault has to be paid for out of a margin that is already spent | **0.41** [0.34, 0.49] | 66/160 |

The regimes are **not nested severity levels**; they name qualitatively
different situations. `On approach` is the most forgiving
(0.88 pooled over every fault) and
`Critical` the least (0.41) — a spread
of 0.46 in landing probability
produced *entirely* by where the vehicle started, with the fault mix held
identical.

# Results

## The fault $\times$ regime matrix

This is the study's primary result: the landing probability of every fault from
every regime, over shared initial conditions.


![Landing probability by fault and initial-condition regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/G1_heatmap.png)


Read down a column to compare faults at a fixed situation; read across a row to
see how much of a given fault's cost is really the situation's. Each cell rests
on 10 samples, so a single cell carries a 95 % interval roughly
$\pm$0.25 wide — the cells are for the *pattern*, and every number quoted in
the text below is a pooled marginal with its interval attached.

## What each fault costs, pooled



![Pooled landing rate per fault, Wilson intervals](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/G2_forest.png)


| Fault | Class | Landing rate | k/n | Survival | Lost | McNemar |
|:--------------------------|:------------|:--------------------|:------|:--------|:-----|:-----------|
| Healthy (control) | none | 0.88 [0.76, 0.94] | 44/50 | — | — | — |
| Thrust-vector misalignment (3°, 2°) | additive | 0.88 [0.76, 0.94] | 44/50 | 1.00 | 0 | $p$ = 1.000 |
| Thrust oscillation (chugging) | additive | 0.88 [0.76, 0.94] | 44/50 | 1.00 | 0 | $p$ = 1.000 |
| Thrust excess, $\eta$=1.30 | multiplicative | 0.88 [0.76, 0.94] | 44/50 | 1.00 | 0 | $p$ = 1.000 |
| TVC effectiveness loss (35 %) | multiplicative | 0.88 [0.76, 0.94] | 44/50 | 1.00 | 0 | $p$ = 1.000 |
| Gimbal seizure | structural | 0.82 [0.69, 0.90] | 41/50 | 0.93 | 3 | $p$ = 0.250 |
| Throat-erosion drift | multiplicative | 0.80 [0.67, 0.89] | 40/50 | 0.91 | 4 | $p$ = 0.125 |
| Valve stuck open (thrust floor) | structural | 0.80 [0.67, 0.89] | 40/50 | 0.91 | 4 | $p$ = 0.125 |
| Gimbal underdamped, $\zeta$=0.25 | multiplicative | 0.78 [0.65, 0.87] | 39/50 | 0.89 | 5 | $p$ = 0.062 |
| Slow thrust response, $\tau_T$=2.5 s | multiplicative | 0.76 [0.63, 0.86] | 38/50 | 0.86 | 6 | $p$ = 0.031 |
| Mixture-ratio shift (coupled) | multiplicative | 0.76 [0.63, 0.86] | 38/50 | 0.86 | 6 | $p$ = 0.031 |
| Transport delay (1 interval) | structural | 0.76 [0.63, 0.86] | 38/50 | 0.86 | 6 | $p$ = 0.031 |
| Thrust reduction, $\eta$=0.50 | multiplicative | 0.66 [0.52, 0.78] | 33/50 | 0.75 | 11 | $p$ = 0.001 |
| Gimbal bandwidth loss, $\omega_n$=0.6 | multiplicative | 0.56 [0.42, 0.69] | 28/50 | 0.64 | 16 | $p < 10^{-4}$ |
| Thrust reduction, $\eta$=0.15 | multiplicative | 0.00 [0.00, 0.07] | 0/50 | 0.00 | 44 | $p < 10^{-4}$ |
| Engine out | structural | 0.00 [0.00, 0.07] | 0/50 | 0.00 | 44 | $p < 10^{-4}$ |

Landing rate carries its 95 % Wilson interval; *survival* is the paired
share of healthy-landable states the fault keeps, *lost* the count it
takes away, and *McNemar* the exact two-sided test on the discordant
pairs.


The healthy control lands from **0.88** [0.76, 0.94] of the sampled states.
That number is not 1.00 and is not meant to be: the box contains states from
which a *healthy* Apollo LM cannot reach the pad inside the deadline, and
pricing them is the whole reason the control is run on the same samples.

The most expensive fault in the catalogue is
**Thrust reduction, $\eta$=0.15** (**0.00** [0.00, 0.07]); the cheapest is
**Thrust-vector misalignment (3°, 2°)** (**0.88** [0.76, 0.94]).
7 of the 15 faults degrade the landing rate significantly
against the paired healthy control at the 5 % level.

The engine-out row is a **cross-check on the whole apparatus rather than a new
result**: Study A's roll-authority budget says a single gimbal can trim a
one-engine-out asymmetry only if $y_{eng} \le d z_{eng} \tan\delta_{max}$
= 0.263 m, and this vehicle is built at $y_{eng}$ = 1.5 m. It should therefore
never land engine-out at any initial condition, and it does not
(0/50). A campaign that
produced engine-out landings here would be reporting a bug.

## Paired survival: the same states, a different vehicle

The pooled rate above still mixes the fault's cost with the cost of the state
dispersion. The paired view removes the latter: of the initial conditions the
*healthy* vehicle lands from, what share does the faulted vehicle still land
from? The initial conditions are literally identical, so what is left is the
plant.


![Paired survival relative to the healthy control](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/G3_paired.png)


11 faults keep
at least 85 % of the healthy vehicle's landable states
(Thrust-vector misalignment (3°, 2°), Thrust oscillation (chugging), Thrust excess, $\eta$=1.30, Slow thrust response, $\tau_T$=2.5 s, Gimbal underdamped, $\zeta$=0.25, TVC effectiveness loss (35 %), Mixture-ratio shift (coupled), Throat-erosion drift, Valve stuck open (thrust floor), Gimbal seizure, Transport delay (1 interval)). These are faults the *planner*
absorbs: it knows the damaged plant, and it re-optimises around it. That is a
statement about open-loop replanning with a perfect plant estimate, not about a
controller that has to discover the fault first — see the limitations.


At the other end, 2 faults
destroy at least 65 % of them
(Thrust reduction, $\eta$=0.15, Engine out). No amount of replanning
recovers these, because the vehicle no longer has the authority the trajectory
requires.


### The additive faults cost nothing at all

Every additive fault in the catalogue
(Thrust-vector misalignment (3°, 2°), Thrust oscillation (chugging)) loses **zero** of the healthy
vehicle's landable initial conditions — not few, zero. This is the framework's
section 4 prediction landing exactly: an additive fault is an unknown input
that does not depend on state or command, and an optimiser that knows the
disturbance simply builds it into the plan. The corollary is the part that
matters operationally: their cost is *entirely* a detection and estimation
problem. Give the planner the wrong bias and it aims the trajectory wrong; give
it the right one and the fault is free.


### A sluggish gimbal is worse than a seized one

The catalogue's most counter-intuitive result, and it is not a small margin:
the seized gimbal keeps 0.93 of the healthy vehicle's landable
states while the merely *slow* one keeps 0.64 — pooled landing
rates 0.82 against
0.56.

The reason is that the two faults present the planner with different kinds of
problem. A seized gimbal is a **constant, known offset**: the deflection is
frozen where the fault caught it, the resulting force and moment are fixed for
the rest of the flight, and the trajectory can be planned around a constant.
A slow gimbal is a **lagging actuator that still moves**: it answers every
command late and in the wrong amount during exactly the transients where the
authority is needed, and the planner cannot get the deflection where it wants
it when it wants it. Losing an actuator cleanly is easier to fly than keeping
one that is late — which is a direct argument for the framework's section 7
detection layer being worth more than raw actuator redundancy, because a fault
you have identified as a fixed offset has largely stopped being a fault.


## How the failures fail

Landing rate alone hides the engineering distinction between a vehicle that
*arrives too hard* and a vehicle for which no arrival exists at all. The first
is a trajectory-shaping problem; the second is a control-authority problem, and
no better guidance law fixes it.


![Outcome composition per fault](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/G4_outcomes.png)


| Fault | landed | gate miss | no trajectory | lost first |
|:------------------------------|:-:|:-:|:-:|:-:|
| Healthy (control) | 88 % | 0 % | 12 % | 0 % |
| Thrust-vector misalignment (3°, 2°) | 88 % | 0 % | 12 % | 0 % |
| Thrust oscillation (chugging) | 88 % | 0 % | 12 % | 0 % |
| Thrust reduction, $\eta$=0.50 | 66 % | 8 % | 26 % | 0 % |
| Thrust reduction, $\eta$=0.15 | 0 % | 14 % | 86 % | 0 % |
| Thrust excess, $\eta$=1.30 | 88 % | 0 % | 12 % | 0 % |
| Slow thrust response, $\tau_T$=2.5 s | 76 % | 2 % | 22 % | 0 % |
| Gimbal bandwidth loss, $\omega_n$=0.6 | 56 % | 0 % | 44 % | 0 % |
| Gimbal underdamped, $\zeta$=0.25 | 78 % | 0 % | 22 % | 0 % |
| TVC effectiveness loss (35 %) | 88 % | 0 % | 12 % | 0 % |
| Mixture-ratio shift (coupled) | 76 % | 4 % | 20 % | 0 % |
| Throat-erosion drift | 80 % | 8 % | 12 % | 0 % |
| Valve stuck open (thrust floor) | 80 % | 8 % | 12 % | 0 % |
| Engine out | 0 % | 0 % | 100 % | 0 % |
| Gimbal seizure | 82 % | 4 % | 14 % | 0 % |
| Transport delay (1 interval) | 76 % | 0 % | 24 % | 0 % |

`lost first` is the share of samples where the initial state is already past
the hard loss-of-control criteria (tilt beyond 90°, tumbling beyond 120°/s,
speed beyond 1.5 $V_{max}$, or below the contact altitude); it is a property of
the *sample*, not of the fault, and is therefore identical across every row — a
useful internal consistency check on the pairing.

## Landing probability against the initial condition

The regimes are boxes. This is the continuous cut through them: landing rate
against initial altitude, with the fault classes separated.


![Landing rate against initial altitude by class](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/G5_altitude.png)


| Fault class | On approach | Dispersed | Upset | Low and late | Critical | pooled |
|:--|:-:|:-:|:-:|:-:|:-:|:-:|
| healthy | 1.00 | 1.00 | 1.00 | 0.80 | 0.60 | **0.88** [0.76, 0.94] |
| additive | 1.00 | 1.00 | 1.00 | 0.80 | 0.60 | **0.88** [0.80, 0.93] |
| multiplicative | 0.89 | 0.76 | 0.71 | 0.64 | 0.38 | **0.68** [0.63, 0.72] |
| structural | 0.75 | 0.65 | 0.65 | 0.57 | 0.35 | **0.59** [0.53, 0.66] |

## How close the survivors came

Landing is a binary, but the gate margin behind it is not: a margin of 1.0 *is*
the gate, and the distance below it says how much of the touchdown budget the
recovery had to spend.


![Gate-margin distribution over solved cases](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/G6_margin.png)


# What this means for a fault-tolerant architecture

**The framework's three-way structural classification predicts the outcome
better than fault severity does.** Grouped by class, the pooled landing rates
are healthy 0.88, additive 0.88, multiplicative 0.68, structural 0.59. Structural faults are
the ones that remove authority outright; multiplicative faults scale with the
operating point, so the planner can trade against them; additive faults are
biases and disturbances that an optimiser with a correct plant model simply
plans around.

**Where the vehicle is matters as much as what broke.** The regime spread
(0.41 to 0.88) is comparable to the
spread across the fault catalogue itself. A fault-tolerance budget quoted as a
single per-fault probability is not a budget; it is an average over a mission
phase distribution that was never stated.

**Altitude is the resource.** The `Critical` regime differs
from the others mainly in having less of it, and it is where the fault classes
separate most sharply. Recovery is paid for in altitude: the same fault that is
a nuisance on approach, where there is a kilometre of it to spend, is what
decides the landing once the vehicle is low.

**The three FTC layers of framework section 7 are visible in the data.** The
faults the planner absorbs are the ones a *base* robust/adaptive layer would
handle; the ones that produce `gate miss` rather than `no trajectory` are
disturbance-estimation problems; the ones that produce `no trajectory` need the
detection-and-switching layer, and in several cases need an abort decision
rather than a control law.

# Limitations

* **The planner is given the damaged plant exactly.** Every number here is an
  upper bound on what an FTC system achieves, because fault detection,
  isolation and identification are not modelled. In practice the plant estimate
  arrives late and wrong, and both shrink these numbers.
* **Open loop.** Each result is a single optimal-control solve, not a closed
  loop. There is no re-solve as the trajectory is flown, so a fault whose model
  error grows in flight (the drift case in particular) is treated more kindly
  here than a real one would be.
* **A box is not a distribution.** The regimes have uniform density and no
  covariance structure. They describe boxes, not the operational likelihood of
  being in them.
* **Dead time is quantised to the control grid.** A delay of one 1 s interval
  is exact on a zero-order-hold grid, but the framework's warning about
  10–30 ms delays eroding phase margin belongs to a closed-loop bandwidth this
  1 s planning grid cannot resolve.
* **Oscillation frequency is grid-limited.** Chugging is modelled at 0.25 Hz;
  the 50–500 Hz longitudinal modes and the kHz acoustic modes of framework
  §2.3 are far outside what a 1 s grid with 2 sub-steps can represent, and are
  a structural-dynamics problem rather than a trajectory one.
* **One fault at a time, on engine 2.** The vehicle is laterally symmetric so
  the engine index does not matter, but simultaneous or cascading faults are
  not covered.
* **Local infeasibility is not global.** The NLP is nonconvex; `no trajectory`
  means IPOPT failed from two independent seeds, not that none exists.
* **Constant mass**, inherited from the base model, which understates the
  propellant cost of a partial fault.
* **The easy regimes saturate.** In `On approach` and `Dispersed` the healthy
  control lands from nearly every admissible state, so those columns bound the
  fault effect from above rather than resolving it. The discrimination lives in
  the `Low and late` and `Critical` columns, and the pooled marginals inherit
  the mix.
* **Per-cell samples are small.** With 10 initial conditions per cell, an
  individual cell of the matrix carries a wide interval. The pooled marginals
  (n = 50 per fault) and the paired comparisons are what
  the conclusions rest on.

# Reproducing

```bash
python studies/fault_taxonomy/run_taxonomy_study.py 10   # the campaign
python studies/fault_taxonomy/analyse.py                  # figures + headline JSON
python studies/fault_taxonomy/build_report.py             # this document
```
