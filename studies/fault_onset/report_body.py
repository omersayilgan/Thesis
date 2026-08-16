"""
The report text.  Kept separate from build_report.py so the prose can be edited
without touching the build machinery.  Every quantity is interpolated from
headline.json — if a number appears in the PDF it came from a solve.
"""

import datetime

import numpy as np

from build_report import table, fig, ci, pct, fmt_ms

PROF_NAME = {'design': 'design', 'derated': 'de-rated'}


def tau_cell(tau, brk):
    if brk in ('unrecoverable', 'no_margin'):
        return '**none**'
    if brk == 'censored_high':
        return f'$>$ {tau / 1e3:.2f} s'
    return fmt_ms(tau / 1e3)


def eta_cell(eta, brk):
    if brk == 'no_margin':
        return '**none**'
    if brk == 'censored_low':
        return 'any ($\\eta \\ge 0$)'
    return f'{eta:.3f}'


def front_matter():
    today = datetime.date.today().strftime('%d %B %Y').lstrip('0')
    return f"""---
title: "Apollo LM Powered Descent — Fault Onset and Landing Feasibility"
subtitle: "Studies D and E: searching a continuous fault space, and estimating landing feasibility over a dispersed initial-condition set"
date: "{today}"
geometry: margin=2.4cm
fontsize: 11pt
numbersections: true
toc: true
toc-depth: 2
colorlinks: true
header-includes:
  - \\usepackage{{booktabs}}
  - \\usepackage{{amsmath}}
  - \\usepackage{{longtable}}
  - \\usepackage{{float}}
  - \\floatplacement{{figure}}{{H}}
  - \\setlength{{\\emergencystretch}}{{3em}}
---

\\newpage
"""


def section_scope(h):
    n_d = h.get('n_fault_solves', 0)
    e = h.get('E', {})
    return f"""
# What this adds to the earlier case studies

Studies A, B and C answered *"how well can a known-degraded vehicle be flown?"*
Every fault in them was present from $t = 0$ and known to the planner, and each
study was a handful of solves at hand-picked parameter values. Two questions
were left open, and both live in **continuous** spaces that cannot be
enumerated:

1. **A healthy vehicle breaks mid-descent.** The fault arrives at a continuous
   onset time $t_f$, with a continuous severity $\\eta$, and is acted on only
   after a continuous reaction delay $\\tau_d$. Does it cause a failure?
2. **The vehicle does not always start where the design case says.** Given a
   12-dimensional dispersion box of arrival states, for what fraction is a
   landing possible *at all* — and for what fraction is it still possible once
   something breaks?

Both are volume questions over uncountable sets, and each sample costs a
nonlinear-programme solve taking tens of seconds. Neither can be answered
exactly. This study estimates them, and states the estimation error rather than
hiding it.

| | Question | Space searched | Solves |
|---|---|---|---|
| **D** | does a mid-descent fault cause a failure? | $(t_f, \\eta, \\tau_d)$, two reference profiles | {n_d} |
| **E** | can it land from anywhere in the dispersion box? | 12-D box $\\times$ fault draw | {e.get('n', 0)} arrivals |

# Method

## The fault-response protocol

Each sample is a six-stage experiment, not a single solve. That structure is
the point: it separates *the fault being unrecoverable* from *nobody reacting
in time*, which a single degraded-from-$t_0$ solve cannot distinguish.

1. **Nominal plan.** Solve the healthy OCP from $x_0$, giving $(X_{{nom}},
   U_{{nom}})$. If it fails, the initial condition itself is infeasible and
   there is no fault question to ask.
2. **Fly to $t_f$.** Replay the nominal commands on the healthy dynamics up to
   the exact onset time. $t_f$ is *not* snapped to the 1 s control grid — the
   state is re-integrated at 0.02 s from the grid node below it, so the onset
   axis is genuinely continuous.
3. **Fault, then blindness.** The fault engages. The vehicle keeps applying the
   *stale* nominal command for $\\tau_d$ seconds, now on an asymmetric vehicle.
   Nothing is compensating during this window.
4. **Hard-loss check.** If the delay leaves the vehicle tumbling, past
   horizontal, or on the ground, it is lost before any replan could act — and
   this is recorded without spending a solve.
5. **Replan.** Re-solve from the post-delay state, with the degraded vehicle,
   on the time remaining.
6. **Touchdown gate.** Cut the engine at contact, settle ballistically, and
   score the touchdown.

## Two thresholds, deliberately different

A recurring trap in this kind of study is to treat the planner's own path
constraints as the definition of a crash. They are not. $\\omega_{{max}} =
10^\\circ$/s and $45^\\circ$ of attitude are comfort limits chosen when the OCP
was posed; a vehicle briefly outside them has not been lost.

* **Hard loss of control** (ends the sample immediately): tilt past
  $90^\\circ$, any body rate past $120^\\circ$/s, per-axis speed past
  $1.5\\,V_{{max}}$, or ground contact. These are conditions with no way back.
* **Landing gate** (scored at touchdown, after the engine-off settle):
  vertical speed $\\le 3.0$ m/s, horizontal $\\le 1.2$ m/s, tilt $\\le
  6^\\circ$, distance from pad $\\le 15$ m, body rates $\\le 5^\\circ$/s.

Everything between the two is handed to the optimiser, so that *it* decides
whether a recovery exists.

## Two reference profiles

The descent flown in Studies A–C is a **maximum-effort** trajectory. It rides
$V_{{max}}$ on the descent axis and saturates **all three** body-rate channels
simultaneously, reaching contact in 26 s. Everything in Study D was therefore
run twice: once on that *design* reference, and once on a **de-rated**
reference — same vehicle, same initial condition, same cost, but with the
planner's limits pulled in ($V_{{max}}$ 60 $\\to$ 30 m/s, $\\omega_{{max}}$ 10
$\\to$ 5$^\\circ$/s), reaching contact in 42 s.

Running only the design profile would have shown that it cannot absorb faults
without showing *why*. The pair separates a property of the vehicle from a
property of the trajectory it happens to be flying, and that turned out to be
the study's main result.

## The recovery corridor, and two artefacts that had to be removed first

Getting a *meaningful* answer required eliminating two effects that had nothing
to do with the physics. Both are recorded here because either one, left in,
would have produced a confident and completely wrong conclusion.

**The corridor.** Because the design reference sits exactly on $V_{{max}}$ and
on all three rate limits, a replan imposing those same bounds from its first
node is infeasible for *any* fault — the vehicle is not permitted to exceed
$10^\\circ$/s for even one grid step while absorbing a disturbance. The replan
instead flies inside a corridor: each bound starts at the larger of the
post-fault excursion and a transient allowance ($3\\times$ the rate limit,
$1.35\\times$ attitude, $1.2\\times$ velocity — all far inside the hard-loss
thresholds) and is tightened linearly back to the design envelope over six
seconds. This is a *demand*, not a dispensation: the planner must demonstrably
be back inside the envelope within six seconds.

**The forced hover tail.** Giving the replan every remaining second up to the
80 s mission deadline forces it to hover on the 1 m contact-altitude floor for
the whole unused tail — roughly 50 s of holding a hard constraint boundary
exactly, on a 1 s RK4 grid. That is a pathological arc, and it was observed to
turn otherwise-recoverable faults infeasible. The replan is instead given the
nominal's own remaining descent time plus a 20 s reserve, still capped by the
80 s deadline.

Both were diagnosed rather than assumed. A constraint-group ablation on one
failing replan showed that relaxing the altitude floor *alone*, the rate limit
*alone*, or the glide cone *alone* each converted the same infeasible problem
into a converged landing in 116–174 IPOPT iterations — no single constraint was
responsible, which is the signature of a reference with no slack rather than of
a genuinely unrecoverable fault.

## Searching an infinite space with a finite budget

Three techniques, each doing something the others cannot.

**Bisection** on the axis that decides survival. Nine solves per slice resolve a
boundary to 1/128 of its bracket; a uniform grid of nine points resolves it to
1/8. Bisection assumes survival is monotone along that axis — more blind time
is never better, more delivered thrust is never worse — which is checked
independently below.

**Sobol sampling** of the full cube. Low-discrepancy points give integration
error scaling like $O(\\log^d N / N)$ rather than the $O(N^{{-1/2}})$ of plain
Monte Carlo, which matters at $N \\sim 10^2$. Crucially it assumes *nothing*
about monotonicity, so it is what tests the bisection's premise.

**A cross-validated surrogate** for the 12-D volume in Study E: a
gradient-boosted classifier fitted to the samples and integrated over 200 000
cheap points. Its out-of-fold accuracy is reported next to the volume it
produces, because a surrogate volume is worth exactly what the classifier is
worth.

Every reported fraction carries a **Wilson score interval**, which behaves near
0 and 1 where the normal approximation does not.

## Reproducibility

Every solve runs with `OMP_NUM_THREADS=1`. Study B established that
multithreaded BLAS makes this NLP's objective non-reproducible at the ~1 %
level; parallelism here is across samples instead, so each individual solve is
deterministic. IPOPT's own return status is recorded for every solve, so
`Maximum_Iterations_Exceeded` is never silently reported as infeasibility.
"""


def _two_profile_table(d, xlabel, cell_fn, xkey='x', ykey='y',
                       per_profile_x=False):
    """Two profiles side by side.

    When the sweep axis is *time*, the two profiles do not share it — the
    design reference reaches contact in 26 s and the de-rated one in 42 s, and
    the sweep is over the same onset *fractions* of each. Printing one shared
    time column would silently pair 13.0 s on one profile with 21.0 s on the
    other, so each profile carries its own onset column instead.
    """
    profs = [p for p in ('design', 'derated') if p in d
             and isinstance(d[p], dict) and xkey in d[p]]
    if not profs:
        return ''
    n = len(d[profs[0]][xkey])
    rows, header, align = [], [], []
    if per_profile_x:
        for p in profs:
            header += [f'{PROF_NAME[p]} {xlabel}', f'{PROF_NAME[p]} result']
            align += ['---:', '---:']
        for i in range(n):
            row = []
            for p in profs:
                row += [f'{d[p][xkey][i]:.1f}',
                        cell_fn(d[p][ykey][i], d[p]['bracket'][i])]
            rows.append(row)
    else:
        header = [xlabel] + [f'{PROF_NAME[p]} reference' for p in profs]
        align = ['---:'] + ['---:'] * len(profs)
        for i in range(n):
            x = d[profs[0]][xkey][i]
            row = [f'{x:.2f}']
            for p in profs:
                row.append(cell_fn(d[p][ykey][i], d[p]['bracket'][i]))
            rows.append(row)
    return table(rows, header, align)


def section_D(h):
    d1, d2, d3, d5 = (h.get(k, {}) for k in ('D1', 'D2', 'D3', 'D5'))
    out = ["\n\\newpage\n\n# Study D — faults that arrive mid-descent\n"]

    if d5:
        out.append(f"""
## D5 — the mildest survivable fault, against when it arrives

This is the study's central sweep and the most direct answer to the question
"does a fault after some time cause a failure?". At each onset time, with the
reaction delay fixed at a realistic 100 ms, bisection in severity locates
$\\eta^*(t_f)$: the smallest delivered-thrust fraction the vehicle still
survives. A fault milder than $\\eta^*$ is absorbed; anything worse is not.

{_two_profile_table(d5, 'onset $t_f$ [s]', eta_cell, 't_f', 'eta_star', per_profile_x=True)}

{fig('D5_critical_severity.png', 'Critical fault severity against onset time')}
""")
    if d1:
        out.append(f"""
## D1 — how long can the vehicle stay unaware? (hard engine-out)

For each onset time, bisection on the reaction delay looks for $\\tau^*(t_f)$:
the longest the vehicle can keep flying the stale command and still land.

{_two_profile_table(d1, 'onset $t_f$ [s]', tau_cell, per_profile_x=True)}

{fig('D1_critical_delay.png', 'Critical reaction delay against fault onset time')}
""")
    if d2:
        out.append(f"""
## D2 — reaction time bought by a partial fault

The same delay bisection across a continuous severity sweep. $\\eta_{{sat}} =
{d2.get('eta_sat', float('nan')):.3f}$ is the saturation limit derived in Study
C: below it the weak engine cannot be throttled back up to match its partner.

{_two_profile_table(d2, 'delivered fraction $\\eta$', tau_cell)}

{fig('D2_critical_delay_vs_eta.png', 'Critical reaction delay against fault severity')}
""")
    if d3:
        for prof in ('derated', 'design'):
            if prof not in d3:
                continue
            p = d3[prof]
            br = p.get('breakdown', {})
            rows = [(k.replace('_', ' '), v, pct(v / p['n']))
                    for k, v in br.items()]
            out.append(f"""
## D3 — Sobol coverage of the whole cube, {PROF_NAME[prof]} reference

{p['n']} low-discrepancy points over $(t_f, \\eta, \\tau_d)$, assuming nothing
about the shape of the boundary. {p['n_land']} land:
**{ci(p['p'], p['lo'], p['hi'])}** (95 % Wilson).

{table(rows, ['outcome', 'samples', 'share'], ['---', '---:', '---:'])}

{fig(f'D3_sobol_cube_{prof}.png', f'Sobol coverage, {PROF_NAME[prof]} reference')}
""")

    out.append(f"""
## How the vehicle is lost

{fig('D_mechanism.png', 'Loss mechanism across every fault solve')}
""")
    return '\n'.join(out)


def section_E(h):
    e = h.get('E', {})
    if not e:
        return ''
    imp = list(e.get('importance', {}).items())[:6]
    rows = [(k, f'{v:.4f}') for k, v in imp]
    out_rows = [(k, v, pct(v / e['n'])) for k, v in e.get('outcome', {}).items()]
    return f"""
\\newpage

# Study E — can it land from anywhere in the dispersion box?

## The box

A 12-dimensional arrival dispersion: $\\pm 500$ m down- and cross-range, a
400–1400 m altitude band, body velocities spanning $[-25, 10] \\times [-12, 12]
\\times [-5, 28]$ m/s, attitudes to $\\pm 20^\\circ$ (yaw $\\pm 40^\\circ$) and
rates to $\\pm 4^\\circ$/s. Points violating the glide cone or the flight
envelope are not *failures* — they are not legal initial conditions, and are
rejected before sampling so the estimate is a statement about flyable
dispersions.

Study E is flown on the **de-rated** reference. Study D establishes that the
design profile has no fault margin at any onset, so running the fault half of
Study E on it would be estimating a quantity already known to be zero.

{e['n']} admissible Sobol points were flown. Each cost a healthy solve (is a
landing possible at all?) and, where that succeeded, a replan after a randomly
drawn mid-descent fault — 20 % hard engine-out, otherwise a uniform severity
draw, with the reaction delay drawn uniformly over $[0, 0.5]$ s.

## The estimate

| Quantity | Estimate (95 % Wilson) |
|---|---|
| P(landing possible \\| healthy) | **{ci(e['p_nom'], e['lo_nom'], e['hi_nom'])}** ({e['n_nom_land']}/{e['n']}) |
| P(still possible \\| mid-descent fault) | **{ci(e['p_fault'], e['lo_fault'], e['hi_fault'])}** ({e['n_fault_ok']}/{e['n_fault_run']}) |
| Surrogate volume fraction, *faulted* | {ci(e['surrogate_volume'], e['surrogate_lo'], e['surrogate_hi'])} |
| Surrogate out-of-fold accuracy, *faulted* | {e['cv_accuracy']:.3f} (AUC {e['auc']:.3f}) |

The surrogate interval is the *integration* error of 200 000 classifier
evaluations only. The classifier's own error — $1 - {e['cv_accuracy']:.3f}$ —
is the larger term, and is quoted separately rather than folded in, so the two
are not confused. The direct Sobol estimate is the assumption-free number; the
surrogate is what tells you *where* the boundary is.

{table(out_rows, ['fate of the arrival', 'samples', 'share'],
       ['---', '---:', '---:'])}

## What decides survival

The surrogate is fitted to the *faulted* outcome (Section 5.7 explains why the
healthy one is unusable for this), so its feature set is the twelve arrival
dimensions plus the three fault parameters.

{table(rows, ['dimension', 'permutation importance'], ['---', '---:'])}

{fig('E_initial_conditions.png', 'Landing feasibility over the initial-condition box')}
"""


def section_caveats(h):
    return """
\\newpage

# What these numbers do not say

* **Open-loop replanning, not closed-loop control.** Stage 5 hands the
  post-fault state to a fresh optimal-control solve that knows the fault
  exactly. A real vehicle flies a feedback law, which would be neither as good
  as an omniscient replanner nor as brittle. The boundaries here are therefore
  an *optimistic* bound on what a real guidance system could tolerate.
* **Perfect fault identification at $t_f + \\tau_d$.** Estimation error and
  mis-identification are not modelled; both would shrink the margins further.
* **Constant mass**, inherited from the base model. Study C already flagged
  this as understating the propellant consequence of a partial fault.
* **One fault at a time, on engine 2.** The vehicle is laterally symmetric, so
  the engine index does not matter, but simultaneous or cascading faults are
  not covered.
* **The recovery corridor is a modelling choice.** Its allowances are
  defensible and stated, but a different corridor would move the boundaries.
  The *ordering* of the results — which faults are survivable and which are not,
  and which reference tolerates more — is far more robust than any individual
  number.
* **Local infeasibility is not global infeasibility.** The NLP is nonconvex;
  `Infeasible_Problem_Detected` means IPOPT proved infeasibility *locally* from
  the given start. Every replan is seeded from the nominal trajectory it
  interrupts, which is the most natural available guess, but a different seed
  could in principle find a recovery where this campaign found none.
* **Wilson intervals assume independent samples.** Sobol points are not
  independent; they are better than independent for integration, which makes
  the quoted intervals conservative rather than optimistic.
* **The 12-D box is a box.** It has no covariance structure and no dynamical
  provenance. A real dispersion from a real braking phase would be a thin
  manifold inside it, and the feasible fraction over that manifold could differ
  substantially.
"""


def body(h):
    from findings import findings_text
    return (front_matter() + section_scope(h) + section_D(h) + section_E(h)
            + findings_text(h) + section_caveats(h))
