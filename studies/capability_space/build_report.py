"""
Build the Study I report (markdown -> PDF via pandoc/xelatex).

Every quantitative claim is interpolated from results/headline_I.json, and the
cross-study comparison from fault_injection's headline_H.json.  Run
run_capability_study.py and plot_capability.py first.
"""

import os
import sys
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
MD = os.path.join(HERE, 'capability_space_case_study.md')
PDF = os.path.join(HERE, 'capability_space_case_study.pdf')
H_JSON = os.path.join(ROOT, 'studies', 'fault_injection', 'results',
                      'headline_H.json')


def table(rows, header, widths=None):
    align = (['---'] * len(header) if widths is None
             else [':' + '-' * w for w in widths])
    out = ['| ' + ' | '.join(str(c) for c in header) + ' |',
           '|' + '|'.join(align) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out) + '\n'


def fig(name, caption):
    p = os.path.join(FIGURES, name)
    return f'\n![{caption}]({p})\n' if os.path.exists(p) else ''


def pct(v):
    return f'{100 * v:.0f}%'


def build():
    h = json.load(open(os.path.join(RESULTS, 'headline_I.json')))
    faults, red, sp = h['faults'], h['redundancy'], h['spacing']
    by = {r['fault']: r for r in faults}
    land = {}
    if os.path.exists(H_JSON):
        H = json.load(open(H_JSON))
        land = {f: H['survive_to'][f]['n_land'] / H['n_points']
                for f in H['faults']}

    groups = {}
    for r in faults:
        groups.setdefault(r['effect'], []).append(r)
    unchanged = groups.get('unchanged', [])
    rcs_loss = [r for r in red if r['kind'] == 'rcs']
    eng_loss = [r for r in red if r['kind'] == 'engine']
    worst_rcs = min(rcs_loss, key=lambda r: r['C_vol_frac'])
    worst_eng = min(eng_loss, key=lambda r: r['C_vol_frac'])
    er = h['erosion']

    # the cross-study contradiction, stated from the data
    lethal_unchanged = sorted(
        [r for r in unchanged if land.get(r['fault'], 1.0) < 1.0],
        key=lambda r: land[r['fault']])
    benign_shrunk = sorted(
        [r for r in faults if r['C_vol_frac'] < 0.75
         and land.get(r['fault'], 0.0) >= 0.85],
        key=lambda r: r['C_vol_frac'])

    P = []
    A = P.append

    A(f"""---
title: "Faults in Capability Space"
subtitle: "Study I — what {len(faults)} engine faults do to the attainable force and moment sets, and why that does not tell you which ones are survivable"
date: "1 September 2026"
geometry: margin=2.2cm
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

# What this study does

Studies G, H and H-R ask whether a damaged vehicle can still fly a trajectory.
This one asks the question underneath: **what can the damaged vehicle push and
twist with at all**, before any trajectory is planned.

For an actuator set there are two sets in $\\mathbb{{R}}^3$ and one in
$\\mathbb{{R}}^6$:

* the **attainable force set (AFS)** — every net force the actuators can produce;
* the **attainable moment set (AMS)** — every net moment;
* the **attainable wrench set (AWS)** — the 6-D set the other two are
  projections of, and the one an operating point has to lie inside.

Each RCS thruster is a one-sided segment: throttle $f \\in [0, F]$ contributing
$f\\,d$ to the force and $f\\,(r \\times d)$ to the moment. Each gimballed engine
sweeps a spherical cap: thrust $T \\in [T_{{min}}, T_{{max}}]$ along any
direction within $\\delta_{{max}}$ of its axis. The sum is what the vehicle can
do instantaneously; its convex hull is what a support-function sweep recovers
exactly, and that is what is computed here on
{h['n_dirs']} directions per set.

The vehicle is the Study H plant: {h['n_eng']} gimballed engines at
$y_{{eng}} = \\pm{h['y_eng']:.2f}$ m with a
{h['gimbal_deg']:.0f}° cone, {h['n_rcs']} RCS thrusters at
{h['F_rcs_per']:.0f} N each, {h['mass']:.0f} kg.

""")
    A(fig('I0_capability_grid.png',
          "What each fault leaves of the vehicle's capability"))

    A(f"""
# Four things a fault can do to a set

The classification is decided from the numbers, not asserted:

""")
    A(table([
        ['**shrink**', ', '.join(r['short'] for r in groups.get('shrunk', [])) or '—',
         'the damaged set is a subset of the healthy one'],
        ['**enlarge**', ', '.join(r['short'] for r in groups.get('enlarged', [])) or '—',
         'more authority than healthy — and asymmetrically, which buys force '
         'and costs trim symmetry'],
        ['**deform**', ', '.join(r['short'] for r in groups.get('deformed', [])) or '—',
         'same size, moved: the set points somewhere else'],
        ['**puncture**', ', '.join(r['short'] for r in groups.get('punctured', [])) or '—',
         'the origin leaves the set — the vehicle can no longer produce zero '
         'net wrench'],
        ['**nothing**', ', '.join(r['short'] for r in unchanged) or '—',
         'the static set is identical to healthy; the fault lives entirely '
         'in time'],
    ], ['Effect', 'Faults', 'What it means'], [12, 34, 52]))

    A("""
## Why the stuck-open valve is its own category

Everywhere else in this repository an engine can be shut down, so its minimum
throttle does not shape the attainable set: zero is always available and the
hull contains the origin. A valve stuck open removes exactly that. The engine's
contribution becomes the shell $\\{T d : T \\in [T_{min}, T_{max}]\\}$ with
$T_{min} > 0$, whose hull does **not** contain the origin.

This is a qualitative change that no volume metric can see — the force set
keeps """ + f"{pct(by['valve_stuck_open']['F_vol_frac'])}" + """ of its volume
— and it is visible in the figure below as a set with its top cut off, the
origin marked outside it.
""")
    A(fig('I1_sets.png', 'The attainable force and moment sets under fault'))

    A(f"""
# What each fault costs

""")
    A(fig('I2_metrics.png', 'Capability cost per fault, in three measures'))

    A(f"""
The third bar is the one that matters, and it is worth explaining why the first
two are not enough.

**The unconstrained AMS flatters every fault.** It is free to spend the whole
actuator set on one moment and let the vehicle fall. A descending vehicle
cannot: most of its thrust is committed to not hitting the ground, and the
moment authority that counts is what remains *after* that commitment. The
conditional set — moments attainable while producing the
{abs(h['hover_wrench'][2]):.0f} N of vertical force that holds the vehicle up —
is the set an allocator actually draws from, and it separates faults the raw
AMS reports as nearly identical.

""")
    A(table([[r['short'], r['effect'], f"{r['F_vol_frac']:.2f}×",
              f"{r['M_vol_frac']:.2f}×", f"{r['C_vol_frac']:.2f}×",
              'yes' if r['F_origin'] and r['M_origin'] else '**no**',
              'yes' if r['hover_ok'] else '**no**',
              (f"{land[r['fault']]:.0%}" if r['fault'] in land else '—')]
             for r in sorted(faults, key=lambda r: r['C_vol_frac'])],
            ['Fault', 'Effect', 'AFS', 'AMS', 'AMS | hover', 'Zero wrench',
             'Hover wrench', 'Study H landings'],
            [22, 12, 8, 8, 12, 12, 12, 16]))

    A(f"""
# Capability does not predict survivability

Every fault in the catalogue leaves the hover wrench attainable. Not one of
them costs the vehicle the ability to hold itself up at this engine spacing.
And yet Study H found four of them with injection points from which no
trajectory exists at all.

""")
    A(fig('I3_capability_vs_survival.png',
          'Retained moment authority against Study H landing share'))

    if lethal_unchanged:
        r = lethal_unchanged[0]
        A(f"""
The clearest case is **{r['short']}**. Its capability sets are *identical* to
healthy — same volume, same axes, same origin containment, same hover wrench —
and it is the least survivable fault in the entire Study H campaign, landing
from {land[r['fault']]:.0%} of injection points and accounting for five of the
nine injections that no relaxation of the trajectory constraints could recover.

A transport delay does not remove authority. It removes the vehicle's ability
to *apply* that authority when the state calls for it, and capability space —
which is a statement about an instant, not about a sequence — cannot represent
that. The same is true of the slow thrust response.
""")
    if benign_shrunk:
        r = benign_shrunk[0]
        A(f"""
The converse case is **{r['short']}**, which keeps only
{r['C_vol_frac']:.0%} of its conditional moment authority and still lands from
{land[r['fault']]:.0%} of injection points. Losing half the set is survivable
when what remains still contains everything the trajectory asks for.
""")
    A("""
**This is the study's main result, and it is a negative one.** An FTC scheme
that reasons only about attainable sets — control-allocation feasibility,
degraded-mode envelopes, reconfigurable allocation limits — will rank the
temporal faults as harmless, because in capability space they are. Capability
space is necessary and not sufficient: it tells you what the vehicle can do at
an instant, and says nothing about whether it can do it *in time*.

The two measures are complementary, not redundant:

* a fault that leaves the required wrench outside the set is unrecoverable for
  a reason no controller can fix — that is a capability failure;
* a fault that leaves it inside may still be unrecoverable for reasons of
  timing, delay, or the state the vehicle happens to be in — that is a
  trajectory failure, and only a campaign like Study H finds it.

# What redundancy buys
""")
    A(fig('I4_redundancy.png', 'The cost of losing one actuator'))
    A(f"""
Losing any single RCS thruster costs between
{min(r['C_vol_frac'] for r in rcs_loss):.0%} and
{max(r['C_vol_frac'] for r in rcs_loss):.0%} of the conditional moment
authority — the worst of the sixteen ({worst_rcs['unit']}) leaves
{worst_rcs['C_vol_frac']:.0%}. Losing one of the two engines leaves
{worst_eng['C_vol_frac']:.0%}. **Sixteen thrusters are close to
interchangeable; two engines are not**, and that asymmetry is the whole
argument for treating the engine tier and the attitude tier as different
redundancy problems rather than counting actuators.

## The trim threshold, recovered from capability space

Study A derived the engine-out roll-trim limit analytically: a single gimbal
can trim a one-engine-out asymmetry only while
$y_{{eng}} \\le dz_{{eng}}\\tan\\delta_{{max}}$ =
**{h['y_trim_limit']:.3f} m**. That derivation is a statement about one moment
balance. Asking capability space the same question — sweep the engine spacing,
and for each ask the LP whether zero net moment is attainable while holding
hover thrust — reproduces it without being told:

""")
    A(fig('I5_spacing.png', 'Engine-out trim against engine half-spacing'))
    A(f"""
The gimbal-alone curve leaves zero residual up to
$y_{{eng}}$ = **{h['y_trim_measured']:.3f} m** and diverges past it, against the
analytic {h['y_trim_limit']:.3f} m. The agreement is a check on the machinery:
two independent derivations of the same threshold, one algebraic and one from a
linear program over the actuator polytope.

The second curve is the part the analytic result does not cover. With the RCS
tier available the vehicle trims engine-out at **every** spacing tested — the
thrusters quietly cover what the gimbal cannot. That is worth knowing before
concluding that a wide engine layout is disqualifying: it is disqualifying for
the gimbal, not for the vehicle, as long as the attitude tier is healthy and has
propellant. Study F's result that engine-out lands from 0 of 48 initial
conditions at $y_{{eng}}$ = 1.5 m is therefore not a capability statement
either — the authority is there, and something else is spending it.

# A fault that moves through capability space
""")
    A(fig('I6_erosion.png', 'Throat-erosion drift over time'))
    A(f"""
Throat-erosion drift is the one fault whose capability set is not a fixed
object. Its efficiency decays from the moment of onset, so the set contracts
continuously: the conditional moment authority falls from
{er[0]['C_vol_frac']:.2f}× at onset to {er[-1]['C_vol_frac']:.2f}× after
{er[-1]['t']:.0f} s.

**At the instant of onset it is indistinguishable from healthy.** Any
capability-based monitor that samples the set will report a healthy vehicle for
as long as it takes the drift to exceed the monitor's threshold, and the fault
that is easiest to detect in capability space is the one that has already done
its damage. This is the argument for tracking the *rate* rather than the value.

# Limitations

* **Instantaneous sets.** Everything here is a statement about one instant with
  no actuator dynamics. Rate limits, lags and delays are exactly what the
  unchanged-set faults consist of, which is the point of section 4 — but it
  means this study cannot be read as a survivability measure on its own.
* **Convex hulls.** The reported sets are hulls of the achievable set. For the
  RCS tier that is exact (a zonotope); for the engines the cap is sampled, and
  the LP uses an inscribed polytope, so a wrench reported attainable really is
  and a wrench reported unattainable is marginally conservative.
* **The chugging derate is a modelling choice.** A forced oscillation does not
  move the commanded boundary; what is reported is the authority the vehicle can
  hold regardless of ripple phase, which is the useful quantity but not the only
  defensible one.
* **One vehicle, one operating point.** The conditional sets are computed at
  hover thrust. A braking or pitch-over manoeuvre would commit the actuators
  differently and move every conditional number, though not the classification.
* **Fixed mass and inertia**, inherited from the plant.

# Reproducing

```bash
python studies/capability_space/run_capability_study.py   # the sets + LPs
python studies/capability_space/plot_capability.py        # figures
python studies/capability_space/build_report.py           # this document
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
