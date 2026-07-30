"""
Cross-case comparison for the degraded-gimbal study.
════════════════════════════════════════════════════
Produces two figures:

  gimbal_tracking.png     small multiples — engine 2's yaw gimbal, commanded vs
                          actual, one panel per case.  This is the figure that
                          shows the actuator falling behind its command.
  degradation_metrics.png what the degradation costs: optimal objective,
                          tracking error, how the optimiser redistributes gimbal
                          effort onto the healthy engine, and RCS usage.

Reads solution.npz / metrics.json from each case directory, so run
run_gimbal_study.py first.
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

CASES = [('G1', 'G1_nominal',                    'baseline',    '#2a78d6'),
         ('G2', 'G2_mild_wn1.5',                 'mild',        '#eda100'),
         ('G3', 'G3_severe_wn0.6',               'severe',      '#eb6834'),
         ('G4', 'G4_underdamped_wn1.0_zeta0.25', 'underdamped', '#e34948')]
C_E1, C_E2 = '#2a78d6', '#eb6834'
INK, INK_MUTED = '#0b0b0b', '#52514e'
DEGRADED = 1

cfg = af.OCPConfig()
runs = []
for tag, dirname, kind, color in CASES:
    d = os.path.join(HERE, dirname)
    if not os.path.exists(os.path.join(d, 'solution.npz')):
        sys.exit(f'missing results in {dirname} — run run_gimbal_study.py first')
    z = np.load(os.path.join(d, 'solution.npz'))
    with open(os.path.join(d, 'metrics.json')) as fh:
        M = json.load(fh)
    runs.append(dict(tag=tag, kind=kind, color=color,
                     Xs=z['Xs'], Us=z['Us'], M=M))

# ══════════════════════════════════════════════════════════════════════
#  FIGURE 1 — small multiples of the degraded gimbal's tracking
# ══════════════════════════════════════════════════════════════════════

fig, axes = plt.subplots(2, 2, figsize=(14, 8.5), sharex=True, sharey=True)
fig.suptitle('Apollo LM — Engine 2 Yaw Gimbal: Commanded vs Actual\n'
             'engine 1 healthy throughout; only engine 2\'s actuator changes',
             fontsize=14, weight='bold', color=INK, y=0.985)

for ax, r in zip(axes.flat, runs):
    Xs, Us, M = r['Xs'], r['Us'], r['M']
    t  = np.arange(Xs.shape[1]) * cfg.dt
    tu = np.arange(Us.shape[1]) * cfg.dt
    ax.step(tu, np.rad2deg(Us[af.IDX_U_DY[DEGRADED]]), where='post',
            color=INK_MUTED, lw=1.4, ls='--', label='commanded', zorder=3)
    ax.plot(t, np.rad2deg(Xs[af.IDX_DY[DEGRADED]]), color=r['color'], lw=2.2,
            label='actual', zorder=4)
    for v in (-6, 6):
        ax.axhline(v, ls=':', lw=1, color=INK_MUTED, alpha=0.7, zorder=1)
    ax.set_title(f"{r['tag']}  {r['kind']} — "
                 f"$\\omega_n$={M['wn']:.1f} rad/s, $\\zeta$={M['zeta']:.2f}"
                 f"   ·   RMS error {M['gimbal_rms_err_E2_deg']:.2f}°",
                 fontsize=10.5, color=INK, loc='left')
    ax.grid(True, alpha=0.25, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color(INK_MUTED)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    ax.legend(fontsize=9, loc='lower right', framealpha=0.95)

for ax in axes[-1]:
    ax.set_xlabel('Time [s]', color=INK_MUTED)
for ax in axes[:, 0]:
    ax.set_ylabel('Yaw gimbal  $\\delta_y$  [°]', color=INK_MUTED)

fig.tight_layout(rect=[0, 0, 1, 0.945])
out1 = os.path.join(HERE, 'gimbal_tracking.png')
fig.savefig(out1, dpi=150, facecolor='white')
print(f'[saved] {out1}')

# ══════════════════════════════════════════════════════════════════════
#  FIGURE 2 — what the degradation costs
# ══════════════════════════════════════════════════════════════════════

tags   = [r['tag'] for r in runs]
colors = [r['color'] for r in runs]
x      = np.arange(len(runs))
J0     = runs[0]['M']['objective']
rcs0   = runs[0]['M']['rcs_impulse_Ns']

fig, axes = plt.subplots(2, 2, figsize=(14, 9))
fig.suptitle('Apollo LM — Cost of Degrading One Gimbal Actuator',
             fontsize=14, weight='bold', color=INK, y=0.985)


def barpanel(ax, vals, title, ylabel, fmt='{:.2f}', pad_frac=0.18):
    ax.bar(x, vals, width=0.6, color=colors, zorder=3)
    for xi, v in zip(x, vals):
        # keep the label outside the bar whichever way it points
        ax.annotate(fmt.format(v), xy=(xi, v), xytext=(0, 4 if v >= 0 else -13),
                    textcoords='offset points', ha='center', fontsize=9.5,
                    color=INK, weight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['tag']}\n{r['kind']}" for r in runs], fontsize=9)
    ax.set_ylabel(ylabel, color=INK_MUTED)
    ax.set_title(title, fontsize=10.5, color=INK, loc='left')
    lo = min(0, min(vals) * 1.45)
    ax.set_ylim(lo, max(vals) * (1 + pad_frac) if max(vals) > 0 else 1)
    ax.grid(True, axis='y', alpha=0.25, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color(INK_MUTED)
    ax.tick_params(colors=INK_MUTED)


barpanel(axes[0, 0],
         [100 * (r['M']['objective'] / J0 - 1) for r in runs],
         'Optimal objective $J$, change from baseline\n'
         'nonconvex NLP — the ordering between cases is NOT resolvable '
         '(see README)',
         'Change in $J$  [%]', fmt='{:+.2f}%', pad_frac=0.24)

barpanel(axes[0, 1],
         [r['M']['gimbal_rms_err_E2_deg'] for r in runs],
         'Engine 2 gimbal command-tracking error',
         'RMS  $|\\delta - \\delta_{cmd}|$  [°]', fmt='{:.3f}°')

# gimbal effort, per engine — identity here is the engine, not the case
w = 0.36
e1 = [r['M']['gimbal_rms_cmd_E1_deg'] for r in runs]
e2 = [r['M']['gimbal_rms_cmd_E2_deg'] for r in runs]
ax = axes[1, 0]
ax.bar(x - w / 2 - 0.01, e1, width=w, color=C_E1, label='E1 (healthy)', zorder=3)
ax.bar(x + w / 2 + 0.01, e2, width=w, color=C_E2, label='E2 (degraded)',
       zorder=3)
for xi, (a, b) in enumerate(zip(e1, e2)):
    ax.annotate(f'{a:.2f}', xy=(xi - w / 2, a), xytext=(0, 4),
                textcoords='offset points', ha='center', fontsize=9, color=INK)
    ax.annotate(f'{b:.2f}', xy=(xi + w / 2, b), xytext=(0, 4),
                textcoords='offset points', ha='center', fontsize=9, color=INK)
ax.set_xticks(x)
ax.set_xticklabels([f"{r['tag']}\n{r['kind']}" for r in runs], fontsize=9)
ax.set_ylabel('RMS gimbal command  [°]', color=INK_MUTED)
ax.set_title('Where the optimiser puts its gimbal effort', fontsize=11,
             color=INK, loc='left')
ax.set_ylim(0, max(e1 + e2) * 1.2)
ax.grid(True, axis='y', alpha=0.25, zorder=0)
ax.set_axisbelow(True)
for s in ('top', 'right'):
    ax.spines[s].set_visible(False)
for s in ('bottom', 'left'):
    ax.spines[s].set_color(INK_MUTED)
ax.tick_params(colors=INK_MUTED)
ax.legend(fontsize=9, framealpha=0.95)

barpanel(axes[1, 1],
         [100 * (r['M']['rcs_impulse_Ns'] / rcs0 - 1) for r in runs],
         'RCS propellant use, change from baseline',
         'Change in RCS impulse  [%]', fmt='{:+.1f}%')

fig.tight_layout(rect=[0, 0, 1, 0.96])
out2 = os.path.join(HERE, 'degradation_metrics.png')
fig.savefig(out2, dpi=150, facecolor='white')
print(f'[saved] {out2}')

# ── console table for the writeup ───────────────────────────────────────────
rows = [('objective J',                'objective',            '{:.4e}'),
        ('  vs baseline [%]',          None,                   ''),
        ('E2 gimbal RMS track err [°]', 'gimbal_rms_err_E2_deg', '{:.3f}'),
        ('E2 gimbal max track err [°]', 'gimbal_max_err_E2_deg', '{:.3f}'),
        ('E1 RMS gimbal command [°]',  'gimbal_rms_cmd_E1_deg', '{:.3f}'),
        ('E2 RMS gimbal command [°]',  'gimbal_rms_cmd_E2_deg', '{:.3f}'),
        ('peak differential thrust [N]', 'peak_diff_thrust_N',  '{:.0f}'),
        ('peak |roll| [°]',            'peak_roll_deg',         '{:.2f}'),
        ('peak |p| [°/s]',             'peak_p_degs',           '{:.2f}'),
        ('RCS impulse [N·s]',          'rcs_impulse_Ns',        '{:.0f}'),
        ('DPS impulse [N·s]',          'dps_impulse_Ns',        '{:.3e}'),
        ('terminal speed [m/s]',       'terminal_speed_ms',     '{:.4f}'),
        ('terminal pos err [m]',       'terminal_pos_err_m',    '{:.4f}'),
        ('terminal att err [°]',       'terminal_att_err_deg',  '{:.4f}'),
        ('IPOPT iterations',           'iterations',            '{:.0f}')]

print(f"\n{'metric':32s}" + ''.join(f'{t:>15s}' for t in tags))
for name, key, fmt in rows:
    if key is None:
        cells = [f'{100 * (r["M"]["objective"] / J0 - 1):+.2f}%' for r in runs]
    else:
        cells = [fmt.format(r['M'][key]) for r in runs]
    print(f'{name:32s}' + ''.join(f'{c:>15s}' for c in cells))
