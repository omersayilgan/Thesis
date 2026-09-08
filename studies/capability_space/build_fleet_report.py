"""
Build the Study I-F report (markdown -> PDF via pandoc/xelatex).

Every number comes from results/headline_IF.json; the single-vehicle findings
it compares against come from headline_I.json.  Run run_fleet_capability.py and
plot_fleet_capability.py first.
"""

import os
import json
import subprocess
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
MD = os.path.join(HERE, 'fleet_capability_case_study.md')
PDF = os.path.join(HERE, 'fleet_capability_case_study.pdf')

CAT_ORDER = ['Boosters', 'LEO Satellites', 'GEO Satellites',
             'Crewed Vehicles', 'Deep Space Probes']
SHORT = {'Solar Dynamics Observatory (SDO)': 'SDO',
         'Meteosat Second Generation (MSG)': 'MSG',
         'Orion (CM + European Service Module)': 'Orion',
         'Apollo Command & Service Module': 'Apollo CSM',
         'Apollo Lunar Module': 'Apollo LM',
         'Crew Dragon (Dragon 2)': 'Crew Dragon',
         'Cassini (Cassini-Huygens)': 'Cassini',
         'GRACE-FO (per satellite)': 'GRACE-FO'}


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


def short(n):
    return SHORT.get(n, n)


def fmt(v, f='{:.2f}×'):
    return '—' if v is None or not np.isfinite(v) else f.format(v)


def build():
    h = json.load(open(os.path.join(RESULTS, 'headline_IF.json')))
    rows = [r for r in h['rows'] if r['fault'] != 'healthy']
    live = [r for r in rows if r.get('applicable')
            and np.isfinite(r.get('M_auth_frac', np.nan))]
    faults = h['faults']
    labels = {f['key']: f['label'] for f in faults}
    cats = h['categories']
    vehicles = sorted({r['vehicle'] for r in h['rows']})

    single = None
    p1 = os.path.join(RESULTS, 'headline_I.json')
    if os.path.exists(p1):
        single = json.load(open(p1))

    # per fault, across the fleet
    per_fault = {}
    for f in faults:
        vals = [r['M_auth_frac'] for r in live if r['fault'] == f['key']]
        n_lost = sum(1 for r in live
                     if r['fault'] == f['key'] and not r.get('M_origin', True))
        per_fault[f['key']] = dict(
            n=len(vals), lo=min(vals) if vals else np.nan,
            hi=max(vals) if vals else np.nan,
            mean=float(np.mean(vals)) if vals else np.nan,
            spread=(max(vals) - min(vals)) if vals else np.nan,
            n_lost_origin=n_lost)
    # per category
    per_cat = defaultdict(dict)
    for c in CAT_ORDER:
        for f in faults:
            vals = [r['M_auth_frac'] for r in live
                    if r['fault'] == f['key'] and r['category'] == c]
            per_cat[c][f['key']] = (float(np.mean(vals)) if vals else None,
                                    len(vals))

    w, b = h['within_mean'], h['between_mean']
    same = (w is not None and b is not None and abs(w - b) < 0.02)
    worst_fault = min(per_fault, key=lambda k: per_fault[k]['mean']
                      if np.isfinite(per_fault[k]['mean']) else 9)
    widest = max(per_fault, key=lambda k: per_fault[k]['spread']
                 if np.isfinite(per_fault[k]['spread']) else -1)

    # single-engine vehicles: engine-out is total loss of the tier
    one_eng = sorted({r['vehicle'] for r in rows
                      if r['fault'] == 'engine_out' and r['n_eng'] == 1})
    many_eng = sorted({r['vehicle'] for r in rows
                       if r['fault'] == 'engine_out' and r['n_eng'] >= 3})

    P = []
    A = P.append

    A(f"""---
title: "Faults in Capability Space, Across the Fleet"
subtitle: "Study I-F — {len(faults)} actuator faults applied to every spacecraft in the fleet, and what the spacecraft classes have in common"
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

Study I put twelve faults through **one** vehicle's actuator set — the Apollo
LM as the fault-injection studies model it — and found that a fault's effect on
capability is a poor predictor of whether it is survivable. This study asks the
prior question: **is what we saw a property of that vehicle, or of the faults?**

The same capability measures are applied to every spacecraft in the
actuation-envelope fleet — {h['n_vehicles']} vehicles with usable actuator
geometry, across {len(CAT_ORDER)} classes — and then compared between vehicles
and between classes.

## Restating the faults so any vehicle can suffer them

The Study H catalogue is written against one plant, so each fault is restated
at actuator level:

""")
    A(table([[labels[f['key']], f['tier'],
              'one unit of that tier, swept over every unit']
             for f in faults],
            ['Fault', 'Tier', 'Applied to'], [30, 10, 40]))

    A(f"""
Two conventions are worth stating, because they are choices rather than
readings:

* **`valve stuck open` is {h['stuck_frac']:.0%} of the affected unit's own
  rated thrust.** Study I quoted the floor as a multiple of the LM's hover
  share, and most of this fleet never hovers. A fraction of the unit's own
  rating keeps the structural content of the fault — a floor it cannot throttle
  below — without borrowing an operating point only a lander has.
* **Worst case, not first case.** Removing "thruster 0" measures the layout's
  numbering, not its redundancy. Every single-unit fault is applied to each
  unit in turn and reported at its worst, which is the number a redundancy
  argument actually needs.

The faults left out are left out for a reason established in Study I: transport
delay, slow thrust response and erosion drift at onset **do not change a static
capability set at all**. They are not weak effects here, they are exactly zero,
and they were the least survivable faults in Study H.

## Why the fleet is measured by reach and not by volume

Volume is the natural size of a 3-D set and the wrong measure for a degenerate
one. A vehicle whose only actuator is a single centreline gimballed engine —
Ariane 5, Vega, Vega-C, Juno — has **no roll authority at all**, so its moment
set is a flat disc with exactly zero volume. Every retention ratio would be
0/0, and those vehicles would drop out of the comparison entirely: not because
they lack authority, but because their authority is planar.

The fleet map is therefore drawn from the **mean support** of each set — its
average reach over all directions — which is defined in any dimension, positive
whenever the set is, and comparable across vehicles four orders of magnitude
apart once normalised by their own healthy value. Volumes and the set's actual
dimension are both kept in `IF_fleet.csv`, and a set that has *lost* a
dimension is reported as 0 rather than as a ratio between incommensurable
quantities.

# The fleet map
""")
    A(fig('IF1_fleet_map.png',
          'Moment authority retained after the worst single failure'))

    A(f"""
Read the blanks first. They are not missing data — they are vehicles that
**cannot suffer that fault**, because they have no actuator of that tier. A
spacecraft with no main engine cannot lose one; a spacecraft with no RCS tier
cannot lose a thruster. Fault exposure is a function of architecture before it
is a function of reliability, and the map shows several vehicles that are
immune to entire fault classes by construction.

Across the fleet:

""")
    A(table([[labels[k], str(v['n']),
              fmt(v['mean']), f"{fmt(v['lo'])} – {fmt(v['hi'])}",
              str(v['n_lost_origin'])]
             for k, v in sorted(per_fault.items(),
                                key=lambda kv: kv[1]['mean'])],
            ['Fault', 'Vehicles exposed', 'Mean retained', 'Range',
             'Lost zero-moment'], [30, 16, 14, 18, 16]))

    A(f"""
**{labels[worst_fault]}** is the most damaging fault on average
({fmt(per_fault[worst_fault]['mean'])} of healthy moment volume), and
**{labels[widest]}** is the most variable — its effect ranges from
{fmt(per_fault[widest]['lo'])} to {fmt(per_fault[widest]['hi'])} depending
entirely on which vehicle suffers it. That spread is the study's first real
finding: *the same fault is not the same event on different architectures.*

# Do the spacecraft classes respond alike?
""")
    A(fig('IF2_by_category.png', 'Fault response by spacecraft class'))
    A('\n' + table(
        [[c] + [fmt(per_cat[c][f['key']][0]) for f in faults]
         for c in CAT_ORDER if any(per_cat[c][f['key']][0] is not None
                                   for f in faults)],
        ['Class'] + [labels[f['key']].split('(')[0].split(',')[0].strip()
                     for f in faults]))

    A(f"""
## The quantitative answer
""")
    A(fig('IF3_similarity.png',
          'Distance between fault responses, and class membership'))
    A(f"""
The distance between two vehicles is the mean absolute difference in retained
moment authority over the faults both can suffer — a direct measure of "do these
two react alike". Averaged over every pair:

""")
    A(table([['Same spacecraft class', fmt(w, '{:.3f}'), str(h['within_n'])],
             ['Different classes', fmt(b, '{:.3f}'), str(h['between_n'])]],
            ['Pairing', 'Mean distance', 'Pairs'], [24, 16, 10]))

    per_cat_dist = {}
    for c in CAT_ORDER:
        vs = [v for v in cats if cats[v] == c]
        ds = [h['distance'][a][b] for i, a in enumerate(vs) for b in vs[i + 1:]
              if np.isfinite(h['distance'][a].get(b, np.nan))]
        per_cat_dist[c] = (float(np.mean(ds)) if ds else None, len(vs))
    A('\n' + table(
        [[c, str(n), fmt(d, '{:.3f}') if d is not None else '— (one vehicle)']
         for c, (d, n) in per_cat_dist.items()],
        ['Class', 'Vehicles compared', 'Mean distance within the class'],
        [22, 18, 30]))
    tight = [c for c, (d, n) in per_cat_dist.items() if d is not None and d < w]
    loose = [c for c, (d, n) in per_cat_dist.items() if d is not None and d > b]
    A(f"""
The classes are not equally coherent. {', '.join(tight) if tight else 'None'}
{'hold' if len(tight) != 1 else 'holds'} together more tightly than the fleet
average{',' if loose else '.'} {' while ' + ', '.join(loose) + ' ' + ('are' if len(loose) != 1 else 'is') + ' more spread out than two vehicles picked at random.' if loose else ''}
""")

    if same:
        A(f"""
**Class membership barely predicts fault response.** Same-class pairs differ by
{fmt(w, '{:.3f}')} on average and different-class pairs by {fmt(b, '{:.3f}')} —
a gap of {abs(w - b):.3f}, which is small against the spread within a single
class. Two spacecraft in the same mission category can react to the same fault
quite differently, and two in different categories can react almost identically.

What the vehicles that *do* respond alike have in common is not their mission
but their **actuator architecture**: how many units are in each tier, how far
apart they are, and whether the tiers overlap in what they can produce. A
booster with one engine and no RCS behaves like a probe with one engine and no
RCS. Neither behaves like its own class-mates that carry a thruster ring.
""")
    else:
        A(f"""
**Same-class vehicles do respond more alike** — {fmt(w, '{:.3f}')} against
{fmt(b, '{:.3f}')}, a gap of {abs(w - b):.3f}. Mission class is a partial proxy
for actuator architecture: vehicles built for the same job tend to be built with
the same tiers, and it is the tiers that decide the response.
""")

    A(f"""
# What actually predicts the response

Three architectural facts explain most of the map, and none of them is the
spacecraft's mission.

**1. Tier count decides exposure.** {len(one_eng)} vehicles carry a single main
engine, so `engine out` is not a degradation for them — it is the total loss of
the tier, and the moment set collapses to whatever the RCS ring can produce, or
to nothing if there is none. """)
    if one_eng:
        A(f"""Those are: {', '.join(short(v) for v in one_eng)}.
""")
    if many_eng:
        A(f"""
By contrast {', '.join(short(v) for v in many_eng)} carry three or more, and
lose a fraction rather than a tier.
""")
    A(f"""
**2. A thruster ring is a different kind of redundancy from an engine cluster.**
Study I found this on one vehicle — sixteen thrusters near-interchangeable, two
engines not — and the fleet confirms it as a rule: RCS-tier faults are
consistently the mildest column of the map, and engine-tier faults the harshest,
regardless of class. A ring of many small units degrades gracefully; a cluster
of few large ones degrades in steps.

**3. Gimbals convert thrust into moment, so seizing one costs only vehicles
that have them.** `gimbal seizure` is `n/a` for every vehicle whose engines are
rigidly mounted — and for those, the entire moment tier is the RCS ring, which
is why their `RCS thruster dead` numbers matter more than anyone else's.

# What carries over from the single-vehicle study, and what does not
""")
    A(fig('IF4_exemplars.png', 'The worst single failure per class'))
    A(f"""
**Carries over.** The four effect categories — shrink, enlarge, deform,
puncture — describe every vehicle in the fleet, not just the LM. A stuck-open
valve punctures the set on every vehicle it can strike, taking the origin with
it while leaving most of the volume intact. Thrust excess enlarges the set
asymmetrically everywhere. The taxonomy is a property of the faults.

**Does not carry over.** The *magnitudes* are not transferable at all.
{labels[widest]} costs one vehicle {fmt(per_fault[widest]['lo'])} and another
{fmt(per_fault[widest]['hi'])}. Any number quoted from a single-vehicle
capability study — including Study I's — is a number about that vehicle's
actuator layout, and the honest way to use it is as a method rather than a
result.

**And the central negative result is architectural, not vehicle-specific.**
Every fault that changed nothing in Study I's capability space changes nothing
here either, on any vehicle in the fleet, because a transport delay is not a
statement about actuator geometry at all. Capability space remains necessary
and insufficient across the whole fleet: it tells you what a damaged vehicle
can do at an instant, and nothing about whether it can do it in time.

# Limitations

* **Geometry is largely estimated.** The workbook supplies thrust magnitudes and
  counts; positions, directions, gimbal limits and inertias come from
  `vehicles.py`, and only the Apollo LM's layout is this repository's own
  validated model. The comparisons are therefore between *models* of these
  spacecraft.
* **Instantaneous sets, again.** No actuator dynamics, no rate limits, no
  detection. The temporal fault classes are invisible here by construction.
* **Worst-case single failures only.** Simultaneous faults, and the
  fault-on-fault cases a long mission actually accumulates, are not covered.
* **One operating point is missing.** Study I could condition its moment sets on
  hover thrust because the LM hovers. There is no fleet-wide equivalent, so the
  fleet numbers are unconditional set volumes — the more flattering measure, as
  Study I showed.
* **{len(vehicles) - h['n_vehicles']} vehicles have no usable actuator
  geometry** and are excluded rather than counted as zero.
* **{', '.join(h.get('excluded_no_moment', [])) or 'No vehicle'} had to be left
  out of the similarity comparison entirely**, for having zero moment authority
  in the model: a single centreline engine, rigidly mounted, and no modelled
  RCS layout. Every retention ratio for such a vehicle is 0/0. That is a gap in
  the geometry database rather than a spacecraft without attitude control, and
  it is the same gap the reliability study flags for this vehicle's thruster
  tier.

# Reproducing

```bash
python studies/capability_space/run_fleet_capability.py    # the fleet sweep
python studies/capability_space/plot_fleet_capability.py   # figures
python studies/capability_space/build_fleet_report.py      # this document
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
