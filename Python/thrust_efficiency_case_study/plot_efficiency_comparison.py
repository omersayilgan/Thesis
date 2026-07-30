"""
Cross-case trajectory comparison for the thrust-efficiency study.
════════════════════════════════════════════════════════════════
Overlays the converged cases on the quantities the efficiency loss drives.
Only converged runs are plotted — a non-converged iterate is not a trajectory
and does not belong on a comparison chart.

eta is an ordered severity, so the cases are coloured with a single-hue
sequential ramp (darker = more degraded) rather than categorical hues.

Writes efficiency_comparison.png and efficiency_cost.png next to this script.
"""

import os
import sys
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import apollo_full as af

WEAK = 1
INK, INK_MUTED = '#0b0b0b', '#52514e'
C_WASTE = '#eb6834'

DIRS = ['E1_eta1.00', 'E2_eta0.85', 'E3_eta0.65',
        'E4_eta0.40', 'E5_eta0.25', 'E6_eta0.15']

cfg = af.OCPConfig()
runs = []
for d in DIRS:
    p = os.path.join(HERE, d)
    if not os.path.exists(os.path.join(p, 'metrics.json')):
        continue
    with open(os.path.join(p, 'metrics.json')) as fh:
        M = json.load(fh)
    z = np.load(os.path.join(p, 'solution.npz'))
    runs.append(dict(tag=d.split('_')[0], eta=M['eta'], M=M,
                     Xs=z['Xs'], Us=z['Us'], status=M['status']))
if not runs:
    sys.exit('no results — run run_efficiency_study.py first')

conv = [r for r in runs if r['status'] == 'solved']
# single-hue sequential ramp over the converged cases, darker = lower eta
ramp = plt.get_cmap('Blues')(np.linspace(0.38, 0.95, len(conv)))
for r, c in zip(sorted(conv, key=lambda r: -r['eta']), ramp):
    r['color'] = c

lm_of = lambda eta: af.LMParams(thrust_eff_eng={WEAK: eta})


def series(r):
    Xs, Us, lm = r['Xs'], r['Us'], lm_of(r['eta'])
    t = np.arange(Xs.shape[1]) * cfg.dt
    T = Xs[af.IDX_T]
    F = np.array([lm.eta_of(i) * T[i] for i in range(lm.n_eng)])
    L_tvc = sum(lm.eng_pos(i)[1] *
                (-F[i] * np.cos(Xs[af.IDX_DP[i]]) * np.cos(Xs[af.IDX_DY[i]]))
                for i in range(lm.n_eng))
    return [
        ('Total delivered thrust  [N]',              t, F.sum(axis=0)),
        ('Weak engine command  $T_2$  [N]',          t, T[WEAK]),
        ('Healthy engine command  $T_1$  [N]',       t, T[1 - WEAK]),
        ('Delivered thrust asymmetry  $F_1-F_2$  [N]', t, F[1 - WEAK] - F[WEAK]),
        ('TVC roll moment  $L$  [N·m]',              t, L_tvc),
        ('Altitude  $-z_E$  [m]',                    t, -Xs[2]),
    ]


specs = [series(r) for r in conv]

fig, axes = plt.subplots(3, 2, figsize=(14, 13), sharex=True)
fig.suptitle('Apollo LM — Powered Descent with a Partial-Thrust Engine\n'
             'engine 2 delivers only $\\eta$ of its commanded thrust; '
             'engine 1 healthy',
             fontsize=14, weight='bold', color=INK, y=0.985)

for i, ax in enumerate(axes.flat):
    title = specs[0][i][0]
    for r, spec in zip(conv, specs):
        _, t, y = spec[i]
        ax.plot(t, y, color=r['color'], lw=2,
                label=f"{r['tag']}  $\\eta$={r['eta']:.2f}", zorder=3)
    if title.startswith('Total delivered'):
        for v, txt in ((45040, '2-engine max'), (12530, 'hover')):
            ax.axhline(v, ls=':', lw=1, color=INK_MUTED, alpha=0.75, zorder=1)
            ax.annotate(txt, xy=(78, v), fontsize=8, color=INK_MUTED,
                        va='bottom', ha='right')
    if 'command' in title:
        ax.axhline(af.LMParams().T_max_eng, ls='--', lw=1, color=INK_MUTED,
                   alpha=0.6, zorder=1)
        ax.annotate('command limit 22 520 N', xy=(78, af.LMParams().T_max_eng),
                    fontsize=8, color=INK_MUTED, va='bottom', ha='right')
    if title.startswith(('Delivered thrust asym', 'TVC roll')):
        ax.axhline(0.0, ls=':', lw=1, color=INK_MUTED, alpha=0.75, zorder=1)
    ax.set_ylabel(title, fontsize=10, color=INK_MUTED)
    ax.grid(True, alpha=0.25, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color(INK_MUTED)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    if i >= 4:
        ax.set_xlabel('Time [s]', color=INK_MUTED)

axes.flat[0].legend(fontsize=9, loc='upper right', framealpha=0.95, ncol=2)

fig.tight_layout(rect=[0, 0, 1, 0.955])
out1 = os.path.join(HERE, 'efficiency_comparison.png')
fig.savefig(out1, dpi=150, facecolor='white')
print(f'[saved] {out1}')

# ══════════════════════════════════════════════════════════════════════
#  what the loss costs
# ══════════════════════════════════════════════════════════════════════

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('Apollo LM — Cost of a Partial-Thrust Engine',
             fontsize=14, weight='bold', color=INK, y=0.98)
etas = [r['eta'] for r in conv]
cols = [r['color'] for r in conv]
xs = np.arange(len(conv))
labels = [f"{r['tag']}\n$\\eta$={r['eta']:.2f}" for r in conv]
J0 = [r for r in conv if r['eta'] == 1.0][0]['M']['objective']


def bars(ax, vals, title, ylabel, fmt):
    ax.bar(xs, vals, width=0.6, color=cols, zorder=3)
    for xi, v in zip(xs, vals):
        ax.annotate(fmt.format(v), xy=(xi, v), xytext=(0, 4 if v >= 0 else -13),
                    textcoords='offset points', ha='center', fontsize=9.5,
                    color=INK, weight='bold')
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel(ylabel, color=INK_MUTED)
    ax.set_title(title, fontsize=11, color=INK, loc='left')
    ax.set_ylim(min(0, min(vals) * 1.4), max(vals) * 1.2 if max(vals) > 0 else 1)
    ax.grid(True, axis='y', alpha=0.25, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color(INK_MUTED)
    ax.tick_params(colors=INK_MUTED)


bars(axes[0], [100 * (r['M']['objective'] / J0 - 1) for r in conv],
     'Optimal objective $J$ vs baseline\n(nonconvex — small gaps not resolvable)',
     'Change in $J$  [%]', '{:+.1f}%')
bars(axes[1], [r['M']['wasted_impulse_Ns'] / 1e3 for r in conv],
     'Impulse burnt but not delivered',
     'Wasted impulse  [kN·s]', '{:.0f}')
bars(axes[2], [r['M']['mean_abs_tvc_roll_Nm'] for r in conv],
     'Mean |TVC roll moment| carried',
     'Mean $|L|$  [N·m]', '{:.0f}')

fig.tight_layout(rect=[0, 0, 1, 0.93])
out2 = os.path.join(HERE, 'efficiency_cost.png')
fig.savefig(out2, dpi=150, facecolor='white')
print(f'[saved] {out2}')

# ── table ───────────────────────────────────────────────────────────────────
rows = [('status', '{}'), ('objective', '{:.4e}'),
        ('peak_delivered_total_N', '{:.0f}'),
        ('mean_cmd_weak_N', '{:.0f}'), ('mean_cmd_strong_N', '{:.0f}'),
        ('dps_impulse_cmd_Ns', '{:.3e}'),
        ('dps_impulse_delivered_Ns', '{:.3e}'),
        ('wasted_impulse_Ns', '{:.3e}'),
        ('mean_abs_tvc_roll_Nm', '{:.0f}'),
        ('mean_abs_gimbal_dy_deg', '{:.2f}'),
        ('rcs_impulse_Ns', '{:.0f}'), ('time_to_contact_s', '{:.0f}'),
        ('peak_roll_deg', '{:.2f}'), ('terminal_speed_ms', '{:.2e}'),
        ('terminal_pos_err_m', '{:.3f}'), ('iterations', '{:.0f}')]
print(f"\n{'metric':28s}" + ''.join(f"{f'eta={r['eta']:.2f}':>13s}"
                                    for r in runs))
for key, fmt in rows:
    print(f'{key:28s}' + ''.join(f'{fmt.format(r["M"][key]):>13s}'
                                 for r in runs))
