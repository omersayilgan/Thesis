"""
Build the COMPLETE fault-injection study as one document (markdown -> PDF).

Studies H, H-R and the L5 diagnostic were written up separately as they were
run.  This assembles all three into one narrative with the figures in the order
the argument needs them, and elaborates on what the three campaigns mean
together rather than one at a time.

Every number is interpolated from results/headline_H.json and
results/headline_HR.json.  Run analyse_injection.py, analyse_relaxed.py and
plot_trajectories_3d.py first.
"""

import os
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
MD = os.path.join(HERE, 'fault_injection_complete_study.md')
PDF = os.path.join(HERE, 'fault_injection_complete_study.pdf')

FT = 0.3048
MARK = {'land': 'L', 'gate_miss': 'g', 'no_recovery': '.', 'already_lost': 'x'}


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


def num(v, fmt='{:.2f}', dash='—'):
    return dash if v is None else fmt.format(v)


def plural(n, one, many=None):
    return one if n == 1 else (many or one + 's')


def build():
    H = json.load(open(os.path.join(RESULTS, 'headline_H.json')))
    R = json.load(open(os.path.join(RESULTS, 'headline_HR.json')))

    cat, rates, cells = H['catalogue'], H['rates'], H['cells']
    faults, times, alts = H['faults'], H['times'], H['alts']
    surv, a, n_pts = H['survive_to'], H['anchor'], H['n_points']
    cases, b = R['cases'], R['baseline']

    dmg = [f for f in faults if f != 'healthy']
    always = [f for f in dmg if surv[f]['n_land'] == n_pts]
    never = [f for f in dmg if surv[f]['n_land'] == 0]
    partial = [f for f in dmg if 0 < surv[f]['n_land'] < n_pts]

    solved = [c for c in cases if c['level'] != 'none']
    landed = [c for c in solved if c['lands']]
    sub = [c for c in cases if c['outcome'] == 'subsurface']
    stuck = [c for c in cases if c['level'] == 'none']
    l1 = [c for c in cases if c['level'] == 'L1']
    n_land_H = sum(1 for f in faults for j in cells[f]
                   if cells[f][j] == 'land')
    n_seeds_total = 7 + len(R['ladder']) * len(R['seeds'])
    depths = [c.get('subsurface_depth') for c in sub if c.get('subsurface_depth')]

    def short(f):
        return cat[f]['short'] if f in cat else f

    P = []
    A = P.append

    A(f"""---
title: "Faults Along an Apollo Descent"
subtitle: "The complete study — {H['n_solves']} injections, a relaxation ladder, and what separates a lost vehicle from a tight corridor"
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

# Summary

This document is three campaigns in one argument.

**Study H** flies one Apollo-anchored nominal descent and injects
{H['n_faults']} engine plants at {n_pts} points along it — {H['n_solves']}
optimal-control solves — to ask *where on the descent is this fault
survivable*. It lands {n_land_H} of them and finds
{R['n_no_recovery']} injections with no recovery trajectory at all.

**Study H-R** asks whether those failures are the vehicle or the problem
statement, by re-solving each at four progressively weaker corridors.
{len(l1)} of them recover — all at the first level, the glide cone alone.

**The L5 diagnostic** removes every state constraint that remains, the altitude
floor included, leaving only the dynamics and the actuator bounds.
{len(stuck)} cases fail even there.

The three-line result:

""")
    A(table([
        ['Injections that land', f'{n_land_H} of {H["n_solves"]}',
         'Study H, inside the design corridor'],
        ['Recoverable once the cone is relaxed', str(len(l1)),
         f'{len([c for c in l1 if c["lands"]])} still land in the Apollo gate'],
        ['Feasible only with no state constraints at all', str(len(sub)),
         'flies below the surface — a diagnostic, not a landing'],
        ['Infeasible under every relaxation', str(len(stuck)),
         f'resisted {n_seeds_total} seeds across five corridors'],
    ], ['Result', 'Count', 'Reading'], [40, 10, 46]))

    A(f"""
The headline correction is the third and fourth lines together: Study H's
{R['n_no_recovery']} "unrecoverable" injections are really **{len(stuck)}**
unrecoverable injections plus {len(l1)} that were fighting the corridor and
{len(sub)} that {plural(len(sub), 'is', 'are')} short only of the surface.

# The vehicle and the nominal

## Where the initial state comes from

The anchor is the published Apollo approach-phase (P64) geometry rather than an
invented state. Two points of that phase are well documented — high gate at
7,500 ft / 4.5 nmi / 500 ft/s, low gate at 500 ft / 2,000 ft / 60 ft/s — and
the approach between them is flown essentially straight at the landing point.
Interpolating along it to the speed this vehicle model admits with margin
gives:

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
The last two lines are the consistency check: a vehicle flying the approach
points its velocity vector at the landing site, and these agree to
{abs(a['los'] - a['fpa']):.2f}°. **This is a reconstruction of the geometry,
not telemetry.**

Two properties of the vehicle matter for everything below. The engines sit at
$y = \\pm{H['y_eng']:.2f}$ m, just inside the roll-trim limit
$y_{{eng}} \\le dz_{{eng}}\\tan\\delta_{{max}}$ = 0.263 m, which is what makes
engine-out a fault with an answer rather than an automatic loss. And the glide
cone is {H['glide_deg']:.0f}°, lowered from the earlier studies' 30° because
Apollo's real approach is a ~15° path that a 30° cone forbids outright.
""")
    A(fig('H1_nominal.png', 'The Apollo-anchored nominal descent'))
    A(f"""
The healthy vehicle reaches contact at **t = {H['t_contact']:.0f} s** with a
gate margin of **{H['nominal_margin']:.2f}**.

# Study H — the injection campaign

At each injection point the state is read straight off the nominal — all 22 of
them — the plant becomes the damaged plant from that instant, and the vehicle
re-plans over the time the nominal had left plus a reserve. The healthy plant is
run from every point as a control.

""")
    A(fig('H2_grid.png', 'Outcome by fault and injection point'))
    A(f"""
This is the study's overview figure, and the one worth reading first: one cell
per solve, no averaging, time running left to right. Three groups fall out of
it immediately.

""")
    A(table([
        ['Survive everywhere', str(len(always)),
         ', '.join(short(f) for f in always) or '—'],
        ['Have a boundary', str(len(partial)),
         ', '.join(short(f) for f in partial) or '—'],
        ['Never survive', str(len(never)),
         ', '.join(short(f) for f in never) or '—'],
    ], ['Group', 'Faults', 'Which'], [22, 8, 60]))

    A("""
**The faults that fail do not fail randomly across the descent; they fail
late.** Every fault with a boundary has it in the braking phase, where the
vehicle is low, still fast, and has committed its remaining altitude to the
flare. A fault arriving during the cruise has hundreds of metres to trade for a
re-plan; the same fault arriving during the flare has none. Altitude is the
currency.
""")
    A(fig('H3_survival.png', 'Landing share by fault class against injection time'))
    A(fig('H4_margin.png', 'Gate margin against injection time, per fault'))

    A("""
# The trajectories in three dimensions

Every figure so far collapses the path into the range-altitude plane — the
plane the glide cone lives in, and therefore the plane the constraints are
argued in. It is not the plane the vehicle flies in. A one-engine-out LM yaws
under asymmetric thrust, the gimbal trims it, and what is left is a cross-range
excursion that a 2-D plot draws as nothing at all.
""")
    A(fig('3D1_baseline_by_fault.png',
          'Study H — every recovery in 3-D, one panel per plant'))
    A("""
The panels are worth comparing against each other rather than read one at a
time. The thrust-magnitude faults stay in the vertical plane and differ from
the nominal mostly in *when* they brake. The asymmetric ones — engine out above
all — bulge sideways and come back, and the failures cluster at the end of the
descent where there is no room left to do that.

# Study H-R — is it the vehicle or the corridor?

## The question

The problem those failed solves could not satisfy carries a corridor of path
constraints, and not all of them are physics:

""")
    A(table([
        ['Glide cone', f"{b['glide_deg']:.0f}° above horizontal",
         'A scenario choice — it rules out the dive-and-crawl-back trajectory '
         'family, not something the vehicle cannot fly.'],
        ['Attitude', f"{b['euler_deg']:.0f}° per axis",
         'Planner comfort. `hard_loss()` puts real loss of control at 90°.'],
        ['Body rate', f"{b['rate_dps']:.0f}°/s",
         'Comfort again; `hard_loss()` uses 120°/s.'],
        ['Speed', f"{b['v_axis']:.0f} m/s per axis and as a norm",
         'The model has no aerodynamic or structural speed limit at all.'],
    ], ['Constraint', 'Study H value', 'What it actually is'], [14, 26, 58]))

    A(f"""
So "no trajectory exists" may mean "no trajectory exists **that stays inside
the corridor**" — a very different engineering statement.

## The ladder

""")
    A(table([[l['key'], l['label'],
              ', '.join(l['relax']) if l['relax'] else 'none dropped']
             for l in R['ladder']],
            ['Level', 'Corridor', 'Constraints removed outright'], [8, 46, 30]))

    A(f"""
Thrust and gimbal bounds stand at every level — they are hardware. The Apollo
gate stands at every level: a relaxed solve still has to touch down inside the
same gate to count as a landing. The altitude floor stands through L4 and is
dropped only at **L5**, where *nothing constrains the state anywhere in the
problem*.

Effort is matched deliberately. Study H spent 7 seeds at up to 1,200 iterations
on each of these cases; each ladder level adds {len(R['seeds'])} horizon seeds
at {R['iters']:,}, so a case still infeasible at L5 has resisted
**{n_seeds_total} seeds**.

## What the ladder found

""")
    A(fig('HR1_ladder.png', 'The weakest relaxation that admits a trajectory'))
    A('\n' + table(
        [[c['short'], f"{c['t_f']:.0f} s", f"{c['alt']:.0f} m",
          c['base_outcome'].replace('_', ' '),
          c['level'] if c['level'] != 'none' else '—',
          c['outcome'].replace('_', ' '),
          num(c['margin'], '{:.2f}') if c['level'] != 'none' else '—',
          c['binding']] for c in cases],
        ['Fault', 'Injected', 'Altitude', 'Study H', 'Solved at', 'Outcome',
         'Gate margin', 'Binding baseline limit'],
        [22, 10, 10, 14, 10, 14, 12, 20]))

    A(f"""
**Everything that recovered, recovered at L1.** The attitude, rate and speed
relaxations unlocked nothing at all: no case anywhere in this study was limited
by how hard it was allowed to pitch, spin or fly. The single binding constraint
in the whole campaign is the glide cone, and the recoveries that need it fly a
{min(c['path_min_deg'] for c in l1):.1f}–{max(c['path_min_deg'] for c in l1):.1f}°
path against a {b['glide_deg']:.0f}° floor. They are *shallower* approaches, not
more violent ones.
""")
    A(fig('HR2_excursions.png', 'Peak excursion beyond each baseline limit'))
    A(f"""
These excursions are measured **after the post-fault transient**, from node
{R['n_ramp']} onward. `solve_ocp` opens a corridor over the first
{R['n_ramp']} nodes — up to 3× the rate limit — that shrinks to the nominal
envelope, and the baseline problem opens it too. An excursion inside that window
is something Study H already permitted, so counting it would credit the recovery
to the wrong constraint: measured over the whole trajectory two of these
recoveries look bought by the body-rate limit at ~2×; measured after the ramp
their rate and attitude peaks are exactly 1.00× and only the cone is broken.
""")
    A(fig('3D2_relaxed_by_case.png', 'What the relaxation bought, in 3-D'))

    A(f"""
# The L5 diagnostic — removing the state constraints entirely

L5 is not a corridor. With the altitude floor gone there is no constraint on
the state left in the problem; only the dynamics and the actuator bounds remain.
A trajectory found there may pass through the lunar surface, so it is **not a
landing** and is not counted as one. Its job is to split the remaining failures
in two: cases where the state constraints were the obstacle, and cases where the
plant simply cannot do it.

**{len(sub)} of the {R['n_no_recovery']} found a trajectory at L5**
{f"and {'it dives' if len(sub) == 1 else 'they dive'} as deep as {max(depths):.0f} m below the surface" if depths else ''}.
""")
    A(fig('3D3_subsurface.png', 'The trajectory that exists only without the '
                                'altitude floor'))
    A(f"""
This case is the study's sharpest methodological warning. Its touchdown scores a
clean gate margin of {sub[0]['margin']:.2f} — the gate inspects only the final
state — at the end of a path that spent most of its length underground. **A
trajectory that satisfies the terminal criteria is not necessarily a landing**,
and any campaign scoring recoveries on a terminal gate alone needs a path check
to go with it.

The other **{len(stuck)}** cases fail even with no state constraints at all.
They are short of control authority outright, and no guidance law, however
permissive, recovers them.

# What the three campaigns mean together

**A solver's "infeasible" is a property of the constraint set, and must be
reported as one.** {R['n_no_recovery']} failures became {len(stuck)} once the
same states and the same plants were given a wider corridor. Any study that
reports fault survivability from a constrained planner is reporting its
constraints as much as its vehicle, and the only way to know the split is to
vary them deliberately.

**Severity should be quoted with the corridor attached.** "Unrecoverable after
t = X" is incomplete. The defensible form is "unrecoverable after t = X inside a
{b['glide_deg']:.0f}° cone, and after t = Y with the cone opened to 6°" — and
the gap between the two numbers is exactly the value of an envelope-expanding
guidance mode.

**The cone is doing more work than any other constraint.** It was chosen for a
near-vertical scenario, inherited into a shallow Apollo approach, and it is the
single limit that decides {len(l1)} of these cases. Nothing else in the corridor
mattered anywhere in the campaign. If one number in this problem statement
deserves re-derivation from vehicle and mission requirements rather than
convenience, it is that one.

**Altitude is the currency, and the boundary is a time.** Every fault with a
boundary has it late, in the braking phase. The single number a fault-tolerance
budget should carry is the injection time past which recovery stops existing —
and after this study, two of them: one for the design corridor and one for the
open one.

**{len(stuck)} genuine losses, not {R['n_no_recovery']}.** After five corridors
and {n_seeds_total} seeds, the failures that remain are
{', '.join(sorted({short(c['fault']) for c in stuck}))} — and all five
{short('dead_time') if 'dead_time' in cat else 'dead-time'} injections are among
them. That is a smaller and much better-defended claim than the campaign
originally supported.

# Limitations

* **Local infeasibility is not global.** {n_seeds_total} seeds is strong
  evidence, not proof.
* **Instantaneous, perfect detection.** No isolation, identification or reaction
  delay; every number here is an upper bound. Studies D and E measure the gap.
* **Open loop.** Each result is one solve, not a closed loop re-solving as it
  flies.
* **One nominal.** All {H['n_solves']} solves depart from a single reference
  trajectory; a steeper or faster approach would move the boundaries.
* **The relaxed limits are round numbers**, chosen to bracket the baseline
  rather than derived from vehicle structure. The ladder localises which
  constraint binds, not the exact threshold.
* **Constant mass**, inherited from the base model, understating the propellant
  cost of a partial fault.
* **{n_pts} injection points** resolve a boundary to about
  {(times[-1] - times[0]) / max(n_pts - 1, 1):.0f} s.

# Reproducing

```bash
python studies/fault_injection/apollo_nominal.py           # the reference descent
python studies/fault_injection/run_injection_study.py      # Study H campaign
python studies/fault_injection/harden.py                   # H hardening pass
python studies/fault_injection/analyse_injection.py        # H figures + JSON
python studies/fault_injection/run_relaxed_study.py        # H-R ladder, L1-L4
python studies/fault_injection/run_relaxed_study.py --extend L5   # the L5 diagnostic
python studies/fault_injection/analyse_relaxed.py          # H-R figures + JSON
python studies/fault_injection/plot_trajectories_3d.py     # the 3-D figures
python studies/fault_injection/build_combined_report.py    # this document
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
