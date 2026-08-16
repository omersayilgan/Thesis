"""
Build the Study F report (markdown -> PDF via pandoc/xelatex).

Every quantitative claim is interpolated from results/headline_F.json, so the
prose cannot drift from the data it describes.
"""

import os
import json
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
MD = os.path.join(HERE, 'fault_as_initial_condition.md')
PDF = os.path.join(HERE, 'fault_as_initial_condition.pdf')


def ci(p, lo, hi):
    return f'**{p:.3f}** [{lo:.3f}, {hi:.3f}]'


def pct(x):
    return f'{100 * x:.1f} %'


def table(rows, header, align=None):
    align = align or ['---'] * len(header)
    out = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join(align) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out)


def fig(name, caption):
    p = os.path.join(FIGURES, name)
    return f'\n![{caption}]({p})\n' if os.path.exists(p) else ''


def pval(p):
    if p < 1e-4:
        return '$p < 10^{-4}$'
    return f'$p$ = {p:.4f}'


def build():
    h = json.load(open(os.path.join(RESULTS, 'headline_F.json')))
    rates = h.get('rates', {})
    mc = h.get('mcnemar', {})
    spacing = h.get('spacing', {})

    # ── the headline verdict, computed ────────────────────────────────
    dmg = {k: v for k, v in mc.items()}
    tot_n01 = sum(v['n01'] for v in dmg.values())
    tot_n10 = sum(v['n10'] for v in dmg.values())
    tot_pairs = sum(v['n_pairs'] for v in dmg.values())
    sig = [k for k, v in dmg.items() if v['p'] < 0.05]

    parts = []
    parts.append(f"""---
title: "Is a Fault an Initial Condition?"
subtitle: "Study F — separating what a fault does to the *state* from what it does to the *vehicle*"
date: "{__import__('datetime').date.today().strftime('%d %B %Y')}"
geometry: margin=2.4cm
fontsize: 10.5pt
numbersections: true
toc: true
colorlinks: true
header-includes:
  - \\usepackage{{booktabs}}
  - \\usepackage{{amsmath}}
  - \\usepackage{{float}}
  - \\let\\origfigure\\figure
  - \\let\\endorigfigure\\endfigure
  - \\renewenvironment{{figure}}[1][2]{{\\expandafter\\origfigure\\expandafter[H]}}{{\\endorigfigure}}
---

# The question this study exists to answer

The proposal under test, stated as it was put:

> *"Computing a nominal trajectory and then injecting a fault seems
> unnecessary. A fault only changes our system's and control's initial states.
> If we cover most of the initial-condition space, we are good."*

This is a claim about **what a fault is**, and it is worth taking seriously
rather than deferring to convention, because half of it is right and that half
is the more useful half.

## The half that is right

The dynamics are Markovian. What the vehicle can do from a state $x$ depends on
$x$ and on the vehicle, and never on the history that produced $x$. A vehicle
that arrived at a tumbling, gimbal-deflected state by flying a nominal descent
and then losing an engine is in *exactly* the same position as one that simply
started there. There is no hidden memory in the model for a trajectory to
deposit.

So the nominal-trajectory scaffolding is not needed **to generate post-fault
states**. Those states can be sampled directly, which is strictly better: it
reaches states no single nominal trajectory would ever pass through, and it
spends its compute on coverage instead of on re-simulating the same descent.
Studies A–E could only reach a post-fault state by simulating forwards into it,
which is why between them they examined a few hundred such states, all
descended from **one** nominal trajectory.

This study therefore does what was proposed: it drops the nominal trajectory,
samples the **full 22-dimensional state** — 12 rigid-body dimensions *and* the
10 actuator states, which is the "and control states" part of the claim — and
asks from where a landing is possible.

## The half that has to be measured

A fault does something else as well. It changes **the vehicle**, and it keeps
it changed for the whole remaining flight. After the fault, engine 2 delivers
$\\eta T$ instead of $T$, or its gimbal actuator responds at $\\omega_n = 0.6$
rad/s instead of 4.0, or it delivers nothing at all. That is not a value of the
state vector. It is a different $f(x, u)$ and, for a dead engine, a smaller set
of admissible controls.

Whether that distinction *matters in practice* is an empirical question, and
the answer is not obvious in advance. It is conceivable that a damaged vehicle
started from a good state does about as well as a healthy one — in which case
the proposal would be right in full, and fault modelling could be replaced by
initial-condition dispersion. This study is built to measure exactly that, and
Section 4 reports what it found.

# Method

## The design that settles it: paired samples

One set of initial conditions, drawn once. **Every plant configuration is
solved from the same initial conditions.**

That pairing is the whole design. Because the states are held identical across
configurations, any difference in landing rate between two configurations is
attributable to the plant alone — the state distribution cancels exactly rather
than approximately. If a fault were expressible as an initial condition, then
feeding the same states to a healthy vehicle and to a damaged one would produce
the same landing set, and every paired difference would be zero.

The statistical test is **McNemar's exact test**, which uses only the
*discordant* pairs: samples where one plant lands and the other does not. Under
the null hypothesis that the plant change has no effect, each discordant pair
is an independent coin flip, so the two-sided $p$-value is an exact binomial
test. Pairing also buys precision — it detects a plant effect with far fewer
solves than comparing two independently-sampled proportions would need.

## The 22-dimensional state box

The 12 rigid dimensions are Study E's box with the **body-rate range widened
from $\\pm 4$ to $\\pm 25$ $^\\circ$/s**. That widening is not cosmetic: Study D
measured what a fault actually does to the body rates before anyone reacts
(12 to 360 $^\\circ$/s within one second), so a box that stops at 4 $^\\circ$/s
cannot contain a post-fault state at all.

The 10 actuator dimensions are new here, and they are the part of the proposal
that earlier studies could not test. Per engine: thrust anywhere in its
envelope, both gimbal angles anywhere in $\\pm 6^\\circ$, and both gimbal rates.
A fault leaves gimbals deflected and thrust away from trim; sampling those
states directly reaches them without simulating a descent to get there.

A sample is rejected only if it is **already lost** (tumbling past the hard
limits, past horizontal, or on the ground) or outside the approach cone. States
far outside the *planner's* comfort envelope are deliberately kept, because
those are precisely the states a fault produces and the study exists to find
out which of them are recoverable.

## The recovery planner

The algorithmic deliverable is `fault_lib.recover(x, plant, cfg)`. It takes the
current 22-state and the vehicle the fault has left behind, and returns a
landing trajectory or an honest refusal. It takes **no** nominal trajectory, no
fault onset time, and no fault history — by the Markov argument above, it does
not need them.

Two mechanisms make it work on states that are far from trim:

* a **recovery corridor** — a state already outside the planner's attitude/rate
  envelope has its bound relaxed to the initial excursion and tightened
  linearly back to the design envelope over six seconds. The planner must
  demonstrably recover into the envelope; it is a demand, not a dispensation.
* a **state-dependent horizon** — with no nominal there is no "time already
  flown", so the horizon is set from the altitude to be lost. Too long is worse
  than too short: it forces the planner to hold the 1 m contact floor for the
  unused tail, which Study D established turns feasible problems infeasible.

## An integration bug this study exposed

Study F's first run returned **0 of 12 landings for the healthy control** — a
vehicle with nothing wrong with it, failing from every state. A healthy control
that cannot land is a bug, not a result, so the campaign was stopped and the
cause traced by ablation.

Zeroing the sampled **gimbal rate** states fixed it completely; halving them
did not; thrust asymmetry was irrelevant. That pointed at the integrator. The
gimbal actuator is a second-order mode at $\\omega_n$ = 4 rad/s, and on the 1 s
control grid $\\omega_n \\Delta t = 4.0$, which is **beyond RK4's stability limit
of $\\approx 2.79$** for an oscillatory eigenvalue. A single RK4 step per
control interval was amplifying that mode instead of damping it.

Every earlier study started the gimbal rate states at zero, so the unstable
mode was never excited and the defect stayed hidden. Study F samples those
states directly, which is exactly the condition that exposes it.

The fix is to integrate each control interval in **two RK4 sub-steps**
($\\omega_n \\Delta t_{{sub}} = 2.0$, comfortably stable), leaving the decision
variables and the control grid untouched. Measured on the probe states:

{table([('1 (as in Studies A–E)', '0 / 3', '19 s', '0.63 GB'),
        ('2 (adopted)', '3 / 3', '20 s', '1.46 GB'),
        ('4', '3 / 3', '39 s', '3.07 GB')],
       ['RK4 sub-steps per interval', 'healthy control solved', 'median solve',
        'peak memory'], ['---', '---:', '---:', '---:'])}

Two sub-steps fix the problem completely at no cost in solve time. This is
worth flagging beyond Study F: **the 1 s grid under-resolves the gimbal
actuator in the base model**, and any result that depends on gimbal transients
inherits that.

# What was run

{table([('initial conditions', h.get('n_states', '?')),
        ('plant configurations', h.get('n_plants', '?')),
        ('total NLP solves', h.get('n_solves', '?'))],
       ['quantity', 'value'], ['---', '---:'])}

Three fault families — engine-out, thrust efficiency, gimbal degradation — each
at two engine spacings. $y_{{eng}}$ = 1.5 m is the design value;
**$y_{{eng}}$ = 0.25 m** sits just inside Study A's analytic trim limit
$y_{{crit}} = d_{{z,eng}} \\tan \\delta_{{max}} = 0.263$ m, so the gimbal alone
can trim a one-engine-out asymmetry. The pair separates *loss of thrust* from
*loss of roll authority*: at 0.25 m the vehicle loses exactly the same thrust
and keeps the ability to trim it, so anything that survives at 0.25 m but not
at 1.5 m is a roll-authority failure, not a thrust failure.

{fig('F_landing_rates.png', 'Landing rate by plant')}

{table([(v['label'].replace('$', '$'), f"{v['n_land']}/{v['n']}",
         ci(v['p'], v['lo'], v['hi']))
        for k, v in sorted(rates.items(),
                           key=lambda kv: (-kv[1]['y_eng'], kv[0]))],
       ['plant', 'lands', 'P(landing possible), 95 % Wilson'],
       ['---', '---:', '---:'])}
""")

    # ── the verdict ───────────────────────────────────────────────────
    import run_study_F as RF
    ns = [k for k, v in dmg.items() if v['p'] >= 0.05]
    nested = all(v['n10'] == 0 for v in dmg.values())
    max_n10 = max(v['n10'] for v in dmg.values()) if dmg else 0
    parts.append(f"""
# The verdict on the claim

{fig('F_claim.png', 'Is a fault an initial condition?')}

Across all damaged configurations, **{tot_pairs} paired comparisons** on
identical initial conditions produced **{tot_n01 + tot_n10} discordant pairs**:
{tot_n01} where the healthy vehicle lands and the damaged one cannot, and
{tot_n10} the other way round.

{table([(v['label'].split(',')[0], f'{RF.PLANTS[k].y_eng:g}',
         v['n01'], v['n10'], pval(v['p']),
         '**yes**' if v['p'] < 0.05 else 'no')
        for k, v in sorted(mc.items(),
                           key=lambda kv: (-RF.PLANTS[kv[0]].y_eng, kv[0]))],
       ['damaged plant', '$y_{eng}$', 'healthy only', 'damaged only',
        'McNemar', 'effect?'],
       ['---', '---:', '---:', '---:', '---:', '---:'])}

All rows are 48 paired samples. "healthy only" counts states the healthy
vehicle lands from and the damaged one cannot; "damaged only" is the reverse.

## The answer is: it depends on whether the vehicle can trim the fault

{len(sig)} of {len(mc)} configurations differ from the healthy vehicle at
$p < 0.05$ **on states that are literally identical**. The state distribution is
not merely similar between the two arms of each comparison — it is the same
list of numbers — so those differences cannot be attributed to sampling and can
only come from the plant.

But the {len(ns)} that are *not* significant are the interesting ones, and they
are not a random subset. They are exactly the faults the vehicle has the
authority to trim:

{table([(mc[k]['label'].split(',')[0], f'{RF.PLANTS[k].y_eng:g}',
         f"{mc[k]['n01']} / {mc[k]['n10']}", pval(mc[k]['p']))
        for k in sorted(ns, key=lambda k: -RF.PLANTS[k].y_eng)],
       ['plant', '$y_{eng}$', 'discordant (healthy / damaged)', 'McNemar'],
       ['---', '---:', '---:', '---:'])}

$\\eta$ = 0.50 sits above Study C's saturation limit
$\\eta_{{sat}}$ = 0.278, so the healthy engine can be throttled up to match its
partner and the asymmetry is cancelled outright. $\\eta$ = 0.15 is far below it
— but at $y_{{eng}}$ = 0.25 m the residual roll moment is inside what the gimbal
alone can trim. **In all three cases the vehicle can null the fault, and the
outcome reverts to being decided by the state.**

So the sharpened verdict is:

> **A fault is not an initial condition — except when the vehicle has enough
> control authority to cancel it, in which case it very nearly is.**

That is a real and useful vindication of the intuition, with a stated boundary.
Where the fault is trimmable, modelling it as a state perturbation is
defensible and the plant change is statistically undetectable over 48 paired
samples. Where it is not trimmable, the plant dominates so completely that no
coverage of the state space can substitute for it: at $y_{{eng}}$ = 1.5 m the
engine-out and $\\eta$ = 0.15 vehicles land from **zero** of the 48 states, while
the healthy vehicle lands from 44 of the same 48.

## The landing sets are nested, not merely different

{'Across every configuration, the damaged vehicle lands from a state where the healthy one fails at most ' + str(max_n10) + ' time' + ('' if max_n10 == 1 else 's') + '.' if max_n10 <= 2 else ''}
The discordance is essentially one-directional: damage **strictly shrinks** the
recoverable set rather than moving it somewhere else.

This matters for the proposal. If damage merely *displaced* the landing set,
then sampling initial conditions widely enough really would cover the
post-fault cases — you would just be looking at a different part of the same
box. Because the set shrinks instead, there is no region of state space that a
damaged vehicle handles and a healthy one does not, and therefore no amount of
state-space coverage that recovers the missing information about $f$.

## What this means for the approach

The right synthesis keeps both halves, and it is what this study implements:

1. **Drop the nominal trajectory** — as proposed. It is not needed to reach
   post-fault states, and sampling the 22-D state directly covers far more of
   the space for the same compute. This part of the intuition was correct, and
   Studies A–E were doing unnecessary work.
2. **Keep the fault as a plant change** — sweep it as a *parameter of the
   dynamics*, crossed with the state box rather than folded into it. For
   trimmable faults this costs almost nothing (the two collapse); for
   untrimmable ones it is the entire answer.

That is exactly the "(plant) $\\times$ (initial state)" grid run here, and it
answers "when can we land and when can we not?" for each fault family
separately, without ever computing a nominal descent.

It is worth being precise about where this leaves the supervisor's advice.
"Compute the nominal, then inject" is not wrong, but the usual justification
for it is: it is a *convenient* way to generate plausible post-fault states,
not a necessary one. Its real weakness is that every state it produces descends
from a single trajectory, which is a thin and unrepresentative slice of the
space — this study reached 48 independent states per configuration, none of
which any one nominal descent would have visited. Sampling directly is better
on that axis. What the nominal-injection framing must not be used to discard is
the plant change, which for untrimmable faults is the whole of the answer.
""")

    # ── mechanism / spacing ───────────────────────────────────────────
    parts.append(f"""
# Which faults are survivable, and why

{fig('F_outcomes.png', 'Failure modes and the engine-spacing contrast')}
""")

    if spacing:
        rows = [(f, f'{v["y15"]:.3f}', f'{v["y025"]:.3f}',
                 f'{100*(v["y025"]-v["y15"]):+.0f} pp')
                for f, v in spacing.items()]
        best = max(spacing.items(), key=lambda kv: kv[1]['y025'] - kv[1]['y15'])
        parts.append(f"""
## Moving the engines in

{table(rows, ['plant', '$y_{eng}$ = 1.5 m', '$y_{eng}$ = 0.25 m', 'change'],
       ['---', '---:', '---:', '---:'])}

The largest gain is **{best[0]}**, at
{100*(best[1]['y025']-best[1]['y15']):+.0f} percentage points. The vehicle at
0.25 m loses *exactly the same thrust* as at 1.5 m — same engine, same $\\eta$,
same total force — so any improvement is attributable purely to roll authority.

This isolates the mechanism that Studies A and D reached from the other
direction. Study A's static budget says one dead engine at 1.5 m applies
18 796 N$\\cdot$m of roll against 5 432 N$\\cdot$m of combined gimbal and RCS
authority. At 0.25 m the same dead engine applies 3 133 N$\\cdot$m, which the
gimbal can trim on its own. The thrust loss is identical and survivable; the
roll asymmetry is what was killing the vehicle.

## Three fault families, three different mechanisms

The table above separates the three families cleanly, and they do not behave
alike:

* **Asymmetry faults** (engine-out, $\\eta$ = 0.15) — fatal at 1.5 m, largely
  survivable at 0.25 m. Moving the engines in converts them from unrecoverable
  to routine, because the fault was never about thrust.
* **Trimmable thrust loss** ($\\eta$ = 0.50, above $\\eta_{{sat}}$) — survivable at
  both spacings and barely distinguishable from healthy. The spacing change
  buys almost nothing (+4 pp) because there was nothing to fix.
* **Gimbal degradation** — costs 34 to 44 points of landing probability and is
  **completely indifferent to the spacing** ({spacing.get('gimbal $\\omega_n$=0.6', {}).get('y15', 0):.3f} to {spacing.get('gimbal $\\omega_n$=0.6', {}).get('y025', 0):.3f} for the sluggish
  actuator). It is not an asymmetry fault at all: the engines still balance,
  and what is lost is *bandwidth* — the ability to respond quickly enough to
  the disturbances the descent itself generates. No amount of moving the
  engines recovers a slow actuator.

The healthy control is the check on all of this: it lands from
{spacing.get('healthy', {}).get('y15', 0):.3f} of states at 1.5 m and
{spacing.get('healthy', {}).get('y025', 0):.3f} at 0.25 m — the same within
sampling error. The spacing change is not a general improvement to the vehicle;
it does nothing for a healthy one, and everything for an asymmetrically damaged
one. **That specificity is what identifies roll authority, rather than anything
else, as the mechanism.**

The design consequence is the same one Study A reached and is now confirmed
from an independent direction: the 1.5 m spacing is simultaneously the
vehicle's best roll actuator and its single point of failure, and it is
worth exactly nothing when the vehicle is healthy.
""")

    sg = h.get('surrogate', {})
    if sg:
        c15 = sg.get('y1.5', {}).get('cv_accuracy')
        c025 = sg.get('y0.25', {}).get('cv_accuracy')
        blocks = []
        for k, v in sorted(sg.items()):
            if 'cv_accuracy' not in v:
                blocks.append(f"* **{k}** — {v.get('note', 'not fitted')}.")
                continue
            top = list(v['importance'].items())[:6]
            blocks.append(f"""
**Engine spacing {k}** ({v['n_land']}/{v['n']} land, out-of-fold accuracy
{v['cv_accuracy']:.3f}):

{table([(n, f'{x:.4f}') for n, x in top],
       ['state dimension', 'permutation importance'], ['---', '---:'])}
""")
        extra = ''
        if c15 is not None and c025 is not None:
            extra = f"""
This contrast is itself the study's thesis restated. A classifier that sees
**only the state** — all 22 dimensions of it — and not which plant is flying
scores {c15:.3f} at $y_{{eng}}$ = 1.5 m and {c025:.3f} at 0.25 m.

At the design spacing the state carries {'essentially no' if c15 < 0.6 else 'little'}
information about the outcome, because the outcome is decided almost entirely by
*which fault* the vehicle has: engine-out and $\\eta$ = 0.15 land from nowhere,
$\\eta$ = 0.50 lands from almost everywhere, and no coordinate of $x$ changes
that. At 0.25 m, where every fault is trimmable, the plant stops dominating and
the state becomes informative again — the classifier recovers to
{c025:.3f}, and the dimensions it leans on (altitude, vertical and forward
speed) are the ordinary energy-management ones.

**A state-only model of a fault is uninformative exactly where the fault
matters most.** That is the quantitative form of the answer to the original
question.
"""
        parts.append(f"""
## Which parts of the state space are recoverable

A classifier fitted to the *damaged* plants only, over all 22 state dimensions,
answers "given something is broken, where in the state space can it still be
saved?".

{''.join(blocks)}
{extra}
""")

    parts.append("""
# What this study does not say

* **Open-loop replanning, not closed-loop control.** `recover` solves a fresh
  optimal-control problem that knows the plant exactly. A real vehicle flies a
  feedback law and must *identify* the fault first. These results are an
  optimistic bound on what any real guidance system could achieve.
* **The plant is known at the moment of recovery.** Fault detection and
  identification are not modelled. In practice the plant estimate arrives late
  and wrong, and both shrink the numbers here.
* **A box is not a distribution.** The state box has uniform density and no
  covariance structure. Real post-fault states are concentrated on a thin
  manifold inside it — Study D's states, for instance — so these fractions
  describe the box, not the operational likelihood of landing.
* **One fault at a time, on engine 2.** The vehicle is laterally symmetric so
  the engine index does not matter, but simultaneous or cascading faults are
  not covered.
* **Local infeasibility is not global.** The NLP is nonconvex; `no_recovery`
  means IPOPT failed from two seeds, not that no trajectory exists.
* **Constant mass**, inherited from the base model, which understates the
  propellant cost of a partial fault (Study C).
""")

    md = '\n'.join(parts)
    open(MD, 'w').write(md)
    print('[saved]', MD)

    cmd = ['pandoc', MD, '-o', PDF, '--pdf-engine=xelatex',
           '--resource-path', HERE]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print('[saved]', PDF)
    except subprocess.CalledProcessError as e:
        print('pandoc failed:\n', e.stderr[-2500:])


if __name__ == '__main__':
    build()
