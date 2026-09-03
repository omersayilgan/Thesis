---
title: "Study G — Appendix A: Initial Conditions and Vehicle Geometry"
subtitle: "Every state flown, and the engine layout it was flown with"
date: "17 August 2026"
geometry: margin=2.0cm
fontsize: 9pt
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

# Which initial conditions belong to which fault

**All of them, and they are the same ones.** The campaign is a *paired* design:
one set of initial conditions is drawn per regime and then reused, unchanged,
for every one of the sixteen plant configurations. That is deliberate and it is
what makes the study's comparisons work — because the state distribution is
literally identical across faults, any difference in landing rate is
attributable to the plant alone, and the healthy-vs-fault comparison becomes a
within-sample McNemar test on discordant pairs rather than a contrast between
two independently drawn samples.

So there is no per-fault initial-condition list to give. There is one list, of
5 x 10 = 50 states, reproduced in full in
section 4; section 5 then shows what each fault did from each of them.


# The vehicle and where its engines are

The lander carries **two independently gimballed TVC engines**, each rated at
half the nominal DPS thrust, mounted symmetrically either side of the
centreline in a plane below the centre of gravity. Body axes are x forward,
y right, z **down**, so a positive `z` engine station is *below* the CG.

| Engine | Body station (x, y, z) [m] | Thrust [N] | Hover share [N] | Gimbal [°] | Role |
|:------------------|:------------------------|:--------------|:--------------|:----------|:----------------------|
| Engine 1 (index 0) | (+0.00, -1.50, +2.50) | 2280 – 22520 | 6265 | ±6.0 | healthy in every case |
| Engine 2 (index 1) | (+0.00, +1.50, +2.50) | 2280 – 22520 | 6265 | ±6.0 | **carries the fault** |


Every fault in the catalogue acts on **engine 2** (index 1, body station
y = +1.50 m). Engine 1 stays healthy throughout, so each
case is an *asymmetry* the vehicle has to trim as well as a loss of
performance. The vehicle is laterally symmetric, so which engine is chosen does
not matter — only that it is one of two.

The lateral half-spacing $y_{eng}$ = 1.50 m is the parameter behind
the engine-out result: a single gimbal can trim a one-engine-out roll asymmetry
only while $y_{eng} \le d z_{eng} \tan\delta_{max}$ =
0.263 m, and this vehicle is built at
1.50 m — a factor of 5.7
outside it.


| Vehicle parameter | Value |
|:----------------------------------|:----------------------------------------------|
| Mass | 7711 kg |
| Inertia $I_{xx}, I_{yy}, I_{zz}$ | 5368, 5368, 5040 kg·m² |
| Lunar gravity | 1.625 m/s² |
| Hover thrust (total) | 12530 N |
| DPS envelope (total) | 4560 – 45040 N |
| Engine plane below CG, $dz_{eng}$ | 2.50 m |
| Engine half-spacing, $y_{eng}$ | 1.50 m |
| Thrust lag $\tau_T$ / gimbal $\omega_n$, $\zeta$ | 0.40 s / 4.0 rad/s, 0.70 |
| RCS | 4 quads x 4 thrusters, 445 N each, arm 1.70 m |
| Glide-slope cone | 30° from horizontal |
| Contact altitude (engine cut) | 1.0 m |


# The sampling box of each regime

Initial conditions are scrambled Sobol points in these boxes, rejected if they
fall outside the approach cone or are already past the hard loss-of-control
criteria. `upset` additionally keeps only draws that are genuinely upset (a body
rate of at least 10 °/s on some axis, or at least 15° of tilt).


## `approach` — On approach

high, descending, small dispersions — the vehicle is where a healthy descent would have put it, and the fault is the only thing wrong.


| State | Unit | lower | upper |
|:------------|:--------|:------------|:------------|
| x_E | m | -350 | +350 |
| y_E | m | -350 | +350 |
| alt | m | +800 | +1300 |
| u | m/s | -20 | +0 |
| v | m/s | -5 | +5 |
| w | m/s | +0 | +25 |
| phi | deg | -8 | +8 |
| theta | deg | -8 | +8 |
| psi | deg | -15 | +15 |
| p | deg/s | -3 | +3 |
| q | deg/s | -3 | +3 |
| r | deg/s | -3 | +3 |
| T1 | N | +5325 | +7205 |
| dp1 | deg | -1.5 | +1.5 |
| dy1 | deg | -1.5 | +1.5 |
| dp1_dot | deg/s | -3 | +3 |
| dy1_dot | deg/s | -3 | +3 |
| T2 | N | +5325 | +7205 |
| dp2 | deg | -1.5 | +1.5 |
| dy2 | deg | -1.5 | +1.5 |
| dp2_dot | deg/s | -3 | +3 |
| dy2_dot | deg/s | -3 | +3 |


## `dispersed` — Dispersed

Study F's wide box: position, velocity, attitude, rates and both sets of actuator states drawn over their full admissible ranges.


| State | Unit | lower | upper |
|:------------|:--------|:------------|:------------|
| x_E | m | -900 | +900 |
| y_E | m | -900 | +900 |
| alt | m | +300 | +1400 |
| u | m/s | -25 | +10 |
| v | m/s | -12 | +12 |
| w | m/s | -5 | +28 |
| phi | deg | -25 | +25 |
| theta | deg | -25 | +25 |
| psi | deg | -40 | +40 |
| p | deg/s | -25 | +25 |
| q | deg/s | -25 | +25 |
| r | deg/s | -25 | +25 |
| T1 | N | +2280 | +2.252e+04 |
| dp1 | deg | -6 | +6 |
| dy1 | deg | -6 | +6 |
| dp1_dot | deg/s | -14.4 | +14.4 |
| dy1_dot | deg/s | -14.4 | +14.4 |
| T2 | N | +2280 | +2.252e+04 |
| dp2 | deg | -6 | +6 |
| dy2 | deg | -6 | +6 |
| dp2_dot | deg/s | -14.4 | +14.4 |
| dy2_dot | deg/s | -14.4 | +14.4 |


## `upset` — Upset

the corner of the box where the vehicle is already rotating or tilted (>= 10 deg/s on some axis, or >= 15 deg of tilt) with the gimbals deflected — the states a fault transient actually produces.


| State | Unit | lower | upper |
|:------------|:--------|:------------|:------------|
| x_E | m | -600 | +600 |
| y_E | m | -600 | +600 |
| alt | m | +500 | +1100 |
| u | m/s | -30 | +15 |
| v | m/s | -15 | +15 |
| w | m/s | +0 | +30 |
| phi | deg | -40 | +40 |
| theta | deg | -40 | +40 |
| psi | deg | -60 | +60 |
| p | deg/s | -30 | +30 |
| q | deg/s | -30 | +30 |
| r | deg/s | -30 | +30 |
| T1 | N | +2280 | +2.252e+04 |
| dp1 | deg | -6 | +6 |
| dy1 | deg | -6 | +6 |
| dp1_dot | deg/s | -14.4 | +14.4 |
| dy1_dot | deg/s | -14.4 | +14.4 |
| T2 | N | +2280 | +2.252e+04 |
| dp2 | deg | -6 | +6 |
| dy2 | deg | -6 | +6 |
| dp2_dot | deg/s | -14.4 | +14.4 |
| dy2_dot | deg/s | -14.4 | +14.4 |


## `low_late` — Low and late

between 60 m and 200 m and still descending: the fault arrives when there is very little altitude left to trade for time.


| State | Unit | lower | upper |
|:------------|:--------|:------------|:------------|
| x_E | m | -200 | +200 |
| y_E | m | -200 | +200 |
| alt | m | +60 | +200 |
| u | m/s | -25 | +10 |
| v | m/s | -14 | +14 |
| w | m/s | +5 | +32 |
| phi | deg | -28 | +28 |
| theta | deg | -28 | +28 |
| psi | deg | -40 | +40 |
| p | deg/s | -16 | +16 |
| q | deg/s | -16 | +16 |
| r | deg/s | -16 | +16 |
| T1 | N | +3759 | +9398 |
| dp1 | deg | -4 | +4 |
| dy1 | deg | -4 | +4 |
| dp1_dot | deg/s | -8 | +8 |
| dy1_dot | deg/s | -8 | +8 |
| T2 | N | +3759 | +9398 |
| dp2 | deg | -4 | +4 |
| dy2 | deg | -4 | +4 |
| dp2_dot | deg/s | -8 | +8 |
| dy2_dot | deg/s | -8 | +8 |


## `critical` — Critical

below 140 m, descending hard, tilted and rotating — the regime where even the healthy vehicle frequently has no trajectory left, so the fault has to be paid for out of a margin that is already spent.


| State | Unit | lower | upper |
|:------------|:--------|:------------|:------------|
| x_E | m | -140 | +140 |
| y_E | m | -140 | +140 |
| alt | m | +50 | +140 |
| u | m/s | -30 | +15 |
| v | m/s | -18 | +18 |
| w | m/s | +8 | +34 |
| phi | deg | -35 | +35 |
| theta | deg | -35 | +35 |
| psi | deg | -50 | +50 |
| p | deg/s | -22 | +22 |
| q | deg/s | -22 | +22 |
| r | deg/s | -22 | +22 |
| T1 | N | +3133 | +1.002e+04 |
| dp1 | deg | -6 | +6 |
| dy1 | deg | -6 | +6 |
| dp1_dot | deg/s | -12 | +12 |
| dy1_dot | deg/s | -12 | +12 |
| T2 | N | +3133 | +1.002e+04 |
| dp2 | deg | -6 | +6 |
| dy2 | deg | -6 | +6 |
| dp2_dot | deg/s | -12 | +12 |
| dy2_dot | deg/s | -12 | +12 |


# The initial conditions

Positions are in the landing-pad frame (x north, y east) with **altitude
positive up**; velocities are body-frame; angles are degrees. `T1`/`T2` are the
two engines' thrust states and `dp`/`dy` their pitch and yaw gimbal deflections,
with `_dot` the corresponding gimbal rates. Sampling the actuator states
directly is the point of the 22-dimensional box: a fault leaves the gimbals
deflected and the thrust away from trim, and those are states no 12-dimensional
sampling can reach.


## `approach` — On approach  (10 states)


### Rigid-body states


| # | x_E [m] | y_E [m] | alt [m] | u [m/s] | v [m/s] | w [m/s] | phi [deg] | theta [deg] | psi [deg] | p [deg/s] | q [deg/s] | r [deg/s] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | -107 | 58 | 1108 | -8.15 | 2.86 | 12.86 | 0.58 | -0.42 | -10.46 | 0.71 | -2.11 | -0.31 |
| 1 | 333 | -47 | 862 | -13.72 | -2.73 | 3.67 | -0.64 | 7.11 | 2.99 | -0.95 | 1.12 | 1.85 |
| 2 | 108 | 196 | 1249 | -2.58 | -1.43 | 9.21 | 6.56 | 2.18 | 8.35 | -2.10 | 1.88 | 0.97 |
| 3 | -331 | -186 | 1003 | -18.06 | 1.58 | 24.26 | -6.74 | -5.37 | -0.93 | 2.61 | -0.89 | -2.50 |
| 4 | -261 | 336 | 869 | -16.07 | 0.59 | 15.74 | 5.70 | 0.06 | 12.31 | -0.68 | 2.81 | -2.23 |
| 5 | 3 | -346 | 1115 | -0.82 | -0.16 | 0.69 | -5.51 | -7.50 | -4.89 | 0.99 | -0.32 | 0.67 |
| 6 | 260 | 110 | 978 | -10.40 | -3.85 | 12.19 | 3.66 | -2.29 | -14.00 | 2.14 | -2.67 | 2.89 |
| 7 | -5 | -121 | 1224 | -5.22 | 4.31 | 21.38 | -3.60 | 5.22 | 6.53 | -2.58 | 0.18 | -1.33 |
| 8 | -70 | 239 | 927 | -1.51 | -3.35 | 21.92 | 4.16 | 1.75 | 13.13 | 2.98 | 0.52 | -0.51 |
| 9 | 195 | -227 | 1180 | -16.61 | 3.48 | 6.86 | -4.10 | -6.69 | -5.72 | -1.73 | -2.34 | 2.02 |


### Actuator states


| # | T1 [N] | dp1 [deg] | dy1 [deg] | dp1_dot [deg/s] | dy1_dot [deg/s] | T2 [N] | dp2 [deg] | dy2 [deg] | dp2_dot [deg/s] | dy2_dot [deg/s] |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 7126 | 0.94 | -1.48 | 0.00 | 2.16 | 6964 | 1.31 | 1.02 | -0.89 | -0.96 |
| 1 | 6214 | -0.24 | 0.72 | -0.23 | -2.62 | 5554 | -0.44 | -0.67 | 1.00 | 1.99 |
| 2 | 6551 | 0.56 | 1.26 | 2.58 | -1.00 | 6303 | -1.30 | 0.00 | -2.39 | 0.44 |
| 3 | 5639 | -1.26 | -0.48 | -2.44 | 0.59 | 5833 | 0.43 | -1.31 | 2.50 | -2.61 |
| 4 | 6414 | -0.72 | -0.11 | -2.17 | 1.02 | 6048 | -0.94 | 1.21 | -0.29 | -0.30 |
| 5 | 5505 | 1.42 | 0.88 | 2.03 | -0.58 | 6518 | 0.31 | -0.11 | 0.08 | 2.65 |
| 6 | 6791 | -0.78 | 0.35 | -1.16 | -2.19 | 5740 | 0.95 | 0.56 | -1.79 | 1.29 |
| 7 | 5882 | 0.08 | -1.10 | 1.39 | 2.58 | 7150 | -0.32 | -1.12 | 1.58 | -1.75 |
| 8 | 5414 | -0.96 | 1.35 | -1.77 | -1.20 | 5916 | -0.84 | 0.23 | -0.66 | 2.25 |
| 9 | 6267 | 0.26 | -0.57 | 1.53 | 0.02 | 6386 | 0.16 | -1.46 | 0.45 | -0.70 |


## `dispersed` — Dispersed  (10 states)


### Rigid-body states


| # | x_E [m] | y_E [m] | alt [m] | u [m/s] | v [m/s] | w [m/s] | phi [deg] | theta [deg] | psi [deg] | p [deg/s] | q [deg/s] | r [deg/s] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | -275 | 150 | 978 | -4.26 | 6.86 | 11.98 | 1.83 | -1.31 | -27.90 | 5.91 | -17.59 | -2.62 |
| 1 | 278 | 503 | 1287 | 5.49 | -3.44 | 7.16 | 20.50 | 6.81 | 22.26 | -17.53 | 15.63 | 8.04 |
| 2 | -852 | -478 | 746 | -21.61 | 3.79 | 27.02 | -21.07 | -16.77 | -2.49 | 21.77 | -7.38 | -20.81 |
| 3 | 8 | -890 | 993 | 8.57 | -0.37 | -4.09 | -17.22 | -23.43 | -13.05 | 8.22 | -2.69 | 5.59 |
| 4 | 668 | 282 | 692 | -8.20 | -9.24 | 11.09 | 11.45 | -7.15 | -37.33 | 17.81 | -22.28 | 24.10 |
| 5 | -12 | -311 | 1234 | 0.86 | 10.34 | 23.23 | -11.23 | 16.33 | 17.42 | -21.47 | 1.53 | -11.09 |
| 6 | -181 | 615 | 579 | 7.36 | -8.04 | 23.93 | 13.00 | 5.47 | 35.01 | 24.81 | 4.33 | -4.28 |
| 7 | 502 | -584 | 1136 | -19.06 | 8.35 | 4.06 | -12.80 | -20.90 | -15.25 | -14.41 | -19.51 | 16.86 |
| 8 | 178 | 40 | 543 | -2.57 | 5.29 | 2.94 | 6.87 | -11.02 | -34.52 | -11.12 | -5.52 | 9.71 |
| 9 | -506 | -13 | 1103 | -11.35 | -4.94 | 15.07 | -6.28 | 15.51 | 14.60 | 2.78 | 20.70 | -22.28 |


### Actuator states


| # | T1 [N] | dp1 [deg] | dy1 [deg] | dp1_dot [deg/s] | dy1_dot [deg/s] | T2 [N] | dp2 [deg] | dy2 [deg] | dp2_dot [deg/s] | dy2_dot [deg/s] |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 21666 | 3.77 | -5.91 | 0.01 | 10.38 | 19921 | 5.23 | 4.09 | -4.25 | -4.63 |
| 1 | 15475 | 2.25 | 5.04 | 12.37 | -4.80 | 12805 | -5.18 | 0.01 | -11.46 | 2.13 |
| 2 | 5661 | -5.06 | -1.91 | -11.69 | 2.82 | 7746 | 1.72 | -5.25 | 12.01 | -12.51 |
| 3 | 4210 | 5.68 | 3.53 | 9.73 | -2.80 | 15125 | 1.22 | -0.42 | 0.37 | 12.72 |
| 4 | 18061 | -3.13 | 1.38 | -5.56 | -10.52 | 6745 | 3.80 | 2.26 | -8.59 | 6.19 |
| 5 | 8268 | 0.31 | -4.42 | 6.69 | 12.40 | 21925 | -1.27 | -4.50 | 7.57 | -8.42 |
| 6 | 3234 | -3.84 | 5.39 | -8.49 | -5.75 | 8641 | -3.37 | 0.90 | -3.17 | 10.82 |
| 7 | 12417 | 1.02 | -2.28 | 7.36 | 0.07 | 13700 | 0.65 | -5.86 | 2.16 | -3.37 |
| 8 | 9853 | -2.17 | -4.80 | -4.34 | 7.87 | 3106 | 3.32 | 3.20 | -10.38 | -10.34 |
| 9 | 19031 | 4.98 | 1.77 | 5.01 | -13.31 | 18285 | -0.60 | -2.06 | 9.35 | 4.30 |


## `upset` — Upset  (10 states)


### Rigid-body states


| # | x_E [m] | y_E [m] | alt [m] | u [m/s] | v [m/s] | w [m/s] | phi [deg] | theta [deg] | psi [deg] | p [deg/s] | q [deg/s] | r [deg/s] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | -183 | 100 | 870 | -3.34 | 8.57 | 15.43 | 2.92 | -2.09 | -41.85 | 7.09 | -21.11 | -3.15 |
| 1 | 571 | -81 | 574 | -15.87 | -8.18 | 4.41 | -3.21 | 35.53 | 11.97 | -9.50 | 11.21 | 18.48 |
| 2 | 185 | 336 | 1038 | 9.20 | -4.30 | 11.05 | 32.80 | 10.90 | 33.38 | -21.03 | 18.76 | 9.65 |
| 3 | -568 | -319 | 743 | -25.64 | 4.73 | 29.11 | -33.71 | -26.83 | -3.73 | 26.12 | -8.86 | -24.97 |
| 4 | -448 | 576 | 583 | -21.16 | 1.78 | 18.89 | 28.51 | 0.30 | 49.24 | -6.76 | 28.14 | -22.32 |
| 5 | 6 | -593 | 878 | 13.16 | -0.47 | 0.82 | -27.55 | -37.49 | -19.57 | 9.87 | -3.23 | 6.70 |
| 6 | 445 | 188 | 714 | -8.40 | -11.55 | 14.63 | 18.32 | -11.44 | -55.99 | 21.37 | -26.74 | 28.92 |
| 7 | -8 | -208 | 1009 | 3.25 | 12.93 | 25.66 | -17.98 | 26.12 | 26.13 | -25.76 | 1.83 | -13.31 |
| 8 | -121 | 410 | 652 | 11.61 | -10.05 | 26.30 | 20.80 | 8.75 | 52.51 | 29.78 | 5.19 | -5.14 |
| 9 | 335 | -389 | 956 | -22.36 | 10.44 | 8.24 | -20.48 | -33.44 | -22.87 | -17.29 | -23.41 | 20.23 |


### Actuator states


| # | T1 [N] | dp1 [deg] | dy1 [deg] | dp1_dot [deg/s] | dy1_dot [deg/s] | T2 [N] | dp2 [deg] | dy2 [deg] | dp2_dot [deg/s] | dy2_dot [deg/s] |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 21666 | 3.77 | -5.91 | 0.01 | 10.38 | 19921 | 5.23 | 4.09 | -4.25 | -4.63 |
| 1 | 11853 | -0.96 | 2.89 | -1.13 | -12.60 | 4742 | -1.76 | -2.67 | 4.81 | 9.56 |
| 2 | 15475 | 2.25 | 5.04 | 12.37 | -4.80 | 12805 | -5.18 | 0.01 | -11.46 | 2.13 |
| 3 | 5661 | -5.06 | -1.91 | -11.69 | 2.82 | 7746 | 1.72 | -5.25 | 12.01 | -12.51 |
| 4 | 14005 | -2.87 | -0.42 | -10.42 | 4.88 | 10066 | -3.76 | 4.84 | -1.39 | -1.44 |
| 5 | 4210 | 5.68 | 3.53 | 9.73 | -2.80 | 15125 | 1.22 | -0.42 | 0.37 | 12.72 |
| 6 | 18061 | -3.13 | 1.38 | -5.56 | -10.52 | 6745 | 3.80 | 2.26 | -8.59 | 6.19 |
| 7 | 8268 | 0.31 | -4.42 | 6.69 | 12.40 | 21925 | -1.27 | -4.50 | 7.57 | -8.42 |
| 8 | 3234 | -3.84 | 5.39 | -8.49 | -5.75 | 8641 | -3.37 | 0.90 | -3.17 | 10.82 |
| 9 | 12417 | 1.02 | -2.28 | 7.36 | 0.07 | 13700 | 0.65 | -5.86 | 2.16 | -3.37 |


## `low_late` — Low and late  (10 states)


### Rigid-body states


| # | x_E [m] | y_E [m] | alt [m] | u [m/s] | v [m/s] | w [m/s] | phi [deg] | theta [deg] | psi [deg] | p [deg/s] | q [deg/s] | r [deg/s] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | -61 | 33 | 146 | -4.26 | 8.00 | 18.89 | 2.05 | -1.46 | -27.90 | 3.78 | -11.26 | -1.68 |
| 1 | 62 | 112 | 186 | 5.49 | -4.01 | 14.95 | 22.96 | 7.63 | 22.26 | -11.22 | 10.01 | 5.15 |
| 2 | 2 | -198 | 148 | 8.57 | -0.44 | 5.74 | -19.28 | -26.24 | -13.05 | 5.26 | -1.72 | 3.58 |
| 3 | 148 | 63 | 110 | -8.20 | -10.78 | 18.17 | 12.82 | -8.01 | -37.33 | 11.40 | -14.26 | 15.42 |
| 4 | -3 | -69 | 179 | 0.86 | 12.07 | 28.10 | -12.58 | 18.29 | 17.42 | -13.74 | 0.98 | -7.10 |
| 5 | -40 | 137 | 96 | 7.36 | -9.38 | 28.67 | 14.56 | 6.13 | 35.01 | 15.88 | 2.77 | -2.74 |
| 6 | 112 | -130 | 166 | -19.06 | 9.74 | 12.41 | -14.34 | -23.41 | -15.25 | -9.22 | -12.49 | 10.79 |
| 7 | 40 | 9 | 91 | -2.57 | 6.17 | 11.49 | 7.70 | -12.34 | -34.52 | -7.12 | -3.53 | 6.21 |
| 8 | -112 | -3 | 162 | -11.35 | -5.77 | 21.42 | -7.04 | 17.37 | 14.60 | 1.78 | 13.25 | -14.26 |
| 9 | -152 | 89 | 199 | -14.97 | -2.19 | 25.56 | 3.71 | -5.74 | -20.10 | -15.70 | -6.53 | -8.96 |


### Actuator states


| # | T1 [N] | dp1 [deg] | dy1 [deg] | dp1_dot [deg/s] | dy1_dot [deg/s] | T2 [N] | dp2 [deg] | dy2 [deg] | dp2_dot [deg/s] | dy2_dot [deg/s] |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 9160 | 2.51 | -3.94 | 0.01 | 5.77 | 8674 | 3.49 | 2.72 | -2.36 | -2.57 |
| 1 | 7435 | 1.50 | 3.36 | 6.87 | -2.67 | 6691 | -3.46 | 0.01 | -6.37 | 1.18 |
| 2 | 4297 | 3.79 | 2.35 | 5.41 | -1.55 | 7338 | 0.82 | -0.28 | 0.21 | 7.07 |
| 3 | 8156 | -2.09 | 0.92 | -3.09 | -5.85 | 5003 | 2.54 | 1.51 | -4.77 | 3.44 |
| 4 | 5427 | 0.21 | -2.94 | 3.71 | 6.89 | 9232 | -0.85 | -3.00 | 4.20 | -4.68 |
| 5 | 4025 | -2.56 | 3.60 | -4.72 | -3.19 | 5531 | -2.25 | 0.60 | -1.76 | 6.01 |
| 6 | 6583 | 0.68 | -1.52 | 4.09 | 0.04 | 6941 | 0.44 | -3.91 | 1.20 | -1.87 |
| 7 | 5869 | -1.45 | -3.20 | -2.41 | 4.37 | 3989 | 2.21 | 2.13 | -5.77 | -5.74 |
| 8 | 8426 | 3.32 | 1.18 | 2.78 | -7.39 | 8218 | -0.40 | -1.37 | 5.20 | 2.39 |
| 9 | 6170 | 1.89 | 0.18 | 1.50 | -4.27 | 8983 | 3.76 | 1.10 | -3.36 | 4.36 |


## `critical` — Critical  (10 states)


### Rigid-body states


| # | x_E [m] | y_E [m] | alt [m] | u [m/s] | v [m/s] | w [m/s] | phi [deg] | theta [deg] | psi [deg] | p [deg/s] | q [deg/s] | r [deg/s] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | -43 | 23 | 105 | -3.34 | 10.28 | 21.38 | 2.56 | -1.83 | -34.87 | 5.20 | -15.48 | -2.31 |
| 1 | 43 | 78 | 131 | 9.20 | -5.16 | 17.58 | 28.70 | 9.53 | 27.82 | -15.42 | 13.76 | 7.08 |
| 2 | 1 | -138 | 107 | 13.16 | -0.56 | 8.71 | -24.10 | -32.80 | -16.31 | 7.24 | -2.37 | 4.92 |
| 3 | 104 | 44 | 82 | -8.40 | -13.86 | 20.68 | 16.03 | -10.01 | -46.66 | 15.67 | -19.61 | 21.21 |
| 4 | -2 | -48 | 126 | 3.25 | 15.51 | 30.24 | -15.73 | 22.86 | 21.77 | -18.89 | 1.34 | -9.76 |
| 5 | -28 | 96 | 73 | 11.61 | -12.07 | 30.79 | 18.20 | 7.66 | 43.76 | 21.84 | 3.81 | -3.77 |
| 6 | 78 | -91 | 118 | -22.36 | 12.53 | 15.14 | -17.92 | -29.26 | -19.06 | -12.68 | -17.17 | 14.83 |
| 7 | 28 | 6 | 70 | -1.16 | 7.93 | 14.25 | 9.62 | -15.43 | -43.16 | -9.79 | -4.85 | 8.54 |
| 8 | -79 | -2 | 116 | -12.45 | -7.41 | 23.82 | -8.79 | 21.72 | 18.25 | 2.44 | 18.22 | -19.61 |
| 9 | -106 | 62 | 139 | -17.11 | -2.81 | 27.80 | 4.64 | -7.18 | -25.12 | -21.59 | -8.98 | -12.32 |


### Actuator states


| # | T1 [N] | dp1 [deg] | dy1 [deg] | dp1_dot [deg/s] | dy1_dot [deg/s] | T2 [N] | dp2 [deg] | dy2 [deg] | dp2_dot [deg/s] | dy2_dot [deg/s] |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 9733 | 3.77 | -5.91 | 0.01 | 8.65 | 9139 | 5.23 | 4.09 | -3.55 | -3.86 |
| 1 | 7626 | 2.25 | 5.04 | 10.31 | -4.00 | 6716 | -5.18 | 0.01 | -9.55 | 1.77 |
| 2 | 3790 | 5.68 | 3.53 | 8.11 | -2.33 | 7506 | 1.22 | -0.42 | 0.31 | 10.60 |
| 3 | 8506 | -3.13 | 1.38 | -4.64 | -8.77 | 4653 | 3.80 | 2.26 | -7.16 | 5.16 |
| 4 | 5172 | 0.31 | -4.42 | 5.57 | 10.33 | 9822 | -1.27 | -4.50 | 6.31 | -7.01 |
| 5 | 3457 | -3.84 | 5.39 | -7.08 | -4.79 | 5298 | -3.37 | 0.90 | -2.64 | 9.01 |
| 6 | 6584 | 1.02 | -2.28 | 6.13 | 0.06 | 7021 | 0.65 | -5.86 | 1.80 | -2.81 |
| 7 | 5711 | -2.17 | -4.80 | -3.62 | 6.56 | 3414 | 3.32 | 3.20 | -8.65 | -8.61 |
| 8 | 8836 | 4.98 | 1.77 | 4.18 | -11.09 | 8582 | -0.60 | -2.06 | 7.79 | 3.58 |
| 9 | 6079 | 2.84 | 0.28 | 2.25 | -6.40 | 9517 | 5.64 | 1.65 | -5.04 | 6.54 |


# What each fault did from each of them

One grid per regime: rows are the sixteen plants, columns are the numbered
initial conditions above. The columns are the *same states* in every row, which
is what makes a row-to-row difference a statement about the plant.

`L` landed · `g` flew but missed the touchdown gate · `.` no trajectory found ·
`x` already lost before the planner ran


## `approach` — On approach


| Fault | `0 1 2 3 4 5 6 7 8 9` | landed |
|:------------------------------|:------------------------|:--------|
| Healthy (control) | `L L L L L L L L L L` | 10/10 |
| Thrust reduction, $\eta$=0.50 | `L L L L L L L L L L` | 10/10 |
| Thrust reduction, $\eta$=0.15 | `. g . . . g . . . .` | 0/10 |
| Thrust excess, $\eta$=1.30 | `L L L L L L L L L L` | 10/10 |
| Valve stuck open (thrust floor) | `L L L L L L L L L L` | 10/10 |
| Engine out | `. . . . . . . . . .` | 0/10 |
| Slow thrust response, $\tau_T$=2.5 s | `L L L L L L L L L L` | 10/10 |
| Gimbal bandwidth loss, $\omega_n$=0.6 | `L L L L L L L L L L` | 10/10 |
| Gimbal underdamped, $\zeta$=0.25 | `L L L L L L L L L L` | 10/10 |
| Gimbal seizure | `L L L L L L L L L L` | 10/10 |
| TVC effectiveness loss (35 %) | `L L L L L L L L L L` | 10/10 |
| Thrust-vector misalignment (3°, 2°) | `L L L L L L L L L L` | 10/10 |
| Thrust oscillation (chugging) | `L L L L L L L L L L` | 10/10 |
| Transport delay (1 interval) | `L L L L L L L L L L` | 10/10 |
| Mixture-ratio shift (coupled) | `L L L L L L L L L L` | 10/10 |
| Throat-erosion drift | `L L L L L L L L L L` | 10/10 |


## `dispersed` — Dispersed


| Fault | `0 1 2 3 4 5 6 7 8 9` | landed |
|:------------------------------|:------------------------|:--------|
| Healthy (control) | `L L L L L L L L L L` | 10/10 |
| Thrust reduction, $\eta$=0.50 | `L L g L L L L L L L` | 9/10 |
| Thrust reduction, $\eta$=0.15 | `. g . g . . . g g .` | 0/10 |
| Thrust excess, $\eta$=1.30 | `L L L L L L L L L L` | 10/10 |
| Valve stuck open (thrust floor) | `L L L g L L L g L L` | 8/10 |
| Engine out | `. . . . . . . . . .` | 0/10 |
| Slow thrust response, $\tau_T$=2.5 s | `L L L L L L L L L L` | 10/10 |
| Gimbal bandwidth loss, $\omega_n$=0.6 | `L . . . L . . . L L` | 4/10 |
| Gimbal underdamped, $\zeta$=0.25 | `L . . L L L L L L L` | 8/10 |
| Gimbal seizure | `L L g L L L L L L L` | 9/10 |
| TVC effectiveness loss (35 %) | `L L L L L L L L L L` | 10/10 |
| Thrust-vector misalignment (3°, 2°) | `L L L L L L L L L L` | 10/10 |
| Thrust oscillation (chugging) | `L L L L L L L L L L` | 10/10 |
| Transport delay (1 interval) | `L L L L L . L L L L` | 9/10 |
| Mixture-ratio shift (coupled) | `L L g L L L L L L L` | 9/10 |
| Throat-erosion drift | `L L g g L L L L L L` | 8/10 |


## `upset` — Upset


| Fault | `0 1 2 3 4 5 6 7 8 9` | landed |
|:------------------------------|:------------------------|:--------|
| Healthy (control) | `L L L L L L L L L L` | 10/10 |
| Thrust reduction, $\eta$=0.50 | `L L L g g L L L L g` | 7/10 |
| Thrust reduction, $\eta$=0.15 | `. . . . . . . . . g` | 0/10 |
| Thrust excess, $\eta$=1.30 | `L L L L L L L L L L` | 10/10 |
| Valve stuck open (thrust floor) | `L L L g L L L L L g` | 8/10 |
| Engine out | `. . . . . . . . . .` | 0/10 |
| Slow thrust response, $\tau_T$=2.5 s | `L L L g L L L . L L` | 8/10 |
| Gimbal bandwidth loss, $\omega_n$=0.6 | `L L . . L . L . . .` | 4/10 |
| Gimbal underdamped, $\zeta$=0.25 | `L L . . L L L L L L` | 8/10 |
| Gimbal seizure | `L L L g L L L L L L` | 9/10 |
| TVC effectiveness loss (35 %) | `L L L L L L L L L L` | 10/10 |
| Thrust-vector misalignment (3°, 2°) | `L L L L L L L L L L` | 10/10 |
| Thrust oscillation (chugging) | `L L L L L L L L L L` | 10/10 |
| Transport delay (1 interval) | `L L L L L L L . L L` | 9/10 |
| Mixture-ratio shift (coupled) | `L L L g L L L L L L` | 9/10 |
| Throat-erosion drift | `L L L g L L L L L g` | 8/10 |


## `low_late` — Low and late


| Fault | `0 1 2 3 4 5 6 7 8 9` | landed |
|:------------------------------|:------------------------|:--------|
| Healthy (control) | `L L L L L . L L L .` | 8/10 |
| Thrust reduction, $\eta$=0.50 | `. L L L . . L L . .` | 5/10 |
| Thrust reduction, $\eta$=0.15 | `. . . . . . . . . .` | 0/10 |
| Thrust excess, $\eta$=1.30 | `L L L L L . L L L .` | 8/10 |
| Valve stuck open (thrust floor) | `L L L L L . L L L .` | 8/10 |
| Engine out | `. . . . . . . . . .` | 0/10 |
| Slow thrust response, $\tau_T$=2.5 s | `L L L L L . L L . .` | 7/10 |
| Gimbal bandwidth loss, $\omega_n$=0.6 | `L . L L L . L L L .` | 7/10 |
| Gimbal underdamped, $\zeta$=0.25 | `L L L L L . L L L .` | 8/10 |
| Gimbal seizure | `L L L L L . L L L .` | 8/10 |
| TVC effectiveness loss (35 %) | `L L L L L . L L L .` | 8/10 |
| Thrust-vector misalignment (3°, 2°) | `L L L L L . L L L .` | 8/10 |
| Thrust oscillation (chugging) | `L L L L L . L L L .` | 8/10 |
| Transport delay (1 interval) | `L L L L L . L L . .` | 7/10 |
| Mixture-ratio shift (coupled) | `L L L L L . L L . .` | 7/10 |
| Throat-erosion drift | `L L L L L . L L L .` | 8/10 |


## `critical` — Critical


| Fault | `0 1 2 3 4 5 6 7 8 9` | landed |
|:------------------------------|:------------------------|:--------|
| Healthy (control) | `L L . L L . L L . .` | 6/10 |
| Thrust reduction, $\eta$=0.50 | `. L . . . . L . . .` | 2/10 |
| Thrust reduction, $\eta$=0.15 | `. . . . . . . . . .` | 0/10 |
| Thrust excess, $\eta$=1.30 | `L L . L L . L L . .` | 6/10 |
| Valve stuck open (thrust floor) | `L L . L L . L L . .` | 6/10 |
| Engine out | `. . . . . . . . . .` | 0/10 |
| Slow thrust response, $\tau_T$=2.5 s | `. L . L . . L . . .` | 3/10 |
| Gimbal bandwidth loss, $\omega_n$=0.6 | `L . . L . . . L . .` | 3/10 |
| Gimbal underdamped, $\zeta$=0.25 | `L . . L L . L L . .` | 5/10 |
| Gimbal seizure | `. L . L L . L L . .` | 5/10 |
| TVC effectiveness loss (35 %) | `L L . L L . L L . .` | 6/10 |
| Thrust-vector misalignment (3°, 2°) | `L L . L L . L L . .` | 6/10 |
| Thrust oscillation (chugging) | `L L . L L . L L . .` | 6/10 |
| Transport delay (1 interval) | `. L . L . . L . . .` | 3/10 |
| Mixture-ratio shift (coupled) | `. L . L . . L . . .` | 3/10 |
| Throat-erosion drift | `L L . L L . L L . .` | 6/10 |


# Files

```
results/G_initial_conditions.csv   the 50 states above, one row each
results/G_states.npz               the same states plus every regime's box
results/G_samples.csv              one row per solve (state x plant)
```
