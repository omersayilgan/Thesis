"""
STUDY G — trajectory figures
════════════════════════════
Turns results/G_trajectories.npz into the visual companion to the landing-rate
tables: what the vehicle actually flew, fault by fault and state by state.

Three views, each answering a different question:

  T1  <regime>_profile   altitude against distance-to-pad, one panel per fault,
                         all of that regime's initial conditions overlaid.
                         Shows how the recovery is shaped and where the glide
                         cone binds.
  T2  <regime>_ground    the same trajectories seen from above.  Shows lateral
                         excursion and whether the vehicle arrives on the pad
                         or beside it.
  T3  <regime>_one_ic    one initial condition, all sixteen plants.  This is
                         the study's premise made visible: identical state,
                         different vehicle, different future.  The sample drawn
                         is the one the faults disagree on most.

Colour means outcome (T1/T2) or fault class (T3) — never both in one figure.
Runs in seconds; needs run_trajectories.py to have been run first.
"""

import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')

import fault_catalogue as fc   # noqa: E402
import campaign as cp          # noqa: E402
import apollo_full as af       # noqa: E402

SURFACE = '#fcfcfb'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8985'
STATUS = {'land': '#0ca30c', 'gate_miss': '#fab219',
          'no_recovery': '#d03b3b', 'already_lost': '#8a8985'}
OUT_LABEL = {'land': 'landed', 'gate_miss': 'flew, missed the gate',
             'no_recovery': 'no trajectory found',
             'already_lost': 'lost before the planner ran'}
CLASS_COLOR = {'none': '#9a9994', 'additive': '#2a78d6',
               'multiplicative': '#eb6834', 'structural': '#1baf7a'}

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE,
    'axes.edgecolor': '#d8d7d2', 'axes.labelcolor': INK2,
    'text.color': INK, 'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': '#e7e6e1', 'grid.linewidth': 0.7,
    'axes.axisbelow': True, 'font.size': 8,
})


def klass(structure):
    if structure == 'none':
        return 'none'
    return 'multiplicative' if 'multiplicative' in structure else structure


def load():
    tj = np.load(os.path.join(RESULTS, 'G_trajectories.npz'))
    rows = cp.read_csv(os.path.join(RESULTS, 'G_samples.csv'))
    st = np.load(os.path.join(RESULTS, 'G_states.npz'), allow_pickle=True)
    outcome = {(r['regime'], int(r['sample']), r['fault']): r['outcome']
               for r in rows}
    regs = [str(g) for g in st['regimes']]
    states = {g: st[f'rows_{g}'] for g in regs}
    return tj, outcome, regs, states


def path(tj, reg, i, f):
    """Powered arc + ballistic settle, concatenated, or None."""
    k = f'{reg}|{i}|{f}'
    if f'X|{k}' not in tj:
        return None
    return np.hstack([tj[f'X|{k}'], tj[f'F|{k}']])


def faults_present(outcome):
    have = {f for (_, _, f) in outcome}
    return [k for k in fc.KEYS if k in have]


# ══════════════════════════════════════════════════════════════════════
#  T1 / T2 — one panel per fault, every initial condition overlaid
# ══════════════════════════════════════════════════════════════════════

def grid_figure(tj, outcome, states, reg, faults, mode, path_out):
    n_ic = len(states[reg])
    ncol = 4
    nrow = int(np.ceil(len(faults) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(13.5, 3.0 * nrow),
                             squeeze=False)

    # common limits so panels are comparable at a glance — a per-panel autoscale
    # would make a 40 m excursion and a 900 m one look identical
    lim = 0.0
    alt_max = 0.0
    for f in faults:
        for i in range(n_ic):
            P = path(tj, reg, i, f)
            if P is None:
                continue
            lim = max(lim, float(np.hypot(P[0], P[1]).max()))
            alt_max = max(alt_max, float((-P[2]).max()))
    for i in range(n_ic):
        r = states[reg][i]
        lim = max(lim, float(np.hypot(r[0], r[1])))
        alt_max = max(alt_max, float(r[2]))

    cfg = af.OCPConfig()
    for j, f in enumerate(faults):
        ax = axes[j // ncol][j % ncol]
        landed = 0
        for i in range(n_ic):
            oc = outcome.get((reg, i, f), '')
            P = path(tj, reg, i, f)
            if oc == 'land':
                landed += 1
            if P is None:
                # no trajectory exists from this state: mark where it started,
                # because an absent line is otherwise indistinguishable from a
                # state that was never sampled
                r = states[reg][i]
                xy = (np.hypot(r[0], r[1]), r[2]) if mode == 'profile' \
                    else (r[0], r[1])
                ax.plot(*xy, 'x', color=STATUS[oc or 'no_recovery'], ms=5,
                        mew=1.4, zorder=4)
                continue
            c = STATUS.get(oc, MUTED)
            if mode == 'profile':
                ax.plot(np.hypot(P[0], P[1]), -P[2], color=c, lw=1.1,
                        alpha=0.85)
                ax.plot(np.hypot(P[0, 0], P[1, 0]), -P[2, 0], 'o', color=c,
                        ms=3.2, mec=SURFACE, mew=0.6)
            else:
                ax.plot(P[0], P[1], color=c, lw=1.1, alpha=0.85)
                ax.plot(P[0, 0], P[1, 0], 'o', color=c, ms=3.2, mec=SURFACE,
                        mew=0.6)

        if mode == 'profile':
            # the glide-slope cone: altitude must stay above tan(30 deg) * range
            rr = np.linspace(0, 1.05 * lim, 2)
            ax.plot(rr, np.tan(cfg.glide_slope) * rr, ls='--', lw=1.0,
                    color=MUTED, alpha=0.8)
            ax.set_xlim(0, 1.05 * lim)
            ax.set_ylim(0, 1.08 * alt_max)
        else:
            ax.plot(0, 0, '*', color='#d03b3b', ms=11, zorder=5)
            th = np.linspace(0, 2 * np.pi, 60)
            ax.plot(15 * np.cos(th), 15 * np.sin(th), lw=1.0, color=MUTED,
                    alpha=0.8)
            ax.set_xlim(-1.1 * lim, 1.1 * lim)
            ax.set_ylim(-1.1 * lim, 1.1 * lim)
            ax.set_aspect('equal', adjustable='box')

        ax.set_title(f'{fc.CASES[f].label}   ({landed}/{n_ic})', fontsize=8.5,
                     color=CLASS_COLOR[klass(fc.CASES[f].structure)],
                     loc='left', pad=4)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        if j // ncol == nrow - 1:
            ax.set_xlabel('distance to pad [m]' if mode == 'profile'
                          else '$x_E$ north [m]')
        if j % ncol == 0:
            ax.set_ylabel('altitude [m]' if mode == 'profile'
                          else '$y_E$ east [m]')

    for j in range(len(faults), nrow * ncol):
        axes[j // ncol][j % ncol].axis('off')

    what = ('Descent profiles' if mode == 'profile' else 'Ground tracks')
    extra = ('dashed line = 30° glide-slope cone'
             if mode == 'profile' else 'circle = 15 m landing gate, star = pad')
    fig.suptitle(f'{what} — {fc.REG[reg].label} regime, all {n_ic} initial '
                 f'conditions per fault\n{extra}; '
                 'panel title colour = FTC fault structure',
                 fontsize=11, weight='bold', color=INK, x=0.012, ha='left')
    fig.legend(handles=[Line2D([0], [0], color=STATUS[o], lw=2.4,
                               label=OUT_LABEL[o])
                        for o in ('land', 'gate_miss', 'no_recovery')],
               loc='lower center', ncol=3, frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, -0.004))
    fig.tight_layout(rect=[0, 0.028, 1, 0.945])
    fig.savefig(path_out, dpi=140)
    plt.close(fig)
    print(f'[saved] {path_out}')


# ══════════════════════════════════════════════════════════════════════
#  T3 — one initial condition, every plant
# ══════════════════════════════════════════════════════════════════════

def pick_ic(outcome, reg, faults, n_ic):
    """The sample the faults disagree on most — the one worth drawing."""
    best, best_i = -1, 0
    for i in range(n_ic):
        ocs = [outcome.get((reg, i, f), '') for f in faults]
        k = sum(o == 'land' for o in ocs)
        spread = min(k, len(faults) - k)      # maximal at a 50/50 split
        if spread > best:
            best, best_i = spread, i
    return best_i, best


def one_ic_figure(tj, outcome, states, reg, faults, path_out):
    n_ic = len(states[reg])
    i, spread = pick_ic(outcome, reg, faults, n_ic)
    r = states[reg][i]
    cfg = af.OCPConfig()

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0))
    ax, bx = axes
    drawn = {}
    for f in faults:
        P = path(tj, reg, i, f)
        cl = klass(fc.CASES[f].structure)
        c = CLASS_COLOR[cl]
        if P is None:
            continue
        drawn[f] = (P, c)
        lw = 2.4 if f == 'healthy' else 1.3
        ax.plot(np.hypot(P[0], P[1]), -P[2], color=c, lw=lw, alpha=0.9,
                zorder=3 if f == 'healthy' else 2)
        bx.plot(P[0], P[1], color=c, lw=lw, alpha=0.9,
                zorder=3 if f == 'healthy' else 2)

    lost = [f for f in faults if f not in drawn]
    lim = max([float(np.hypot(P[0], P[1]).max()) for P, _ in drawn.values()]
              + [float(np.hypot(r[0], r[1]))])
    rr = np.linspace(0, 1.05 * lim, 2)
    ax.plot(rr, np.tan(cfg.glide_slope) * rr, ls='--', lw=1.0, color=MUTED)
    ax.plot(np.hypot(r[0], r[1]), r[2], 'o', color=INK, ms=7, zorder=6)
    ax.annotate('the shared initial condition',
                (np.hypot(r[0], r[1]), r[2]), textcoords='offset points',
                xytext=(10, 8), fontsize=8.5, color=INK2)
    ax.set_xlabel('distance to pad [m]'); ax.set_ylabel('altitude [m]')
    ax.set_xlim(0, 1.05 * lim); ax.set_ylim(0, 1.1 * r[2])
    ax.set_title('Descent profile', fontsize=9.5, loc='left', color=INK2)

    bx.plot(0, 0, '*', color='#d03b3b', ms=13, zorder=6)
    th = np.linspace(0, 2 * np.pi, 60)
    bx.plot(15 * np.cos(th), 15 * np.sin(th), lw=1.0, color=MUTED)
    bx.plot(r[0], r[1], 'o', color=INK, ms=7, zorder=6)
    bx.set_xlabel('$x_E$ north [m]'); bx.set_ylabel('$y_E$ east [m]')
    bx.set_aspect('equal', adjustable='datalim')
    bx.set_title('Ground track', fontsize=9.5, loc='left', color=INK2)
    for a in (ax, bx):
        for s in ('top', 'right'):
            a.spines[s].set_visible(False)

    handles = [Line2D([0], [0], color=CLASS_COLOR[c], lw=2.2,
                      label='healthy' if c == 'none' else c)
               for c in ('none', 'additive', 'multiplicative', 'structural')]
    note = (f'{len(lost)} of {len(faults)} plants found no trajectory at all '
            f'from this state: ' +
            ', '.join(fc.CASES[f].short for f in lost)) if lost else \
        'every plant found a trajectory from this state'
    fig.suptitle(f'One initial condition, {len(faults)} vehicles — '
                 f'{fc.REG[reg].label} regime, sample {i}\n{note}',
                 fontsize=11, weight='bold', color=INK, x=0.012, ha='left')
    fig.legend(handles=handles, loc='lower center', ncol=4, frameon=False,
               fontsize=9, bbox_to_anchor=(0.5, -0.005))
    fig.tight_layout(rect=[0, 0.045, 1, 0.9])
    fig.savefig(path_out, dpi=150)
    plt.close(fig)
    print(f'[saved] {path_out}  (sample {i}, disagreement {spread})')


def main():
    tj, outcome, regs, states = load()
    faults = faults_present(outcome)
    for reg in regs:
        grid_figure(tj, outcome, states, reg, faults, 'profile',
                    os.path.join(FIGURES, f'T1_{reg}_profile.png'))
        grid_figure(tj, outcome, states, reg, faults, 'ground',
                    os.path.join(FIGURES, f'T2_{reg}_ground.png'))
        one_ic_figure(tj, outcome, states, reg, faults,
                      os.path.join(FIGURES, f'T3_{reg}_one_ic.png'))


if __name__ == '__main__':
    main()
