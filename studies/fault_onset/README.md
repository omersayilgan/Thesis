# Fault-Onset & Initial-Condition Study

Studies **D** and **E**: what the three earlier case studies (A, B, C) could not
answer, because all three assumed the fault was known from `t = 0`.

| | Question | Continuous space searched |
|---|---|---|
| **D** | A healthy vehicle breaks *mid-descent*. Does it survive? | `(t_f, η, τ_d)` — onset time × severity × reaction delay, on **two** reference profiles |
| **E** | The vehicle arrives dispersed. Can it land *at all*, and can it still land after a fault? | 12-D initial-condition box (+ a fault draw) |
| **F** | **Is a fault an initial condition?** Drops the nominal trajectory entirely. | 22-D state box (12 rigid + 10 **actuator**) × 12 plant configurations, paired |

Both spaces are uncountable and each sample costs an NLP solve, so neither is
enumerated — they are **estimated**, with the error stated:

* **bisection** on whichever axis decides survival — 9 solves per slice resolve
  a boundary to 1/128 of its bracket, where a 9-point grid manages 1/8;
* **Sobol** low-discrepancy sampling for coverage without assuming monotonicity;
* **Wilson score intervals** on every reported fraction;
* a **cross-validated surrogate classifier** for the 12-D volume, quoted next to
  its own out-of-fold accuracy so the classifier's error is never hidden inside
  the volume estimate.

## Files

| File | What it is |
|---|---|
| `fault_lib.py` | The experiment: fault injection, reaction delay, replan OCP, landing gate |
| `campaign.py` | Parallel execution (BLAS pinned to 1 thread) + CSV bookkeeping |
| `run_study_D.py` | D1/D2 delay bisection, D5 severity bisection, D3 Sobol cube |
| `run_study_E.py` | Sobol Monte Carlo over the initial-condition box |
| `analyse.py` | Figures + `results/headline.json` (every number in the D/E report) |
| `run_study_F.py` | 22-D state box × plant configurations, paired |
| `analyse_F.py` | Study F figures + McNemar tests + `results/headline_F.json` |
| `build_report_F.py` | Builds `fault_as_initial_condition.pdf` |
| `report_body.py`, `findings.py` | The report text, interpolated from `headline.json` |
| `build_report.py` | `results/headline.json` + figures → `fault_onset_study.pdf` |
| `results/` | One CSV row per solve — the raw campaign record |
| `figures/` | Generated figures |

## Headline results

| | |
|---|---|
| Hard engine-out, any onset, either profile | **never recoverable** — confirms Study A's roll-budget deficit dynamically |
| Critical severity η*, de-rated profile | **0.289 – 0.992**, U-shaped in onset time — the vehicle is most vulnerable in mid-descent |
| η* at both ends of the descent | approaches Study C's analytic η_sat = 0.278 from above, without crossing it |
| Design (max-effort) reference | absorbs essentially nothing; the de-rated one absorbs 7 of 8 onsets |
| P(land \| healthy) over the 12-D box | **0.977** [0.948, 0.990] |
| P(land \| mid-descent fault) | **0.205** [0.156, 0.264] |
| What decides fault survival | severity (0.179) ≫ onset time (0.040) ≫ everything else; reaction delay scores **0.000** |

~707 NLP solves in total (272 Study D, 435 Study E).

## Study F — is a fault an initial condition?

Study F tests the claim that a fault can be modelled purely as a change of
initial conditions, so no nominal trajectory need be computed. It samples the
full 22-D state (including the actuator/control states) and solves **every
plant configuration from identical initial conditions**, making the comparison
a within-sample McNemar test in which the state distribution cancels exactly.

| | |
|---|---|
| Verdict | **A fault is not an initial condition — except when the vehicle can trim it, in which case it very nearly is** |
| Significant plant effect | 7 of 10 damaged configurations at *p* < 0.05, on literally identical states |
| Not significant | η=0.50 (both spacings) and η=0.15 at y_eng=0.25 m — exactly the *trimmable* faults |
| Landing sets | **nested, not displaced** — 182 discordant pairs one way, 2 the other |
| Engine-out, y_eng 1.5 → 0.25 m | 0.000 → **0.708** (+71 pp) |
| η=0.15, y_eng 1.5 → 0.25 m | 0.000 → **0.833** (+83 pp) |
| Gimbal degradation | 0.479 → 0.479 — **completely indifferent to spacing** (bandwidth, not asymmetry) |
| Healthy control | 0.917 → 0.896 — spacing does nothing for an undamaged vehicle |
| State-only classifier | CV 0.500 at 1.5 m vs 0.758 at 0.25 m — the state is uninformative exactly where the fault dominates |

It also exposed a latent bug in the base model: the gimbal actuator
(ω_n = 4 rad/s) is **numerically unstable on the 1 s grid**, since ω_n·Δt = 4.0
exceeds RK4's stability limit of ≈2.79. Earlier studies never excited it
because they start the gimbal rate states at zero. Fixed with two RK4
sub-steps per control interval; see `fault_as_initial_condition.pdf` §2.4.

Report: [`fault_as_initial_condition.pdf`](fault_as_initial_condition.pdf)
(576 solves, 48 shared initial conditions × 12 plants).

## Reproducing

```bash
python run_study_D.py        # 272 solves
python run_study_E.py        # 220 arrivals, 435 solves
python run_study_F.py 48     # 48 states x 12 plants = 576 solves
python analyse_F.py && python build_report_F.py
python analyse.py
python build_report.py
```

`FAULT_WORKERS=6 python run_study_D.py` to change the pool size, and
`python run_study_D.py D5 D3` to run selected parts.

## The parts of Study D

| Part | Bisects | Answers |
|---|---|---|
| D1 | reaction delay $\tau_d$, engine-out | how long may the vehicle stay unaware? |
| D2 | reaction delay $\tau_d$, across severity | how much reaction time does a partial fault buy? |
| D5 | severity $\eta$, across onset time | how mild must a fault be to survive, and does timing change that? |
| D3 | nothing — Sobol over the whole cube | coverage without assuming monotonicity; tests D1/D2/D5's premise |

Each runs on both the **design** reference (the max-effort descent of Studies
A–C, contact at 26 s) and a **de-rated** one (`V_max` 60→30 m/s, `omega_max`
10→5 °/s, contact at 42 s). The pair is what separates a property of the
vehicle from a property of the trajectory it is flying.

## The fault-response protocol

1. **Nominal plan** — solve the healthy OCP from `x0`.
2. **Fly to `t_f`** — replay the nominal commands on the healthy dynamics to the
   exact, off-grid onset time.
3. **Fault + delay** — the fault engages; the *stale* nominal command keeps
   being applied for `τ_d` on the now-asymmetric vehicle.
4. **Hard-loss check** — tumble / past-horizontal / impact ends it here.
5. **Replan** — re-solve from the post-delay state, degraded vehicle, on the
   time left before the 80 s deadline, inside a recovery corridor.
6. **Touchdown gate** — cut the engine at contact, settle ballistically, score.

Two artefacts had to be removed before any of this measured physics; both are
documented in `fault_lib` and in the report.

The **recovery corridor** is the first, documented in `fault_lib.solve_ocp`:
the nominal descent rides `V_max` and the body-rate limit *exactly*, so a hard
path bound at the first replan node would report "infeasible" for a 0.001 m/s
overshoot. Instead each bound starts at the actual post-fault excursion and is
tightened linearly back to the nominal envelope over `n_relax` steps — the
planner must demonstrably recover, but is not condemned by the grid.

The **forced hover tail** is the second (`fault_lib.T_RESERVE`): running the
replan all the way to the 80 s mission deadline makes it hold the 1 m contact
floor exactly for ~50 s, which turned recoverable faults infeasible. The replan
gets the nominal's remaining descent time plus a 20 s reserve instead.
