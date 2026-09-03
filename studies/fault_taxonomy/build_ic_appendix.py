"""
STUDY G — Appendix A: the initial conditions, engine by engine and state by state
═════════════════════════════════════════════════════════════════════════════════
Writes out exactly what was flown, so the campaign can be audited or replayed
without re-reading the code:

  1. the vehicle geometry — where the engines are, what they can do, and which
     one carries the fault;
  2. the sampling box of every regime, coordinate by coordinate;
  3. every initial condition actually used, all 22 states of each;
  4. the per-sample outcome of every fault from every one of them.

The point of (4) is that the design is *paired*: one set of initial conditions
per regime, reused for all sixteen plants.  So the honest answer to "which
initial conditions were tested for fault X" is "all of them, the same ones as
for every other fault" — and the outcome grid is where that pairing becomes
visible, because two faults differing on one sample differ on that sample alone.

Run:  python build_ic_appendix.py      (after the campaign)
"""

import os
import sys
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')
MD = os.path.join(HERE, 'initial_conditions_appendix.md')
PDF = os.path.join(HERE, 'initial_conditions_appendix.pdf')
CSV = os.path.join(RESULTS, 'G_initial_conditions.csv')

import apollo_full as af      # noqa: E402
import fault_catalogue as fc  # noqa: E402
import campaign as cp         # noqa: E402


def table(rows, header, widths=None):
    align = (['---'] * len(header) if widths is None
             else [':' + '-' * w for w in widths])
    out = ['| ' + ' | '.join(str(c) for c in header) + ' |',
           '|' + '|'.join(align) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out) + '\n'


#  land / gate miss / no trajectory / lost before the planner ran
MARK = {'land': 'L', 'gate_miss': 'g', 'no_recovery': '.', 'already_lost': 'x'}


def build():
    lm = af.LMParams()
    cfg = af.OCPConfig()
    st = np.load(os.path.join(RESULTS, 'G_states.npz'), allow_pickle=True)
    regs = [str(r) for r in st['regimes']]
    rows = cp.read_csv(os.path.join(RESULTS, 'G_samples.csv'))
    by = {(r['regime'], int(r['sample']), r['fault']): r['outcome']
          for r in rows}
    faults = [k for k in fc.KEYS
              if any(r['fault'] == k for r in rows)]

    P = []
    A = P.append

    A(r"""---
title: "Study G — Appendix A: Initial Conditions and Vehicle Geometry"
subtitle: "Every state flown, and the engine layout it was flown with"
date: "17 August 2026"
geometry: margin=2.0cm
fontsize: 9pt
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

# Which initial conditions belong to which fault

**All of them, and they are the same ones.** The campaign is a *paired* design:
one set of initial conditions is drawn per regime and then reused, unchanged,
for every one of the sixteen plant configurations. That is deliberate and it is
what makes the study's comparisons work — because the state distribution is
literally identical across faults, any difference in landing rate is
attributable to the plant alone, and the healthy-vs-fault comparison becomes a
within-sample McNemar test on discordant pairs rather than a contrast between
two independently drawn samples.

So there is no per-fault initial-condition list to give. There is one list, of
""" + f"""{len(regs)} x {len(st['rows_' + regs[0]])} = """
      f"""{sum(len(st['rows_' + g]) for g in regs)} states, reproduced in full in
section 4; section 5 then shows what each fault did from each of them.
""")

    # ── 1. geometry ──────────────────────────────────────────────────────
    A("""
# The vehicle and where its engines are

The lander carries **two independently gimballed TVC engines**, each rated at
half the nominal DPS thrust, mounted symmetrically either side of the
centreline in a plane below the centre of gravity. Body axes are x forward,
y right, z **down**, so a positive `z` engine station is *below* the CG.
""")

    rows_g = []
    for i in range(lm.n_eng):
        x_e, y_e, z_e = lm.eng_pos(i)
        rows_g.append([
            f'Engine {i + 1} (index {i})',
            f'({x_e:+.2f}, {y_e:+.2f}, {z_e:+.2f})',
            f'{lm.T_min_eng:.0f} – {lm.T_max_eng:.0f}',
            f'{lm.T_hover_eng:.0f}',
            f'±{np.rad2deg(lm.gimbal_max):.1f}',
            'healthy in every case' if i != fc.ENG else '**carries the fault**'])
    A(table(rows_g,
            ['Engine', 'Body station (x, y, z) [m]', 'Thrust [N]',
             'Hover share [N]', 'Gimbal [°]', 'Role'],
            [18, 24, 14, 14, 10, 22]))

    A(f"""
Every fault in the catalogue acts on **engine 2** (index {fc.ENG}, body station
y = {lm.eng_pos(fc.ENG)[1]:+.2f} m). Engine 1 stays healthy throughout, so each
case is an *asymmetry* the vehicle has to trim as well as a loss of
performance. The vehicle is laterally symmetric, so which engine is chosen does
not matter — only that it is one of two.

The lateral half-spacing $y_{{eng}}$ = {lm.y_eng:.2f} m is the parameter behind
the engine-out result: a single gimbal can trim a one-engine-out roll asymmetry
only while $y_{{eng}} \\le d z_{{eng}} \\tan\\delta_{{max}}$ =
{lm.dz_eng * np.tan(lm.gimbal_max):.3f} m, and this vehicle is built at
{lm.y_eng:.2f} m — a factor of {lm.y_eng / (lm.dz_eng * np.tan(lm.gimbal_max)):.1f}
outside it.
""")

    rows_v = [
        ['Mass', f'{lm.mass:.0f} kg'],
        ['Inertia $I_{xx}, I_{yy}, I_{zz}$',
         f'{lm.Ixx:.0f}, {lm.Iyy:.0f}, {lm.Izz:.0f} kg·m²'],
        ['Lunar gravity', f'{lm.g_moon:.3f} m/s²'],
        ['Hover thrust (total)', f'{lm.T_hover:.0f} N'],
        ['DPS envelope (total)', f'{lm.T_min:.0f} – {lm.T_max:.0f} N'],
        ['Engine plane below CG, $dz_{eng}$', f'{lm.dz_eng:.2f} m'],
        ['Engine half-spacing, $y_{eng}$', f'{lm.y_eng:.2f} m'],
        ['Thrust lag $\\tau_T$ / gimbal $\\omega_n$, $\\zeta$',
         f'{lm.tau_T:.2f} s / {lm.gimbal_wn:.1f} rad/s, {lm.gimbal_zeta:.2f}'],
        ['RCS', f'{lm.n_quads} quads x 4 thrusters, {lm.F_rcs_per:.0f} N each, '
                f'arm {lm.rcs_arm:.2f} m'],
        ['Glide-slope cone', f'{np.rad2deg(cfg.glide_slope):.0f}° from horizontal'],
        ['Contact altitude (engine cut)', f'{cfg.h_contact:.1f} m'],
    ]
    A('\n' + table(rows_v, ['Vehicle parameter', 'Value'], [34, 46]))

    # ── 2. regime boxes ──────────────────────────────────────────────────
    A("""
# The sampling box of each regime

Initial conditions are scrambled Sobol points in these boxes, rejected if they
fall outside the approach cone or are already past the hard loss-of-control
criteria. `upset` additionally keeps only draws that are genuinely upset (a body
rate of at least 10 °/s on some axis, or at least 15° of tilt).
""")
    for g in regs:
        lo, hi = st[f'lo_{g}'], st[f'hi_{g}']
        rows_b = [[nm, u, f'{lo[i]:+.4g}', f'{hi[i]:+.4g}']
                  for i, (nm, u) in enumerate(zip(fc.ALL_NAMES, fc.ALL_UNITS))]
        A(f"\n## `{g}` — {fc.REG[g].label}\n\n{fc.REG[g].blurb}.\n")
        A('\n' + table(rows_b, ['State', 'Unit', 'lower', 'upper'],
                       [12, 8, 12, 12]))

    # ── 3. the states themselves ─────────────────────────────────────────
    A("""
# The initial conditions

Positions are in the landing-pad frame (x north, y east) with **altitude
positive up**; velocities are body-frame; angles are degrees. `T1`/`T2` are the
two engines' thrust states and `dp`/`dy` their pitch and yaw gimbal deflections,
with `_dot` the corresponding gimbal rates. Sampling the actuator states
directly is the point of the 22-dimensional box: a fault leaves the gimbals
deflected and the thrust away from trim, and those are states no 12-dimensional
sampling can reach.
""")

    rigid_hdr = ['#'] + [f'{n} [{u}]' for n, u in
                         zip(fc.RIGID_NAMES, fc.RIGID_UNITS)]
    act_hdr = ['#'] + [f'{n} [{u}]' for n, u in
                       zip(fc.ACT_NAMES, fc.ACT_UNITS)]
    # Per-column precision rather than a blanket %g: thirteen columns of
    # '+1.002e+04' do not fit the page, and metres of downrange do not need
    # four decimals to be reproducible.
    RIG_FMT = ['.0f', '.0f', '.0f', '.2f', '.2f', '.2f',
               '.2f', '.2f', '.2f', '.2f', '.2f', '.2f']
    ACT_FMT = ['.0f', '.2f', '.2f', '.2f', '.2f'] * 2

    def row_of(i, vals, fmts):
        return [i] + [format(v, f) for v, f in zip(vals, fmts)]
    flat = []
    for g in regs:
        R = st[f'rows_{g}']
        A(f'\n## `{g}` — {fc.REG[g].label}  ({len(R)} states)\n')
        A('\n### Rigid-body states\n')
        A('\n' + table([row_of(i, R[i, :12], RIG_FMT)
                        for i in range(len(R))], rigid_hdr))
        A('\n### Actuator states\n')
        A('\n' + table([row_of(i, R[i, 12:], ACT_FMT)
                        for i in range(len(R))], act_hdr))
        for i in range(len(R)):
            flat.append(dict(regime=g, sample=i,
                             **{n: float(v) for n, v in
                                zip(fc.ALL_NAMES, R[i])}))

    cp.write_csv(CSV, flat, fieldnames=['regime', 'sample'] + fc.ALL_NAMES)

    # ── 4. outcome grid ──────────────────────────────────────────────────
    A("""
# What each fault did from each of them

One grid per regime: rows are the sixteen plants, columns are the numbered
initial conditions above. The columns are the *same states* in every row, which
is what makes a row-to-row difference a statement about the plant.

`L` landed · `g` flew but missed the touchdown gate · `.` no trajectory found ·
`x` already lost before the planner ran
""")
    for g in regs:
        n = len(st[f'rows_{g}'])
        A(f'\n## `{g}` — {fc.REG[g].label}\n')
        grid = []
        for f in faults:
            marks = [MARK.get(by.get((g, i, f), ''), '?') for i in range(n)]
            grid.append([fc.CASES[f].label, '`' + ' '.join(marks) + '`',
                         f'{marks.count("L")}/{n}'])
        # The marks column is set in a monospace span so each symbol sits under
        # its own column number; in a proportional face they drift apart and
        # the grid stops being readable as a grid.
        A('\n' + table(grid, ['Fault',
                              '`' + ' '.join(str(i) for i in range(n)) + '`',
                              'landed'], [30, 24, 8]))

    A(f"""
# Files

```
results/G_initial_conditions.csv   the {len(flat)} states above, one row each
results/G_states.npz               the same states plus every regime's box
results/G_samples.csv              one row per solve (state x plant)
```
""")

    open(MD, 'w').write('\n'.join(P))
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
