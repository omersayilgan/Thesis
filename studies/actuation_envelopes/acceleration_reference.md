---
title: "Achievable Acceleration Across the Fleet"
subtitle: "Maximum linear and angular acceleration per body axis, by spacecraft class"
date: "26 August 2026"
geometry: margin=1.8cm
fontsize: 10pt
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

# What these numbers are

For each spacecraft the actuation-envelope model builds the **achievable force
set** and the **achievable moment set** — every net wrench the vehicle's
thrusters and gimballed engines can produce with all of them available at once.
The maximum force along a body axis is the support function of that set
evaluated on the axis, and the accelerations follow directly:

$$a_j = \frac{h_F(e_j)}{m} \qquad\qquad \alpha_j = \frac{h_M(e_j)}{I_{jj}}$$

Each axis is evaluated in both directions and the **larger of the two** is
reported here, since the question is what the vehicle can achieve. Layouts are
often strongly asymmetric — a lander can push hard along $-z$ and barely at all
along $+z$ — so the full signed breakdown is in Appendix A.

Three properties of this figure are worth being explicit about, because they
make it an **upper bound** rather than an operating value:

* **Everything fires at once.** The number assumes every thruster and engine is
  simultaneously available and commanded to the optimum. No propellant budget,
  duty cycle, thermal limit or control-allocation loss is applied.
* **It is instantaneous.** Angular acceleration is $M/I_{jj}$ about the
  principal axes, neglecting gyroscopic coupling and products of inertia, so it
  is a small-rate figure and not a slew capability.
* **Main engines are included.** For satellites the axial number is dominated
  by the apogee engine, which is a manoeuvre actuator and not something used
  for attitude or translation control. The lateral and angular figures are the
  ones that describe day-to-day control authority.

Masses and thrust levels are read from the fleet workbook; dimensions and
inertias are shape-model estimates (uniform cylinder or box), which is the
dominant uncertainty in every angular figure. A factor-of-two error in $I_{jj}$
moves $\alpha_j$ by the same factor.

# Data coverage — and two kinds of zero

A zero in these tables means one of two entirely different things, and pooling
them would produce nonsense:

**Structural zero.** The modelled actuators genuinely produce no authority
about that axis. A single centreline gimballed engine cannot generate roll no
matter how large it is, which is why Ariane 5, Vega and Vega-C all show
$\alpha_z = 0$ — real launchers solve this with a separate roll-control system
that is not in the model. These are real results and are kept.

**Data gap.** The vehicle has the hardware, but the workbook records no thrust
value for it. Reporting that as zero authority would be a statement about the
spreadsheet, not the spacecraft.


| Vehicle | Class | Why it is excluded |
|:------------------------------|:------------------|:----------------------------------------------|
| Sentinel-1A | LEO Satellites | no actuator thrust recorded |
| GOES-16 (GOES-R) | GEO Satellites | no thrust recorded for either tier |
| GOES-19 (GOES-U) | GEO Satellites | no thrust recorded for either tier |


Those 3 carry no usable figure at all and are excluded from every
statistic below.

The distinction is drawn **per quantity**, because a vehicle can be sound in
one and empty in the other:


| Vehicle | Linear usable | Angular usable | What is missing |
|:--------------------------|:-------------|:--------------|:----------------------------------------|
| Juno | yes | no | 12 RCS thrusters named with no thrust recorded |


Juno is the case that matters. Its main engine is documented, so its linear
figure stands; but that engine is rigidly mounted on the centreline and
produces no moment, which means its entire attitude authority is the twelve
thrusters the workbook names and gives no thrust for. Its angular row is
therefore not a measurement of Juno and is excluded from the angular
statistics.

Note also what is **not** a gap: every booster here records its RCS tier as
"None at vehicle level", which is a design fact rather than a hole — a launcher
of this kind controls attitude with engine gimbal alone. Europa Clipper
likewise records "same engine set, no separate RCS tier". Those vehicles are
complete and are kept.

Usable vehicles per class:


| Class | Linear | Angular |
|:----------------------|:--------------|:--------------|
| Boosters | 4 of 4 | 4 of 4 |
| Crewed Vehicles | 4 of 4 | 4 of 4 |
| GEO Satellites | 2 of 4 | 2 of 4 |
| LEO Satellites | 3 of 4 | 3 of 4 |
| Deep Space Probes | 5 of 5 | 4 of 5 |


\newpage

# Per-vehicle acceleration

Linear acceleration in m/s²; angular acceleration in °/s². Both are the maximum
over the two directions along each axis. Body axes follow each vehicle's own
convention as built in the model: **$z$ is the main-engine / thrust axis**, and
$x,y$ are lateral. That is why the $a_z$ column is almost always the largest —
it is the main engine, and the lateral columns are what the RCS alone can do.


## Boosters

| Vehicle | Mass [kg] | $a_x$ | $a_y$ | $a_z$ | $\alpha_x$ | $\alpha_y$ | $\alpha_z$ |
|:------------------------------|:----------|:--------|:--------|:--------|:--------|:--------|:--------|
| Vega-C | 210,000 | 2.51 | 2.51 | 22.14 | 24.4 | 24.4 | 0 |
| Vega | 137,000 | 2.43 | 2.43 | 21.47 | 27.6 | 27.6 | 0 |
| Delta IV Heavy | 725,700 | 1.35 | 1.35 | 12.91 | 6.6 | 6.6 | 34.0 |
| Ariane 5 ECA | 780,000 | 0.13 | 0.13 | 1.23 | 0.877 | 0.877 | 0 |


## Crewed Vehicles

| Vehicle | Mass [kg] | $a_x$ | $a_y$ | $a_z$ | $\alpha_x$ | $\alpha_y$ | $\alpha_z$ |
|:------------------------------|:----------|:--------|:--------|:--------|:--------|:--------|:--------|
| Crew Dragon (Dragon 2) | 12,519 | 0.13 | 0.13 | 42.82 | 127.6 | 127.6 | 14.4 |
| Apollo Lunar Module | 15,103 | 0.41 | 0.41 | 3.21 | 153.1 | 153.1 | 34.4 |
| Apollo Command & Service Module | 30,320 | 0.28 | 0.28 | 3.07 | 7.2 | 7.2 | 3.4 |
| Orion (CM + European Service Module) | 26,536 | 0.14 | 0.14 | 1.06 | 4.1 | 4.1 | 2.2 |


## GEO Satellites

| Vehicle | Mass [kg] | $a_x$ | $a_y$ | $a_z$ | $\alpha_x$ | $\alpha_y$ | $\alpha_z$ |
|:------------------------------|:----------|:--------|:--------|:--------|:--------|:--------|:--------|
| Meteosat Second Generation (MSG) | 2,000 | 0.0119 | 0.0107 | 0.41 | 0.640 | 9.7 | 1.2 |
| Solar Dynamics Observatory (SDO) | 3,100 | 0.0212 | 0.0154 | 0.18 | 0.463 | 0.463 | 2.2 |
| GOES-16 (GOES-R) * | 5,192 | — | — | — | — | — | — |
| GOES-19 (GOES-U) * | 5,000 | — | — | — | — | — | — |


## LEO Satellites

| Vehicle | Mass [kg] | $a_x$ | $a_y$ | $a_z$ | $\alpha_x$ | $\alpha_y$ | $\alpha_z$ |
|:------------------------------|:----------|:--------|:--------|:--------|:--------|:--------|:--------|
| SMAP | 944 | 0.0141 | 0.0102 | 0.0133 | 0.960 | 0.960 | 2.1 |
| Sentinel-3A | 1,250 | 0.0024 | 0.0017 | 0.0022 | 0.237 | 0.115 | 0.210 |
| GRACE-FO (per satellite) | 600 | 3.3e-05 | 3.3e-05 | 1.7e-04 | 2.9e-03 | 5.6e-03 | 1.7e-03 |
| Sentinel-1A * | 2,300 | — | — | — | — | — | — |


## Deep Space Probes

| Vehicle | Mass [kg] | $a_x$ | $a_y$ | $a_z$ | $\alpha_x$ | $\alpha_y$ | $\alpha_z$ |
|:------------------------------|:----------|:--------|:--------|:--------|:--------|:--------|:--------|
| Juno * | 3,625 | 0 | 0 | 0.18 | — | — | — |
| Cassini (Cassini-Huygens) | 5,574 | 0.0063 | 0.0063 | 0.16 | 0.240 | 1.2 | 0.256 |
| New Horizons | 478 | 0.0033 | 0.0033 | 0.0402 | 1.0 | 1.0 | 0.219 |
| Europa Clipper | 5,800 | 0 | 0 | 0.0379 | 0.539 | 0.520 | 0 |
| Voyager 1 | 815 | 0.0041 | 0.0041 | 0.0058 | 0.949 | 0.949 | 1.0 |


\newpage

# Typical values by class

Median across the vehicles of each class with usable data, with the full range
in brackets. The sample per class is small — this is a fleet survey, not a
population — so the **range** is the honest statistic and the median is an
indicative middle, not an expectation.


| Class | n lin/ang | Axial $a_z$ [m/s²] | Lateral $a_{x,y}$ [m/s²] | Pitch/yaw $\alpha_{x,y}$ [°/s²] | Roll $\alpha_z$ [°/s²] |
|:----------------------|:---------|:----------------------|:------------------------|:------------------------|:----------------------|
| Boosters | 4/4 | 17.19  [1.23–22.14] | 1.89  [0.13–2.51] | 15.5  [0.877–27.6] | 0  [0–34.0] |
| Crewed Vehicles | 4/4 | 3.14  [1.06–42.82] | 0.21  [0.13–0.41] | 67.4  [4.1–153.1] | 8.9  [2.2–34.4] |
| GEO Satellites | 2/2 | 0.29  [0.18–0.41] | 0.0165  [0.0119–0.0212] | 5.1  [0.463–9.7] | 1.7  [1.2–2.2] |
| LEO Satellites | 3/3 | 0.0022  [1.7e-04–0.0133] | 0.0024  [3.3e-05–0.0141] | 0.237  [5.6e-03–0.960] | 0.210  [1.7e-03–2.1] |
| Deep Space Probes | 5/4 | 0.0402  [0.0058–0.18] | 0.0033  [0–0.0063] | 0.979  [0.539–1.2] | 0.238  [0–1.0] |


![Acceleration by spacecraft class](/home/omersayilgan/Desktop/ThesisGit/studies/actuation_envelopes/figures/_acceleration_by_category.png)


\newpage

# What the classes actually look like

**Axial acceleration separates the classes by four orders of magnitude, and it
is really a statement about mission phase.** Boosters sit around
17.19 m/s² because they must lift themselves against Earth
gravity — anything below ~10 m/s² does not leave the pad. Crewed vehicles come
next at about 3.14 m/s², sized for abort and orbital
manoeuvring. GEO satellites (0.29 m/s²) and deep-space probes
(0.0402 m/s²) carry an apogee or main engine sized for
orbit insertion. LEO satellites are lowest of all
(0.0022 m/s²) because most carry no main engine at all: their
axial figure *is* their RCS.

**Lateral acceleration is about an order of magnitude below axial — and the
exceptions say why.** For every vehicle in the fleet that has a main engine,
the axial-to-lateral ratio clusters tightly around **10:1**
(interquartile range 8–12:1 over 13 vehicles). The
reason is pure layout: the main engine points along one axis and everything
sideways has to come from small RCS thrusters.

The vehicles that break the pattern break it in the direction that confirms it.
Sentinel-3A, SMAP, Voyager 1 carry **no main engine at all**, and their
ratios are 0.9:1, 0.9:1, 1.4:1 — near unity, because
every axis including the nominal thrust axis is served by the same RCS. At the
other extreme Crew Dragon reaches 340:1, its eight SuperDracos
sized for launch abort against a Draco RCS sized for docking.

The practical consequence is the same either way: on any vehicle with a main
engine, a guidance scheme that wants lateral authority is really asking the
vehicle to tilt and use the main engine. That is a rotational manoeuvre with
the associated delay, not a translation — which is exactly why the Apollo
landing studies in this repository spend their control authority on attitude.

**Angular acceleration does not track size or thrust; it tracks what the
vehicle was built to do.** The two largest figures in the fleet belong to the
Apollo LM and Crew Dragon at 153 and 128 °/s² —
compact vehicles carrying RCS sized for landing and for docking. Boosters,
with thrust in the meganewtons, manage
0.9–30 °/s²: their inertia is enormous and their
only moment source is a few degrees of gimbal deflection on an engine close to
the roll axis. Deep-space probes sit near
1.0 °/s².

The rule that falls out: **a vehicle designed to manoeuvre precisely near
something else has of order 100 °/s²; a vehicle designed to fly a trajectory
has of order 1–30 °/s²**. Proximity operations are an angular-authority
problem, and the fleet is sized accordingly.

**Roll is the axis that gets sacrificed.** Three of the four boosters have
exactly zero roll authority from their modelled actuators, and Europa Clipper
has none either. Roll is the axis a single centreline engine cannot touch, and
in the fleet it is consistently the weakest or missing channel. Where a vehicle
does have roll authority it usually comes from an offset engine cluster
(Delta IV Heavy's three boosters) or from a dedicated RCS ring.

## The rule-of-thumb table

Rounded to the nearest order of magnitude, which is the precision these
shape-model inertias actually support:


| Class | Axial $a_z$ | Lateral $a_{x,y}$ | Pitch/yaw $\alpha_{x,y}$ | Roll $\alpha_z$ |
|:----------------------|:----------------|:------------------|:------------------|:------------------------|
| Boosters | 1–20 m/s² | 0.1–3 m/s² | 0.9–30 °/s² | 30 °/s² — but 3 of 4 have none at all |
| Crewed Vehicles | 1–40 m/s² | 0.1–0.4 m/s² | 4–200 °/s² | 2–30 °/s² |
| GEO Satellites | 0.2–0.4 m/s² | 0.01–0.02 m/s² | 0.5–10 °/s² | 1–2 °/s² |
| LEO Satellites | 0.0002–0.01 m/s² | 0.00003–0.01 m/s² | 0.006–1.0 °/s² | 0.002–2 °/s² |
| Deep Space Probes | 0.006–0.2 m/s² | 0.003–0.006 m/s² | 0.5–1 °/s² | 0.2–1 °/s² — but 1 of 4 have none at all |


\newpage

# Appendix A — signed per-axis detail

The tables above take the larger of the two directions along each axis. Layouts
are frequently asymmetric, and where they are, the *smaller* direction is the
one that constrains a controller. Linear in m/s², angular in °/s².


## Boosters

| Vehicle | $+a_x$ | $-a_x$ | $+a_y$ | $-a_y$ | $+a_z$ | $-a_z$ | $+\alpha_x$ | $-\alpha_x$ | $+\alpha_y$ | $-\alpha_y$ | $+\alpha_z$ | $-\alpha_z$ |
|:--------------------------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|
| Vega-C | 2.51 | 2.51 | 2.51 | 2.51 | 0 | 22.14 | 24.4 | 24.4 | 24.4 | 24.4 | 0 | 0 |
| Vega | 2.43 | 2.43 | 2.43 | 2.43 | 0 | 21.47 | 27.6 | 27.6 | 27.6 | 27.6 | 0 | 0 |
| Delta IV Heavy | 1.35 | 1.35 | 1.35 | 1.35 | 0 | 12.91 | 6.6 | 6.6 | 6.6 | 6.6 | 34.0 | 34.0 |
| Ariane 5 ECA | 0.13 | 0.13 | 0.13 | 0.13 | 0 | 1.23 | 0.877 | 0.877 | 0.877 | 0.877 | 0 | 0 |


## Crewed Vehicles

| Vehicle | $+a_x$ | $-a_x$ | $+a_y$ | $-a_y$ | $+a_z$ | $-a_z$ | $+\alpha_x$ | $-\alpha_x$ | $+\alpha_y$ | $-\alpha_y$ | $+\alpha_z$ | $-\alpha_z$ |
|:--------------------------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|
| Crew Dragon (Dragon 2) | 0.13 | 0.13 | 0.13 | 0.13 | 0.18 | 42.82 | 127.6 | 127.6 | 127.6 | 127.6 | 14.4 | 6.0 |
| Apollo Lunar Module | 0.41 | 0.41 | 0.41 | 0.41 | 0.12 | 3.21 | 153.1 | 153.1 | 153.1 | 153.1 | 34.4 | 34.4 |
| Apollo Command & Service Module | 0.28 | 0.28 | 0.28 | 0.28 | 0.0587 | 3.07 | 7.2 | 7.2 | 7.2 | 7.2 | 3.4 | 3.4 |
| Orion (CM + European Service Module) | 0.14 | 0.14 | 0.14 | 0.14 | 0.0488 | 1.06 | 4.1 | 4.1 | 4.1 | 4.1 | 2.2 | 2.2 |


## GEO Satellites

| Vehicle | $+a_x$ | $-a_x$ | $+a_y$ | $-a_y$ | $+a_z$ | $-a_z$ | $+\alpha_x$ | $-\alpha_x$ | $+\alpha_y$ | $-\alpha_y$ | $+\alpha_z$ | $-\alpha_z$ |
|:--------------------------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|
| Meteosat Second Generation (MSG) | 0.0029 | 0.0119 | 0.0041 | 0.0107 | 0.0098 | 0.41 | 0.569 | 0.640 | 9.7 | 9.5 | 1.2 | 0.293 |
| Solar Dynamics Observatory (SDO) | 0.0071 | 0.0212 | 0.0129 | 0.0154 | 0.0200 | 0.18 | 0.388 | 0.463 | 0.388 | 0.463 | 2.2 | 0.918 |


## LEO Satellites

| Vehicle | $+a_x$ | $-a_x$ | $+a_y$ | $-a_y$ | $+a_z$ | $-a_z$ | $+\alpha_x$ | $-\alpha_x$ | $+\alpha_y$ | $-\alpha_y$ | $+\alpha_z$ | $-\alpha_z$ |
|:--------------------------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|
| SMAP | 0.0047 | 0.0141 | 0.0086 | 0.0102 | 0.0133 | 0.0133 | 0.804 | 0.960 | 0.804 | 0.960 | 2.1 | 0.895 |
| Sentinel-3A | 7.9e-04 | 0.0024 | 0.0014 | 0.0017 | 0.0022 | 0.0022 | 0.199 | 0.237 | 0.096 | 0.115 | 0.210 | 0.088 |
| GRACE-FO (per satellite) | 3.3e-05 | 3.3e-05 | 3.3e-05 | 3.3e-05 | 3.3e-05 | 1.7e-04 | 2.9e-03 | 2.9e-03 | 5.6e-03 | 5.6e-03 | 1.7e-03 | 1.7e-03 |


## Deep Space Probes

| Vehicle | $+a_x$ | $-a_x$ | $+a_y$ | $-a_y$ | $+a_z$ | $-a_z$ | $+\alpha_x$ | $-\alpha_x$ | $+\alpha_y$ | $-\alpha_y$ | $+\alpha_z$ | $-\alpha_z$ |
|:--------------------------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|:------|
| Juno | 0 | 0 | 0 | 0 | 0 | 0.18 | — | — | — | — | — | — |
| Cassini (Cassini-Huygens) | 0.0063 | 0.0063 | 0.0063 | 0.0063 | 1.0e-03 | 0.16 | 0.240 | 0.240 | 1.2 | 1.2 | 0.256 | 0.209 |
| New Horizons | 0.0033 | 0.0033 | 0.0033 | 0.0033 | 0.0033 | 0.0402 | 1.0 | 1.0 | 1.0 | 1.0 | 0.219 | 0.219 |
| Europa Clipper | 0 | 0 | 0 | 0 | 0 | 0.0379 | 0.539 | 0.539 | 0.520 | 0.520 | 0 | 0 |
| Voyager 1 | 0.0041 | 0.0041 | 0.0041 | 0.0041 | 0.0058 | 0.0058 | 0.949 | 0.949 | 0.949 | 0.949 | 1.0 | 0.435 |


\newpage

# Limitations

* **Upper bound, not an operating value.** Every actuator fires at once, at
  full thrust, in the optimal direction. Real control allocation, duty cycles,
  propellant budgets and thermal limits all reduce these figures.
* **Inertia is a shape model.** Every vehicle is treated as a uniform cylinder
  or box at its published envelope dimensions. This is the largest single
  uncertainty in the angular columns and it is a *systematic* one: real
  spacecraft concentrate mass at the base, so true $I_{xx}, I_{yy}$ are
  generally smaller than modelled and true angular accelerations correspondingly
  larger.
* **Actuator geometry is largely assumed.** Thrust magnitudes and counts come
  from the workbook; where thrusters sit and which way they point is a layout
  model (rings, face pairs, canted clusters), chosen per vehicle and recorded
  in the provenance sheet of `actuation_envelope_summary.xlsx`.
* **Small samples.** Two to five vehicles per class. The ranges are a survey of
  these particular spacecraft, not a distribution over the class.
* **Mass is a single reference value** — usually launch or wet mass. A vehicle
  near end of life with empty tanks accelerates considerably harder than these
  numbers suggest.
* **No gyroscopic coupling.** $\alpha_j = M_j / I_{jj}$ holds at low rates.
  For a spinning vehicle (Juno, or any spin-stabilised probe) the achievable
  angular acceleration about the transverse axes is materially different.

# Reproducing

```bash
python studies/actuation_envelopes/build_acceleration_tables.py
```

Outputs `acceleration_reference.pdf`, `acceleration_reference.csv` and
`figures/_acceleration_by_category.png` in this directory. The underlying
envelope model, its per-value provenance flags and the three-panel per-vehicle
figures are produced by `build_report.py` alongside it.
