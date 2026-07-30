---
title: "Thrust-Efficiency Case Study"
subtitle: "Apollo LM Powered Descent with a Partial-Thrust Engine"
date: "30 July 2026"
geometry: margin=2.5cm
fontsize: 11pt
numbersections: true
toc: true
colorlinks: true
header-includes:
  - \usepackage{booktabs}
  - \usepackage{amsmath}
---

# Thrust-Efficiency Case Study

Engine 2 delivers only a fraction $\eta$ of its commanded thrust as useful
force,

$$
F_\text{delivered} = \eta\,T, \qquad \eta \in (0, 1],
$$

while its actuator dynamics — and therefore its propellant draw — still act on
the full $T$. The shortfall is **lost power, not saved fuel**. Engine 1 is
healthy; everything else is held at the baseline. Implemented through the new
`LMParams.thrust_eff_eng`.

| Case | Directory | $\eta$ | Regime | Result |
|---|---|---|---|---|
| E1 | `E1_eta1.00/` | 1.00 | baseline | lands, $J$ = 2.867e8 |
| E2 | `E2_eta0.85/` | 0.85 | throttle-only trim | lands, +1.8 % |
| E3 | `E3_eta0.65/` | 0.65 | throttle-only trim | lands, +12.0 % |
| E4 | `E4_eta0.40/` | 0.40 | throttle-only trim | lands, +30.4 % |
| E5 | `E5_eta0.25/` | 0.25 | gimbal + RCS committed | converges but **misses the landing gate** |
| E6 | `E6_eta0.15/` | 0.15 | untrimmable | **no solution** |

Each directory holds `states.png`, `controls.png`, `actuators.png`,
`thrusters.png`, `trajectory_with_axes.png`, `console_log.txt`, `metrics.json`
and `solution.npz`. Three cross-case figures sit at the top level:

* `efficiency_regime_map.png` — the analytic regime boundaries
* `efficiency_comparison.png` — the converged trajectories overlaid
* `efficiency_cost.png` — what the loss costs

Reproduce with:

```bash
python run_efficiency_study.py         # all six cases, about 12 min
python plot_regime_map.py              # analytic regime map (no solve)
python plot_efficiency_comparison.py   # trajectory overlay + cost figures
```

## The headline result

**The binding constraint is not the lost thrust — it is the roll asymmetry the
loss creates.** Losing efficiency on one engine of a laterally-spaced pair is
primarily a *roll-trim* problem, exactly as in the engine-out study.

Even at $\eta = 0.15$ the vehicle retains 25 900 N of total delivered thrust
against a 12 530 N hover requirement — a thrust-to-weight of 2.07, ample on
paper. It still cannot land, because the two engines sit at $y = \pm 1.5$ m and
unequal *delivered* thrust is a roll moment.

### The three regimes

Balanced hover requires both engines to deliver $T_\text{hover}/2$, so the weak
one must be commanded at $(T_\text{hover}/2)/\eta$ — and that command is bounded
by $T_{\max,\text{eng}} = 22\,520$ N. This gives the first boundary:

$$
\eta_\text{sat} = \frac{T_\text{hover}/2}{T_{\max,\text{eng}}}
                = \frac{6265}{22\,520} = \mathbf{0.278}
$$

Below $\eta_\text{sat}$ the weak engine saturates, the delivered thrusts can no
longer be equalised, and the leftover asymmetry becomes a residual roll moment
$L = y_\text{eng}\,(F_1 - F_2)$ that the gimbal and RCS must absorb. Setting that
equal to the available authority gives the second boundary:

$$
\eta_\text{min} = \frac{T_\text{hover} - L_\text{auth}/y_\text{eng}}
                       {2\,T_{\max,\text{eng}}} = \mathbf{0.198},
\qquad L_\text{auth} = 3293 + 2140 = 5432\ \text{N·m}
$$

| Regime | Condition | Behaviour |
|---|---|---|
| I | $\eta \ge 0.278$ | Trimmable by differential throttling alone; gimbal and RCS stay free for manoeuvring |
| II | $0.198 \le \eta < 0.278$ | Trimmable only with the gimbal and RCS committed to static roll trim |
| III | $\eta < 0.198$ | Residual roll moment exceeds all available authority — infeasible |

The authority is evaluated **at hover**, which is deliberate: the gimbal's roll
capacity is $\big(\sum_i F_i\big) d_{z,eng}\tan\delta_{y,\max}$, so it scales
with delivered thrust and is *weakest* at hover — which is precisely where the
vehicle must end up. During the high-thrust braking phase the same solutions
carry roll moments of 7 000–10 500 N·m, well above the hover budget, without
difficulty.

## Results

| Metric | $\eta$=1.00 | 0.85 | 0.65 | 0.40 | 0.25 | 0.15 |
|---|---|---|---|---|---|---|
| Status | solved | solved | solved | solved | solved | **FAILED** |
| Objective $J$ | 2.867e8 | 2.919e8 | 3.211e8 | 3.737e8 | 5.626e8 | — |
| $J$ vs baseline | — | +1.8 % | +12.0 % | +30.4 % | **+96.2 %** | — |
| Peak delivered thrust [N] | 45 036 | 41 658 | 36 254 | 22 867 | 16 848 | 11 881 |
| Mean weak-engine command [N] | 10 757 | 11 411 | 13 340 | 18 697 | **22 101** | 22 517 |
| Mean healthy command [N] | 10 430 | 10 336 | 10 347 | 9 563 | 8 593 | 5 716 |
| Impulse burnt [N·s] | 1.716e6 | 1.762e6 | 1.919e6 | 2.289e6 | 2.486e6 | — |
| Impulse delivered [N·s] | 1.716e6 | 1.623e6 | 1.540e6 | 1.380e6 | 1.144e6 | — |
| **Wasted impulse [N·s]** | 0 | 1.39e5 | 3.78e5 | 9.09e5 | **1.34e6** | — |
| Mean \|TVC roll moment\| [N·m] | 697 | 1 630 | 2 916 | 3 445 | 4 601 | — |
| Mean \|yaw gimbal\| [°] | 1.22 | 1.63 | 3.13 | 3.95 | **5.75** | — |
| RCS impulse [N·s] | 91 068 | 97 353 | 107 900 | 147 380 | **274 533** | — |
| Time to contact [s] | 26 | 27 | 30 | 41 | **74** | — |
| Terminal speed [m/s] | 3.8e-6 | 5.9e-6 | 2.6e-6 | 6.0e-6 | 0.193 | 25.5 |
| Terminal attitude error [°] | ~0 | ~0 | ~0 | ~0 | **5.95** | 34.2 |
| IPOPT iterations | 168 | 208 | 199 | 192 | 204 | 400 (capped) |

### Regime I is graceful; the penalty is propellant

For $\eta \ge 0.40$ every case lands to full precision (terminal speed below
$10^{-5}$ m/s). The optimiser simply commands the weak engine higher — the mean
command rises from 10 757 N to 18 697 N — and equalises the *delivered* thrusts.
Roll trim costs nothing extra because differential throttling handles it.

What it does cost is propellant. At $\eta = 0.40$ the vehicle burns
2.289e6 N·s of impulse to deliver 1.380e6 N·s: **909 kN·s, roughly 40 %, is
wasted**. The descent also slows — thrust-to-weight falls from 3.59 to 1.80, so
contact takes 41 s rather than 26 s.

### Regime II converges but does not land acceptably

$\eta = 0.25$ sits between the two boundaries, and the model behaves exactly as
the regime analysis predicts, on three independent signals:

* the weak engine's mean command is 22 101 N against a 22 520 N limit — **it is
  saturated essentially throughout**;
* the mean yaw-gimbal deflection is 5.75° of the 6° available — **96 % of the
  gimbal range is consumed holding static trim**;
* RCS impulse triples, from 91 068 to 274 533 N·s.

The trajectory carries a persistent ~3 300 N delivered-thrust asymmetry and
~4 800 N·m roll moment for the entire descent, visible as the flat shelves in
`efficiency_comparison.png`.

The NLP converges, but **the landing criteria are not met**: touchdown attitude
error is 5.95° against the 5° gate, with 0.193 m/s residual speed. With the
gimbal saturated and the RCS committed, there is nothing left to null the roll
with. Contact also takes 74 s of the fixed 80 s horizon, so the vehicle is
nearly out of time as well.

**The practical limit is therefore $\eta \approx 0.28$, not 0.198.** The
analytic boundary at 0.198 is where a solution stops *existing*; the boundary at
0.278 is where an *acceptable landing* stops existing. For design purposes the
latter is the number that matters, and it coincides with $\eta_\text{sat}$ —
the point where differential throttling alone can no longer equalise the
delivered thrusts.

### Regime III is infeasible

At $\eta = 0.15$ the residual roll moment at hover is 8 662 N·m against
5 432 N·m of authority — a deficit of 3 229 N·m. IPOPT exits with
`Maximum_Iterations_Exceeded` after the 400-iteration cap with a constraint
violation of 0.393 still outstanding (the converged cases reach $10^{-6}$). The
final iterate is 34.2° off in attitude and moving at 25.5 m/s. As in the
engine-out study, the figures in that directory are a diverging iterate plotted
for diagnosis, **not a trajectory**.

## Relationship to the other two studies

All three fault studies converge on the same conclusion about this vehicle:

| Study | Fault | Failure mode |
|---|---|---|
| Engine-out | one engine dead | **roll authority** — infeasible at design spacing |
| Degraded gimbal | one slow actuator | none — graceful, ~10–20 % in $J$ |
| Thrust efficiency | one weak engine | **roll authority** — unacceptable below $\eta \approx 0.28$ |

The two thrust-related faults both fail through roll, and both fail at the
lateral spacing $y_\text{eng} = 1.5$ m rather than through any shortage of
thrust. The gimbal fault is benign precisely because it does not create an
asymmetry — it only makes one actuator slower to respond.

This strengthens the engine-out study's design recommendation: the 1.5 m
spacing, chosen to give differential-throttle roll authority, is what converts
*any* thrust asymmetry into a trim problem the vehicle cannot absorb. A smaller
spacing would raise $\eta_\text{sat}$ tolerance in exactly the way it restored
engine-out survivability.

## What the model does and does not capture

* **$\eta$ is constant and known from $t=0$.** The optimiser plans around it
  with full knowledge. A real efficiency loss would appear mid-descent, and the
  open-loop OCP cannot represent detection delay or the transient.
* **Constant mass.** This is the most consequential simplification here, and it
  cuts against the reported numbers. The wasted impulse at $\eta = 0.25$ is
  1.34e6 N·s, comparable to the *entire* delivered impulse. At an $I_{sp}$ of
  ~311 s that is several hundred kilograms of extra propellant on a 7 711 kg
  vehicle — so a mass-tracking model would show the vehicle getting lighter
  faster, and might well run out of propellant before it runs out of roll
  authority. **The propellant consequence of a partial-thrust engine is
  understated by this model.**
* **$\eta$ applies to force only.** The loss is modelled as a pure force
  scaling: no change to the thrust lag, no change to the throttle envelope, no
  extra thermal or vibration effect. A real cause (injector fouling, chamber
  erosion, feed-pressure loss) would likely also shift the throttle limits and
  the actuator response.
* **Both gimbal axes and the moment arm are unchanged.** The weak engine still
  gimbals normally, and its reduced thrust reduces its gimbal *authority*
  proportionally — which is captured — but nothing else about its geometry
  changes.
* **The objective comparison inherits the nonconvexity caveat** documented in
  the gimbal study: single-digit-percent gaps in $J$ are not resolvable without
  a multi-start. Here the effect sizes (+1.8 % to +96 %) are large and monotone
  in $\eta$, so the trend is safe even though the +1.8 % entry on its own is
  not.
* **Feedback.** As throughout, these are open-loop reference trajectories.
