"""
STUDY H — analysis
══════════════════
Turns results/H_samples.csv into results/headline_H.json and the report's
figures.  The organising axis is *when on the descent the fault arrived*, so
every figure is drawn against injection time or the altitude that goes with it.
"""

import os
import sys
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')

import injection_catalogue as ic   # noqa: E402
import apollo_nominal as an        # noqa: E402
import fault_lib as fl             # noqa: E402
import campaign as cp              # noqa: E402

SURFACE = '#fcfcfb'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8985'
CLASS_COLOR = {'none': '#9a9994', 'additive': '#2a78d6',
               'multiplicative': '#eb6834', 'structural': '#1baf7a'}
STATUS = {'land': '#0ca30c', 'gate_miss': '#fab219',
          'no_recovery': '#d03b3b', 'already_lost': '#8a8985'}
OUT_LABEL = {'land': 'landed', 'gate_miss': 'flew, missed the gate',
             'no_recovery': 'no trajectory found',
             'already_lost': 'lost before the planner ran'}

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE, 'axes.edgecolor': '#d8d7d2',
    'axes.labelcolor': INK2, 'text.color': INK,
    'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': '#e7e6e1', 'grid.linewidth': 0.8,
    'axes.axisbelow': True, 'font.size': 9,
})


def load():
    rows = cp.read_csv(os.path.join(RESULTS, 'H_samples.csv'))
    for r in rows:
        r['lands'] = r['lands'] in ('True', 'true', '1')
        r['point'] = int(r['point'])
        for k in ('t_f', 'alt', 'rng', 'margin', 'v_horiz_0', 'v_desc_0',
                  'wall', 'v_vert', 'v_horiz', 'tilt_deg', 'pos_err',
                  'rate_deg'):
            try:
                r[k] = float(r[k])
            except (ValueError, KeyError, TypeError):
                r[k] = np.nan
    return rows


def nominal():
    return np.load(os.path.join(RESULTS, 'nominal.npz'))


# ══════════════════════════════════════════════════════════════════════
#  H1 — the nominal itself
# ══════════════════════════════════════════════════════════════════════

def fig_nominal(nom, times, path):
    X = nom['X']
    t = np.arange(X.shape[1]) * float(nom['dt'])
    alt, rng = -X[2], np.hypot(X[0], X[1])
    spd = np.linalg.norm(X[3:6], axis=0)
    glide = float(nom['glide_deg'])

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.1))
    ax, bx, cx = axes

    ax.plot(rng, alt, color='#2a78d6', lw=2.2)
    rr = np.linspace(0, rng.max() * 1.02, 2)
    ax.plot(rr, np.tan(np.deg2rad(glide)) * rr, ls='--', lw=1.1, color=MUTED)
    ax.text(rng.max() * 0.55, np.tan(np.deg2rad(glide)) * rng.max() * 0.55,
            f'  {glide:.0f}° cone', color=INK2, fontsize=8)
    ax.plot(rng[times], alt[times], 'o', color='#d03b3b', ms=5.5, zorder=5,
            mec=SURFACE, mew=1.0)
    ax.set_xlabel('distance to pad [m]'); ax.set_ylabel('altitude [m]')
    ax.set_title('Descent profile (red = injection points)', fontsize=9.5,
                 loc='left', color=INK2)
    ax.invert_xaxis()

    bx.plot(t, alt, color='#2a78d6', lw=2.0, label='altitude [m]')
    bx.plot(t[times], alt[times], 'o', color='#d03b3b', ms=5, mec=SURFACE,
            mew=1.0, zorder=5)
    bx.set_xlabel('time [s]'); bx.set_ylabel('altitude [m]')
    bx.set_title('Altitude against time', fontsize=9.5, loc='left', color=INK2)

    cx.plot(t, spd, color='#eb6834', lw=2.0)
    cx.plot(t[times], spd[times], 'o', color='#d03b3b', ms=5, mec=SURFACE,
            mew=1.0, zorder=5)
    cx.axhline(float(nom['v_norm']), ls='--', lw=1.1, color=MUTED)
    cx.text(t[-1], float(nom['v_norm']), ' speed cap', color=INK2, fontsize=8,
            va='bottom', ha='right')
    cx.set_xlabel('time [s]'); cx.set_ylabel('speed $\\|v\\|$ [m/s]')
    cx.set_title('Speed against time', fontsize=9.5, loc='left', color=INK2)

    for a in axes:
        for s in ('top', 'right'):
            a.spines[s].set_visible(False)
    fig.suptitle('The Apollo-anchored nominal descent', fontsize=11.5,
                 weight='bold', color=INK, x=0.012, ha='left')
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(path, dpi=150); plt.close(fig)
    print(f'[saved] {path}')


# ══════════════════════════════════════════════════════════════════════
#  H2 — the outcome grid
# ══════════════════════════════════════════════════════════════════════

def fig_grid(rows, faults, times, alts, path):
    fig, ax = plt.subplots(figsize=(1.0 + 0.52 * len(times),
                                    1.6 + 0.40 * len(faults)))
    by = {(r['fault'], r['point']): r for r in rows}
    for i, f in enumerate(faults):
        for j in range(len(times)):
            r = by.get((f, j))
            if r is None:
                continue
            ax.add_patch(plt.Rectangle((j + 0.03, i + 0.06), 0.94, 0.88,
                                       facecolor=STATUS.get(r['outcome'],
                                                            MUTED),
                                       edgecolor=SURFACE, linewidth=1.4))
    ax.set_xlim(0, len(times)); ax.set_ylim(len(faults), 0)
    ax.set_xticks(np.arange(len(times)) + 0.5)
    ax.set_xticklabels([f'{t:.0f}\n{a:.0f} m' for t, a in zip(times, alts)],
                       fontsize=7.5)
    ax.set_yticks(np.arange(len(faults)) + 0.5)
    ax.set_yticklabels([ic.CASES[f].label for f in faults], fontsize=8.5)
    for tl, f in zip(ax.get_yticklabels(), faults):
        tl.set_color(CLASS_COLOR[ic.CASES[f].klass])
    ax.set_xlabel('injection time [s]  /  altitude at injection', fontsize=9)
    ax.grid(False); ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title('Outcome by fault and injection point', fontsize=11,
                 weight='bold', color=INK, loc='left')
    ax.legend(handles=[Patch(facecolor=STATUS[o], label=OUT_LABEL[o])
                       for o in ('land', 'gate_miss', 'no_recovery')],
              loc='upper center', bbox_to_anchor=(0.5, -0.13), ncol=3,
              frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight'); plt.close(fig)
    print(f'[saved] {path}')


# ══════════════════════════════════════════════════════════════════════
#  H3 — survival against injection time
# ══════════════════════════════════════════════════════════════════════

def fig_survival(rows, times, path):
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    for cl in ('none', 'additive', 'multiplicative', 'structural'):
        ps = []
        for j in range(len(times)):
            rs = [r for r in rows if r['klass'] == cl and r['point'] == j]
            ps.append(sum(r['lands'] for r in rs) / len(rs) if rs else np.nan)
        c = CLASS_COLOR[cl]
        ax.plot(times, ps, '-o', color=c, lw=2.0, ms=5, mec=SURFACE, mew=1.0,
                label='healthy' if cl == 'none' else cl)
    ax.set_xlabel('injection time on the nominal descent [s]')
    ax.set_ylabel('share of that class landing')
    ax.set_ylim(-0.03, 1.05)
    ax.legend(frameon=False, fontsize=8.5, loc='lower left')
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.set_title('When the fault arrives decides whether it is survivable',
                 fontsize=11, weight='bold', color=INK, loc='left')
    fig.tight_layout()
    fig.savefig(path, dpi=150); plt.close(fig)
    print(f'[saved] {path}')


# ══════════════════════════════════════════════════════════════════════
#  H4 — margin against injection time, per fault
# ══════════════════════════════════════════════════════════════════════

def fig_margin(rows, faults, times, path):
    ncol = 4
    nrow = int(np.ceil(len(faults) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(13.0, 2.6 * nrow),
                             squeeze=False, sharex=True, sharey=True)
    by = {(r['fault'], r['point']): r for r in rows}
    for i, f in enumerate(faults):
        ax = axes[i // ncol][i % ncol]
        ax.axhline(1.0, ls='--', lw=1.0, color=MUTED)
        xs, ys, cs = [], [], []
        for j, t in enumerate(times):
            r = by.get((f, j))
            if r is None:
                continue
            m = r['margin']
            xs.append(t)
            ys.append(min(m, 20.0) if np.isfinite(m) else 20.0)
            cs.append(STATUS.get(r['outcome'], MUTED))
        ax.plot(xs, ys, '-', color=CLASS_COLOR[ic.CASES[f].klass], lw=1.2,
                alpha=0.7, zorder=1)
        ax.scatter(xs, ys, c=cs, s=26, zorder=3, edgecolor=SURFACE,
                   linewidth=0.8)
        ax.set_yscale('log'); ax.set_ylim(0.2, 30)
        ax.set_title(ic.CASES[f].label, fontsize=8.5, loc='left',
                     color=CLASS_COLOR[ic.CASES[f].klass])
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        if i // ncol == nrow - 1:
            ax.set_xlabel('injection time [s]')
        if i % ncol == 0:
            ax.set_ylabel('gate margin')
    for i in range(len(faults), nrow * ncol):
        axes[i // ncol][i % ncol].axis('off')
    fig.suptitle('Touchdown gate margin against injection time  '
                 '(dashed line = the gate; points above it miss; '
                 'a point at the ceiling found no trajectory)',
                 fontsize=10.5, weight='bold', color=INK, x=0.012, ha='left')
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(path, dpi=145); plt.close(fig)
    print(f'[saved] {path}')


# ══════════════════════════════════════════════════════════════════════
#  H5 — trajectories
# ══════════════════════════════════════════════════════════════════════

def fig_traj(rows, faults, nom, path):
    tj = np.load(os.path.join(RESULTS, 'H_trajectories.npz'))
    X = nom['X']
    alt_n, rng_n = -X[2], np.hypot(X[0], X[1])
    by = {(r['fault'], r['point']): r for r in rows}
    n_pts = 1 + max(r['point'] for r in rows)

    ncol = 4
    nrow = int(np.ceil(len(faults) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(13.2, 2.9 * nrow),
                             squeeze=False, sharex=True, sharey=True)
    for i, f in enumerate(faults):
        ax = axes[i // ncol][i % ncol]
        ax.plot(rng_n, alt_n, color=MUTED, lw=1.6, alpha=0.85, zorder=1)
        for j in range(n_pts):
            r = by.get((f, j))
            k = f'X|{j}|{f}'
            if r is None:
                continue
            if k not in tj:
                ax.plot(r['rng'], r['alt'], 'x', color=STATUS['no_recovery'],
                        ms=6, mew=1.6, zorder=4)
                continue
            P = np.hstack([tj[k], tj[f'F|{j}|{f}']])
            ax.plot(np.hypot(P[0], P[1]), -P[2],
                    color=STATUS.get(r['outcome'], MUTED), lw=1.1, alpha=0.9,
                    zorder=2)
        ax.set_title(ic.CASES[f].label, fontsize=8.5, loc='left',
                     color=CLASS_COLOR[ic.CASES[f].klass])
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        if i // ncol == nrow - 1:
            ax.set_xlabel('distance to pad [m]')
        if i % ncol == 0:
            ax.set_ylabel('altitude [m]')
    for i in range(len(faults), nrow * ncol):
        axes[i // ncol][i % ncol].axis('off')
    # once, not per panel: the axes are shared, so twelve inversions cancel
    # back to the original direction
    axes[0][0].invert_xaxis()
    fig.suptitle('Post-injection recoveries, all injection points  '
                 '(grey = the nominal descent they departed from)',
                 fontsize=11, weight='bold', color=INK, x=0.012, ha='left')
    fig.legend(handles=[Line2D([0], [0], color=STATUS[o], lw=2.4,
                               label=OUT_LABEL[o])
                        for o in ('land', 'gate_miss', 'no_recovery')],
               loc='lower center', ncol=3, frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, -0.004))
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(path, dpi=145); plt.close(fig)
    print(f'[saved] {path}')


# ══════════════════════════════════════════════════════════════════════

def main():
    rows = load()
    nom = nominal()
    faults = [k for k in ic.ordered_keys()
              if any(r['fault'] == k for r in rows)]
    n_pts = 1 + max(r['point'] for r in rows)
    times = [next(r['t_f'] for r in rows if r['point'] == j)
             for j in range(n_pts)]
    alts = [next(r['alt'] for r in rows if r['point'] == j)
            for j in range(n_pts)]
    tidx = [int(round(t / float(nom['dt']))) for t in times]

    def rate(rs):
        k, n = sum(r['lands'] for r in rs), len(rs)
        p, lo, hi = fl.wilson(k, n)
        return dict(k=int(k), n=int(n), p=p, lo=lo, hi=hi)

    per_fault = {f: rate([r for r in rows if r['fault'] == f]) for f in faults}
    per_point = {j: rate([r for r in rows if r['point'] == j])
                 for j in range(n_pts)}
    cells = {f: {j: next((r['outcome'] for r in rows
                          if r['fault'] == f and r['point'] == j), None)
                 for j in range(n_pts)} for f in faults}
    per_class = {cl: rate([r for r in rows if r['klass'] == cl])
                 for cl in ic.CLASS_ORDER
                 if any(r['klass'] == cl for r in rows)}

    # last injection time each fault still survives, and the first it fails
    survive_to = {}
    for f in faults:
        ok = [j for j in range(n_pts) if cells[f][j] == 'land']
        bad = [j for j in range(n_pts) if cells[f][j] != 'land']
        survive_to[f] = dict(
            last_land_t=times[max(ok)] if ok else None,
            last_land_alt=alts[max(ok)] if ok else None,
            first_fail_t=times[min(bad)] if bad else None,
            first_fail_alt=alts[min(bad)] if bad else None,
            n_land=len(ok))

    head = dict(
        n_solves=len(rows), n_points=n_pts, n_faults=len(faults),
        faults=faults, times=times, alts=alts,
        t_contact=float(nom['t_contact']), y_eng=float(nom['y_eng']),
        glide_deg=float(nom['glide_deg']), v_norm=float(nom['v_norm']),
        nominal_margin=float(nom['margin']), nominal_N=int(nom['N']),
        anchor=dict(zip(['alt', 'rng', 'v_h', 'v_v', 'los', 'fpa'],
                        [float(v) for v in nom['anchor']])),
        catalogue={f: dict(label=ic.CASES[f].label, short=ic.CASES[f].short,
                           section=ic.CASES[f].section,
                           structure=ic.CASES[f].structure,
                           klass=ic.CASES[f].klass,
                           temporal=ic.CASES[f].temporal,
                           detail=ic.CASES[f].detail) for f in faults},
        rates=per_fault, by_point=per_point, by_class=per_class,
        cells=cells, survive_to=survive_to,
        wall_hours=sum(r['wall'] for r in rows) / 3600.0)
    with open(os.path.join(RESULTS, 'headline_H.json'), 'w') as fh:
        json.dump(head, fh, indent=1, default=float)
    print(f"[saved] {os.path.join(RESULTS, 'headline_H.json')}")

    fig_nominal(nom, tidx, os.path.join(FIGURES, 'H1_nominal.png'))
    fig_grid(rows, faults, times, alts, os.path.join(FIGURES, 'H2_grid.png'))
    fig_survival(rows, times, os.path.join(FIGURES, 'H3_survival.png'))
    fig_margin(rows, faults, times, os.path.join(FIGURES, 'H4_margin.png'))
    fig_traj(rows, faults, nom, os.path.join(FIGURES, 'H5_trajectories.png'))


if __name__ == '__main__':
    main()
