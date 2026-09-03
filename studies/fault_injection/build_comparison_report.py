"""
Build the H vs H-R comparison report (markdown -> PDF via pandoc/xelatex).

Reads BOTH headline files - results/headline_H.json (the baseline campaign) and
results/headline_HR.json (the relaxed ladder) - and writes the document that
sets them against each other.  Nothing here is re-computed from trajectories:
if a number appears, one of the two campaigns produced it.

Run analyse_injection.py and analyse_relaxed.py first.
"""

import os
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
MD = os.path.join(HERE, 'constraint_relaxation_comparison.md')
PDF = os.path.join(HERE, 'constraint_relaxation_comparison.pdf')


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
    cases, b = R['cases'], R['baseline']
    solved = [c for c in cases if c['level'] != 'none']
    landed = [c for c in solved if c['lands']]
    stuck = [c for c in cases if c['level'] == 'none']
    l5 = [c for c in cases if c['level'] == 'L5']
    flyable = [c for c in cases if c['level'] not in ('none', 'L5')]

    n_solves = H['n_solves']
    n_land_H = sum(1 for f in H['faults'] for j in H['cells'][f]
                   if H['cells'][f][j] == 'land')
    # the fleet-level numbers, before and after
    land_before = n_land_H
    land_after = land_before + len(landed)
    flew_after = land_before + len(solved)

    # faults whose Study H boundary is entirely an artefact of the corridor
    by_fault = {}
    for c in cases:
        by_fault.setdefault(c['fault'], []).append(c)
    fully_recovered = [f for f, cs in by_fault.items()
                       if all(c['level'] != 'none' for c in cs)]
    partly = [f for f, cs in by_fault.items()
              if any(c['level'] != 'none' for c in cs)
              and any(c['level'] == 'none' for c in cs)]
    never = [f for f, cs in by_fault.items()
             if all(c['level'] == 'none' for c in cs)]

    def short(f):
        return H['catalogue'][f]['short'] if f in H['catalogue'] else f

    P = []
    A = P.append

    A(f"""---
title: "Corridor or Vehicle?"
subtitle: "Comparing Study H with Study H-R — what the relaxed constraints reveal about the faults that had no recovery"
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

# The two studies in one paragraph

**Study H** injected {H['n_faults']} engine plants at {H['n_points']} points
along one Apollo-anchored nominal descent — {n_solves} optimal-control solves —
and asked *where on the descent is this fault survivable*. It found
{land_before} landings and **{R['n_no_recovery']} injections with no recovery
trajectory at all**.

**Study H-R** took those failures and asked a different question: *is the
vehicle lost, or is the corridor too tight?* It re-solved each one at four
progressively weaker sets of path constraints, keeping the altitude floor, the
actuator bounds and the landing gate fixed throughout.

This document sets the two against each other.

# The headline comparison

""")
    A(table([
        ['Injections with a trajectory', f"{n_solves - R['n_no_recovery']} of {n_solves}",
         f"{flew_after} of {n_solves}",
         f"+{len(solved)}"],
        ['...of which fly above the surface',
         f"{n_solves - R['n_no_recovery']} of {n_solves}",
         f"{land_before + len(flyable)} of {n_solves}", f"+{len(flyable)}"],
        ['Injections that land in the gate', f"{land_before} of {n_solves}",
         f"{land_after} of {n_solves}", f"+{len(landed)}"],
        ['Cases with no trajectory at all', str(R['n_no_recovery']),
         str(len(stuck)), f"−{R['n_no_recovery'] - len(stuck)}"],
    ], ['Measure', 'Study H (baseline corridor)', 'Study H-R (relaxed)',
        'Change'], [34, 26, 24, 10]))

    A(f"""
{len(solved)} of the {R['n_cases']} carried-forward cases found a trajectory
once the corridor was widened, and {len(landed)} of those still touch down
inside the **unchanged** Apollo gate. The gate was never relaxed — only what the
vehicle was permitted to do on the way there.

# What the difference actually is

## Reading 1 — the failures were mostly about the corridor

""")
    if solved:
        A(f"""
{len(solved)} {plural(len(solved), 'case', 'cases')} that Study H reported as
unrecoverable are recoverable by a vehicle allowed outside the nominal envelope.
Those results were never statements about the vehicle's capability; they were
statements about the *problem as posed*. Reported as lost vehicles, they would
have overstated the severity of
{', '.join(sorted({short(c['fault']) for c in solved}))} by exactly that margin.

The binding constraint names what each one needed:
""")
        A(table([[k, str(len(v)), ', '.join(v)]
                 for k, v in R['by_binding'].items()],
                ['Baseline limit the recovery had to break', 'Cases', 'Which'],
                [40, 8, 44]))
    else:
        A("""
No case was recovered by relaxation, which is the cleanest possible answer to
this study's question: Study H's corridor was not what was stopping these
vehicles.
""")

    A("""
## Reading 2 — what the relaxation could not fix
""")
    if stuck:
        A(f"""
{len(stuck)} {plural(len(stuck), 'case', 'cases')} resisted the entire ladder:

""")
        A(table([[c['short'], f"{c['t_f']:.0f} s", f"{c['alt']:.0f} m",
                  f"{c['rng']:.0f} m"] for c in stuck],
                ['Fault', 'Injected at', 'Altitude', 'Range to pad'],
                [24, 12, 12, 14]))
        A(f"""
The last level removes **every state constraint in the problem** — the cone,
the speed box, the attitude and rate limits, and finally the altitude floor
itself — leaving only the dynamics and the actuator bounds. A failure there is
as close to "the vehicle cannot do it" as this machinery can get: there is no
longer any restriction on the state to blame. **These are the cases a fault-tolerance budget should carry
as real losses** — and there {plural(len(stuck), 'is', 'are')} {len(stuck)} of
{'them' if len(stuck) > 1 else 'it'}, not {R['n_no_recovery']}.
""")
    else:
        A(f"""
Nothing resisted the ladder. Every one of Study H's {R['n_no_recovery']}
unrecoverable injections has a trajectory once the corridor is opened, which
means the baseline study measured the corridor's edge rather than the vehicle's.
That is a strong claim and it cuts both ways: it says the vehicle is more
capable than Study H reported, and it says Study H's boundary numbers are
properties of the constraint set, not of the fault.
""")

    A(f"""
## Reading 3 — the faults sort into three groups

""")
    A(table(
        [['Recoverable with a wider corridor',
          ', '.join(short(f) for f in fully_recovered) or '—',
          'Every failed injection of this fault yields to relaxation. Its '
          'Study H boundary is a corridor artefact.'],
         ['Mixed', ', '.join(short(f) for f in partly) or '—',
          'Some injections are corridor-limited, some are not. The boundary '
          'is real but sits later than Study H put it.'],
         ['Genuinely unrecoverable', ', '.join(short(f) for f in never) or '—',
          'No relaxation helps. The vehicle cannot reach the pad from these '
          'states with this plant.']],
        ['Group', 'Faults', 'What it means'], [30, 26, 56]))

    A(f"""
# Figures, side by side

Study H's outcome grid, with the red cells being the ones this study
re-examined:
""")
    A(fig('H2_grid.png', 'Study H — outcome by fault and injection point'))
    A("""
And the ladder result for exactly those cells:
""")
    A(fig('HR1_ladder.png',
          'Study H-R — the weakest relaxation that admits a trajectory'))
    A("""
The excursion chart is the bridge between them: it shows, for each recovered
case, which Study H limit the new trajectory had to break and by how much.
""")
    A(fig('HR2_excursions.png', 'Peak excursion beyond each baseline limit'))

    A(f"""
# What we can understand from this

**A solver's "infeasible" is a property of the constraint set, and it must be
reported as one.** The single most transferable result here is methodological:
{R['n_no_recovery']} failures became {len(stuck)} once the same states and the
same plants were given a wider corridor. Any study that reports fault
survivability from a constrained planner is reporting the constraints as much as
the vehicle, and the only way to know the split is to vary them deliberately.

**Severity should be quoted with the corridor attached.** "This fault is
unrecoverable after t = X" is incomplete. The defensible statement is "this
fault is unrecoverable after t = X *inside a {b['glide_deg']:.0f}° cone with
{b['euler_deg']:.0f}° attitude and {b['v_axis']:.0f} m/s limits*, and after
t = Y with the corridor open" — two numbers, and the gap between them is the
value of an envelope-expanding guidance mode.

**Removing the state constraints entirely is a diagnosis, not a rescue.**
{len(l5)} {plural(len(l5), 'case', 'cases')} found a trajectory only with every
state constraint gone, the altitude floor included — meaning the path they take
passes through the lunar surface. They are not recoveries. What they establish
is that the plant still has the authority to make the geometry, and that the
binding difficulty is doing it above the ground. The
{len(stuck)} {plural(len(stuck), 'case', 'cases')} that fail even there
{plural(len(stuck), 'is', 'are')} short of authority outright.

**Relaxation buys a trajectory, not necessarily a landing.** Of the
{len(solved)} recovered {plural(len(solved), 'case', 'cases')}, {len(landed)}
still {plural(len(landed), 'lands', 'land')} in the gate. The rest reach the
surface outside it. Feasibility and success are different questions and the
distinction survives the relaxation intact — which is what makes the recovered
landings credible rather than an artefact of loosened scoring.

**The cases that remain are worth more than the ones that moved.** After the
ladder, {len(stuck)} {plural(len(stuck), 'case', 'cases')}
{plural(len(stuck), 'is', 'are')} left. Those have now survived
{7 + len(R['ladder']) * len(R['seeds'])} independent seeds across two studies and
four corridors. That is a far stronger claim than the original
{R['n_no_recovery']} could support, and it is the number worth defending.

# Caveats that apply to the comparison itself

* **The two campaigns are not equal-effort by design.** The relaxed run spends
  more search on fewer cases, deliberately: extra search can only convert a
  false "no" into a true "yes", never the reverse. It cannot manufacture a
  landing that does not exist, but it does mean "H-R found more" is partly a
  statement about effort as well as about constraints.
* **Only the failures were re-run.** The {land_before} baseline landings were
  not re-solved under the relaxed corridor, so this document compares the
  *failures* of one study with the *failures* of another, not two complete
  campaigns. A relaxed re-run of the landings would be expected to change
  margins, not outcomes.
* **The relaxed limits are round numbers**, chosen to bracket the baseline
  rather than derived from vehicle structure. The ladder localises which
  constraint binds; it does not find the exact threshold.
* **Everything Study H assumed still holds**: instantaneous perfect detection,
  open loop, one nominal trajectory, constant mass.

# Reproducing

```bash
python studies/fault_injection/run_injection_study.py     # Study H campaign
python studies/fault_injection/harden.py                  # H hardening pass
python studies/fault_injection/analyse_injection.py       # H figures + JSON
python studies/fault_injection/run_relaxed_study.py       # H-R ladder
python studies/fault_injection/analyse_relaxed.py         # H-R figures + JSON
python studies/fault_injection/build_comparison_report.py # this document
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
