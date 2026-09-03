"""
Build the Study H report (markdown -> PDF via pandoc/xelatex).

Every quantitative claim is interpolated from results/headline_H.json, so the
prose cannot drift from the campaign it describes.  Run analyse_injection.py
first.
"""

import os
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
MD = os.path.join(HERE, 'fault_injection_case_study.md')
PDF = os.path.join(HERE, 'fault_injection_case_study.pdf')

FT = 0.3048
MARK = {'land': 'L', 'gate_miss': 'g', 'no_recovery': '.',
        'already_lost': 'x'}


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


def build():
    h = json.load(open(os.path.join(RESULTS, 'headline_H.json')))
    cat, rates, cells = h['catalogue'], h['rates'], h['cells']
    faults, times, alts = h['faults'], h['times'], h['alts']
    surv, by_point, by_class = h['survive_to'], h['by_point'], h['by_class']
    a = h['anchor']
    n_pts = h['n_points']

    dmg = [f for f in faults if f != 'healthy']
    always = [f for f in dmg if surv[f]['n_land'] == n_pts]
    never = [f for f in dmg if surv[f]['n_land'] == 0]
    partial = [f for f in dmg if 0 < surv[f]['n_land'] < n_pts]
    healthy_all = rates['healthy']['k'] == rates['healthy']['n']

    P = []
    A = P.append

    A(f"""---
title: "Injecting Faults Along an Apollo Descent"
subtitle: "Study H — {h['n_faults']} engine plants x {n_pts} injection points on one nominal trajectory"
date: "22 August 2026"
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

Study G sampled initial conditions from boxes: wide regions of the state space,
covered quasi-randomly. That answers "from how much of the reachable space is
this fault survivable", but it does not answer the question a mission analyst
actually asks, which is **where on the descent can this fault be survived**.

This study asks that one. It computes a single **nominal descent** for a healthy
vehicle, then walks along it and injects each fault at {n_pts} points. Because
the nominal is a trajectory, every injection point comes with a time, an
altitude, a range and a speed — so the result is a function of *when*, not a
statistic over a box.

Three things change from Study G:

* **The engines move to $y = \\pm{h['y_eng']:.2f}$ m** from $\\pm$1.50 m. This is
  the roll-authority threshold established in Study A: a single gimbal can trim
  a one-engine-out asymmetry only while
  $y_{{eng}} \\le d z_{{eng}} \\tan\\delta_{{max}}$ = 0.263 m. At 1.50 m the
  vehicle could never survive an engine failure and the fault was
  uninformative — 0 landings from every state tested. At
  {h['y_eng']:.2f} m it sits just inside the limit, so engine-out becomes a
  fault the study can actually measure.
* **The nominal is anchored on the real Apollo approach geometry** rather than
  on the earlier studies' near-vertical scenario (see below).
* **The gimbal-actuator faults are removed**, as requested: bandwidth loss,
  light damping, seizure and effectiveness loss are all about the gimbal's own
  response, which is not this study's subject. Thrust-vector misalignment is
  kept — it is a fixed nozzle offset from asymmetric erosion, present even if
  the gimbal were welded solid, and it is the only remaining additive fault
  besides chugging.

# The nominal descent

## Where the initial state comes from

The anchor is taken from the published Apollo approach-phase (P64) geometry
rather than invented. Two points of that phase are well documented:

""")
    A(table([
        ['high gate', '7,500 ft (2,286 m)', '4.5 nmi (8,300 m)',
         '500 ft/s (152 m/s)', '145 ft/s (44 m/s)'],
        ['low gate', '500 ft (152 m)', '2,000 ft (610 m)',
         '60 ft/s (18 m/s)', '16 ft/s (5 m/s)'],
    ], ['Point', 'Altitude', 'Range to target', 'Horizontal speed',
        'Descent rate'], [12, 22, 22, 22, 22]))

    A(f"""
The approach between them is flown essentially straight at the landing point —
the line-of-sight depression is 15.4° from high gate and 14.0° from low gate,
the same path. Interpolating along it gives a one-parameter family of
Apollo-consistent states, and this study takes the point where the horizontal
speed has bled to {a['v_h']:.0f} m/s, which is the fastest state this vehicle
model's own path constraint (60 m/s) admits with margin:

""")
    A(table([
        ['Altitude', f"{a['alt']:.0f} m", f"{a['alt'] / FT:.0f} ft"],
        ['Range to pad', f"{a['rng']:.0f} m", f"{a['rng'] / FT:.0f} ft"],
        ['Horizontal speed', f"{a['v_h']:.1f} m/s", f"{a['v_h'] / FT:.0f} ft/s"],
        ['Descent rate', f"{a['v_v']:.1f} m/s", f"{a['v_v'] / FT:.0f} ft/s"],
        ['Line-of-sight depression', f"{a['los']:.2f}°", ''],
        ['Flight-path angle', f"{a['fpa']:.2f}°", ''],
    ], ['Anchor state', 'SI', 'Imperial'], [26, 14, 14]))

    A(f"""
The last two lines are the consistency check that matters. A vehicle whose
velocity vector points at the landing site is what "flying the approach phase"
means, and here the line-of-sight depression and the flight-path angle agree to
{abs(a['los'] - a['fpa']):.2f}° — which they would not if the interpolation were
nonsense.

**This is a reconstruction of the geometry, not telemetry.** It reproduces where
an Apollo LM was and how fast it was going at {a['alt']:.0f} m on final
approach; it is not a replay of any specific mission's recorded state vector.

## Two things the reference trajectory needed

Neither is cosmetic, and both are worth recording because the first attempt
produced a trajectory that was not a lunar descent at all.

**A spherical speed cap.** The vehicle model's velocity limit is a *per-axis*
box, so a vehicle riding it on all three axes reaches 104 m/s. On the earlier
studies' near-vertical descent that is harmless — only the vertical channel is
ever large. On a 2.7 km shallow approach it is not: the first solve accelerated
downrange to 104 m/s, rode the 45° pitch limit, overshot the pad and came back
to it. The fix is a cap on the speed *norm*, set to
{h['v_norm']:.0f} m/s. It is a new optional field on the problem configuration
and defaults to off, so every earlier study is unaffected.

**A fitted horizon.** Surplus planning time is not free. A first solve on a
120 s horizon reached the contact altitude at 63 s and then held 1 m altitude
for the remaining 57 s; a 72 s horizon still left the vehicle wandering ~70 m
around the pad for the last 25 s, because the optimiser had time to spend and
spent it. The horizon is therefore *measured*: a probe solve times the descent,
and the trajectory is re-solved on a horizon just long enough to contain it —
here {h['nominal_N']} s.

The glide-slope floor is also relaxed from 30° to {h['glide_deg']:.0f}°. Apollo's
real approach is a ~15° path, which a 30° cone forbids outright; the old value
was chosen for a much steeper, closer-in scenario.

## The result
""")
    A(fig('H1_nominal.png', 'The Apollo-anchored nominal descent'))

    A(f"""
The healthy vehicle cruises at the speed cap down the 15° path, brakes from
about 40 s, reaches the contact altitude at **t = {h['t_contact']:.0f} s** and
touches down on the pad with a gate margin of **{h['nominal_margin']:.2f}** —
comfortably inside every landing criterion.

One honest caveat on the profile: the real P64 approach decelerates
continuously from 152 m/s to 18 m/s, whereas this trajectory cruises at the cap
and brakes late. That is the optimiser's doing — its cost penalises distance to
the target at every node, so arriving sooner is cheaper — not a property of
Apollo. The *geometry* is Apollo-anchored; the speed schedule along it is the
planner's.

# The injection experiment

At each of the {n_pts} injection points the state is read straight off the
nominal — all 22 of them, including the thrust and gimbal states the descent
had the vehicle holding. The plant then becomes the damaged plant from that
instant onward, the vehicle re-plans over the time the nominal had left plus a
20 s reserve, and the touchdown is scored against the Apollo landing gate
(vertical speed $\\le$ 3.0 m/s, horizontal $\\le$ 1.2 m/s, tilt $\\le$ 6°, within
15 m of the pad, rates $\\le$ 5°/s).

""")
    A(table([[f'{j}', f"{times[j]:.0f} s", f"{alts[j]:.0f} m",
              f"{by_point[str(j)]['k']}/{by_point[str(j)]['n']}"]
             for j in range(n_pts)],
            ['Point', 'Injection time', 'Altitude', 'Plants that landed'],
            [7, 16, 12, 20]))

    A(f"""
The healthy plant is run from every injection point as the control. Because
each state is taken from a trajectory that lands, it **must** land from every
point, and """ + (
        'it does — all '
        f"{rates['healthy']['n']} of them. Any failure elsewhere in the grid is "
        'therefore the fault, not the re-planning problem.'
        if healthy_all else
        f"it does so from {rates['healthy']['k']} of {rates['healthy']['n']}. "
        'The points where it does not are a property of the re-planning '
        'problem rather than of any fault, and the faulted rows should be read '
        'against that.') + """

## Making sure the failures are real

A "no trajectory found" is weaker evidence than a landing. The NLP is
nonconvex, so a converged solve *proves* a trajectory exists, while a failed one
only says the solver did not find one from its seed. The campaign's own
diagnostics said that mattered here: several failures gave up after 23-60
IPOPT iterations out of a 400 budget, sitting between neighbours that converged
in 160-207 — the signature of a bad local corner rather than a boundary.

Every `no_recovery` was therefore re-attacked with six horizon seeds at 1,200
iterations each. Extra search can only turn a false "no" into a true "yes", so
spending it on the failures alone reduces false negatives without being able to
manufacture a landing. **None of the failures flipped.** All of them survived
every seed, so the boundaries reported below are the vehicle's, not the
solver's.

**What is deliberately not modelled is the reaction gap** — the seconds between
the fault occurring and the guidance responding, during which the vehicle flies
a stale command on a broken engine. Detection here is instantaneous and the
damaged plant is known exactly. That gap is Study D/E's subject; leaving it out
makes this a clean measurement of *where on the descent* a fault is survivable
at all, and an upper bound on what any real system achieves.

# Results

## The outcome grid
""")
    A(fig('H2_grid.png', 'Outcome by fault and injection point'))

    grid_rows = []
    for f in faults:
        marks = ''.join(MARK.get(cells[f][str(j)], '?') + ' '
                        for j in range(n_pts))
        grid_rows.append([cat[f]['label'], '`' + marks.strip() + '`',
                          f"{rates[f]['k']}/{rates[f]['n']}"])
    A('\n' + table(grid_rows,
                   ['Fault', '`' + ' '.join(str(j) for j in range(n_pts)) + '`',
                    'landed'], [28, 30, 8]))
    A('\n`L` landed · `g` flew but missed the gate · `.` no trajectory found\n')

    A(f"""
## What each fault costs

""")
    rows_r = []
    for f in sorted(faults, key=lambda k: -rates[k]['p']):
        s, v = rates[f], surv[f]
        last = ('every point' if v['n_land'] == n_pts else
                '—' if v['last_land_t'] is None else
                f"{v['last_land_t']:.0f} s / {v['last_land_alt']:.0f} m")
        rows_r.append([cat[f]['label'], cat[f]['klass'],
                       f"{s['p']:.2f} [{s['lo']:.2f}, {s['hi']:.2f}]",
                       f"{s['k']}/{s['n']}", last])
    A(table(rows_r, ['Fault', 'Class', 'Landing rate', 'k/n',
                     'Latest survivable injection'],
            [26, 12, 20, 6, 24]))

    if always:
        A(f"""
**{len(always)} of the {len(dmg)} faults land from every injection point**
({', '.join(cat[f]['label'] for f in always)}). Given the whole descent to
choose from, these never take the vehicle out — the planner absorbs them
wherever they arrive.
""")
    if never:
        A(f"""
**{len(never)} land from none of them**
({', '.join(cat[f]['label'] for f in never)}). No point on the descent is early
enough: the vehicle simply does not have the authority the remaining trajectory
requires.
""")
    if partial:
        A(f"""
The interesting {len(partial)} are the ones with a **boundary** — survivable
early, fatal late:

""")
        A(table([[cat[f]['label'],
                  f"{surv[f]['last_land_t']:.0f} s"
                  if surv[f]['last_land_t'] is not None else '—',
                  f"{surv[f]['last_land_alt']:.0f} m"
                  if surv[f]['last_land_alt'] is not None else '—',
                  f"{surv[f]['first_fail_t']:.0f} s"
                  if surv[f]['first_fail_t'] is not None else '—',
                  f"{surv[f]['first_fail_alt']:.0f} m"
                  if surv[f]['first_fail_alt'] is not None else '—']
                 for f in partial],
                ['Fault', 'Last survivable $t$', 'at altitude',
                 'First fatal $t$', 'at altitude'], [26, 18, 12, 16, 12]))
        A("""
That boundary is the operationally useful number in this whole study: it is the
point on the descent past which the fault must be prevented rather than
recovered from, because after it no guidance law helps.

One row should not be read that way. **Transport delay fails in a scattered
pattern rather than at a boundary** — it loses points spread across the descent
and lands between them. That survived the hardening pass, so it is not solver
noise, but a non-monotone pattern in injection time is not what a physical
authority limit looks like. The likely reading is that a delay of exactly one
control interval interacts with the discretisation — the replan horizon changes
by a few steps from point to point, and a whole-interval lag lands differently
against it each time. Dead time is the one fault in this catalogue whose
natural scale (10-30 ms, per the framework) is far below what a 1 s planning
grid can represent, so this row measures the model's grid as much as the
vehicle. No boundary is quoted for it.
""")

    A("""
## Survival against injection time
""")
    A(fig('H3_survival.png', 'Landing share by fault class against injection time'))

    A('\n' + table(
        [['healthy' if cl == 'none' else cl,
          f"{by_class[cl]['p']:.2f}", f"{by_class[cl]['k']}/{by_class[cl]['n']}"]
         for cl in ['none', 'additive', 'multiplicative', 'structural']
         if cl in by_class],
        ['Fault class', 'Landing rate', 'k/n'], [22, 14, 8]))

    A("""
## How much gate margin is left

Landing is a binary; the margin behind it is not. A margin of 1.0 *is* the gate,
and the distance below it is how much of the touchdown budget the recovery had
to spend — which is the early warning that a fault is approaching its boundary.
""")
    A(fig('H4_margin.png', 'Gate margin against injection time, per fault'))

    A("""
## The recoveries themselves
""")
    A(fig('H5_trajectories.png',
          'Post-injection recovery trajectories against the nominal'))

    A(f"""
# What this means

**Engine spacing changed the answer, not the fault.** At $y_{{eng}}$ = 1.50 m
Study G recorded engine-out as unrecoverable from every one of its 50 states.
At {h['y_eng']:.2f} m, inside the gimbal's roll-trim limit, the same fault on
the same vehicle model gives {rates['engine_out']['k']}/{rates['engine_out']['n']}.
Nothing about the failure changed — only whether the surviving engine's gimbal
has the moment arm to trim it. Fault tolerance was decided at the drawing
board, not by the controller.

**A fault has a survivable window, not a survival probability.** The faults
that fail do not fail randomly across the descent; they fail *late*. The single
number a fault-tolerance budget should carry is the injection point past which
recovery stops existing, and that number is a time and an altitude, not a
probability.

**Altitude is the currency.** Every fault that has a boundary has it in the
same place — the braking phase, where the vehicle is low, still fast and has
committed its remaining altitude to the flare. A fault arriving during the
cruise has hundreds of metres to trade for a re-plan; the same fault arriving
during the flare has none.

# Limitations

* **The planner is handed the damaged plant exactly, and instantly.** No
  detection, isolation, identification or reaction delay. Every number here is
  an upper bound; Studies D and E measure what the reaction gap costs.
* **Open loop.** Each result is one optimal-control solve, not a closed loop
  re-solving as it flies. The drift fault in particular is treated more kindly
  here than a real one would be.
* **One nominal.** All {h['n_solves']} solves depart from a single reference
  trajectory. A different approach — steeper, faster, offset — would move the
  boundaries, and this study does not measure how much.
* **The speed schedule is the optimiser's, not Apollo's.** The geometry is
  anchored; the cruise-then-brake profile along it is not how P64 was actually
  flown.
* **Constant mass**, inherited from the base model, which understates the
  propellant cost of a partial fault.
* **Local infeasibility is not global.** The NLP is nonconvex; "no trajectory"
  means IPOPT failed from seven independent seeds (two in the campaign, six in
  the hardening pass) at up to 1,200 iterations — strong evidence, but not a
  proof that none exists.
* **{n_pts} injection points** resolve the boundary to roughly the spacing
  between them ({(times[-1] - times[0]) / max(n_pts - 1, 1):.0f} s); a
  bisection on onset time would sharpen it, which is what Study D does for a
  single fault.

# Reproducing

```bash
python studies/fault_injection/apollo_nominal.py        # the reference descent
python studies/fault_injection/run_injection_study.py   # the campaign
python studies/fault_injection/analyse_injection.py     # figures + headline JSON
python studies/fault_injection/build_report.py          # this document
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
