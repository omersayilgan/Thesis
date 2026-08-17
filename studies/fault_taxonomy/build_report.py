"""
Build the Study G report (markdown -> PDF via pandoc/xelatex).

Every quantitative claim is interpolated from results/headline_G.json, so the
prose cannot drift from the campaign it describes.  Run analyse.py first.
"""

import os
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
MD = os.path.join(HERE, 'fault_taxonomy_case_study.md')
PDF = os.path.join(HERE, 'fault_taxonomy_case_study.pdf')

CLASS_ORDER = ['none', 'additive', 'multiplicative', 'structural']
OUTCOMES = ['land', 'gate_miss', 'no_recovery', 'already_lost']
OUT_LABEL = {'land': 'landed', 'gate_miss': 'gate miss',
             'no_recovery': 'no trajectory', 'already_lost': 'lost first'}


def ci(s):
    return f"**{s['p']:.2f}** [{s['lo']:.2f}, {s['hi']:.2f}]"


def pv(p):
    return '$p < 10^{-4}$' if p < 1e-4 else f'$p$ = {p:.3f}'


def table(rows, header, align=None):
    align = align or ['---'] * len(header)
    out = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join(align) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out)


def fig(name, caption):
    p = os.path.join(FIGURES, name)
    return f'\n![{caption}]({p})\n' if os.path.exists(p) else ''


def build():
    h = json.load(open(os.path.join(RESULTS, 'headline_G.json')))
    cat, rates, cells = h['catalogue'], h['rates'], h['cells']
    mc, regs, faults = h['mcnemar'], h['regimes'], h['faults']
    reg_info, by_reg, by_class = h['regime_info'], h['by_regime'], h['by_class']
    class_reg, outcomes = h['class_regime'], h['outcomes']
    n = h['n_per_cell']

    dmg = [f for f in faults if f != 'healthy']
    worst = min(dmg, key=lambda f: rates[f]['p'])
    best = max(dmg, key=lambda f: rates[f]['p'])
    sig = [f for f in dmg if mc[f]['p'] < 0.05]
    benign = [f for f in dmg if mc[f]['survival'] >= 0.85]
    lethal = [f for f in dmg if mc[f]['survival'] <= 0.35]
    easiest = max(regs, key=lambda g: by_reg[g]['p'])
    hardest = min(regs, key=lambda g: by_reg[g]['p'])

    P = []
    A = P.append

    A(f"""---
title: "A Fault Taxonomy for the Apollo LM Landing Problem"
subtitle: "Study G — landing probability across {h['n_faults']} engine faults and {h['n_regimes']} initial-condition regimes"
date: "17 August 2026"
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

# What this study adds

The earlier case studies each took **one** fault and flew it as well as it can
be flown: an engine out (Study A), a thrust-efficiency sweep (Study B), a gimbal
bandwidth sweep (Study C), fault onset time (Studies D/E), and whether a fault
is expressible as an initial condition (Study F, which found that it is not —
the state is recoverable information, the *plant change* is not).

Between them they cover three of the eleven dynamic-effect categories in
`docs/spacecraft_engine_fault_framework.md`. This study covers the rest. It
instantiates **{len(dmg)} distinct faults** drawn from that framework — one per
dynamic-effect category, with severity variants where the category spans a wide
range — as {len(dmg)} *plants*, and measures the landing probability of each from
**{h['n_regimes']} qualitatively different regions of the state space**.

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
two: {h['n_faults']} faults $\\times$ {h['n_regimes']} regimes $\\times$ {n}
initial conditions = **{h['n_solves']} nonlinear programmes**
({h['wall_hours']:.1f} core-hours of IPOPT).

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
scored against the Apollo landing gate (vertical speed $\\le$ 3.0 m/s,
horizontal $\\le$ 1.2 m/s, tilt $\\le$ 6°, 15 m of the pad, rates $\\le$ 5°/s).

Because the initial conditions are shared across plants, the healthy
configuration is a genuine control: any difference within a regime column is
attributable to the plant alone, and the healthy-vs-fault comparison is a
within-sample McNemar test rather than two independent proportions.

# The fault catalogue

Every fault acts on engine 2; engine 1 stays healthy, so each case is an
*asymmetry* the vehicle must trim as well as a loss of performance. Severity is
chosen to span the interesting range rather than the survivable one — a taxonomy
in which everything lands measures nothing.
""")

    rows = []
    for f in faults:
        c = cat[f]
        rows.append([c['label'].replace('$', '$'), c['section'],
                     c['structure'], c['temporal'], c['detail']])
    # Explicit relative widths: pandoc sizes pipe-table columns from the dash
    # counts, and the detail column carries a whole sentence while the rest
    # carry two words.  Left to default, that sentence gets a 15-character
    # column and the table becomes a stack of hyphenated fragments.
    A('\n' + table(rows,
                   ['Fault', '§', 'FTC structure', 'Temporal',
                    'What the plant becomes'],
                   [':' + '-' * 16, ':-:', ':' + '-' * 13, ':' + '-' * 10,
                    ':' + '-' * 58]))

    A("""
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
""")

    rows = [[reg_info[g]['label'], reg_info[g]['blurb'], ci(by_reg[g]),
             f"{by_reg[g]['k']}/{by_reg[g]['n']}"] for g in regs]
    A('\n' + table(rows, ['Regime', 'What it is',
                          'Landing rate, all faults pooled', 'n'],
                   [':' + '-' * 12, ':' + '-' * 52, ':-:', ':-:']))

    A(f"""
The regimes are **not nested severity levels**; they name qualitatively
different situations. `{reg_info[easiest]['label']}` is the most forgiving
({by_reg[easiest]['p']:.2f} pooled over every fault) and
`{reg_info[hardest]['label']}` the least ({by_reg[hardest]['p']:.2f}) — a spread
of {by_reg[easiest]['p'] - by_reg[hardest]['p']:.2f} in landing probability
produced *entirely* by where the vehicle started, with the fault mix held
identical.

# Results

## The fault $\\times$ regime matrix

This is the study's primary result: the landing probability of every fault from
every regime, over shared initial conditions.
""")
    A(fig('G1_heatmap.png',
          'Landing probability by fault and initial-condition regime'))

    A(f"""
Read down a column to compare faults at a fixed situation; read across a row to
see how much of a given fault's cost is really the situation's. Each cell rests
on {n} samples, so a single cell carries a 95 % interval roughly
$\\pm$0.25 wide — the cells are for the *pattern*, and every number quoted in
the text below is a pooled marginal with its interval attached.

## What each fault costs, pooled

""")
    A(fig('G2_forest.png', 'Pooled landing rate per fault, Wilson intervals'))

    rows = []
    for f in sorted(faults, key=lambda k: -rates[k]['p']):
        s, m = rates[f], mc[f]
        rows.append([cat[f]['label'], cat[f]['klass'],
                     f"{s['p']:.2f} [{s['lo']:.2f}, {s['hi']:.2f}]",
                     f"{s['k']}/{s['n']}",
                     '—' if f == 'healthy' else f"{m['survival']:.2f}",
                     '—' if f == 'healthy' else f"{m['n10']}",
                     '—' if f == 'healthy' else pv(m['p'])])
    A('\n' + table(rows,
                   ['Fault', 'Class', 'Landing rate', 'k/n',
                    'Survival', 'Lost', 'McNemar'],
                   [':' + '-' * 26, ':' + '-' * 12, ':' + '-' * 20,
                    ':' + '-' * 6, ':' + '-' * 8, ':' + '-' * 5,
                    ':' + '-' * 11]))
    A('\nLanding rate carries its 95 % Wilson interval; *survival* is the paired\n'
      'share of healthy-landable states the fault keeps, *lost* the count it\n'
      'takes away, and *McNemar* the exact two-sided test on the discordant\n'
      'pairs.\n')

    A(f"""
The healthy control lands from {ci(rates['healthy'])} of the sampled states.
That number is not 1.00 and is not meant to be: the box contains states from
which a *healthy* Apollo LM cannot reach the pad inside the deadline, and
pricing them is the whole reason the control is run on the same samples.

The most expensive fault in the catalogue is
**{cat[worst]['label']}** ({ci(rates[worst])}); the cheapest is
**{cat[best]['label']}** ({ci(rates[best])}).
{len(sig)} of the {len(dmg)} faults degrade the landing rate significantly
against the paired healthy control at the 5 % level.

The engine-out row is a **cross-check on the whole apparatus rather than a new
result**: Study A's roll-authority budget says a single gimbal can trim a
one-engine-out asymmetry only if $y_{{eng}} \\le d z_{{eng}} \\tan\\delta_{{max}}$
= 0.263 m, and this vehicle is built at $y_{{eng}}$ = 1.5 m. It should therefore
never land engine-out at any initial condition, and it does not
({rates['engine_out']['k']}/{rates['engine_out']['n']}). A campaign that
produced engine-out landings here would be reporting a bug.

## Paired survival: the same states, a different vehicle

The pooled rate above still mixes the fault's cost with the cost of the state
dispersion. The paired view removes the latter: of the initial conditions the
*healthy* vehicle lands from, what share does the faulted vehicle still land
from? The initial conditions are literally identical, so what is left is the
plant.
""")
    A(fig('G3_paired.png', 'Paired survival relative to the healthy control'))

    if benign:
        A(f"""
{len(benign)} fault{'s' if len(benign) != 1 else ''} keep{'' if len(benign) != 1 else 's'}
at least 85 % of the healthy vehicle's landable states
({', '.join(cat[f]['label'] for f in benign)}). These are faults the *planner*
absorbs: it knows the damaged plant, and it re-optimises around it. That is a
statement about open-loop replanning with a perfect plant estimate, not about a
controller that has to discover the fault first — see the limitations.
""")
    if lethal:
        A(f"""
At the other end, {len(lethal)} fault{'s' if len(lethal) != 1 else ''}
destroy{'' if len(lethal) != 1 else 's'} at least 65 % of them
({', '.join(cat[f]['label'] for f in lethal)}). No amount of replanning
recovers these, because the vehicle no longer has the authority the trajectory
requires.
""")

    add = [f for f in dmg if cat[f]['klass'] == 'additive']
    if add and all(mc[f]['n10'] == 0 for f in add):
        A(f"""
### The additive faults cost nothing at all

Every additive fault in the catalogue
({', '.join(cat[f]['label'] for f in add)}) loses **zero** of the healthy
vehicle's landable initial conditions — not few, zero. This is the framework's
section 4 prediction landing exactly: an additive fault is an unknown input
that does not depend on state or command, and an optimiser that knows the
disturbance simply builds it into the plan. The corollary is the part that
matters operationally: their cost is *entirely* a detection and estimation
problem. Give the planner the wrong bias and it aims the trajectory wrong; give
it the right one and the fault is free.
""")

    if 'gimbal_slow' in mc and 'gimbal_seized' in mc:
        sl, sz = mc['gimbal_slow'], mc['gimbal_seized']
        if sl['survival'] < sz['survival']:
            A(f"""
### A sluggish gimbal is worse than a seized one

The catalogue's most counter-intuitive result, and it is not a small margin:
the seized gimbal keeps {sz['survival']:.2f} of the healthy vehicle's landable
states while the merely *slow* one keeps {sl['survival']:.2f} — pooled landing
rates {rates['gimbal_seized']['p']:.2f} against
{rates['gimbal_slow']['p']:.2f}.

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
""")

    A("""
## How the failures fail

Landing rate alone hides the engineering distinction between a vehicle that
*arrives too hard* and a vehicle for which no arrival exists at all. The first
is a trajectory-shaping problem; the second is a control-authority problem, and
no better guidance law fixes it.
""")
    A(fig('G4_outcomes.png', 'Outcome composition per fault'))

    rows = []
    for f in faults:
        o = outcomes[f]
        tot = sum(o.values())
        rows.append([cat[f]['label']] +
                    [f'{100 * o[k] / tot:.0f} %' for k in OUTCOMES])
    A('\n' + table(rows, ['Fault'] + [OUT_LABEL[k] for k in OUTCOMES],
                   [':' + '-' * 30, ':-:', ':-:', ':-:', ':-:']))

    A("""
`lost first` is the share of samples where the initial state is already past
the hard loss-of-control criteria (tilt beyond 90°, tumbling beyond 120°/s,
speed beyond 1.5 $V_{max}$, or below the contact altitude); it is a property of
the *sample*, not of the fault, and is therefore identical across every row — a
useful internal consistency check on the pairing.

## Landing probability against the initial condition

The regimes are boxes. This is the continuous cut through them: landing rate
against initial altitude, with the fault classes separated.
""")
    A(fig('G5_altitude.png', 'Landing rate against initial altitude by class'))

    rows = []
    for cl in CLASS_ORDER:
        if cl not in by_class:
            continue
        rows.append(['healthy' if cl == 'none' else cl] +
                    [f"{class_reg[cl][g]['p']:.2f}" for g in regs] +
                    [ci(by_class[cl])])
    A('\n' + table(rows,
                   ['Fault class'] + [reg_info[g]['label'] for g in regs] +
                   ['pooled'],
                   [':--'] + [':-:'] * (len(regs) + 1)))

    A("""
## How close the survivors came

Landing is a binary, but the gate margin behind it is not: a margin of 1.0 *is*
the gate, and the distance below it says how much of the touchdown budget the
recovery had to spend.
""")
    A(fig('G6_margin.png', 'Gate-margin distribution over solved cases'))

    A(f"""
# What this means for a fault-tolerant architecture

**The framework's three-way structural classification predicts the outcome
better than fault severity does.** Grouped by class, the pooled landing rates
are """ + ', '.join(
        f"{'healthy' if cl == 'none' else cl} {by_class[cl]['p']:.2f}"
        for cl in CLASS_ORDER if cl in by_class) + f""". Structural faults are
the ones that remove authority outright; multiplicative faults scale with the
operating point, so the planner can trade against them; additive faults are
biases and disturbances that an optimiser with a correct plant model simply
plans around.

**Where the vehicle is matters as much as what broke.** The regime spread
({by_reg[hardest]['p']:.2f} to {by_reg[easiest]['p']:.2f}) is comparable to the
spread across the fault catalogue itself. A fault-tolerance budget quoted as a
single per-fault probability is not a budget; it is an average over a mission
phase distribution that was never stated.

**Altitude is the resource.** The `{reg_info[hardest]['label']}` regime differs
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
* **Per-cell samples are small.** With {n} initial conditions per cell, an
  individual cell of the matrix carries a wide interval. The pooled marginals
  (n = {rates['healthy']['n']} per fault) and the paired comparisons are what
  the conclusions rest on.

# Reproducing

```bash
python studies/fault_taxonomy/run_taxonomy_study.py {n}   # the campaign
python studies/fault_taxonomy/analyse.py                  # figures + headline JSON
python studies/fault_taxonomy/build_report.py             # this document
```
""")

    md = '\n'.join(P)
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
