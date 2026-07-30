"""
The four gimbal actuator models, on their own.
═════════════════════════════════════════════
Before looking at any trajectory: what does each (wn, zeta) pair actually do?
Analytic second-order step and frequency response for

    d_ddot = wn^2 (d_cmd - d) - 2 zeta wn d_dot

  left   response to a step command to the 6 deg gimbal limit
  right  closed-loop magnitude response, with the OCP's own 1 rad/s command
         update rate marked — past that line the actuator cannot follow what
         the optimiser is allowed to ask for

Writes actuator_step_response.png next to this script.  No solve required.
"""

import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apollo_full as af

# validated categorical slots 1-4 (dataviz reference palette); G1 is the
# reference case so it takes slot 1, degradations run warm
CASES = [('G1  $\\omega_n$=4.0, $\\zeta$=0.70  (baseline)', 4.0, 0.70, '#2a78d6'),
         ('G2  $\\omega_n$=1.5, $\\zeta$=0.70  (mild)',     1.5, 0.70, '#eda100'),
         ('G3  $\\omega_n$=0.6, $\\zeta$=0.70  (severe)',   0.6, 0.70, '#eb6834'),
         ('G4  $\\omega_n$=1.0, $\\zeta$=0.25  (underdamped)',
                                                            1.0, 0.25, '#e34948')]
INK, INK_MUTED = '#0b0b0b', '#52514e'

lm = af.LMParams()
cfg = af.OCPConfig()
STEP = np.rad2deg(lm.gimbal_max)          # step to the 6 deg gimbal limit


def step_response(t, wn, zeta):
    """Unit step response of the second-order servo, scaled to STEP."""
    if zeta < 1.0:
        wd = wn * np.sqrt(1 - zeta**2)
        y = 1 - np.exp(-zeta * wn * t) * (np.cos(wd * t)
                                          + zeta / np.sqrt(1 - zeta**2)
                                          * np.sin(wd * t))
    elif zeta == 1.0:
        y = 1 - np.exp(-wn * t) * (1 + wn * t)
    else:
        r1 = -wn * (zeta - np.sqrt(zeta**2 - 1))
        r2 = -wn * (zeta + np.sqrt(zeta**2 - 1))
        y = 1 + (r2 * np.exp(r1 * t) - r1 * np.exp(r2 * t)) / (r1 - r2)
    return STEP * y


fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 5.6))
fig.suptitle('Apollo LM — Gimbal Actuator Models Compared '
             '(second-order servo, one axis)',
             fontsize=14, weight='bold', color=INK)

# ── left: step response ─────────────────────────────────────────────────────
t = np.linspace(0, 20, 2000)
for label, wn, zeta, color in CASES:
    axL.plot(t, step_response(t, wn, zeta), color=color, lw=2,
             label=label, zorder=3)
    # settling time, 4/(zeta*wn) rule of thumb — direct-labelled, no legend-only
    ts = 4.0 / (zeta * wn)
    if ts <= t[-1]:
        axL.plot([ts], [step_response(np.array([ts]), wn, zeta)[0]], 'o',
                 ms=7, color=color, mec='white', mew=1.6, zorder=4)

axL.axhline(STEP, ls='--', lw=1, color=INK_MUTED, alpha=0.6, zorder=1)
axL.annotate('commanded (6° limit)', xy=(19.6, STEP), xytext=(0, 5),
             textcoords='offset points', ha='right', fontsize=9,
             color=INK_MUTED)
# the grid interval: one command is held this long
axL.axvspan(0, cfg.dt, color=INK_MUTED, alpha=0.10, zorder=0)
axL.annotate(f'one command\ninterval ({cfg.dt:.0f} s)', xy=(cfg.dt, STEP * 0.12),
             xytext=(10, 0), textcoords='offset points', fontsize=8.5,
             color=INK_MUTED, va='center')
axL.set_xlabel('Time since step command  [s]', color=INK_MUTED)
axL.set_ylabel('Gimbal deflection  $\\delta$  [°]', color=INK_MUTED)
axL.set_xlim(0, 20)
axL.set_ylim(0, STEP * 1.55)
axL.grid(True, alpha=0.25, zorder=0)
axL.set_axisbelow(True)
for s in ('top', 'right'):
    axL.spines[s].set_visible(False)
for s in ('bottom', 'left'):
    axL.spines[s].set_color(INK_MUTED)
axL.tick_params(colors=INK_MUTED)
axL.set_title('Step response  (dot = 2% settling time)', fontsize=11,
              color=INK, loc='left')
axL.legend(fontsize=9, loc='lower right', framealpha=0.95)

# ── right: closed-loop magnitude response ───────────────────────────────────
w = np.logspace(-2, 1.4, 600)
for label, wn, zeta, color in CASES:
    mag = 1.0 / np.sqrt((1 - (w / wn)**2)**2 + (2 * zeta * w / wn)**2)
    axR.semilogx(w, 20 * np.log10(mag), color=color, lw=2, zorder=3,
                 label=label.split('  ')[0])
    axR.plot([wn], [20 * np.log10(1.0 / np.sqrt((2 * zeta)**2))], 'o', ms=7,
             color=color, mec='white', mew=1.6, zorder=4)

axR.axhline(-3, ls=':', lw=1, color=INK_MUTED, alpha=0.8, zorder=1)
axR.annotate('−3 dB', xy=(0.0105, -3), xytext=(0, 4),
             textcoords='offset points', fontsize=9, color=INK_MUTED)
w_grid = np.pi / cfg.dt          # Nyquist rate of the 1 s command grid
axR.axvline(w_grid, ls='--', lw=1.2, color=INK_MUTED, alpha=0.7, zorder=2)
axR.annotate(f'command-grid Nyquist\n{w_grid:.2f} rad/s', xy=(w_grid, 8),
             xytext=(-8, 0), textcoords='offset points', ha='right',
             fontsize=9, color=INK_MUTED)

axR.set_xlabel('Command frequency  $\\omega$  [rad/s]', color=INK_MUTED)
axR.set_ylabel('Gimbal response magnitude  [dB]', color=INK_MUTED)
axR.set_ylim(-40, 14)
axR.grid(True, alpha=0.25, which='both', zorder=0)
axR.set_axisbelow(True)
for s in ('top', 'right'):
    axR.spines[s].set_visible(False)
for s in ('bottom', 'left'):
    axR.spines[s].set_color(INK_MUTED)
axR.tick_params(colors=INK_MUTED)
axR.set_title('Magnitude response  (dot = $\\omega_n$)', fontsize=11,
              color=INK, loc='left')
axR.legend(fontsize=9, loc='lower left', framealpha=0.95)

fig.tight_layout(rect=[0, 0, 1, 0.94])
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'actuator_step_response.png')
fig.savefig(out, dpi=150, facecolor='white')
print(f'[saved] {out}')

print(f"\n{'case':14s}{'wn':>7s}{'zeta':>7s}{'f_n [Hz]':>10s}"
      f"{'settle [s]':>12s}{'overshoot':>11s}{'-3dB [rad/s]':>14s}")
for label, wn, zeta, _ in CASES:
    os_pct = (100 * np.exp(-np.pi * zeta / np.sqrt(1 - zeta**2))
              if zeta < 1 else 0.0)
    # closed-loop -3 dB bandwidth of the standard 2nd-order form
    bw = wn * np.sqrt(1 - 2 * zeta**2
                      + np.sqrt(4 * zeta**4 - 4 * zeta**2 + 2))
    print(f'{label.split("  ")[0]:14s}{wn:7.2f}{zeta:7.2f}'
          f'{wn / (2 * np.pi):10.3f}{4 / (zeta * wn):12.1f}'
          f'{os_pct:10.0f}%{bw:14.2f}')
