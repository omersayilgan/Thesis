---
title: "Fault-Tolerant Motion Planning for Rocket-Propelled Spacecraft: Actuator-Fault Impacts in Capability Space and Along an Apollo Lunar Module Descent"
author: "Ömer Sayılgan"
date: "8 September 2026"
abstract: |
  An actuator fault changes both what a spacecraft is able to
  produce at an instant and whether it can still complete its manoeuvre. The
  first question belongs to control-allocation theory, the second to trajectory
  optimisation, and the two are seldom asked of the same vehicle and the same
  faults. This work measures both. Faults are first expressed as perturbations of
  the attainable force and moment sets of a rocket-propelled spacecraft, which
  classifies each fault by whether it contracts, expands or leaves unchanged the
  set of producible wrenches, or removes the zero wrench from it. The
  classification is applied to the Apollo Lunar Module and then to
  18 spacecraft across five mission classes. Survivability is
  then measured independently, by direct transcription of the six-degree-of-freedom
  landing problem and solution as a nonlinear program: 800 solves over
  16 faults and 5 initial-condition regimes,
  576 over engine placement, and 180 faults injected at
  points along a single Apollo-anchored descent. Every fault examined leaves the
  Lunar Module's hover wrench attainable, yet four of them have onset
  points from which no landing trajectory exists. The least survivable fault, a
  one-interval transport delay, leaves the attainable sets numerically identical
  to the healthy vehicle. Attainable-set analysis is therefore necessary but not
  sufficient for fault-tolerant design: it describes what a damaged vehicle can
  produce, and not whether it can produce it in time.

  *Keywords:* fault-tolerant control, control allocation, attainable moment set,
  trajectory optimisation, powered descent, actuator redundancy
documentclass: article
classoption: [10pt]
geometry: "left=2.6cm, right=2.6cm, top=2.5cm, bottom=2.5cm"
indent: true
numbersections: true
colorlinks: true
linkcolor: black
citecolor: black
urlcolor: black
mainfont: texgyretermes
mainfontoptions:
  - Extension=.otf
  - UprightFont=*-regular
  - ItalicFont=*-italic
  - BoldFont=*-bold
  - BoldItalicFont=*-bolditalic
mathfont: texgyretermes-math.otf
header-includes:
  - \usepackage{amsmath}
  - \usepackage{booktabs}
  - \usepackage{longtable}
  - \usepackage{float}
  - \usepackage{titlesec}
  - \usepackage[font=small,labelfont=bf,labelsep=period]{caption}
  - \usepackage{fancyhdr}
  - \renewcommand{\thesection}{\Roman{section}}
  - \renewcommand{\thesubsection}{\Alph{subsection}}
  - \titleformat{\section}{\centering\normalsize\bfseries}{\thesection.}{0.6em}{}
  - \titleformat{\subsection}{\normalsize\bfseries}{\thesubsection.}{0.6em}{}
  - \titlespacing*{\section}{0pt}{1.4em}{0.7em}
  - \titlespacing*{\subsection}{0pt}{1.1em}{0.5em}
  - \pagestyle{fancy}
  - \fancyhf{}
  - \fancyfoot[C]{\thepage}
  - \renewcommand{\headrulewidth}{0pt}
  - \setlength{\parindent}{1.4em}
  - \setlength{\emergencystretch}{3em}
  - \let\origfigure\figure
  - \let\endorigfigure\endfigure
  - \renewenvironment{figure}[1][2]{\expandafter\origfigure\expandafter[H]}{\endorigfigure}
---

# Nomenclature {-}


| Symbol | Definition |
|:----------------------|:--------------------------------------------------------------------------|
| $\mathbf{F}, \mathbf{M}$ | net force and net moment on the vehicle, body frame (N, N m) |
| $\mathbf{w}$ | wrench, the stacked pair $(\mathbf{F}, \mathbf{M}) \in \mathbb{R}^6$ |
| $m, \mathbf{J}$ | vehicle mass and inertia tensor (kg, kg m$^2$) |
| $\mathbf{v}, \boldsymbol{\omega}$ | body-frame velocity and angular rate (m/s, rad/s) |
| $\mathbf{d}_i, \mathbf{r}_i$ | unit thrust direction and position of actuator $i$ |
| $\mathbf{B}$ | allocation matrix mapping actuator commands to wrench |
| $T, T_{min}, T_{max}$ | engine thrust and its throttle limits (N) |
| $\eta$ | thrust efficiency; delivered thrust is $\eta T$ |
| $\delta, \delta_{max}$ | gimbal deflection and its limit (deg) |
| $\omega_n, \zeta$ | natural frequency and damping ratio of the gimbal servo |
| $\tau_T$ | time constant of the engine thrust response (s) |
| $y_{eng}, dz_{eng}$ | engine half-spacing and axial offset from the centre of mass (m) |
| $t_f, \tau_d$ | fault onset time and planner reaction delay (s) |
| $g$ | lunar gravitational acceleration, 1.625 m/s$^2$ |


| Term | Definition |
|:----------------------|:--------------------------------------------------------------------------|
| 6-DoF | six degrees of freedom: three translational, three rotational |
| RCS | reaction control system; the tier of small, fixed, one-sided thrusters |
| TVC | thrust vector control; steering of the main engine by gimbal |
| DPS | descent propulsion system, the Apollo Lunar Module main engine |
| FTC | fault-tolerant control |
| OCP, NLP | optimal control problem; nonlinear program |
| One-sided actuator | an actuator that can push in one direction only, $f_i \ge 0$ |
| AFS | attainable force set: all net forces the actuators can produce |
| AMS | attainable moment set: all net moments the actuators can produce |
| Capability space | the space in which the AFS and AMS live; the space of producible wrenches |
| Conditional AMS | moments attainable while the vertical force is held at the hover value |
| Hover wrench | the wrench that holds the vehicle in steady hover: weight up, zero moment |
| Support function | $h(\mathbf{u}) = \max\{\mathbf{u}\cdot\mathbf{x} : \mathbf{x} \in X\}$, the reach of set $X$ in direction $\mathbf{u}$ |
| Mean support radius | the average of $h(\mathbf{u})$ over directions; a size measure valid for flat sets |
| Glide cone | a minimum elevation angle of the vehicle above the horizon, seen from the landing site |
| Landing gate | the fixed set of touchdown limits a trajectory must satisfy to count as a landing |
| Gate margin | worst gate criterion divided by its limit; $\le 1$ is a landing |
| Transport delay | a fault that shifts the whole control sequence by one discretisation interval |


\setcounter{table}{0}

# Introduction

A rocket-propelled spacecraft controls its position and attitude with a small
number of actuators that push in one direction only. A main engine produces
thrust along its nozzle axis and can be gimballed through a few degrees; a
reaction-control thruster either fires or does not. When one of these actuators
degrades, two distinct questions arise, and they are conventionally answered by
different methods. The first is what the vehicle can still produce: the set of
net forces and moments available from the surviving actuators, studied in the
control-allocation literature as the attainable force and moment sets [15, 16,
18]. The second is whether the vehicle can still complete its manoeuvre: whether
a dynamically feasible, constraint-satisfying trajectory to the goal still
exists, which a trajectory optimiser decides [4, 5, 12]. The first is a
statement about an instant, the second about a sequence.

This thesis measures both on the same vehicles and the same faults. Three
contributions follow.

1. A characterisation of actuator faults in capability space. Each fault is
   expressed as a perturbation of the attainable force and moment sets and
   classified by its effect on them.
2. A fleet survey applying the same measures to 18 spacecraft in
   five mission classes, which tests whether the single-vehicle classification
   is a property of the faults or of the vehicle.
3. A quantitative evaluation of fault-tolerant motion planning for an
   Apollo-class Lunar Module, comprising 1,556
   six-degree-of-freedom optimal-control solves across four campaigns.

The vehicle of record is the Apollo Lunar Module in its powered-descent
configuration. It was chosen because its mass, inertia, thrust, gimbal throw and
reaction-control layout are documented in the public record [24, 26], and
because a lunar landing has an unambiguous success criterion. Fault detection,
isolation and identification are outside the scope: every result assumes the
fault becomes known to the planner at the instant it occurs, except in the one
campaign that varies the reaction delay deliberately. Consequently, every
survivability figure reported here is an upper bound on what a system with a
realistic diagnosis latency would achieve.

Section \ref{sec:background} reviews the two literatures this work sits
between. Sections \ref{sec:vehicles}--\ref{sec:campaigns} give the method:
the vehicle and actuator models, the fault model, the simulation and
motion-planning environment, and the design of the evaluation campaigns.
Section \ref{sec:results} reports the results, Section \ref{sec:discussion}
interprets them, and Section \ref{sec:conclusions} concludes. Every figure was
produced by a script in the accompanying repository; Appendix A maps each result
to its script.

# Background and related work {#sec:background}

## Six-degree-of-freedom spacecraft dynamics

The rigid-body motion of a spacecraft is described by Newton's law for the
translation of the centre of mass and Euler's equations for rotation about it.
Standard treatments are Wie [1], Hughes [2] and Markley and Crassidis [3]. In
the body frame,

$$
m(\dot{\mathbf{v}} + \boldsymbol{\omega} \times \mathbf{v}) = \mathbf{F},
\qquad
\mathbf{J}\dot{\boldsymbol{\omega}} + \boldsymbol{\omega} \times \mathbf{J}\boldsymbol{\omega} = \mathbf{M} .
$$

Two properties of this system matter throughout. The vehicle is underactuated in
the wrench: its actuators cannot produce arbitrary $(\mathbf{F}, \mathbf{M})$
pairs, because thrusters are one-sided and engines are confined to a narrow cone
about the nozzle axis. And force and moment are cross-coupled: an engine offset
from the centre of mass cannot produce force without also producing moment, so
a thrust fault is never only a thrust fault.

## Motion planning by constrained optimisation

Trajectory generation for such systems is posed as an optimal control problem
and solved numerically. Betts [4, 5] distinguishes indirect methods, which solve
the optimality conditions, from direct methods, which discretise the trajectory
and pass the resulting finite problem to a nonlinear-programming solver. Direct
transcription [6, 7] dominates practice because path constraints enter as
ordinary algebraic inequalities.

Powered descent has a substantial convex-optimisation literature. Açıkmeşe and
Ploen [8] cast Mars powered descent as a convex program; Blackmore et al. [9]
extended it to minimum-landing-error guidance; and Açıkmeşe et al. [10] proved
lossless convexification, under which the non-convex lower thrust bound can be
relaxed without changing the optimum. Full 6-DoF landing with attitude states is
not convex, and is treated either by successive convexification [11] or by
direct transcription to a general nonlinear program. Malyuta et al. [12] survey
the field.

The present work uses direct transcription with a general-purpose interior-point
solver rather than a convexified formulation, because several of the faults
studied here alter the structure convexification relies on: a valve stuck open
removes the feasibility of the lower thrust bound, and a transport delay shifts
the control grid. The problem is built with CasADi [14] and solved with
IPOPT [13].

## Control allocation and attainable sets

Where the planner demands a wrench, the allocator must produce it from actuators
with limits. Durham [15, 16] introduced the attainable moment set, the image of
the admissible control set under the allocation map, as the object that decides
whether a demanded moment is achievable. Bodson [17] compared allocation
algorithms and Johansen and Fossen [18] surveyed the field. For one-sided
actuators with bounded magnitude the attainable set is a convex polytope, and
testing whether a required wrench lies inside it is a linear program; Sections
\ref{sec:vehicles} and \ref{sec:results} use exactly that construction.

Whether a set of one-sided actuators retains authority about every axis is
settled by Farkas' lemma [21]: authority is lost precisely when a direction
exists that no surviving actuator can oppose. This gives an exact count of which
actuator failures cost a control degree of freedom, in place of a worst-case
assumption.

## Fault-tolerant control

Zhang and Jiang [19] classify fault-tolerant control into passive schemes, which
are robust to an anticipated fault set, and active schemes, which detect a fault
and reconfigure. Blanke et al. [20] give the standard treatment of diagnosis and
reconfiguration. The faults modelled here are drawn from the propulsion
literature — throat erosion, injector blockage, feed-coupled combustion
instability and valve failures [33, 34] — and are expressed in the three
dynamical forms fault-tolerant control uses: multiplicative changes to actuator
gain, additive disturbances, and structural changes to the input set.

## Position of this work

The allocation literature measures a fault by its effect on the attainable set.
The trajectory-optimisation literature measures it by whether a plan still
exists. Both are standard, and they are rarely applied to the same fault set on
the same vehicle. Section \ref{sec:discussion} shows that on this vehicle they
disagree.

# Vehicle and actuator models {#sec:vehicles}

## The fleet and its data

18
spacecraft with usable actuator geometry are modelled, drawn from five mission
classes: launch-vehicle boosters, low-Earth-orbit satellites,
geostationary satellites, crewed vehicles and deep-space probes. Each vehicle is
described by mass, principal inertia, a list of reaction-control thrusters
(position, unit fire direction, rated thrust) and a list of main engines (pivot
position, nozzle axis, rated thrust, gimbal cone half-angle).

The underlying parameter workbook supplies thrust magnitudes, actuator counts
and masses from published sources. It contains no thruster positions, no thrust
directions, no gimbal limits and no inertia tensors; all four are supplied by
the geometry model, and each entry carries a provenance flag. The split is
87 sourced, 82 estimated and
1 missing across 175 entries. Only the
Apollo Lunar Module layout is a validated model rather than a reconstruction,
which is why the detailed fault campaigns are run on it and not on the fleet.

## Attainable force and moment sets

For a vehicle with one-sided thrusters and gimballed engines, the attainable
force set (AFS) and attainable moment set (AMS) are computed by a
support-function sweep. For each of a large number of unit directions
$\mathbf{u}$, the admissible actuator combination that maximises
$\mathbf{u} \cdot \mathbf{x}$ is found in closed form, and the convex hull of
those support points is the set [15, 16, 22].

Three size measures are used. Volume is the natural one but vanishes for
degenerate sets, and a vehicle with a single centreline gimballed engine has no
roll authority at all, so its moment set is planar. The mean support radius, the
average of the support function over directions, is therefore used wherever
vehicles of different architecture are compared. Containment of the origin is
reported separately, because it is a topological property no size measure
detects: if the origin leaves the set, the zero wrench is no longer attainable.

The unconstrained AMS overstates what a descending vehicle has available,
because it is free to spend the whole actuator set on one moment and let the
vehicle fall. The conditional AMS is therefore also computed: the set of moments
attainable while the vertical force is held at the value that supports the
vehicle's weight, obtained by solving one linear program per direction. Whether
the hover wrench itself remains attainable is tested the same way.

## Redundancy as a geometric property

A count of actuators is a poor measure of redundancy when actuators are
one-sided, because the survivors may all push the same way. The exact criterion
is Farkas' lemma [21]: a set of thrusters retains authority about every axis
unless some direction exists that none of the survivors can oppose. Enumerating
subsets and testing this condition identifies the minimal fatal loss sets. The
same enumeration over all $2^N$ subsets of $N$ actuators gives the fraction of
the loss space that costs a degree of freedom. That fraction is a property of
geometry alone: it assumes no per-unit failure probability, and it is reported
as such rather than as a reliability.

## The Apollo Lunar Module model and its engine spacing

The Lunar Module has one descent engine. To study engine-out faults at all, the
model splits it into two half-thrust engines at $y = \pm y_{eng}$. This is the
one invented parameter in the vehicle, and its value is bounded. A single
surviving gimbal can trim the moment left by a dead engine only while

$$
y_{eng} \;\le\; dz_{eng} \tan \delta_{max} \;=\; 0.263\ \text{m},
$$

with $dz_{eng} = 2.50$ m and
$\delta_{max} = 6^\circ$ taken from the vehicle [26]. Below
this threshold the split adds no roll authority the real vehicle lacked; above
it, the model would fly a vehicle with authority the Lunar Module never had. The
spacing is fixed at $y_{eng} = 0.25$ m throughout, except in the
campaign that varies it deliberately.

# Fault model {#sec:faults}

Faults are expressed as changes to the actuator model, in the three forms used
in the fault-tolerant control literature [19, 20].

*Multiplicative* faults change actuator gain. Thrust efficiency
$\eta \in (0, 1]$ with delivered force $\eta T$ represents turbopump
degradation, injector blockage and throat erosion [33]; $\eta > 1$ represents a
pressurant-regulator runaway. A slow thrust response is a change to the lag time
constant $\tau_T$, and a sluggish or underdamped gimbal a change to
$(\omega_n, \zeta)$.

*Additive* faults introduce a term independent of the command: a fixed nozzle
misalignment from asymmetric erosion, or a feed-coupled thrust oscillation
(chugging) at fixed amplitude and frequency [34].

*Structural* faults change the input set itself. An engine fails off; a valve
sticks open so the engine cannot be throttled below a floor $T_{min} > 0$; a
gimbal seizes; a transport delay shifts the whole control sequence by one
discretisation interval.

The twelve faults evaluated on the Lunar Module are listed in Appendix B with
their class and temporal character. The fleet study uses a nine-fault subset
applicable across architectures.

# Simulation and motion-planning environment {#sec:environment}

## Plant

The plant is a 6-DoF rigid body above a flat lunar surface with constant
gravity $g = 1.625$ m/s$^2$, augmented with actuator states. The rigid body carries twelve states — position and
velocity in the local frame, Euler angles and body rates — and each engine
carries five more: thrust, and pitch and yaw gimbal deflection with their rates.
With two engines the model has 22 states.

Engine thrust responds as a first-order lag. Each gimbal axis is a second-order
servo, $\ddot{\delta} = \omega_n^2(\delta_c - \delta) - 2\zeta\omega_n\dot{\delta}$,
so that a degraded actuator is a change of parameters rather than a change of
equation. The 16 reaction-control thrusters are one-sided,
$0 \le f_i \le F$, and enter through a fixed $6 \times 16$ allocation
matrix $\mathbf{B} = [\mathbf{d}_i;\ \mathbf{r}_i \times \mathbf{d}_i]$.

Vehicle parameters are the documented Apollo values [26]: 7,711 kg
landing mass, 45,040 N of descent-engine thrust,
$\pm6^\circ$ of gimbal throw, and 16 thrusters of
445 N in four quads. Mass is held constant; propellant
depletion is not modelled.

## Transcribed optimal control problem

The landing problem is transcribed directly. States and controls at every node
are decision variables; the dynamics are imposed as equality constraints between
consecutive nodes by fixed-step Runge–Kutta integration; path constraints enter
as algebraic inequalities [5, 6]. The cost penalises distance to the landing site
at every node together with control effort. The problem is built with
CasADi [14] and solved with IPOPT [13]. The path constraints are listed in
Table \ref{tbl:constraints}.


| Constraint | Value | Purpose |
|:----------------|:------------------------------|:----------------------------------------------|
| Glide cone | 12$^\circ$ above the horizon | excludes a dive to the surface followed by a crawl to the pad |
| Attitude | 45$^\circ$ per axis | planner envelope |
| Body rate | 10 $^\circ$/s | planner envelope |
| Speed | 60 m/s per axis and in norm | a per-axis box alone would admit 104 m/s on a shallow approach |
| Altitude floor | $z > 0$, contact at 1 m | the vehicle may not pass through the surface |
| Actuator bounds | thrust and gimbal limits | hardware |

: Path constraints of the nominal landing problem. \label{tbl:constraints}


Two features of the formulation affect the fault results and are stated
explicitly. First, a decaying corridor is applied to the post-fault transient.
The nominal descent rides its velocity limit exactly, so any perturbation places
the post-fault state marginally outside the box, and a hard bound at the first
node would report infeasibility for an overshoot of a few millimetres per
second. The bounds therefore begin at the larger of the initial excursion and a
fixed multiple of the nominal envelope, and contract linearly to the design
envelope within a few seconds. Second, the powered problem terminates at a 1 m
contact altitude where the engine is cut, and the final stretch is an analytic
engine-off ballistic settle. This reproduces the shutdown of the descent engine
when the contact probes below the landing gear touch the surface, and keeps the
problem well posed near the ground.

## Success criterion

A trajectory is scored against a fixed landing gate evaluated at touchdown,
after the ballistic settle: vertical speed $\le 3.0$ m/s, horizontal speed
$\le 1.2$ m/s, tilt $\le 6^\circ$, position error $\le 15$ m and body rate
$\le 5\ ^\circ$/s. The gate margin is the worst of the five criteria normalised
by its limit, so a margin $\le 1$ is a landing and the value is a continuous
severity measure rather than a pass/fail bit.

A separate loss-of-control test marks states from which no vehicle returns —
tilt past $90^\circ$, body rates past $120\ ^\circ$/s, gross speed excursions.
It is deliberately far outside the planner envelope of
Table \ref{tbl:constraints}, so that in every case short of it the solver,
rather than a chosen threshold, decides whether a recovery exists.

## Reference descent

All injection campaigns depart from one nominal descent, anchored on the
documented Apollo approach-phase (P64) geometry [24, 25]. Two points of that
phase are published: high gate at about 7,500 ft, 4.5 nmi and 500 ft/s, and low
gate at about 500 ft, 2,000 ft and 60 ft/s, with the approach between them flown
essentially straight at the landing point. Interpolating to the fastest state
this vehicle model admits with margin gives the anchor state of
Table \ref{tbl:anchor}.


| Quantity | SI | Imperial |
|:--------------------------|:--------------|:--------------|
| Altitude | 736 m | 2416 ft |
| Range to pad | 2724 m | 8937 ft |
| Horizontal speed | 55.0 m/s | 180 ft/s |
| Descent rate | 15.6 m/s | 51 ft/s |
| Line-of-sight depression | 15.13$^\circ$ |  |
| Flight-path angle | 15.87$^\circ$ |  |

: Anchor state of the reference descent, reconstructed from the published Apollo approach geometry [24, 25]. \label{tbl:anchor}


The last two rows are a consistency check: a vehicle flying the approach points
its velocity vector at the landing site, and the two angles agree to
0.75$^\circ$. The anchor is a reconstruction of
published geometry and not telemetry from any particular mission. The healthy
vehicle reaches contact at $t = 65$ s with a gate margin of
0.60. The real P64 approach decelerates continuously,
whereas this trajectory holds the speed cap and brakes late; that is a
consequence of the cost function, not a property of Apollo. The profile and the
injection points used later are shown in Figure \ref{fig:nominal}.


![Reference descent, with the injection points marked. \label{fig:nominal}](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/H1_nominal.png)


# Evaluation campaigns {#sec:campaigns}

Four campaigns of optimal-control solves are run on the Lunar Module model, each
holding a different variable fixed. They are summarised in
Table \ref{tbl:campaigns}.


| Campaign | Variable studied | Design | Solves |
|:----------|:--------------------------------------|:----------------------------------|:----------|
| G | Fault class against initial condition | 16 faults $\times$ 5 regimes $\times$ 10 | 800 |
| F | Engine half-spacing | 12 plants $\times$ 48 states | 576 |
| D, E | Reaction delay and fault severity | bisection on $\tau_d$ and $\eta$; Sobol sample | 272 + 220 |
| H | Injection point along the reference descent | 12 faults $\times$ 15 points | 180 |
| H-R | Constraint relaxation of the H failures | 12 cases $\times$ 4 corridors $\times$ seeds | $\le$ 22 per case |

: Design of the evaluation campaigns. \label{tbl:campaigns}


Campaign G samples initial conditions from five regimes — an approach box, a
dispersed box, a low-and-late box, an upset box and a deliberately critical box
— and applies each fault of the catalogue to each. Campaign F holds the fault
set fixed and varies the engine half-spacing across identical initial
conditions, which isolates the effect of actuator geometry. Campaigns D and E
inject a fault at time $t_f$ and withhold the planner's response for a delay
$\tau_d$, during which the vehicle flies a stale command on a damaged engine;
bisection on $\tau_d$ and on the severity $\eta$ locates the critical values,
and a Sobol-sampled companion measures the drop in landing rate directly.
Campaign H injects each fault at points along the single reference descent, so
that every outcome carries a time, an altitude, a range and a speed. Campaign
H-R re-solves the failures of campaign H under progressively weaker path
constraints, stopping at the first corridor that admits a trajectory; the
altitude floor, the actuator bounds and the landing gate are never relaxed, so
the weakest corridor leaves $z > 0$ as the only constraint on the state.

Initial-condition boxes are sampled with Sobol sequences [28]. Proportions are
reported with Wilson score intervals [29]. Paired comparisons between plants
flown from identical initial conditions use McNemar's test [30].

# Results {#sec:results}

## Actuation and redundancy across the fleet

Figure \ref{fig:accel} shows the per-axis linear and angular acceleration
available to each vehicle, grouped by mission class. Three architectural
patterns appear, and they cut across the classes. Boosters carry one or a few
large gimballed engines and no vehicle-level reaction-control system; their
moment authority is the gimbal deflection times the moment arm, and a single
centreline engine provides no roll authority at all. Several satellites and
Voyager 1 carry only a thruster tier, so every force they produce is coupled to
a moment. Crewed vehicles and large probes carry both tiers.


![Per-axis linear and angular acceleration by spacecraft class. \label{fig:accel}](/home/omersayilgan/Desktop/ThesisGit/studies/actuation_envelopes/figures/_acceleration_by_category.png)


Applying the Farkas test to the Lunar Module's 16 thrusters, which are
responsible for the three moment axes because a gimballed engine performs the
translation, four of the 120
possible losses of two thrusters cost a control degree of freedom; the remainder
are absorbed. Enumerating all $2^N$ loss sets for every vehicle gives the
geometry-only failure share plotted in Figure \ref{fig:reliability}. Orion,
with 24 thrusters and no fatal loss set smaller than
4 units, retains
70\% of its loss space; the Lunar Module, whose
smallest fatal loss sets are pairs, retains 28\%.
Vehicles with a single engine sit at exactly 0.5 on the engine tier, because a
single unit admits only two loss sets.


![Combinatorial success share against thrust-to-weight ratio. \label{fig:reliability}](/home/omersayilgan/Desktop/ThesisGit/studies/reliability/combinatorial_success_vs_tw.png)


## Capability of the Apollo Lunar Module under fault

Each fault of Appendix B was applied to the actuator model and the attainable
sets recomputed. Figure \ref{fig:capgrid} shows the resulting measures and
Figure \ref{fig:sets} the sets themselves. The classification in
Table \ref{tbl:effects} follows from those numbers.


![Capability measures retained under each fault, Apollo Lunar Module. \label{fig:capgrid}](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I0_capability_grid.png)


| Effect on the sets | Faults | Definition |
|:------------------|:------------------------------|:--------------------------------------------|
| Contraction | chugging, $\eta$=0.50, $\eta$=0.15, mixture ratio, engine out | the damaged set is contained in the healthy one |
| Expansion | TVC bias, $\eta$=1.30 | the set grows, but asymmetrically |
| Loss of the origin | stuck open | the zero wrench becomes unattainable |
| No change | $\tau_T$=2.5 s, erosion drift, dead time | the sets are numerically identical to the healthy vehicle |

: Classification of the faults by their effect on the attainable sets. \label{tbl:effects}


The loss-of-origin case is distinct from the others and is invisible to any size
measure. For every other fault the engine can be shut down, so the zero wrench
is available and the hull contains the origin. A valve stuck open removes that
option: the engine's contribution becomes the shell
$\{T\mathbf{d} : T \in [T_{min}, T_{max}]\}$ with $T_{min} > 0$, whose
hull excludes the origin, while retaining
97% of the healthy force-set volume.


![Attainable force sets (top) and moment sets (bottom) under fault. \label{fig:sets}](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I1_sets.png)


Table \ref{tbl:cond} reports the retained fraction of the force set, the moment
set and the conditional moment set at the hover thrust of
12,530 N, together with whether the hover wrench itself
remains attainable. The conditional measure separates faults that the
unconditional sets report as nearly identical. The hover wrench is attainable
under every fault examined.


| Fault | Effect | AFS | AMS | AMS $|$ hover | Hover wrench |
|:----------------------|:--------------|:--------|:--------|:--------------|:--------------|
| engine out | contracted | 0.23 | 0.28 | 0.53 | yes |
| $\eta$=0.15 | contracted | 0.30 | 0.36 | 0.65 | yes |
| stuck open | origin lost | 0.97 | 1.00 | 0.68 | yes |
| $\eta$=0.50 | contracted | 0.52 | 0.59 | 0.94 | yes |
| mixture ratio | contracted | 0.74 | 0.78 | 1.00 | yes |
| healthy | unchanged | 1.00 | 1.00 | 1.00 | yes |
| chugging | contracted | 0.88 | 0.90 | 1.00 | yes |
| $\eta$=1.30 | expanded | 1.39 | 1.30 | 1.00 | yes |
| $\tau_T$=2.5 s | unchanged | 1.00 | 1.00 | 1.00 | yes |
| erosion drift | unchanged | 1.00 | 1.00 | 1.00 | yes |
| dead time | unchanged | 1.00 | 1.00 | 1.00 | yes |
| TVC bias | expanded | 1.08 | 1.04 | 1.08 | yes |

: Retained fraction of each attainable set under fault, Apollo Lunar Module. Values are relative to the healthy vehicle. \label{tbl:cond}


Redundancy within each tier was measured by removing units one at a time.
Losing any single one of the 16 thrusters leaves between
88% and 95% of the conditional moment authority. Losing one of
the two engines leaves 52%.

Sweeping the engine half-spacing and asking, by linear program, whether zero net
moment is attainable while holding hover thrust gives a last trimmable spacing
of 0.258 m, against the analytic bound of
0.263 m derived in Section \ref{sec:vehicles}
(Figure \ref{fig:spacing}). With the thruster tier available, engine-out trim
is achieved at every spacing tested.


![Engine-out trim capability against engine half-spacing. \label{fig:spacing}](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I5_spacing.png)


## Capability across the fleet

The same measures were applied to all 18 vehicles, using the
mean support radius because several moment sets are planar and have zero volume.
Figure \ref{fig:fleetmap} maps the moment authority retained after the worst
single failure of each type, and Table \ref{tbl:fleet} aggregates it.


![Moment authority retained after the worst single failure, by vehicle and fault. \label{fig:fleetmap}](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/IF1_fleet_map.png)


| Fault | Vehicles exposed | Mean retained | Range |
|:------------------------------|:----------------|:--------------|:----------------|
| Engine out | 14 | 0.49 | 0.00 -- 1.00 |
| Thrust reduction, $\eta$=0.15 | 14 | 0.56 | 0.15 -- 1.00 |
| Thrust reduction, $\eta$=0.50 | 14 | 0.74 | 0.50 -- 1.00 |
| Thrust excess, $\eta$=1.30 | 14 | 1.15 | 1.00 -- 1.30 |
| TVC misalignment (3°, 2°) | 14 | 1.01 | 0.94 -- 1.35 |
| Gimbal seizure | 8 | 0.28 | 0.00 -- 0.93 |
| Valve stuck open (30 % floor) | 14 | 0.97 | 0.87 -- 1.00 |
| RCS thruster dead | 12 | 0.95 | 0.87 -- 1.00 |
| RCS thruster stuck open | 12 | 0.95 | 0.87 -- 1.00 |

: Fraction of moment authority retained across the fleet, worst single failure of each type. \label{tbl:fleet}


The four effects of Table \ref{tbl:effects} describe every vehicle in the
fleet. The magnitudes do not transfer: engine-out spans the full range from
total loss of the moment tier to no measurable cost, depending on whether the
vehicle's engines are offset from the centreline.

Defining the distance between two vehicles as the mean absolute difference in
retained authority over the faults both can suffer, same-class pairs differ by
0.130 and different-class pairs by 0.187
(21 and 100 pairs, Figure \ref{fig:similarity}).
The classes are not equally coherent: the low-Earth-orbit satellites respond
almost identically to one another, whereas the two geostationary satellites
differ by more than two vehicles drawn at random. SDO and MSG are both
geostationary and lie at opposite ends of the map; SDO's single engine is on the
centreline and MSG's two are not.


![Pairwise distance between fault responses, with class membership. \label{fig:similarity}](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/IF3_similarity.png)


## Fault class and initial-condition regime

Campaign G comprises 800 solves over 16 faults and
5 regimes. Figure \ref{fig:Ggrid} shows the outcome of every
cell and Table \ref{tbl:Gclass} the landing rate by fault class.


![Outcome by fault and initial-condition regime, campaign G. \label{fig:Ggrid}](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/G0_outcome_grid.png)


| Fault class | Landed | Rate | 95\% Wilson interval |
|:------------------|:------------|:----------|:----------------------|
| none | 44/50 | 0.880 | [0.762, 0.944] |
| additive | 88/100 | 0.880 | [0.802, 0.930] |
| multiplicative | 304/450 | 0.676 | [0.631, 0.717] |
| structural | 119/200 | 0.595 | [0.526, 0.661] |

: Landing rate by fault class, campaign G. \label{tbl:Gclass}


Structural faults land at 0.595, multiplicative
faults at 0.676 and additive faults at
0.880; the healthy control lands at
0.880. The additive and healthy intervals overlap.
Across regimes, the landing rate runs from
0.875 in the approach box to
0.412 in the critical box.

## Engine half-spacing

Campaign F flies 12 plants from 48 identical initial
conditions each, 576 solves in total
(Figure \ref{fig:Fgrid}, Table \ref{tbl:Fspacing}).


![Outcome by plant and engine half-spacing, campaign F. \label{fig:Fgrid}](/home/omersayilgan/Desktop/ThesisGit/studies/fault_onset/figures/F0_outcome_grid.png)


| Plant | $y_{eng}$ = 1.5 m | $y_{eng}$ = 0.25 m | Change |
|:--------------------------|:----------------|:------------------|:----------|
| healthy | 0.917 | 0.896 | -0.021 |
| engine 2 out | 0.000 | 0.708 | +0.708 |
| $\eta$=0.50 | 0.812 | 0.854 | +0.042 |
| $\eta$=0.15 | 0.000 | 0.833 | +0.833 |
| gimbal $\omega_n$=0.6 | 0.479 | 0.479 | +0.000 |
| gimbal $\zeta$=0.25 | 0.583 | 0.562 | -0.021 |

: Landing rate at two engine half-spacings, campaign F. \label{tbl:Fspacing}


The response splits by fault type. Engine-out moves from
0% to
71%, and near-total thrust loss from
0% to
83%. The two gimbal-dynamics faults move by
one percentage point or less.

## Reaction delay and fault severity

Of the 272 solves in campaign D, 57
land, 8 miss the gate, 172
admit no feasible re-plan at the end of the delay, and
35 are lost during the delay itself.

The companion campaign E over 220 Sobol-sampled states gives a landing
rate of 0.977 for the healthy vehicle
[0.948, 0.990] against 0.205
for the faulted vehicle [0.156, 0.264]. A
decision-tree surrogate fitted to those outcomes reaches an AUC of
0.822, with permutation importance concentrated on the fault
severity $\eta$ (0.179) and the onset time $t_f$
(0.040); no component of the vehicle state exceeds
either.

## Injection point along the reference descent

Campaign H injects 12 faults at 15 points along the
reference descent, 180 solves, of which 168 land
(Figure \ref{fig:Hgrid}). The faults fall into three groups: those that survive
every injection point, those with a boundary part-way along the descent, and
those that fail at most of the injection points. Four
faults have at least one injection point with no recovery. Figure \ref{fig:Hsurv} shows the landing
share by fault class against injection time: the failures are concentrated late
in the descent, in the braking phase, where the vehicle is low and still fast.


![Outcome by fault and injection point along the descent, campaign H. \label{fig:Hgrid}](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/H2_grid.png)


![Landing share by fault class against injection time. \label{fig:Hsurv}](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/H3_survival.png)


![Recovery trajectories in three dimensions, one panel per fault. \label{fig:H3d}](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/3D1_baseline_by_fault.png)


Figure \ref{fig:H3d} shows the recoveries in three dimensions. The asymmetric
faults do not remain in the vertical plane: an engine-out vehicle yaws under
asymmetric thrust and recovers through a cross-range excursion that returns to
the landing site.

## Constraint relaxation

Campaign H recorded 11 injections with no recovery
trajectory. Each was re-solved at four progressively weaker corridors
(Figure \ref{fig:HRladder}), the weakest of which enforces only $z > 0$ on the
state.


![Weakest constraint relaxation that admits a trajectory. \label{fig:HRladder}](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/HR1_ladder.png)


Three of the twelve cases recover, all at the first rung, in which only
the glide cone is opened. The attitude, rate and speed relaxations admit no
additional case. The recoveries that need the cone fly a
6.0--6.8$^\circ$
path against the 12$^\circ$ nominal floor.

Nine cases remain infeasible with only $z > 0$ enforced, after
22 independent solver seeds across the four corridors. By fault, these are
dead time (5), engine out (2), $\eta$=0.15 (2).

# Discussion {#sec:discussion}

## Attainable sets do not predict survivability

Section \ref{sec:results} reports two facts that stand in tension. Every fault
examined leaves the Lunar Module's hover wrench attainable
(Table \ref{tbl:cond}), and four of them have onset points from which
no landing trajectory exists (Figure \ref{fig:Hgrid}). Figure \ref{fig:capvs}
plots the two measures against each other.


![Retained conditional moment authority against landing share. \label{fig:capvs}](/home/omersayilgan/Desktop/ThesisGit/studies/capability_space/figures/I3_capability_vs_survival.png)


The transport delay is the clearest case. Its attainable sets are numerically
identical to the healthy vehicle in every measure computed — volume, per-axis
authority, containment of the origin and attainability of the hover wrench — and
it is the least survivable fault in the campaign, landing from
67% of injection points and accounting for
five of the nine injections that no
relaxation recovered. A delay does not remove authority; it removes the ability to apply
that authority at the moment the state requires it. An attainable set is a
statement about an instant and cannot represent this.

The converse also holds. The stuck-open valve retains only
68% of its conditional moment authority
and loses the origin outright, yet lands from
100% of injection points. A reduced set is
survivable as long as what remains contains everything the trajectory demands.

The two measures are therefore complementary rather than redundant. A fault that
places the required wrench outside the attainable set is unrecoverable for a
reason no control law can address, and allocation analysis identifies it
cheaply. A fault that leaves the required wrench inside the set may still be
unrecoverable through timing or through the state the vehicle happens to occupy,
and only a trajectory campaign identifies it. A fault-tolerant scheme that
reasons solely about attainable sets will rank the temporal faults as harmless,
because in capability space they are.

## Two mechanisms of redundancy

A thruster ring and an engine cluster are different redundancy problems, and the
distinction holds at both scales examined. On the Lunar Module, losing one of
16 thrusters costs at most 12% of the conditional moment
authority, whereas losing one of two engines costs 48%. Across the
fleet, thruster-tier faults are the mildest column of Figure \ref{fig:fleetmap}
for every vehicle and engine-tier faults the harshest. A ring of many small
one-sided units degrades gradually; a cluster of few large units degrades in
steps.

This also accounts for the fleet similarity result. The separation between
same-class and different-class pairs is real but small
(0.130 against 0.187), and the vehicles that
respond alike share a tier structure rather than a mission. Two geostationary
satellites lie at opposite ends of the map because one has its engine on the
centreline and the other does not, while a booster and a probe of the same
single-engine architecture lie together. For predicting fault response, actuator
architecture is the useful classification and mission class is not.

## Geometry buys tolerance to geometric faults only

Campaign F isolates the effect of actuator geometry. Moving the engines inside
the roll-trim
threshold of Section \ref{sec:vehicles} takes engine-out from
0% to
71% landings and leaves the
gimbal-dynamics faults where they were. A change to actuator geometry buys
tolerance to faults that are themselves geometric. Faults that are temporal —
delay, lag, oscillation, drift — are untouched by it. They are also the faults
that the attainable sets cannot distinguish from healthy, and the faults that
the constraint relaxation of campaign H-R could not recover. The three results
are consistent with a single division of the fault space into geometric and
temporal effects.

## Constraints belong in the statement of a result

Campaign H-R reduced 11 reported failures to nine by
giving the same states and the same plants a wider corridor, and the only
constraint that mattered was the glide cone. Any study reporting fault
survivability from a constrained planner is reporting its constraints as much as
its vehicle. The defensible form of such a claim is not that a fault is
unrecoverable after a given time, but that it is unrecoverable after that time
within a stated corridor, and after some later time with the corridor opened.
The interval between the two is the value available to an envelope-expanding
guidance mode.

## Limitations

Five assumptions bound the results.

Detection is instantaneous and perfect everywhere except campaigns D and E.
Every survivability figure is therefore an upper bound on what a system with a
diagnosis latency achieves, and campaign D indicates the penalty is not small.

The planning is open loop. Each result is a single optimal-control solve rather
than a closed loop re-solving in flight, which treats evolving faults — the
erosion drift in particular — more favourably than a receding-horizon
implementation would.

Local infeasibility is not global infeasibility. The transcribed problem is
non-convex, so a converged solve proves that a trajectory exists while a failed
solve does not prove that none does. This is why campaign H-R uses 22 seeds
per case before recording a loss.

The fleet geometry is largely estimated. Of 175 geometry
entries, 82 are estimated from published envelopes
rather than sourced, and only the Lunar Module layout is validated. The fleet
comparisons are comparisons between models of these spacecraft.

Mass is constant. The plant does not deplete propellant, which understates the
cost of a partial-thrust fault over a long burn.

# Conclusions {#sec:conclusions}

Actuator faults were characterised in two independent ways on the same vehicles
and the same fault set: as perturbations of the attainable force and moment
sets, and as changes in the existence of a feasible landing trajectory.

Four effects on the attainable sets account for every fault and every vehicle
examined: contraction, expansion, loss of the origin, and no change. The
classification transfers across 18 spacecraft in five mission
classes; the magnitudes do not, and depend on actuator architecture rather than
on mission class.

The two characterisations do not agree. Every fault studied leaves the Lunar
Module's hover wrench attainable, yet four of them have onset points
from which no landing trajectory exists, and the least survivable fault of all
leaves the attainable sets numerically unchanged. Attainable-set analysis is
necessary but not sufficient for fault-tolerant design.

Two mechanisms of redundancy are distinguished by the same data. A ring of many
one-sided thrusters degrades gradually, at most 12% of conditional
moment authority per unit lost, whereas a cluster of two engines degrades in
steps of 48%. Redundancy is a geometric property, not a count:
four of the 120 ways to
lose two Lunar Module thrusters cost a degree of freedom, and the rest are
absorbed.

Actuator geometry buys tolerance to geometric faults and none to temporal ones,
and the temporal faults are precisely those the attainable sets cannot see. The
natural extension of this work is therefore to replace the attainable set, a
statement about an instant, with its reachable set over a horizon, and to pair
it with a detection model and a closed-loop re-planner so that the upper bounds
reported here can be converted into achievable performance.

\newpage

# References {-}

1. Wie, B. *Space Vehicle Dynamics and Control*, 2nd ed. AIAA Education Series, 2008.
2. Hughes, P.C. *Spacecraft Attitude Dynamics*. Wiley, 1986 (Dover reprint, 2004).
3. Markley, F.L., and Crassidis, J.L. *Fundamentals of Spacecraft Attitude Determination and Control*. Springer, 2014.
4. Betts, J.T. "Survey of Numerical Methods for Trajectory Optimization." *Journal of Guidance, Control, and Dynamics*, 21(2):193–207, 1998.
5. Betts, J.T. *Practical Methods for Optimal Control and Estimation Using Nonlinear Programming*, 2nd ed. SIAM, 2010.
6. Hargraves, C.R., and Paris, S.W. "Direct Trajectory Optimization Using Nonlinear Programming and Collocation." *Journal of Guidance, Control, and Dynamics*, 10(4):338–342, 1987.
7. Rao, A.V. "A Survey of Numerical Methods for Optimal Control." *Advances in the Astronautical Sciences*, 135(1):497–528, 2009.
8. Açıkmeşe, B., and Ploen, S.R. "Convex Programming Approach to Powered Descent Guidance for Mars Landing." *Journal of Guidance, Control, and Dynamics*, 30(5):1353–1366, 2007.
9. Blackmore, L., Açıkmeşe, B., and Scharf, D.P. "Minimum-Landing-Error Powered-Descent Guidance for Mars Landing Using Convex Optimization." *Journal of Guidance, Control, and Dynamics*, 33(4):1161–1171, 2010.
10. Açıkmeşe, B., Carson, J.M., and Blackmore, L. "Lossless Convexification of Nonconvex Control Bound and Pointing Constraints of the Soft Landing Optimal Control Problem." *IEEE Transactions on Control Systems Technology*, 21(6):2104–2113, 2013.
11. Szmuk, M., and Açıkmeşe, B. "Successive Convexification for 6-DoF Mars Rocket Powered Landing with Free-Final-Time." *AIAA SciTech Forum*, 2018.
12. Malyuta, D., Reynolds, T.P., Szmuk, M., Lew, T., Bonalli, R., Pavone, M., and Açıkmeşe, B. "Convex Optimization for Trajectory Generation." *IEEE Control Systems Magazine*, 42(5):40–113, 2022.
13. Wächter, A., and Biegler, L.T. "On the Implementation of an Interior-Point Filter Line-Search Algorithm for Large-Scale Nonlinear Programming." *Mathematical Programming*, 106(1):25–57, 2006.
14. Andersson, J.A.E., Gillis, J., Horn, G., Rawlings, J.B., and Diehl, M. "CasADi: A Software Framework for Nonlinear Optimization and Optimal Control." *Mathematical Programming Computation*, 11(1):1–36, 2019.
15. Durham, W.C. "Constrained Control Allocation." *Journal of Guidance, Control, and Dynamics*, 16(4):717–725, 1993.
16. Durham, W.C. "Attainable Moments for the Constrained Control Allocation Problem." *Journal of Guidance, Control, and Dynamics*, 17(6):1371–1373, 1994.
17. Bodson, M. "Evaluation of Optimization Methods for Control Allocation." *Journal of Guidance, Control, and Dynamics*, 25(4):703–711, 2002.
18. Johansen, T.A., and Fossen, T.I. "Control Allocation — A Survey." *Automatica*, 49(5):1087–1103, 2013.
19. Zhang, Y., and Jiang, J. "Bibliographical Review on Reconfigurable Fault-Tolerant Control Systems." *Annual Reviews in Control*, 32(2):229–252, 2008.
20. Blanke, M., Kinnaert, M., Lunze, J., and Staroswiecki, M. *Diagnosis and Fault-Tolerant Control*, 3rd ed. Springer, 2016.
21. Boyd, S., and Vandenberghe, L. *Convex Optimization*. Cambridge University Press, 2004.
22. Rockafellar, R.T. *Convex Analysis*. Princeton University Press, 1970.
23. Klumpp, A.R. "Apollo Lunar Descent Guidance." *Automatica*, 10(2):133–146, 1974.
24. Bennett, F.V. "Apollo Experience Report — Mission Planning for Lunar Module Descent and Ascent." NASA TN D-6846, 1972.
25. Cheatham, D.C., and Bennett, F.V. "Apollo Lunar Module Landing Strategy." *Apollo Lunar Landing Mission Symposium*, NASA, 1966.
26. Grumman Aerospace Corporation. *Apollo Operations Handbook, Lunar Module, LM 10 and Subsequent, Volume I: Subsystems Data*. LMA790-3-LM, 1970.
27. NASA Manned Spacecraft Center. *Apollo 11 Mission Report*. MSC-00171, 1969.
28. Sobol', I.M. "On the Distribution of Points in a Cube and the Approximate Evaluation of Integrals." *USSR Computational Mathematics and Mathematical Physics*, 7(4):86–112, 1967.
29. Wilson, E.B. "Probable Inference, the Law of Succession, and Statistical Inference." *Journal of the American Statistical Association*, 22(158):209–212, 1927.
30. McNemar, Q. "Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages." *Psychometrika*, 12(2):153–157, 1947.
31. Virtanen, P., et al. "SciPy 1.0: Fundamental Algorithms for Scientific Computing in Python." *Nature Methods*, 17:261–272, 2020.
32. Harris, C.R., et al. "Array Programming with NumPy." *Nature*, 585:357–362, 2020.
33. Sutton, G.P., and Biblarz, O. *Rocket Propulsion Elements*, 9th ed. Wiley, 2016.
34. Harrje, D.T., and Reardon, F.H. (eds.) *Liquid Propellant Rocket Combustion Instability*. NASA SP-194, 1972.

\newpage

# Appendix A: Origin of each result {-}

Every number and figure in this document was read from the study that produced
it; no result was recomputed for this document.


| Result | Produced by | Section |
|:--------------------------------------------|:--------------------------------------------|:----------|
| Fleet actuation envelopes, per-axis accelerations | `studies/actuation_envelopes/` | VII.A |
| Thruster-loss enumeration, combinatorial shares | `studies/reliability/` | VII.A |
| Engine-placement threshold | `studies/engine_placement/` | III.D |
| Capability space, single vehicle | `studies/capability_space/run_capability_study.py` | VII.B |
| Capability space, fleet | `studies/capability_space/run_fleet_capability.py` | VII.C |
| Vehicle model and landing OCP | `src/apollo_gnc/apollo_full.py` | V |
| Fault library, gate and loss criteria | `studies/fault_onset/fault_lib.py` | IV, V |
| Campaign G | `studies/fault_taxonomy/` | VII.D |
| Campaign F | `studies/fault_onset/run_study_F.py` | VII.E |
| Campaigns D and E | `studies/fault_onset/run_study_D.py`, `run_study_E.py` | VII.F |
| Campaign H | `studies/fault_injection/run_injection_study.py` | VII.G |
| Campaign H-R | `studies/fault_injection/run_relaxed_study.py` | VII.H |

: Mapping from each result to the script that produced it. \label{tbl:provenance}


\newpage

# Appendix B: Fault catalogue {-}

The faults evaluated on the Apollo Lunar Module, with the class of
Section \ref{sec:faults}, the section of the underlying fault framework each is
drawn from, and its temporal character.


| Fault | Class | Framework § | Temporal character |
|:------------------------------|:------------------|:------------|:----------------------|
| Healthy (control) | none | — | — |
| Thrust-vector misalignment (3°, 2°) | additive | 2.7 | incipient |
| Thrust oscillation (chugging) | additive | 2.3 | intermittent / forced |
| Thrust reduction, $\eta$=0.50 | multiplicative | 2.1 | abrupt / incipient |
| Thrust reduction, $\eta$=0.15 | multiplicative | 2.1 | abrupt |
| Thrust excess, $\eta$=1.30 | multiplicative | 2.2 | abrupt |
| Slow thrust response, $\tau_T$=2.5 s | multiplicative | 2.5 | incipient |
| Mixture-ratio shift (coupled) | multiplicative | 2.4 | incipient |
| Throat-erosion drift | multiplicative | 2.10 | incipient |
| Valve stuck open (thrust floor) | structural | 2.2 / 1.4 | abrupt |
| Engine out | structural | 2.1 / 3.1 | abrupt |
| Transport delay (1 interval) | structural | 2.6 | abrupt / intermittent |

: Fault catalogue evaluated on the Apollo Lunar Module. \label{tbl:catalogue}
