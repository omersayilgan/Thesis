"""
Roll-authority budget for the engine-out condition.
═══════════════════════════════════════════════════
Why case 02 is infeasible, in two panels:

  left   for each engine spacing, the roll moment the surviving engine applies
         (marker) against the authority available to cancel it (stacked bar:
         gimbal at its deflection limit + all 16 RCS thrusters)
  right  the same comparison swept over y_eng, locating the critical spacing
         below which single-engine-out flight is trimmable at all

Writes roll_authority_budget.png next to this script.
"""

import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apollo_full as af

# validated categorical slots 1-3 (see dataviz reference palette)
C_GIMBAL, C_REQ, C_RCS = '#2a78d6', '#eb6834', '#1baf7a'
INK, INK_MUTED = '#0b0b0b', '#52514e'


def budget(y_eng):
    """(required, gimbal, rcs) roll moments [N*m] for one surviving engine."""
    lm = af.LMParams(y_eng=y_eng)
    T = lm.T_hover / (lm.n_eng - 1)                  # survivor holds hover trim
    required = T * y_eng                             # |L| with gimbal centred
    gimbal   = T * lm.dz_eng * np.tan(lm.gimbal_max)
    # max roll moment the RCS box can deliver is the LP optimum over
    # f in [0, F]^16, i.e. the sum of the *positive* roll coefficients. Summing
    # |B[3,:]| would double-count: a quad's up- and down-firing jets sit at the
    # same r and give equal-and-opposite roll, so only one of the pair helps.
    rcs      = np.clip(lm.rcs_geometry()[2][3, :], 0.0, None).sum() * lm.F_rcs_per
    return required, gimbal, rcs


lm0 = af.LMParams()
_, G0, R0 = budget(1.0)                  # gimbal/RCS terms are y_eng-independent
T_SURV = lm0.T_hover / (lm0.n_eng - 1)
Y_CRIT = (G0 + R0) / T_SURV              # required(y) = T*y  crosses  G0 + R0

CASES = [('Nominal\n$y_{eng}$ = 1.5 m', 1.5),
         ('Re-spaced\n$y_{eng}$ = 0.2 m', 0.2)]

fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 5.6),
                               gridspec_kw=dict(width_ratios=[1, 1.15]))
fig.suptitle('Apollo LM — Single-Engine-Out Roll-Trim Authority',
             fontsize=14, weight='bold', color=INK)

# ── left: stacked authority vs required, per case ────────────────────────────
ypos = np.arange(len(CASES))[::-1]
h = 0.42
for y, (label, y_eng) in zip(ypos, CASES):
    req, gim, rcs = budget(y_eng)
    # stacked available authority; 2px surface gap between the two segments
    axL.barh(y, gim, height=h, color=C_GIMBAL, zorder=3)
    axL.barh(y, rcs, height=h, left=gim + 60, color=C_RCS, zorder=3)
    axL.text(gim / 2, y, f'{gim:,.0f}', ha='center', va='center',
             color='white', fontsize=9, weight='bold', zorder=4)
    axL.text(gim + 60 + rcs / 2, y, f'{rcs:,.0f}', ha='center', va='center',
             color='white', fontsize=9, weight='bold', zorder=4)
    # the demand
    axL.plot([req, req], [y - h * 0.95, y + h * 0.95], color=C_REQ, lw=2.5,
             zorder=5, solid_capstyle='butt')
    ok = req <= gim + rcs
    axL.annotate(f'required {req:,.0f} N·m'
                 f'\n{"within authority" if ok else "beyond authority"}',
                 xy=(req, y + h * 0.95), xytext=(8, 12),
                 textcoords='offset points', fontsize=9,
                 color=C_REQ if not ok else INK_MUTED,
                 weight='bold' if not ok else 'normal')

axL.set_yticks(ypos)
axL.set_yticklabels([c[0] for c in CASES], fontsize=10, color=INK)
axL.set_xlabel('Roll moment about the CG  $|L|$  [N·m]', color=INK_MUTED)
axL.set_xlim(0, 21000)
axL.set_ylim(-0.55, len(CASES) - 0.35)
axL.grid(True, axis='x', alpha=0.25, zorder=0)
axL.set_axisbelow(True)
for s in ('top', 'right', 'left'):
    axL.spines[s].set_visible(False)
axL.spines['bottom'].set_color(INK_MUTED)
axL.tick_params(colors=INK_MUTED)
axL.set_title('Authority available vs moment to cancel', fontsize=11,
              color=INK, loc='left')
axL.legend(handles=[
    plt.Line2D([0], [0], color=C_GIMBAL, lw=8,
               label=f'Gimbal @ {np.rad2deg(lm0.gimbal_max):.0f}°'),
    plt.Line2D([0], [0], color=C_RCS, lw=8, label='RCS (16 thrusters)'),
    plt.Line2D([0], [0], color=C_REQ, lw=2.5, label='Required')],
    fontsize=9, loc='lower right', framealpha=0.95)

# ── right: sweep over spacing ────────────────────────────────────────────────
yy = np.linspace(0, 1.6, 200)
req_sweep = T_SURV * yy
avail = np.full_like(yy, G0 + R0)

axR.fill_between(yy, avail, req_sweep, where=req_sweep > avail,
                 color=C_REQ, alpha=0.10, zorder=1)
axR.plot(yy, req_sweep, color=C_REQ, lw=2, zorder=3)
axR.plot(yy, avail, color=C_GIMBAL, lw=2, zorder=3)
axR.axhline(G0, color=C_GIMBAL, lw=1.2, ls=':', alpha=0.8, zorder=2)

axR.text(1.12, T_SURV * 1.12 + 700, 'Required', color=C_REQ,
         fontsize=10, weight='bold', ha='right')
axR.text(1.55, G0 + R0 + 400, 'Available (gimbal + RCS)', color=C_GIMBAL,
         fontsize=10, weight='bold', ha='right')
axR.text(1.55, G0 - 900, 'gimbal alone', color=C_GIMBAL, fontsize=9,
         ha='right', alpha=0.9)

axR.axvline(Y_CRIT, color=INK_MUTED, lw=1.2, ls='--', zorder=2)
axR.annotate(f'$y_{{crit}}$ = {Y_CRIT:.3f} m',
             xy=(Y_CRIT, T_SURV * Y_CRIT), xytext=(14, 26),
             textcoords='offset points', fontsize=10, weight='bold', color=INK,
             arrowprops=dict(arrowstyle='-', color=INK_MUTED, lw=1))

for label, y_eng in CASES:
    req = T_SURV * y_eng
    axR.plot([y_eng], [req], 'o', ms=9, color=C_REQ,
             mec='white', mew=2, zorder=5)
    # keep both labels clear of the 'gimbal alone' line and of each other
    axR.annotate(label.replace('\n', ' '), xy=(y_eng, req),
                 xytext=(-10, -20) if y_eng > 1 else (12, -20),
                 textcoords='offset points', fontsize=9, color=INK_MUTED,
                 ha='right' if y_eng > 1 else 'left')

axR.set_xlabel('Engine lateral half-spacing  $y_{eng}$  [m]', color=INK_MUTED)
axR.set_ylabel('Roll moment  [N·m]', color=INK_MUTED)
axR.set_xlim(0, 1.62)
axR.set_ylim(0, 21000)
axR.grid(True, alpha=0.25, zorder=0)
axR.set_axisbelow(True)
for s in ('top', 'right'):
    axR.spines[s].set_visible(False)
for s in ('bottom', 'left'):
    axR.spines[s].set_color(INK_MUTED)
axR.tick_params(colors=INK_MUTED)
axR.set_title('Trimmable only left of the critical spacing', fontsize=11,
              color=INK, loc='left')

fig.tight_layout(rect=[0, 0, 1, 0.94])
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'roll_authority_budget.png')
fig.savefig(out, dpi=150, facecolor='white')
print(f'[saved] {out}')
print(f'  T_surv = {T_SURV:.1f} N,  gimbal = {G0:.1f},  rcs = {R0:.1f},'
      f'  y_crit = {Y_CRIT:.4f} m')
