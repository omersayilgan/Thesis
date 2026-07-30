"""
The three thrust-efficiency regimes, analytically.
═════════════════════════════════════════════════
Engine 2 delivers eta * T.  Balanced hover needs both engines to deliver
T_hover/2, so the weak one must be commanded (T_hover/2)/eta — bounded by
T_max_eng.  Once it saturates, the leftover delivered-thrust asymmetry becomes a
roll moment, because the engines sit 1.5 m either side of the centreline.

  left   command the weak engine needs for balanced hover, against its limit
  right  the residual roll moment that saturation leaves, against the authority
         available to absorb it

Writes efficiency_regime_map.png next to this script.  No solve required.
"""

import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apollo_full as af

C_NEED, C_LIMIT, C_AUTH = '#eb6834', '#2a78d6', '#1baf7a'
INK, INK_MUTED = '#0b0b0b', '#52514e'

lm = af.LMParams()
Th, Tmax, y, z = lm.T_hover, lm.T_max_eng, lm.y_eng, lm.dz_eng
L_gim = Th * z * np.tan(lm.gimbal_max)
L_rcs = np.clip(lm.rcs_geometry()[2][3, :], 0.0, None).sum() * lm.F_rcs_per
L_auth = L_gim + L_rcs

ETA_SAT = (Th / 2) / Tmax                    # weak-engine command saturates here
# below saturation: F_weak = eta*Tmax, F_strong = Th - F_weak,
# residual roll  L = y*(F_strong - F_weak) = y*(Th - 2*eta*Tmax)
ETA_MIN = (Th - L_auth / y) / (2 * Tmax)     # where residual roll = authority

CASES = [(1.00, 'E1'), (0.85, 'E2'), (0.65, 'E3'),
         (0.40, 'E4'), (0.25, 'E5'), (0.15, 'E6')]

eta = np.linspace(0.10, 1.0, 900)
cmd = np.minimum((Th / 2) / eta, np.inf)
resid = np.where(eta >= ETA_SAT, 0.0, y * np.abs(Th - 2 * eta * Tmax))

fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 5.8))
fig.suptitle('Apollo LM — Partial-Thrust Engine: the Three Regimes',
             fontsize=14, weight='bold', color=INK, y=0.98)


def shade(ax):
    """Regime bands, common to both panels."""
    ax.axvspan(ETA_SAT, 1.02, color=C_AUTH, alpha=0.07, zorder=0)
    ax.axvspan(ETA_MIN, ETA_SAT, color='#eda100', alpha=0.10, zorder=0)
    ax.axvspan(0.09, ETA_MIN, color=C_NEED, alpha=0.10, zorder=0)
    for v in (ETA_SAT, ETA_MIN):
        ax.axvline(v, ls='--', lw=1.2, color=INK_MUTED, alpha=0.8, zorder=2)


# ── left: command required vs available ─────────────────────────────────────
shade(axL)
axL.plot(eta, cmd, color=C_NEED, lw=2.2, zorder=4)
axL.axhline(Tmax, color=C_LIMIT, lw=2, zorder=3)
axL.annotate(f'engine command limit  {Tmax:,.0f} N', xy=(0.99, Tmax),
             xytext=(0, 6), textcoords='offset points', ha='right',
             fontsize=9.5, color=C_LIMIT, weight='bold')
axL.annotate('command needed for\nbalanced hover  $(T_{hover}/2)/\\eta$',
             xy=(0.52, (Th / 2) / 0.52), xytext=(14, 26),
             textcoords='offset points', fontsize=9.5, color=C_NEED,
             weight='bold',
             arrowprops=dict(arrowstyle='-', color=C_NEED, lw=1))
axL.annotate(f'$\\eta_{{sat}}$ = {ETA_SAT:.3f}', xy=(ETA_SAT, Tmax * 1.42),
             xytext=(6, 0), textcoords='offset points', fontsize=9.5,
             color=INK, weight='bold')
axL.set_ylabel('Weak-engine thrust command  [N]', color=INK_MUTED)
axL.set_ylim(0, Tmax * 1.7)
axL.set_title('Can the weak engine be commanded high enough?', fontsize=11,
              color=INK, loc='left')

# ── right: residual roll moment vs authority ────────────────────────────────
shade(axR)
axR.fill_between(eta, L_auth, resid, where=resid > L_auth,
                 color=C_NEED, alpha=0.16, zorder=1)
axR.plot(eta, resid, color=C_NEED, lw=2.2, zorder=4)
axR.axhline(L_auth, color=C_AUTH, lw=2, zorder=3)
axR.axhline(L_gim, color=C_AUTH, lw=1.2, ls=':', alpha=0.85, zorder=3)
axR.annotate(f'gimbal + RCS  {L_auth:,.0f} N·m', xy=(0.99, L_auth),
             xytext=(0, 6), textcoords='offset points', ha='right',
             fontsize=9.5, color=C_AUTH, weight='bold')
axR.annotate(f'gimbal alone  {L_gim:,.0f}', xy=(0.99, L_gim), xytext=(0, -14),
             textcoords='offset points', ha='right', fontsize=9,
             color=C_AUTH, alpha=0.9)
axR.annotate('residual roll moment\nonce the weak engine saturates',
             xy=(0.17, y * abs(Th - 2 * 0.17 * Tmax)), xytext=(26, -6),
             textcoords='offset points', fontsize=9.5, color=C_NEED,
             weight='bold',
             arrowprops=dict(arrowstyle='-', color=C_NEED, lw=1))
axR.annotate(f'$\\eta_{{min}}$ = {ETA_MIN:.3f}', xy=(ETA_MIN, L_auth * 1.30),
             xytext=(9, 0), textcoords='offset points', ha='left',
             fontsize=9.5, color=INK, weight='bold')
axR.set_ylabel('Roll moment  [N·m]', color=INK_MUTED)
axR.set_ylim(0, max(resid.max(), L_auth) * 1.25)
axR.set_title('Can the leftover asymmetry be absorbed?', fontsize=11,
              color=INK, loc='left')

for ax in (axL, axR):
    for e, tag in CASES:
        ax.plot([e], [0], marker='^', ms=9, color=INK, clip_on=False, zorder=6)
        ax.annotate(tag, xy=(e, 0), xytext=(0, -22), textcoords='offset points',
                    ha='center', fontsize=9, color=INK, weight='bold')
    # labelpad clears the E1..E6 case markers sitting on the axis
    ax.set_xlabel('Thrust efficiency of engine 2   $\\eta$', color=INK_MUTED,
                  labelpad=24)
    ax.set_xlim(0.09, 1.02)
    ax.grid(True, alpha=0.22, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('bottom', 'left'):
        ax.spines[s].set_color(INK_MUTED)
    ax.tick_params(colors=INK_MUTED)

# one shared regime legend
from matplotlib.patches import Patch
axR.legend(handles=[
    Patch(facecolor=C_AUTH, alpha=0.30,
          label=f'$\\eta \\geq$ {ETA_SAT:.3f}   throttle-only trim'),
    Patch(facecolor='#eda100', alpha=0.35,
          label=f'{ETA_MIN:.3f}–{ETA_SAT:.3f}   gimbal + RCS committed'),
    Patch(facecolor=C_NEED, alpha=0.35,
          label=f'$\\eta <$ {ETA_MIN:.3f}   untrimmable')],
    fontsize=9, loc='upper right', framealpha=0.96)

fig.tight_layout(rect=[0, 0.02, 1, 0.94])
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'efficiency_regime_map.png')
fig.savefig(out, dpi=150, facecolor='white')
print(f'[saved] {out}')
print(f'  eta_sat = {ETA_SAT:.4f}   eta_min = {ETA_MIN:.4f}')
print(f'  L_gimbal = {L_gim:.1f}   L_rcs = {L_rcs:.1f}   total = {L_auth:.1f}')
