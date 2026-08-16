"""
Nominal vs engine-out comparison.
═════════════════════════════════
Overlays the converged case-1 (both engines, y_eng = 1.5 m) and case-3
(engine 2 dead, y_eng = 0.2 m) solutions on the quantities the failure actually
changes: the descent geometry, the roll axis it loads up, the thrust the
survivor has to supply, and the RCS effort spent holding the asymmetry.

Reads solution.npz from each case directory, so run run_case_study.py first.
Writes nominal_vs_engine_out.png next to this script.
"""

import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'src', 'apollo_gnc'))  # shared engine
import apollo_full as af

C_NOM, C_OUT = '#2a78d6', '#eb6834'          # validated categorical slots 1, 2
INK, INK_MUTED = '#0b0b0b', '#52514e'

SERIES = [('Nominal (2 engines)', '01_nominal_2_engines', 1.5, C_NOM),
          ('Engine 2 out ($y_{eng}$ = 0.2 m)',
           '03_engine_out_survivable_geometry', 0.2, C_OUT)]

runs = []
for label, dirname, y_eng, color in SERIES:
    path = os.path.join(HERE, dirname, 'solution.npz')
    if not os.path.exists(path):
        sys.exit(f'missing {path} — run run_case_study.py first')
    d = np.load(path)
    runs.append((label, d['Xs'], d['Us'], af.LMParams(y_eng=y_eng), color))

cfg = af.OCPConfig()


def panels(label, Xs, Us, lm):
    """(title, t, y) for each comparison panel."""
    t  = np.arange(Xs.shape[1]) * cfg.dt
    tu = np.arange(Us.shape[1]) * cfg.dt
    B  = lm.rcs_geometry()[2]
    f  = Us[af.N_U_DPS:af.N_U_DPS + lm.n_rcs, :]
    wrench = B @ f
    return [
        ('Altitude  $-z_E$  [m]',              t,  -Xs[2]),
        ('Horizontal range  $\\sqrt{x_E^2+y_E^2}$  [m]',
                                               t,  np.hypot(Xs[0], Xs[1])),
        ('Roll  $\\phi$  [°]',                 t,  np.rad2deg(Xs[6])),
        ('Roll rate  $p$  [°/s]',              t,  np.rad2deg(Xs[9])),
        ('Total DPS thrust  [N]',              t,  Xs[af.IDX_T].sum(axis=0)),
        ('Yaw-gimbal deflection  $\\delta_y$  [°]',
                                               t,  np.rad2deg(Xs[af.IDX_DY[0]])),
        ('RCS roll moment  $L$  [N·m]',        tu, wrench[3]),
        ('Total RCS thrust  $\\Sigma f_i$  [N]', tu, f.sum(axis=0)),
    ]

specs = [panels(lbl, Xs, Us, lm) for lbl, Xs, Us, lm, _ in runs]

fig, axes = plt.subplots(4, 2, figsize=(14, 15), sharex=True)
fig.suptitle('Apollo LM — Nominal vs Single-Engine-Out Powered Descent',
             fontsize=15, weight='bold', color=INK)

limits = {  # panel title -> constraint line to draw
    'Roll rate  $p$  [°/s]': (-np.rad2deg(cfg.omega_max),
                               np.rad2deg(cfg.omega_max)),
    'Roll  $\\phi$  [°]':    (-np.rad2deg(cfg.euler_max),
                               np.rad2deg(cfg.euler_max)),
}

for i, ax in enumerate(axes.flat):
    title = specs[0][i][0]
    for (lbl, *_ , color), spec in zip(runs, specs):
        _, t, y = spec[i]
        ax.plot(t, y, color=color, lw=2, label=lbl,
                solid_capstyle='round', zorder=3)
    if title in limits:
        for v in limits[title]:
            ax.axhline(v, ls='--', lw=1, color=INK_MUTED, alpha=0.55, zorder=1)
    if title == 'Total DPS thrust  [N]':
        for v, txt in ((45040, '2-engine max'), (22520, '1-engine max'),
                       (12530, 'hover')):
            ax.axhline(v, ls=':', lw=1, color=INK_MUTED, alpha=0.7, zorder=1)
            ax.annotate(txt, xy=(78, v), fontsize=8, color=INK_MUTED,
                        va='bottom', ha='right')
    if title.startswith('Yaw-gimbal'):
        for v in (-6, 6):
            ax.axhline(v, ls='--', lw=1, color=INK_MUTED, alpha=0.55, zorder=1)
    ax.set_ylabel(title, fontsize=10, color=INK_MUTED)
    ax.grid(True, alpha=0.25, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color(INK_MUTED)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    if i >= 6:
        ax.set_xlabel('Time [s]', color=INK_MUTED)

# one legend for the whole figure — identity is never colour-alone
axes.flat[0].legend(fontsize=10, loc='upper right', framealpha=0.95)

fig.tight_layout(rect=[0, 0, 1, 0.965])
out = os.path.join(HERE, 'nominal_vs_engine_out.png')
fig.savefig(out, dpi=150, facecolor='white')
print(f'[saved] {out}')

# a compact numeric comparison for the writeup
print(f"\n{'quantity':34s} {'nominal':>12s} {'engine-out':>12s}")
rows = []
for lbl, Xs, Us, lm, _ in runs:
    f = Us[af.N_U_DPS:af.N_U_DPS + lm.n_rcs, :]
    rows.append(dict(
        peak_roll=np.abs(np.rad2deg(Xs[6])).max(),
        peak_p=np.abs(np.rad2deg(Xs[9])).max(),
        peak_T=Xs[af.IDX_T].sum(axis=0).max(),
        dy_mean=np.rad2deg(np.abs(Xs[af.IDX_DY[0]]).mean()),
        rcs_impulse=f.sum() * cfg.dt,
        td_speed=np.linalg.norm(Xs[3:6, -1]),
        pos_err=np.linalg.norm(Xs[0:2, -1])))
for k, name in [('peak_roll', 'peak |roll| [deg]'),
                ('peak_p', 'peak |roll rate| [deg/s]'),
                ('peak_T', 'peak total thrust [N]'),
                ('dy_mean', 'mean |yaw gimbal| E1 [deg]'),
                ('rcs_impulse', 'RCS impulse [N.s]'),
                ('td_speed', 'terminal speed [m/s]'),
                ('pos_err', 'terminal horiz. error [m]')]:
    print(f'{name:34s} {rows[0][k]:12.2f} {rows[1][k]:12.2f}')
