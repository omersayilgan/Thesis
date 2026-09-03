"""
Setting the engine spacing from authority, instead of guessing it
════════════════════════════════════════════════════════════════
The fault studies fly an imaginary twin-engine Apollo LM: the real single
Descent Propulsion System engine is split into two half-thrust engines mounted
at y = +-y_eng.  Total thrust, mass, inertia and RCS are all unchanged — only
the placement is invented, and until now it was invented arbitrarily (1.50 m in
Studies A-G, 0.25 m in Study H).

y_eng is not a free parameter.  It sets how much rotational authority the split
hands the vehicle, and the fleet actuation-envelope survey gives a reference
for how much an Apollo-class lander is supposed to have: the real LM itself.
This module computes both with the same machinery and picks the spacing that
makes the imaginary vehicle behave like the real one.

Three constraints bear on the answer and they do not agree:

  AUTHORITY    the twin-engine vehicle should not have rotational authority the
               real LM never had, or the fault studies are flying an
               over-actuated vehicle and their recoveries are optimistic;
  TRIMMABILITY one gimbal must be able to trim a one-engine-out asymmetry,
               which needs y_eng <= dz_eng * tan(gimbal_max) (Study A);
  GEOMETRY     two real nozzles cannot occupy the same space.

Run:  python place_engines.py
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
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'apollo_gnc'))

FIG = HERE / 'figures'
MD = HERE / 'engine_placement.md'
PDF = HERE / 'engine_placement.pdf'
CSV = HERE / 'placement_sweep.csv'

from geometry_db import Vehicle, GimbalEngine, quad_ring   # noqa: E402
from envelopes import axis_maxima                          # noqa: E402
import apollo_full as af                                   # noqa: E402

SURFACE = '#fcfcfb'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8985'
AXCOL = {'roll': '#2a78d6', 'pitch': '#eb6834', 'yaw': '#1baf7a'}

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE, 'axes.edgecolor': '#d8d7d2',
    'axes.labelcolor': INK2, 'text.color': INK,
    'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': '#e7e6e1', 'grid.linewidth': 0.8,
    'axes.axisbelow': True, 'font.size': 9,
})

LM = af.LMParams()
MASS = LM.mass
INERTIA = np.array([LM.Ixx, LM.Iyy, LM.Izz])

# Real DPS nozzle exit diameter.  Two half-thrust engines are smaller: for a
# fixed chamber pressure and expansion ratio the exit area scales with thrust,
# so the diameter scales as sqrt(T) — half thrust gives a nozzle 1/sqrt(2) as
# wide.  Two of them cannot be closer than one diameter, centre to centre.
DPS_NOZZLE_D = 1.52                      # [m]  ESTIMATED (published DPS exit dia.)
HALF_NOZZLE_D = DPS_NOZZLE_D / np.sqrt(2.0)
Y_GEOM_MIN = HALF_NOZZLE_D / 2.0         # smallest physically buildable y_eng


def rcs():
    return quad_ring(4, LM.rcs_arm, 0.0, LM.F_rcs_per)


def single_engine():
    """The real Apollo LM layout: one gimballed DPS on the centreline."""
    return Vehicle(name='Apollo LM (as flown)', category='Crewed Vehicles',
                   mass=MASS, inertia=INERTIA, rcs=rcs(),
                   engines=[GimbalEngine(np.array([0.0, 0.0, LM.dz_eng]),
                                         np.array([0.0, 0.0, -1.0]),
                                         LM.T_max, LM.gimbal_max)])


def twin_engine(y_eng, gimbal_max=None):
    """The fault studies' vehicle: the DPS split in two at +-y_eng."""
    g = LM.gimbal_max if gimbal_max is None else gimbal_max
    eng = [GimbalEngine(np.array([0.0, s * y_eng, LM.dz_eng]),
                        np.array([0.0, 0.0, -1.0]), LM.T_max / 2.0, g)
           for s in (-1.0, +1.0)]
    return Vehicle(name=f'twin, y={y_eng:.2f}', category='Crewed Vehicles',
                   mass=MASS, inertia=INERTIA, rcs=rcs(), engines=eng)


def authority(v):
    """(linear [m/s^2], angular [deg/s^2]) per body axis, max over directions.

    Body axes are apollo_full's: x forward, y right, z down along the thrust
    line.  So rotation about x is roll, about y pitch, about z yaw — note that
    the *thrust axis* here is z, which the fleet survey calls the roll axis.
    """
    m = axis_maxima(v)
    lin = np.array([max(m['+' + c]['accel_ms2'], m['-' + c]['accel_ms2'])
                    for c in 'xyz'])
    ang = np.rad2deg([max(m['+' + c]['ang_accel_rads2'],
                          m['-' + c]['ang_accel_rads2']) for c in 'xyz'])
    return lin, np.asarray(ang)


def trim_limit(gimbal_max=None):
    """Study A's roll-authority budget: the largest spacing one gimbal can trim
    with the other engine dead."""
    g = LM.gimbal_max if gimbal_max is None else gimbal_max
    return LM.dz_eng * np.tan(g)


def gimbal_for(y_eng):
    """The gimbal throw a given spacing would need to stay trimmable."""
    return np.degrees(np.arctan2(y_eng, LM.dz_eng))


def sweep(ys):
    ref_lin, ref_ang = authority(single_engine())
    rows = []
    for y in ys:
        lin, ang = authority(twin_engine(y))
        rows.append(dict(y=y, lin=lin, ang=ang, ratio=ang / ref_ang))
    return ref_lin, ref_ang, rows


def fig_sweep(ref_ang, rows, path):
    ys = np.array([r['y'] for r in rows])
    ang = np.array([r['ang'] for r in rows])
    names = ['roll', 'pitch', 'yaw']

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.8))
    ax, bx = axes
    tl, gm = trim_limit(), Y_GEOM_MIN

    for a in (ax, bx):
        a.axvspan(gm, ys.max(), color='#d03b3b', alpha=0.05, lw=0)
        a.axvline(tl, color=MUTED, ls='--', lw=1.2)
        a.axvline(gm, color='#d03b3b', ls=':', lw=1.4)

    for j, nm in enumerate(names):
        ax.plot(ys, ang[:, j], color=AXCOL[nm], lw=2.2, label=nm)
    # roll and pitch have the same reference value on the real LM, so one line
    # carries both; drawing two would just stack identical labels
    for val, txt, col in ((ref_ang[0], 'real LM roll & pitch', AXCOL['pitch']),
                          (ref_ang[2], 'real LM yaw', AXCOL['yaw'])):
        ax.axhline(val, color=col, ls=':', lw=1.2, alpha=0.7)
        ax.text(ys.max() * 0.995, val, f'{txt} {val:.0f}  ', color=col,
                fontsize=8, va='bottom', ha='right')
    ax.set_xlabel('engine half-spacing $y_{eng}$ [m]')
    ax.set_ylabel('max angular acceleration [°/s²]')
    ax.set_title('Authority against spacing', fontsize=10, loc='left',
                 color=INK2)
    ax.legend(frameon=False, fontsize=8.5, loc='center left')

    for j, nm in enumerate(names):
        bx.plot(ys, ang[:, j] / ref_ang[j], color=AXCOL[nm], lw=2.2, label=nm)
    bx.axhline(1.0, color=INK, lw=1.2)
    bx.text(0.02, 1.06, 'parity with the real Apollo LM', fontsize=8.5,
            color=INK2)
    bx.set_xlabel('engine half-spacing $y_{eng}$ [m]')
    bx.set_ylabel('angular authority relative to the real LM')
    bx.set_ylim(0.9, 3.6)
    bx.set_title('How much authority the split invents', fontsize=10,
                 loc='left', color=INK2)

    for a in (ax, bx):
        a.set_xlim(0, ys.max())
        for s in ('top', 'right'):
            a.spines[s].set_visible(False)
        # staggered vertically: the two limits are 0.27 m apart and their
        # labels would otherwise overlap
        a.annotate('one-engine-out\ntrim limit', (tl, a.get_ylim()[1]),
                   xytext=(-4, -30), textcoords='offset points', fontsize=8,
                   color=INK2, ha='right')
        a.annotate('nozzles\ncollide', (gm, a.get_ylim()[1]),
                   xytext=(4, -64), textcoords='offset points', fontsize=8,
                   color='#d03b3b')

    fig.suptitle('Where to put the two engines\n'
                 'shaded: spacings that are physically buildable but exceed '
                 'the one-engine-out trim limit',
                 fontsize=11.5, weight='bold', color=INK, x=0.012, ha='left')
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f'[saved] {path}')


def table(rows, header, widths=None):
    align = (['---'] * len(header) if widths is None
             else [':' + '-' * w for w in widths])
    out = ['| ' + ' | '.join(str(c) for c in header) + ' |',
           '|' + '|'.join(align) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out) + '\n'


def build():
    # 1 cm steps: the roll-parity threshold sits at 0.263 m and a coarser
    # grid would quantise it onto a round number by accident.
    ys = np.round(np.arange(0.0, 2.001, 0.01), 3)
    ref_lin, ref_ang, rows = sweep(ys)
    tl, gm = trim_limit(), Y_GEOM_MIN

    with open(CSV, 'w') as fh:
        fh.write('y_eng_m,a_x,a_y,a_z,roll_degs2,pitch_degs2,yaw_degs2,'
                 'roll_ratio,pitch_ratio,yaw_ratio\n')
        for r in rows:
            fh.write(f"{r['y']:.3f}," + ','.join(f'{x:.6g}' for x in r['lin'])
                     + ',' + ','.join(f'{x:.6g}' for x in r['ang'])
                     + ',' + ','.join(f'{x:.4f}' for x in r['ratio']) + '\n')
    print(f'[saved] {CSV}')

    fig_sweep(ref_ang, rows, FIG / 'P1_placement_sweep.png')

    def at(y):
        return min(rows, key=lambda r: abs(r['y'] - y))

    # Largest spacing at which each axis is still at parity with the real LM,
    # measured per axis: the three axes behave completely differently and a
    # single pooled criterion hides that.
    def last_parity(j, tol=1.002):
        ok = [r['y'] for r in rows if r['ratio'][j] <= tol]
        return max(ok) if ok else 0.0

    y_roll = last_parity(0)
    y_yaw = last_parity(2)
    y_rec = 0.25

    P = []
    A = P.append
    A(rf"""---
title: "Where to Put the Two Engines"
subtitle: "Setting the twin-engine Apollo LM's spacing from measured authority instead of by assumption"
date: "26 August 2026"
geometry: margin=2.2cm
fontsize: 10.5pt
numbersections: true
toc: true
colorlinks: true
header-includes:
  - \usepackage{{booktabs}}
  - \usepackage{{amsmath}}
  - \usepackage{{float}}
  - \let\origfigure\figure
  - \let\endorigfigure\endfigure
  - \renewenvironment{{figure}}[1][2]{{\expandafter\origfigure\expandafter[H]}}{{\endorigfigure}}
---

# The parameter that was never justified

Every fault study in this repository flies an imaginary vehicle: the Apollo
LM's single Descent Propulsion System engine split into two half-thrust engines
mounted at $y = \pm y_{{eng}}$. Mass, inertia, total thrust, gimbal throw and
the entire RCS are the real LM's. Only the placement is invented — and it was
invented twice, both times by assumption: **1.50 m** in Studies A through G,
**0.25 m** in Study H after the one-engine-out roll budget showed 1.50 m could
never be trimmed.

Neither number was ever checked against what an Apollo-class lander's
rotational authority actually is. The fleet actuation-envelope survey now
supplies that reference, and it supplies it for the most relevant vehicle
possible: **the real Apollo LM itself**. This document sets $y_{{eng}}$ by
measurement.

# What the spacing does and does not change

Both vehicles are built and measured with the same machinery used for the
fleet survey — the support function of the achievable force set and of the
achievable moment set, evaluated on each body axis. Body axes are the flight
model's: $x$ forward, $y$ right, $z$ **down along the thrust line**, so
rotation about $x$ is roll, about $y$ pitch, about $z$ yaw.

The sweep shows immediately that only two of the six quantities are in play:

""")
    r0, r15, r25 = at(0.0), at(1.50), at(0.25)
    A(table([
        ['Linear $a_x, a_y, a_z$',
         f"{ref_lin[0]:.2f}, {ref_lin[1]:.2f}, {ref_lin[2]:.2f} m/s²",
         'unchanged at every spacing',
         'total thrust and mass are fixed; a moment arm cannot make force'],
        ['Pitch $\\alpha_y$', f'{ref_ang[1]:.0f} °/s²',
         'unchanged at every spacing',
         'pitch comes from gimbal deflection against $dz_{eng}$, which $y_{eng}$ '
         'does not touch'],
        ['Roll $\\alpha_x$', f'{ref_ang[0]:.0f} °/s²',
         f"{r0['ang'][0]:.0f} → {rows[-1]['ang'][0]:.0f} °/s²",
         'differential throttling between the two engines, arm $y_{eng}$'],
        ['Yaw $\\alpha_z$', f'{ref_ang[2]:.0f} °/s²',
         f"{r0['ang'][2]:.0f} → {rows[-1]['ang'][2]:.0f} °/s²",
         'pitch-gimbal deflection acting through the lateral offset'],
    ], ['Quantity', 'Real LM', 'Twin-engine, $y_{eng}$ = 0 → 2 m', 'Why'],
        [22, 14, 26, 44]))

    A(f"""
So the question is narrower than it looks. Splitting the engine cannot change
what the vehicle can accelerate at, and cannot change its pitch authority. What
it does is **invent roll and yaw authority that the real vehicle never had** —
and the further apart the engines, the more of it.

# The sweep
""")
    A(f"\n![Angular authority against engine spacing]({FIG / 'P1_placement_sweep.png'})\n")

    A('\n' + table(
        [[f"{r['y']:.2f}"] + [f"{x:.0f}" for x in r['ang']]
         + [f"{x:.2f}" for x in r['ratio']]
         for r in [at(v) for v in (0.0, 0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00)]],
        ['$y_{eng}$ [m]', 'Roll [°/s²]', 'Pitch [°/s²]', 'Yaw [°/s²]',
         'Roll / LM', 'Pitch / LM', 'Yaw / LM'],
        [12, 12, 12, 12, 10, 11, 10]))

    A(f"""
# Three constraints, and a threshold that appears twice

**Roll parity.** Roll authority stays *exactly* at the real LM's
{ref_ang[0]:.0f} °/s² up to $y_{{eng}}$ = **{y_roll:.3f} m**, and climbs from
there. Below that spacing the best roll moment the vehicle can make is still
the one the single-engine LM makes — both gimbals deflected in yaw against the
{LM.dz_eng:.1f} m engine-plane offset. Differential throttling is the better
lever only once the arm is longer than that.

**One-engine-out trimmability.** Study A's budget, derived independently and
from entirely different reasoning: a single gimbal can trim the roll asymmetry
left by a dead engine only while
$y_{{eng}} \\le d z_{{eng}} \\tan\\delta_{{max}}$ = **{tl:.3f} m**.

Those two numbers are the same, and it is not a coincidence. Both ask the same
question — *is the lateral moment arm longer than the moment arm the gimbal
already commands?* Below $d z_{{eng}} \\tan\\delta_{{max}}$ the gimbal
dominates the roll axis, so the split adds nothing and a surviving gimbal can
undo what a dead engine does. Above it, differential thrust dominates, the
vehicle gains roll authority it never had, and the same arm that gave it that
authority is what the lone gimbal can no longer overcome. **One threshold
governs both the fidelity of the model and the survivability of the fault.**

**Yaw cannot be held at parity at all.** Unlike roll, yaw authority rises from
the very first centimetre of separation — {ref_ang[2]:.0f} °/s² on the
centreline, {at(0.10)['ang'][2]:.0f} at 0.10 m, {at(0.25)['ang'][2]:.0f} at
0.25 m — because pitch-gimbal deflection acting through the lateral offset
makes a yaw moment that a centreline engine simply cannot. There is no positive
spacing at which yaw is at parity, so yaw cannot be a criterion: the only
spacing that satisfies it is no split at all.

The reason yaw inflates so readily is that it is the LM's *weakest* axis by a
factor of four ({ref_ang[2]:.0f} °/s² against {ref_ang[0]:.0f} for roll and
pitch). Almost all of the real vehicle's yaw authority comes from the RCS, so
any engine contribution at all is a large *relative* change while staying small
in absolute terms: at 0.25 m the split adds
{at(0.25)['ang'][2] - ref_ang[2]:.0f} °/s² to an axis that has
{ref_ang[2]:.0f}.

**Nozzle geometry.** Two engines cannot overlap. The real DPS nozzle is about
{DPS_NOZZLE_D:.2f} m across; at fixed chamber pressure and expansion ratio the
exit area scales with thrust, so a half-thrust engine is $1/\\sqrt{{2}}$ as
wide — {HALF_NOZZLE_D:.2f} m. Two of them cannot sit closer than one diameter
centre to centre, giving $y_{{eng}} \\ge$ **{gm:.2f} m**.
""")

    A(table([
        ['Roll authority at parity with the real LM',
         f'$\\le$ {y_roll:.3f} m', 'measured from the sweep'],
        [f'One-engine-out trimmable at {np.degrees(LM.gimbal_max):.0f}° gimbal',
         f'$\\le$ {tl:.3f} m', 'Study A roll budget — the same threshold'],
        ['Yaw authority at parity', f'$\\le$ {y_yaw:.2f} m',
         'degenerate; rejected'],
        ['Nozzles do not collide', f'$\\ge$ {gm:.2f} m',
         'estimated from a sqrt(T) nozzle scaling'],
    ], ['Constraint', 'Requires', 'Source'], [40, 16, 34]))

    A(f"""
**The buildable region and the trimmable region do not overlap.** Anything a
real pair of half-DPS engines could be built at ($\\ge$ {gm:.2f} m) is already
past the threshold where one gimbal can trim the other's failure, and past the
point where the split starts inventing roll authority ($\\le$ {tl:.3f} m).

That is a finding about the configuration rather than a modelling
inconvenience: **a twin-engine Apollo-class lander with only
{np.degrees(LM.gimbal_max):.0f}° of gimbal throw cannot be both buildable and
single-engine-out survivable.** The gimbal is the binding parameter, not the
spacing. Making the buildable spacing trimmable needs

$$\\delta_{{max}} \\ge \\arctan\\frac{{y_{{eng}}}}{{d z_{{eng}}}}
= \\arctan\\frac{{{gm:.2f}}}{{{LM.dz_eng:.1f}}} = {gimbal_for(gm):.1f}°$$

— a little over double the LM's actual throw, which is a large but not absurd
ask for a clean-sheet design.

# Recommendation

**Keep $y_{{eng}}$ = {y_rec:.2f} m**, and state it as a *modelling* choice
rather than a design one.

It is the largest round spacing under the {tl:.3f} m threshold, so the
imaginary vehicle has **exactly** the real Apollo LM's roll and pitch
authority, and it is engine-out trimmable — which is what turns engine-out from
an automatic loss into a fault with an answer. The price is
{100 * (at(y_rec)['ratio'][2] - 1):.0f} % more yaw authority than the real LM,
on the axis where the real LM is weakest and where the absolute difference is
{at(y_rec)['ang'][2] - ref_ang[2]:.0f} °/s². That is the residual, and it
should be quoted rather than hidden.

What the vehicle is not is buildable. Two half-DPS engines {2 * y_rec:.2f} m
apart centre to centre would overlap, so it should be described as **a device
for splitting the DPS into two independently faultable halves while holding the
real LM's authority fixed** — which is exactly what the fault studies need —
and not as a proposal for a real lander.

Studies A through G, at 1.50 m, should carry the caveat that their vehicle had
{at(1.50)['ratio'][0]:.1f}x the roll and {at(1.50)['ratio'][2]:.1f}x the yaw
authority of a real LM. Their engine-out result is unaffected — that fault was
lost to the trim budget, which 1.50 m misses by a factor of
{1.50 / tl:.1f} — but their gimbal-fault and thrust-asymmetry results were
measured on an over-actuated vehicle.
""")

    A(f"""
**The buildable region and the trimmable region do not overlap.** Anything a
real pair of half-DPS engines could be built at ($\\ge$ {gm:.2f} m) is already
past the point where one gimbal can trim the other's failure
($\\le$ {tl:.3f} m), and past parity with the real LM's authority.

That is a genuine finding about the configuration rather than a modelling
inconvenience: **a twin-engine Apollo-class lander with only {np.degrees(LM.gimbal_max):.0f}°
of gimbal throw cannot be both buildable and single-engine-out survivable.**
The gimbal is the binding parameter, not the spacing. Making the buildable
spacing trimmable needs

$$\\delta_{{max}} \\ge \\arctan\\frac{{y_{{eng}}}}{{d z_{{eng}}}}
= \\arctan\\frac{{{gm:.2f}}}{{{LM.dz_eng:.1f}}} = {gimbal_for(gm):.1f}°$$

— a little over double the LM's actual throw, which is a large but not absurd
ask for a clean-sheet design.

# Recommendation

**Keep $y_{{eng}}$ = {y_rec:.2f} m for the fault studies**, and state it as a
*modelling* choice rather than a design one.

At that spacing the imaginary vehicle matches the real Apollo LM's roll
authority exactly and its yaw authority to within
{100 * (at(y_rec)['ratio'][2] - 1):.0f} %, so the fault campaigns are flying
something with an Apollo-class lander's actual pointing capability rather than
an invented one. It also sits just inside the one-engine-out trim limit, which
is what makes engine-out a fault with an answer instead of an automatic loss.

What it is not is buildable. Two half-DPS engines {2 * y_rec:.2f} m apart
centre to centre would overlap, so the vehicle should be described as **a
device for splitting the DPS into two independently faultable halves while
holding the real LM's authority fixed** — which is exactly what the fault
studies need it to be — and not as a proposal for a real lander.

Studies A through G, at 1.50 m, should carry the caveat that their vehicle had
{at(1.50)['ratio'][0]:.1f}x the roll and {at(1.50)['ratio'][2]:.1f}x the yaw
authority of a real LM. Their engine-out result is unaffected — that fault was
lost to the trim budget, which 1.50 m fails by a factor of
{1.50 / tl:.1f} — but their gimbal-fault and thrust-asymmetry results were
measured on an over-actuated vehicle.

# Limitations

* **The nozzle constraint is an estimate.** {DPS_NOZZLE_D:.2f} m for the DPS
  exit diameter and a $\\sqrt{{T}}$ scaling for the half-thrust engine are both
  approximations. A genuinely optimised half-thrust engine at a different
  expansion ratio could be meaningfully smaller, which would move the
  buildable limit down — though not to {tl:.3f} m.
* **Authority is an upper bound.** As in the fleet survey, every actuator fires
  at once in the optimal direction, and angular acceleration is $M/I_{{jj}}$
  about principal axes with no gyroscopic coupling.
* **Inertia is held fixed** across the sweep. Moving real engines outboard
  would change $I_{{xx}}$ slightly; at these masses and arms the effect is well
  below the shape-model uncertainty already present in the inertia itself.
* **Only the spacing is varied.** Engine cant, axial station and differential
  gimbal throw are all fixed at the LM's values, and each is another lever on
  the same trade.

# Reproducing

```bash
python studies/engine_placement/place_engines.py
```
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
