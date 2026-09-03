"""
Fleet acceleration reference
════════════════════════════
Reads the actuation-envelope model for all 21 spacecraft and writes a PDF
giving, per vehicle and per category, the maximum achievable linear
acceleration along each body axis and the maximum achievable angular
acceleration about each body axis — then deduces a typical figure per
spacecraft class.

The numbers themselves come from `envelopes.axis_maxima`, which evaluates the
support function of the achievable force set and the achievable moment set on
each of the six body-axis directions.  Nothing new is computed here; this
module is the presentation layer.

Run:  python build_acceleration_tables.py
"""

import sys
import subprocess
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src' / 'apollo_gnc'))

from vehicles import build_all, _read_workbook as read_workbook  # noqa: E402
from envelopes import axis_maxima       # noqa: E402

FIG = HERE / 'figures'
MD = HERE / 'acceleration_reference.md'
PDF = HERE / 'acceleration_reference.pdf'
CSV = HERE / 'acceleration_reference.csv'

CATEGORIES = ['Boosters', 'Crewed Vehicles', 'GEO Satellites',
              'LEO Satellites', 'Deep Space Probes']

SURFACE = '#fcfcfb'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8985'
CAT_COLOR = {'Boosters': '#2a78d6', 'Crewed Vehicles': '#eb6834',
             'GEO Satellites': '#1baf7a', 'LEO Satellites': '#4a3aa7',
             'Deep Space Probes': '#e87ba4'}

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE, 'axes.edgecolor': '#d8d7d2',
    'axes.labelcolor': INK2, 'text.color': INK,
    'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': '#e7e6e1', 'grid.linewidth': 0.8,
    'axes.axisbelow': True, 'font.size': 9,
})


# ══════════════════════════════════════════════════════════════════════
#  1. DATA COVERAGE
# ══════════════════════════════════════════════════════════════════════
#  A zero in this study means one of two entirely different things, and they
#  must never be pooled:
#
#    STRUCTURAL ZERO  the modelled actuators genuinely produce no authority
#                     about that axis.  A single centreline gimballed engine
#                     cannot generate roll, no matter how large it is; that is
#                     a real and important property of the layout.
#    DATA GAP         the vehicle has the hardware, but the workbook records no
#                     thrust value for it.  Reporting that as zero authority
#                     would be a statement about the spreadsheet, not the
#                     spacecraft.
#
#  Vehicles with a data gap are listed in the tables but excluded from every
#  per-category statistic.
# ══════════════════════════════════════════════════════════════════════

def coverage(name, raw):
    """(linear_usable, angular_usable, note) for one vehicle.

    The workbook draws the distinction itself and it only has to be read
    correctly.  A tier recorded as `0` alongside a designation like "None at
    vehicle level" is a vehicle that genuinely has no such tier — every booster
    here controls attitude with its engine gimbal and nothing else, which is a
    real design fact.  A tier recorded as `nan` is one whose hardware the
    designation names but whose thrust nobody wrote down, and that is a hole in
    the data.

    The distinction is made per tier, because a vehicle can be sound in one
    quantity and empty in the other.  Juno's main engine is documented, so its
    linear figure stands; its entire attitude authority is twelve thrusters
    with no recorded thrust, so its angular figure is not a measurement of
    Juno.
    """
    main_gap = np.isnan(raw['F_main']) or np.isnan(raw['n_main'])
    rcs_gap = np.isnan(raw['F_rcs']) or np.isnan(raw['n_rcs'])
    has_main = (not main_gap) and raw['F_main'] > 0 and raw['n_main'] > 0
    has_rcs = (not rcs_gap) and raw['F_rcs'] > 0 and raw['n_rcs'] > 0

    if main_gap and rcs_gap:
        return False, False, 'no thrust recorded for either tier'
    if not (has_main or has_rcs):
        return False, False, 'no actuator thrust recorded'

    # Linear authority survives as long as *some* tier is documented.
    lin_ok = has_main or has_rcs
    # Angular authority is only meaningful if the tier that provides it is
    # documented.  A rigidly mounted centreline main engine produces no moment,
    # so a vehicle whose RCS is missing has no usable angular figure at all.
    ang_ok = has_rcs or (has_main and not rcs_gap)
    note = ''
    if rcs_gap:
        note = (f"{int(raw['n_rcs']) if not np.isnan(raw['n_rcs']) else 'some'} "
                'RCS thrusters named with no thrust recorded')
    elif main_gap:
        note = 'main engine named with no thrust recorded'
    return lin_ok, ang_ok, note


def per_axis(v):
    """Max linear [m/s^2] and angular [deg/s^2] acceleration per body axis,
    taken as the larger of the two directions along that axis."""
    m = axis_maxima(v)
    lin = [max(m['+' + c]['accel_ms2'], m['-' + c]['accel_ms2']) for c in 'xyz']
    ang = [np.rad2deg(max(m['+' + c]['ang_accel_rads2'],
                          m['-' + c]['ang_accel_rads2'])) for c in 'xyz']
    return np.array(lin), np.array(ang), m


def fmt(x, kind):
    """Numbers over five decades need a format that stays readable."""
    if not np.isfinite(x):
        return '—'
    if x == 0.0:
        return '0'
    if kind == 'lin':
        if x >= 0.1:
            return f'{x:.2f}'
        if x >= 1e-3:
            return f'{x:.4f}'
        return f'{x:.1e}'
    if x >= 1.0:
        return f'{x:.1f}'
    if x >= 1e-2:
        return f'{x:.3f}'
    return f'{x:.1e}'


def table(rows, header, widths=None):
    align = (['---'] * len(header) if widths is None
             else [':' + '-' * w for w in widths])
    out = ['| ' + ' | '.join(str(c) for c in header) + ' |',
           '|' + '|'.join(align) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out) + '\n'


# ══════════════════════════════════════════════════════════════════════
#  2. FIGURE
# ══════════════════════════════════════════════════════════════════════

def fig_ranges(data, path):
    """Per-category spread of axial linear and lateral angular acceleration,
    on log axes because the fleet spans six decades."""
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6))
    specs = [(axes[0], 'lin_ax', 'axial linear acceleration  $a_z$  [m/s²]'),
             (axes[1], 'ang_lat', 'lateral angular acceleration  '
                                  r'$\alpha_{x,y}$  [°/s²]')]
    for ax, key, label in specs:
        for i, cat in enumerate(CATEGORIES):
            ok = 'lin_ok' if key.startswith('lin') else 'ang_ok'
            vals = [d[key] for d in data
                    if d['category'] == cat and d[ok] and d[key] > 0]
            if not vals:
                continue
            c = CAT_COLOR[cat]
            ax.plot(vals, [i] * len(vals), 'o', color=c, ms=8, alpha=0.75,
                    mec=SURFACE, mew=1.2, zorder=3)
            ax.plot([min(vals), max(vals)], [i, i], color=c, lw=2.4,
                    alpha=0.35, solid_capstyle='round', zorder=2)
            ax.plot([np.median(vals)], [i], '|', color=c, ms=20, mew=2.6,
                    zorder=4)
        ax.set_xscale('log')
        ax.set_yticks(range(len(CATEGORIES)))
        ax.set_yticklabels(CATEGORIES, fontsize=9)
        for tl, cat in zip(ax.get_yticklabels(), CATEGORIES):
            tl.set_color(CAT_COLOR[cat])
        ax.set_ylim(len(CATEGORIES) - 0.4, -0.6)
        ax.set_xlabel(label)
        ax.grid(axis='y', visible=False)
        for s in ('top', 'right', 'left'):
            ax.spines[s].set_visible(False)
    fig.suptitle('What each class of spacecraft can actually accelerate at\n'
                 'dot = one vehicle, bar = the class range, tick = median '
                 '(vehicles with missing actuator data excluded)',
                 fontsize=11, weight='bold', color=INK, x=0.012, ha='left')
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f'[saved] {path}')


# ══════════════════════════════════════════════════════════════════════
#  3. BUILD
# ══════════════════════════════════════════════════════════════════════

def build():
    V = build_all()
    book = read_workbook()
    data = []
    for v in V:
        lin, ang, m = per_axis(v)
        lin_ok, ang_ok, note = coverage(v.name, book[v.name])
        data.append(dict(
            name=v.name, category=v.category, mass=v.mass,
            inertia=v.inertia, lin_ok=lin_ok, ang_ok=ang_ok, why=note,
            n_rcs=v.n_rcs, n_eng=v.n_engines,
            lin=lin, ang=ang, raw=m,
            lin_ax=lin[2], lin_lat=float(max(lin[0], lin[1])),
            ang_lat=float(max(ang[0], ang[1])), ang_roll=ang[2]))

    good = [d for d in data if d['lin_ok'] or d['ang_ok']]
    gaps = [d for d in data if not (d['lin_ok'] or d['ang_ok'])]
    partial = [d for d in data if d['lin_ok'] != d['ang_ok']]

    with open(CSV, 'w') as fh:
        fh.write('vehicle,category,status,mass_kg,'
                 'a_x_ms2,a_y_ms2,a_z_ms2,'
                 'alpha_x_degs2,alpha_y_degs2,alpha_z_degs2\n')
        for d in data:
            fh.write(f"{d['name']},{d['category']},"
                     f"{'lin' if d['lin_ok'] else ''}"
                     f"{'+ang' if d['ang_ok'] else ''},"
                     f"{d['mass']:.1f},"
                     + ','.join(f'{x:.6g}' for x in d['lin']) + ','
                     + ','.join(f'{x:.6g}' for x in d['ang']) + '\n')
    print(f'[saved] {CSV}')

    fig_ranges(data, FIG / '_acceleration_by_category.png')

    P = []
    A = P.append
    A(r"""---
title: "Achievable Acceleration Across the Fleet"
subtitle: "Maximum linear and angular acceleration per body axis, by spacecraft class"
date: "26 August 2026"
geometry: margin=1.8cm
fontsize: 10pt
numbersections: true
toc: true
colorlinks: true
header-includes:
  - \usepackage{booktabs}
  - \usepackage{amsmath}
  - \usepackage{float}
  - \let\origfigure\figure
  - \let\endorigfigure\endfigure
  - \renewenvironment{figure}[1][2]{\expandafter\origfigure\expandafter[H]}{\endorigfigure}
---

# What these numbers are

For each spacecraft the actuation-envelope model builds the **achievable force
set** and the **achievable moment set** — every net wrench the vehicle's
thrusters and gimballed engines can produce with all of them available at once.
The maximum force along a body axis is the support function of that set
evaluated on the axis, and the accelerations follow directly:

$$a_j = \frac{h_F(e_j)}{m} \qquad\qquad \alpha_j = \frac{h_M(e_j)}{I_{jj}}$$

Each axis is evaluated in both directions and the **larger of the two** is
reported here, since the question is what the vehicle can achieve. Layouts are
often strongly asymmetric — a lander can push hard along $-z$ and barely at all
along $+z$ — so the full signed breakdown is in Appendix A.

Three properties of this figure are worth being explicit about, because they
make it an **upper bound** rather than an operating value:

* **Everything fires at once.** The number assumes every thruster and engine is
  simultaneously available and commanded to the optimum. No propellant budget,
  duty cycle, thermal limit or control-allocation loss is applied.
* **It is instantaneous.** Angular acceleration is $M/I_{jj}$ about the
  principal axes, neglecting gyroscopic coupling and products of inertia, so it
  is a small-rate figure and not a slew capability.
* **Main engines are included.** For satellites the axial number is dominated
  by the apogee engine, which is a manoeuvre actuator and not something used
  for attitude or translation control. The lateral and angular figures are the
  ones that describe day-to-day control authority.

Masses and thrust levels are read from the fleet workbook; dimensions and
inertias are shape-model estimates (uniform cylinder or box), which is the
dominant uncertainty in every angular figure. A factor-of-two error in $I_{jj}$
moves $\alpha_j$ by the same factor.

# Data coverage — and two kinds of zero

A zero in these tables means one of two entirely different things, and pooling
them would produce nonsense:

**Structural zero.** The modelled actuators genuinely produce no authority
about that axis. A single centreline gimballed engine cannot generate roll no
matter how large it is, which is why Ariane 5, Vega and Vega-C all show
$\alpha_z = 0$ — real launchers solve this with a separate roll-control system
that is not in the model. These are real results and are kept.

**Data gap.** The vehicle has the hardware, but the workbook records no thrust
value for it. Reporting that as zero authority would be a statement about the
spreadsheet, not the spacecraft.
""")

    A('\n' + table(
        [[d['name'], d['category'], d['why']] for d in gaps],
        ['Vehicle', 'Class', 'Why it is excluded'], [30, 18, 46]))

    A(f"""
Those {len(gaps)} carry no usable figure at all and are excluded from every
statistic below.

The distinction is drawn **per quantity**, because a vehicle can be sound in
one and empty in the other:
""")
    A('\n' + table(
        [[d['name'], 'yes' if d['lin_ok'] else 'no',
          'yes' if d['ang_ok'] else 'no', d['why']] for d in partial],
        ['Vehicle', 'Linear usable', 'Angular usable', 'What is missing'],
        [26, 13, 14, 40]))

    A(f"""
Juno is the case that matters. Its main engine is documented, so its linear
figure stands; but that engine is rigidly mounted on the centreline and
produces no moment, which means its entire attitude authority is the twelve
thrusters the workbook names and gives no thrust for. Its angular row is
therefore not a measurement of Juno and is excluded from the angular
statistics.

Note also what is **not** a gap: every booster here records its RCS tier as
"None at vehicle level", which is a design fact rather than a hole — a launcher
of this kind controls attitude with engine gimbal alone. Europa Clipper
likewise records "same engine set, no separate RCS tier". Those vehicles are
complete and are kept.

Usable vehicles per class:
""")
    A('\n' + table(
        [[cat,
          f"{sum(1 for d in data if d['category'] == cat and d['lin_ok'])} of "
          f"{sum(1 for d in data if d['category'] == cat)}",
          f"{sum(1 for d in data if d['category'] == cat and d['ang_ok'])} of "
          f"{sum(1 for d in data if d['category'] == cat)}"]
         for cat in CATEGORIES],
        ['Class', 'Linear', 'Angular'], [22, 14, 14]))

    # ── per-vehicle tables ───────────────────────────────────────────────
    A("""
\\newpage

# Per-vehicle acceleration

Linear acceleration in m/s²; angular acceleration in °/s². Both are the maximum
over the two directions along each axis. Body axes follow each vehicle's own
convention as built in the model: **$z$ is the main-engine / thrust axis**, and
$x,y$ are lateral. That is why the $a_z$ column is almost always the largest —
it is the main engine, and the lateral columns are what the RCS alone can do.
""")

    for cat in CATEGORIES:
        rows = [d for d in data if d['category'] == cat]
        if not rows:
            continue
        A(f'\n## {cat}\n')
        trows = []
        for d in sorted(rows, key=lambda d: -d['lin_ax']):
            cells = ([fmt(x, 'lin') for x in d['lin']] if d['lin_ok']
                     else ['—'] * 3)
            cells += ([fmt(x, 'ang') for x in d['ang']] if d['ang_ok']
                      else ['—'] * 3)
            mark = '' if (d['lin_ok'] and d['ang_ok']) else ' *'
            trows.append([d['name'] + mark, f"{d['mass']:,.0f}"] + cells)
        A(table(trows,
                ['Vehicle', 'Mass [kg]', '$a_x$', '$a_y$', '$a_z$',
                 r'$\alpha_x$', r'$\alpha_y$', r'$\alpha_z$'],
                [30, 10, 8, 8, 8, 8, 8, 8]))

    # ── category typicals ────────────────────────────────────────────────
    A("""
\\newpage

# Typical values by class

Median across the vehicles of each class with usable data, with the full range
in brackets. The sample per class is small — this is a fleet survey, not a
population — so the **range** is the honest statistic and the median is an
indicative middle, not an expectation.
""")

    def band(cat, key, kind=None):
        """A rounded range for the rule-of-thumb table.  Deliberately coarse:
        the inertias behind these numbers are shape-model estimates, so a range
        to one significant figure is the most they support."""
        v = [x for x in vals(cat, key) if x > 0]
        if not v:
            return 'none in this sample'
        lo, hi = min(v), max(v)

        def sig1(x):
            if x == 0:
                return '0'
            e = int(np.floor(np.log10(abs(x))))
            r = round(x / 10 ** e) * 10 ** e
            return f'{r:.0f}' if e >= 0 else f'{r:.{-e}f}'

        return sig1(lo) if hi / lo < 1.6 else f'{sig1(lo)}–{sig1(hi)}'

    def stat(vals, kind):
        vals = [v for v in vals if np.isfinite(v)]
        if not vals:
            return '—'
        med = np.median(vals)
        if len(vals) == 1:
            return fmt(med, kind)
        return f'{fmt(med, kind)}  [{fmt(min(vals), kind)}–{fmt(max(vals), kind)}]'

    def vals(cat, key):
        ok = 'lin_ok' if key.startswith('lin') else 'ang_ok'
        return [d[key] for d in data if d['category'] == cat and d[ok]]

    trows = []
    for cat in CATEGORIES:
        nl, na = len(vals(cat, 'lin_ax')), len(vals(cat, 'ang_lat'))
        if not nl and not na:
            continue
        trows.append([
            cat, f'{nl}/{na}',
            stat(vals(cat, 'lin_ax'), 'lin'),
            stat(vals(cat, 'lin_lat'), 'lin'),
            stat(vals(cat, 'ang_lat'), 'ang'),
            stat(vals(cat, 'ang_roll'), 'ang')])
    A('\n' + table(trows,
                   ['Class', 'n lin/ang', 'Axial $a_z$ [m/s²]',
                    'Lateral $a_{x,y}$ [m/s²]',
                    r'Pitch/yaw $\alpha_{x,y}$ [°/s²]',
                    r'Roll $\alpha_z$ [°/s²]'],
                   [22, 9, 22, 24, 24, 22]))

    A('\n' + f"![Acceleration by spacecraft class]({FIG / '_acceleration_by_category.png'})\n")

    # ── the deduction ────────────────────────────────────────────────────
    def med(cat, key):
        v = vals(cat, key)
        return np.median(v) if v else float('nan')

    top_ang = sorted(((d['name'], d['ang_lat']) for d in data if d['ang_ok']),
                     key=lambda t: -t[1])[:2]
    boost_ax = med('Boosters', 'lin_ax')
    crew_ax = med('Crewed Vehicles', 'lin_ax')
    geo_ax = med('GEO Satellites', 'lin_ax')
    leo_ax = med('LEO Satellites', 'lin_ax')
    dsp_ax = med('Deep Space Probes', 'lin_ax')
    # Axial-to-lateral ratio, split by whether the vehicle has a main engine
    # at all: that turns out to be the thing the ratio is really measuring.
    ratios = [(d['name'], d['lin_ax'] / d['lin_lat'], d['n_eng'] > 0)
              for d in data if d['lin_ok'] and d['lin_lat'] > 0]
    with_eng = [r for _, r, e in ratios if e]
    no_eng = [(n, r) for n, r, e in ratios if not e]
    med_ratio = np.median(with_eng)
    q1, q3 = np.percentile(with_eng, [25, 75])

    A(f"""
\\newpage

# What the classes actually look like

**Axial acceleration separates the classes by four orders of magnitude, and it
is really a statement about mission phase.** Boosters sit around
{fmt(boost_ax, 'lin')} m/s² because they must lift themselves against Earth
gravity — anything below ~10 m/s² does not leave the pad. Crewed vehicles come
next at about {fmt(crew_ax, 'lin')} m/s², sized for abort and orbital
manoeuvring. GEO satellites ({fmt(geo_ax, 'lin')} m/s²) and deep-space probes
({fmt(dsp_ax, 'lin')} m/s²) carry an apogee or main engine sized for
orbit insertion. LEO satellites are lowest of all
({fmt(leo_ax, 'lin')} m/s²) because most carry no main engine at all: their
axial figure *is* their RCS.

**Lateral acceleration is about an order of magnitude below axial — and the
exceptions say why.** For every vehicle in the fleet that has a main engine,
the axial-to-lateral ratio clusters tightly around **{med_ratio:.0f}:1**
(interquartile range {q1:.0f}–{q3:.0f}:1 over {len(with_eng)} vehicles). The
reason is pure layout: the main engine points along one axis and everything
sideways has to come from small RCS thrusters.

The vehicles that break the pattern break it in the direction that confirms it.
{', '.join(n for n, _ in no_eng)} carry **no main engine at all**, and their
ratios are {', '.join(f'{r:.1f}:1' for _, r in no_eng)} — near unity, because
every axis including the nominal thrust axis is served by the same RCS. At the
other extreme Crew Dragon reaches {max(with_eng):.0f}:1, its eight SuperDracos
sized for launch abort against a Draco RCS sized for docking.

The practical consequence is the same either way: on any vehicle with a main
engine, a guidance scheme that wants lateral authority is really asking the
vehicle to tilt and use the main engine. That is a rotational manoeuvre with
the associated delay, not a translation — which is exactly why the Apollo
landing studies in this repository spend their control authority on attitude.

**Angular acceleration does not track size or thrust; it tracks what the
vehicle was built to do.** The two largest figures in the fleet belong to the
Apollo LM and Crew Dragon at {top_ang[0][1]:.0f} and {top_ang[1][1]:.0f} °/s² —
compact vehicles carrying RCS sized for landing and for docking. Boosters,
with thrust in the meganewtons, manage
{band('Boosters', 'ang_lat', 'ang')} °/s²: their inertia is enormous and their
only moment source is a few degrees of gimbal deflection on an engine close to
the roll axis. Deep-space probes sit near
{med('Deep Space Probes', 'ang_lat'):.1f} °/s².

The rule that falls out: **a vehicle designed to manoeuvre precisely near
something else has of order 100 °/s²; a vehicle designed to fly a trajectory
has of order 1–30 °/s²**. Proximity operations are an angular-authority
problem, and the fleet is sized accordingly.

**Roll is the axis that gets sacrificed.** Three of the four boosters have
exactly zero roll authority from their modelled actuators, and Europa Clipper
has none either. Roll is the axis a single centreline engine cannot touch, and
in the fleet it is consistently the weakest or missing channel. Where a vehicle
does have roll authority it usually comes from an offset engine cluster
(Delta IV Heavy's three boosters) or from a dedicated RCS ring.

## The rule-of-thumb table

Rounded to the nearest order of magnitude, which is the precision these
shape-model inertias actually support:
""")

    trows = []
    for cat in CATEGORIES:
        if not vals(cat, 'lin_ax') and not vals(cat, 'ang_lat'):
            continue
        rolls = vals(cat, 'ang_roll')
        n_zero = sum(1 for x in rolls if x == 0)
        roll = band(cat, 'ang_roll', 'ang')
        roll = 'none' if roll == 'none in this sample' else roll + ' °/s²'
        if n_zero:
            roll += f' — but {n_zero} of {len(rolls)} have none at all'
        trows.append([cat,
                      band(cat, 'lin_ax', 'lin') + ' m/s²',
                      band(cat, 'lin_lat', 'lin') + ' m/s²',
                      band(cat, 'ang_lat', 'ang') + ' °/s²',
                      roll])
    A('\n' + table(trows,
                   ['Class', 'Axial $a_z$', 'Lateral $a_{x,y}$',
                    r'Pitch/yaw $\alpha_{x,y}$', r'Roll $\alpha_z$'],
                   [22, 16, 18, 18, 24]))

    # ── appendix ─────────────────────────────────────────────────────────
    A("""
\\newpage

# Appendix A — signed per-axis detail

The tables above take the larger of the two directions along each axis. Layouts
are frequently asymmetric, and where they are, the *smaller* direction is the
one that constrains a controller. Linear in m/s², angular in °/s².
""")
    for cat in CATEGORIES:
        rows = [d for d in data
                if d['category'] == cat and (d['lin_ok'] or d['ang_ok'])]
        if not rows:
            continue
        A(f'\n## {cat}\n')
        trows = []
        for d in sorted(rows, key=lambda d: -d['lin_ax']):
            m = d['raw']
            lin = ([fmt(m[s + c]['accel_ms2'], 'lin')
                    for c in 'xyz' for s in '+-'] if d['lin_ok']
                   else ['—'] * 6)
            ang = ([fmt(np.rad2deg(m[s + c]['ang_accel_rads2']), 'ang')
                    for c in 'xyz' for s in '+-'] if d['ang_ok']
                   else ['—'] * 6)
            trows.append([d['name']] + lin + ang)
        A(table(trows,
                ['Vehicle', '$+a_x$', '$-a_x$', '$+a_y$', '$-a_y$',
                 '$+a_z$', '$-a_z$', r'$+\alpha_x$', r'$-\alpha_x$',
                 r'$+\alpha_y$', r'$-\alpha_y$', r'$+\alpha_z$',
                 r'$-\alpha_z$'],
                [26] + [6] * 12))

    A("""
\\newpage

# Limitations

* **Upper bound, not an operating value.** Every actuator fires at once, at
  full thrust, in the optimal direction. Real control allocation, duty cycles,
  propellant budgets and thermal limits all reduce these figures.
* **Inertia is a shape model.** Every vehicle is treated as a uniform cylinder
  or box at its published envelope dimensions. This is the largest single
  uncertainty in the angular columns and it is a *systematic* one: real
  spacecraft concentrate mass at the base, so true $I_{xx}, I_{yy}$ are
  generally smaller than modelled and true angular accelerations correspondingly
  larger.
* **Actuator geometry is largely assumed.** Thrust magnitudes and counts come
  from the workbook; where thrusters sit and which way they point is a layout
  model (rings, face pairs, canted clusters), chosen per vehicle and recorded
  in the provenance sheet of `actuation_envelope_summary.xlsx`.
* **Small samples.** Two to five vehicles per class. The ranges are a survey of
  these particular spacecraft, not a distribution over the class.
* **Mass is a single reference value** — usually launch or wet mass. A vehicle
  near end of life with empty tanks accelerates considerably harder than these
  numbers suggest.
* **No gyroscopic coupling.** $\\alpha_j = M_j / I_{jj}$ holds at low rates.
  For a spinning vehicle (Juno, or any spin-stabilised probe) the achievable
  angular acceleration about the transverse axes is materially different.

# Reproducing

```bash
python studies/actuation_envelopes/build_acceleration_tables.py
```

Outputs `acceleration_reference.pdf`, `acceleration_reference.csv` and
`figures/_acceleration_by_category.png` in this directory. The underlying
envelope model, its per-value provenance flags and the three-panel per-vehicle
figures are produced by `build_report.py` alongside it.
""")

    MD.write_text('\n'.join(P))
    print(f'[saved] {MD}')
    cmd = ['pandoc', str(MD), '-o', str(PDF), '--pdf-engine=xelatex',
           '--resource-path', str(HERE)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f'[saved] {PDF}')
    except subprocess.CalledProcessError as e:
        print('pandoc failed:\n', e.stderr[-2500:])


if __name__ == '__main__':
    build()
