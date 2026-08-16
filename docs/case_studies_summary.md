---
title: "Apollo LM Fault Case Studies — Results Summary"
subtitle: "Three fault studies, thirteen solves, at a glance"
date: "30 July 2026"
geometry: margin=2cm
fontsize: 10.5pt
numbersections: false
colorlinks: true
header-includes:
  - \usepackage{booktabs}
  - \usepackage{amsmath}
  - \pagenumbering{gobble}
---

# Verdict

**This vehicle fails through roll authority, not through thrust.** The two faults
that create a *thrust asymmetry* between the laterally-spaced engines
($y_{eng} = \pm 1.5$ m) push it past controllability while thrust-to-weight stays
comfortable. The fault that creates no asymmetry is benign.

| Study | Fault | Asymmetry? | Verdict |
|---|---|---|---|
| **A** Engine-out | one engine dead | total | **Infeasible** at design spacing. Needs $y_{eng} \le 0.43$ m |
| **B** Degraded gimbal | one sluggish actuator | none | **Graceful.** All cases land; order 10–20 % in $J$ |
| **C** Thrust efficiency | one engine delivers $\eta T$ | partial | **Unacceptable below $\eta \approx 0.28$** |

# All thirteen runs

| Study | Case | Fault | $J$ | Iters | Lands? |
|:--|:--|:--|--:|--:|:--|
| A | 1 | baseline, $y_{eng}$=1.5 m | 2.8675e8 | 173 | yes |
| A | 2 | engine 2 dead, $y_{eng}$=1.5 m | — | 400 | **NO** |
| A | 3 | engine 2 dead, $y_{eng}$=0.2 m | 5.3298e8 | 190 | yes |
| B | G1 | baseline gimbal | 2.8670e8 | 168 | yes |
| B | G2 | $\omega_n$=1.5, $\zeta$=0.70 | 3.5069e8 | 390 | yes |
| B | G3 | $\omega_n$=0.6, $\zeta$=0.70 | 3.1960e8 | 270 | yes |
| B | G4 | $\omega_n$=1.0, $\zeta$=0.25 | 3.4058e8 | 284 | yes |
| C | E1 | $\eta$=1.00 baseline | 2.8670e8 | 168 | yes |
| C | E2 | $\eta$=0.85 | 2.9188e8 | 208 | yes |
| C | E3 | $\eta$=0.65 | 3.2113e8 | 199 | yes |
| C | E4 | $\eta$=0.40 | 3.7374e8 | 192 | yes |
| C | E5 | $\eta$=0.25 | 5.6255e8 | 204 | **marginal**\* |
| C | E6 | $\eta$=0.15 | — | 400 | **NO** |

\* E5 converges but misses the landing gate: 5.95° touchdown attitude error
against a 5° criterion, 0.193 m/s residual speed, and 74 s of the 80 s horizon
consumed. Baseline gimbal is $\omega_n$=4.0 rad/s, $\zeta$=0.70. B/G1 and C/E1
are the same nominal problem and agree exactly — a useful cross-check.

# The three numbers that matter

| Boundary | Value | Meaning |
|---|---|---|
| $y_{crit} = d_{z,eng}\tan\delta_{y,\max} + L_{RCS}/T_{hover}$ | **0.434 m** | max engine spacing for engine-out survivability (0.263 m on gimbal trim alone). Design value 1.5 m is **3.5× beyond** |
| $\eta_{sat} = (T_{hover}/2)/T_{\max,eng}$ | **0.278** | below this the weak engine saturates and throttling can no longer equalise delivered thrust — **the practical limit** |
| $\eta_{min}$ | **0.198** | below this the residual roll moment exceeds gimbal + RCS authority — infeasible |

Each was derived analytically before solving, and each was confirmed by the
solves. Study A predicted static trim would need 4.57° of yaw gimbal; the solve
parked it at 4.65°. Study C predicted saturation at $\eta_{sat}$; at $\eta$=0.25
the weak engine's mean command was 22 101 N against a 22 520 N limit.

# Why thrust is not the problem

| Case | Total delivered thrust | T/W | Outcome |
|---|---|---|---|
| Nominal | 45 040 N | 3.59 | lands |
| A, engine-out | 22 520 N | 1.80 | **infeasible** (roll) |
| C, $\eta$=0.15 | 25 898 N | 2.07 | **infeasible** (roll) |

Both failures retain ample thrust. What they lack is roll authority: the
engine-out roll moment is **18 796 N·m** against **5 432 N·m** available
(3 293 gimbal + 2 140 RCS) — a 13.4 kN·m deficit, which is 143 °/s² of roll
acceleration against a 10 °/s rate limit, violated in 0.07 s.

# What degradation costs when it is survivable

| Quantity | Nominal | A, engine-out ($y_{eng}$=0.2) | B, worst gimbal | C, $\eta$=0.40 |
|---|---|---|---|---|
| Time to contact | 26 s | 47 s | 26 s | 41 s |
| Peak total thrust | 45 036 N | 22 520 N | 45 036 N | 22 867 N |
| Mean yaw gimbal | 1.2° | **4.65° of 6°** | 1.5–1.6° | 3.95° |
| RCS impulse | 91 kN·s | 171 kN·s (+88 %) | 99 kN·s (+8 %) | 147 kN·s (+62 %) |
| Wasted impulse | 0 | 0 | 0 | **909 kN·s (~40 %)** |

Recurring pattern in both asymmetry faults: the dominant engine's yaw gimbal
parks on a static-trim shelf near its limit, and RCS impulse rises sharply
because the asymmetry must be held continuously rather than manoeuvred against.

# Two findings that need a caveat

**1. Study B's objective ordering is not reliable.** The NLP is nonconvex. Three
solves of the *identical* nominal problem under default multithreaded BLAS gave
$J$ spread over 1.0 %; pinning `OMP_NUM_THREADS=1` made it exact (2.867018e8,
168 iters, three times). But pinning does not make different *configurations*
land in comparable minima — G2's objective moved **10.4 %** between two
campaigns, comparable to the whole spread between cases. An earlier monotone
ordering (+11.9/+12.6/+20.4 %) suggested "damping loss costs more than bandwidth
loss"; the reproducible campaign (+22.3/+11.5/+18.8 %) does not support it, and
that conclusion was **withdrawn**. Study B's robust findings are the physical
ones (below). Study C's trend is safe — large, monotone, and corroborated by
three independent physical measures. Study A does not rest on objectives at all.

**2. Study B's compensation mechanism is counterintuitive but robust.** The
optimiser does *not* offload onto the healthy engine. It commands the degraded
gimbal **harder** (RMS 1.51° → 2.70°) while the healthy engine's command *falls*
(1.60° → 1.33–1.55°), because a sluggish actuator attenuates and must be
over-driven. Max tracking error reaches exactly 12.000° — full scale, command at
one ±6° limit while the deflection sits at the other. This held across both
campaigns. Caveat: the optimiser exploits the actuator as a low-pass filter
(only the healthy actuator's 4.04 rad/s bandwidth exceeds the 3.14 rad/s command
grid Nyquist), issuing ±6° square waves no real autopilot would command — an
artefact of penalising *commanded* rate rather than achieved deflection rate.

# Caveats that matter for interpretation

* **Constant mass** — worst for Study C, where 1.34e6 N·s wasted at $\eta$=0.25
  is ~440 kg of extra propellant on a 7 711 kg vehicle. A mass-tracking model
  might run out of propellant before roll authority. **Study C understates the
  propellant consequence.**
* **All faults known from $t=0$** — these answer "how well can a known-degraded
  vehicle be flown?", not "can it respond to a fault?"
* **No actuator slew-rate limit** — a real omission in Study B; a hard rate limit
  would hurt more than lost bandwidth and would block the over-commanding strategy.
* **Open loop, fixed 80 s horizon** — reference trajectories only. Studies A and C
  use 47 s and 74 s of the horizon, so it is closer to binding than nominal suggests.
* **Study A predates the thread-pinning protocol**, so its iteration counts are
  indicative; its verdicts are analytic and unaffected.

# Design implication

The 1.5 m spacing is simultaneously the vehicle's best roll actuator
(differential throttling gives ±4 000 N·m, roughly double the entire RCS roll
budget) **and its single point of failure** — the same moment arm converts any
thrust asymmetry into a trim problem it cannot absorb. Reducing the spacing
relaxes both the engine-out and the $\eta$ limits, at the cost of handing roll
control to the propellant-limited RCS.

Study A's case 3 answers *"what spacing would have survived?"* — not *"can the
vehicle as built survive?"* That answer is no.

---

Full detail, figures, and derivations: `case_studies_full_report.pdf`. Model
documentation: `apollo_full_documentation.pdf`. Per-study writeups sit in each
case-study directory.
