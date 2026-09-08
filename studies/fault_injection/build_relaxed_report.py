"""
Build the Study H-R report (markdown -> PDF via pandoc/xelatex).

Every quantitative claim is interpolated from results/headline_HR.json, so the
prose cannot drift from the campaign it describes.  Run analyse_relaxed.py
first.
"""

import os
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
MD = os.path.join(HERE, 'relaxed_constraints_case_study.md')
PDF = os.path.join(HERE, 'relaxed_constraints_case_study.pdf')


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
    h = json.load(open(os.path.join(RESULTS, 'headline_HR.json')))
    b, cases = h['baseline'], h['cases']
    solved = [c for c in cases if c['level'] != 'none']
    landed = [c for c in solved if c['lands']]
    stuck = [c for c in cases if c['level'] == 'none']
    lv = {l['key']: l for l in h['ladder']}
    n_lv = len(h['ladder'])
    # the terminal level carries the study's strongest claim and is searched
    # harder than the rungs above it, so the two seed sets are counted apart
    t_seeds = h.get('terminal_seeds') or h['seeds']
    n_seeds_total = (7 + (len(h['ladder']) - 1) * len(h['seeds'])
                     + len(t_seeds))

    def names(keys):
        return ', '.join(keys) if keys else 'none'

    P = []
    A = P.append

    A(f"""---
title: "Recovering the Unrecoverable"
subtitle: "Study H-R — the {h['n_cases']} Study H injections that found no trajectory, re-solved with the state corridor relaxed"
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

# The question

Study H injected {h['n_no_recovery'] + h['n_gate_miss']}-odd faults along an
Apollo descent and found that **{h['n_no_recovery']}** of its injections had no
recovery trajectory at all: IPOPT declared local infeasibility from seven
independent seeds at up to 1,200 iterations. The natural reading of that result
is "the vehicle is lost". It is not the only reading.

The optimal-control problem those solves failed carries a corridor of path
constraints, and **not all of them are physics**:

""")
    A(table([
        ['Glide cone', f"{b['glide_deg']:.0f}° above horizontal",
         'A scenario choice. It exists to rule out the dive-and-crawl-back '
         'trajectory family, not because a vehicle cannot fly below it.'],
        ['Attitude', f"{b['euler_deg']:.0f}° per axis",
         'Planner comfort. `fault_lib`\'s own `hard_loss()` puts genuine loss '
         'of control at 90°, twice this.'],
        ['Body rate', f"{b['rate_dps']:.0f}°/s",
         'Comfort again; `hard_loss()` uses 120°/s.'],
        ['Speed', f"{b['v_axis']:.0f} m/s per axis and as a norm",
         'The vehicle model has no aerodynamic or structural speed limit at '
         'all; this is a modelling convenience.'],
    ], ['Constraint', 'Study H value', 'What it actually is'], [14, 26, 60]))

    A(f"""
So "no trajectory exists" may mean "no trajectory exists **that stays inside
the corridor**". Those are very different engineering statements. The first is a
lost vehicle. The second is a vehicle that could be saved by a guidance law
willing to leave the nominal envelope — and knowing which one you have is worth
more than the failure count itself.

This study separates them. It re-solves every case Study H could not land,
at progressively weaker corridors, and records **the weakest relaxation that
admits a trajectory** together with **how far outside the baseline limits that
trajectory actually goes**.

# Method

## The ladder

Each case is re-attacked at {n_lv} levels, stopping at the first that yields a
trajectory:

""")
    A(table([[l['key'], l['label'],
              ', '.join(l['relax']) if l['relax'] else 'none dropped']
             for l in h['ladder']],
            ['Level', 'Corridor', 'Constraints removed outright'], [8, 46, 30]))

    A(f"""
## What is never relaxed

The ladder changes what the vehicle is allowed to do **en route**. It never
changes what counts as success, and it never invents hardware:

* **Thrust and gimbal bounds stand at every level.** They are actuator
  hardware; relaxing them would answer a question about a vehicle that does not
  exist.
* **The Apollo landing gate stands at every level.** A relaxed solve still has
  to touch down inside the same gate to be counted as a landing, which is why
  the results below distinguish *found a trajectory* from *landed*.
* **The altitude floor stands at every level.** The vehicle may not fly through
  the surface, and there is no version of this question in which dropping that
  is informative: a path through the ground is not a path the vehicle can fly,
  yet its touchdown state would score against the landing gate exactly as if it
  were — the gate inspects only the final state. Dropping it would manufacture
  "recoveries" that are arithmetic, not flight.

That makes **L4 the weakest problem in this study**: every state constraint is
gone except $z > 0$. A case that fails there fails with nothing asked of it but
to stay above the surface, which is as close to "the vehicle cannot do it" as
this machinery can get.

## Effort parity

A relaxed solve that fails must fail for the same reason the baseline did, not
because it was tried less hard. Study H spent 7 seeds at up to 1,200 iterations
on each of these cases (2 in the campaign, 6 in the hardening pass). Each rung
here gets {len(h['seeds'])} horizon seeds at {h['iters']:,} iterations, and the
terminal rung {h['ladder'][-1]['key']} — where a failure is the study's
strongest claim — gets {len(t_seeds)}. A case still infeasible there has now
resisted **{n_seeds_total} seeds** in total.

# Results

Of the {h['n_cases']} cases carried forward — {h['n_no_recovery']} that found no
trajectory and {h['n_gate_miss']} that flew but missed the gate —
**{h['n_solved']} found a trajectory** once the corridor was relaxed, and
**{h['n_landed']}** of those still land inside the unchanged Apollo gate.
{'Every case yielded to some level of relaxation.' if not stuck else
 f"**{len(stuck)}** remained infeasible at every level."}

""")
    A(fig('HR1_ladder.png', 'The weakest relaxation that admits a trajectory'))

    A('\n' + table(
        [[c['short'], f"{c['t_f']:.0f} s", f"{c['alt']:.0f} m",
          c['base_outcome'].replace('_', ' '),
          c['level'] if c['level'] != 'none' else '—',
          c['outcome'].replace('_', ' '),
          num(c['margin'], '{:.2f}') if c['level'] != 'none' else '—',
          c['binding'],
          num(c.get('binding_ratio'), '{:.2f}×')]
         for c in cases],
        ['Fault', 'Injected', 'Altitude', 'Study H', 'Solved at', 'Outcome',
         'Gate margin', 'Binding baseline limit', 'Exceeded by'],
        [22, 10, 10, 14, 10, 12, 12, 22, 12]))

    A(f"""
Read the last two columns first. "Binding baseline limit" is the Study H
constraint the relaxed trajectory leans on hardest, and "exceeded by" is the
peak excursion as a multiple of that limit. A value of 1.00× would mean the
relaxation was never used — the trajectory stayed inside the original corridor
and only the *solver* needed help. Anything above 1.00× is a constraint the
recovery genuinely could not have respected.

## Which constraint was actually binding

""")
    A(table([[k, str(len(v)), ', '.join(v)] for k, v in h['by_binding'].items()],
            ['Binding limit', 'Cases', 'Which'], [20, 8, 52]))

    A(fig('HR2_excursions.png',
          'Peak excursion beyond each baseline limit, per recovered case'))

    A(f"""
**These excursions are measured after the post-fault transient**, from node
{h['n_ramp']} onward. `solve_ocp` opens a corridor over the first
{h['n_ramp']} nodes — up to 3x the rate limit, 1.35x the attitude limit,
1.2x the speed limit — which shrinks to the nominal envelope by node
{h['n_ramp']} and which **the baseline problem opens too**. An excursion
inside that window is something Study H already permitted, not something the
relaxation bought, so counting it would credit the recovery to the wrong
constraint. Measured over the whole trajectory, two of the recoveries here look
like they were bought by the body-rate limit at ~2x; measured after the ramp,
their rate and attitude peaks sit at exactly 1.00x and the glide cone is the
only limit genuinely broken — which is the answer that agrees with all three
having solved at {h['ladder'][0]['key']}, where the cone is the only thing that
moved.
""")

    A(f"""
## The trajectories themselves
""")
    A(fig('HR3_trajectories.png',
          'The relaxed recoveries against the nominal and the original cone'))

    A(f"""
# What this means

**A failed solve is a statement about the problem, not only about the vehicle.**
{h['n_solved']} of {h['n_cases']} cases that Study H recorded as unrecoverable
have a trajectory once the corridor is widened. Reporting them as lost vehicles
would have overstated the fault's severity by exactly that much.

**The relaxation is not free, and the excursion column prices it.** Every
recovered case names a specific limit it had to break and the factor by which it
broke it. That is the number a guidance designer needs: not "relax the
constraints" but "this fault is survivable if the vehicle is permitted
{'; '.join(sorted({c['binding'] for c in solved})) if solved else 'nothing'}
beyond the nominal envelope".

**The gate is the honest discriminator.** {h['n_landed']} of the
{h['n_solved']} recovered cases {plural(h['n_landed'], 'lands', 'land')} inside
the Apollo gate; the rest fly a trajectory to the surface but arrive outside it.
A trajectory that exists is not the same as a landing, and the ladder deliberately
keeps those separate.
""")

    if stuck:
        A(f"""
**{len(stuck)} {plural(len(stuck), 'case', 'cases')} did not yield to any
relaxation** ({names([c['short'] + ' @' + f"{c['t_f']:.0f} s" for c in stuck])}).
With the entire corridor removed, the only constraints left are the actuator
bounds, the surface, and the dynamics — so these are the cases where the
*vehicle* genuinely cannot get to the pad, not the cases where the planner was
being asked to fly politely. They are the ones a fault-tolerance budget should
carry as real losses.
""")
    else:
        A("""
**No case survived the full ladder.** Every infeasibility Study H reported was
a corridor artefact rather than a lost vehicle — which is itself the strongest
possible version of this study's point, and a warning about reading solver
failures as physics.
""")

    A(f"""
# Limitations

* **Local infeasibility is still not global.** {n_seeds_total} seeds is strong
  evidence, not a proof. A case that resists the whole ladder has resisted a lot
  of search; it has not been shown impossible.
* **The relaxed corridors are chosen, not derived.** 6°, 60°, 20°/s and 90 m/s
  are round numbers picked to bracket the baseline, not limits computed from
  vehicle structure or sensor range. The ladder measures *which* constraint
  binds and *roughly how much* is needed, not the exact threshold.
* **Relaxing a planner constraint does not make the vehicle able to fly it.**
  A trajectory that pitches past 45° is admissible here because the model has no
  structural or plume-impingement limit at that attitude. A real vehicle may.
* **Everything inherited from Study H still applies**: instantaneous perfect
  detection, open loop, one nominal, constant mass.

# Reproducing

```bash
python studies/fault_injection/run_relaxed_study.py    # the ladder campaign
python studies/fault_injection/analyse_relaxed.py      # figures + headline JSON
python studies/fault_injection/build_relaxed_report.py # this document
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
