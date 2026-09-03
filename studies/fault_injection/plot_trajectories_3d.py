"""
STUDY H / H-R — the trajectories in three dimensions
════════════════════════════════════════════════════
Every earlier figure in this study collapses the trajectory into the
range-altitude plane, which is the plane the glide cone lives in and therefore
the plane the constraints are argued in.  It is not the plane the vehicle flies
in.  A one-engine-out LM does not stay in the plane at all: the asymmetric
thrust yaws it, the gimbal trims the yaw, and what is left is a cross-range
excursion that a 2-D plot draws as nothing.

These figures put the paths back in 3-D, north-east-up, and sort them the way
the study's own questions sort them:

    by CAMPAIGN     baseline (Study H's corridor), relaxed (L1), and
                    unconstrained (L5, every state constraint gone)
    by FAULT        one panel per plant, so a fault's whole family of
                    recoveries is seen together against the nominal

Every panel carries the same three references: the nominal descent in grey, the
landing pad at the origin, and the lunar surface as the z = 0 plane.  The last
one earns its place here - the L5 trajectory is the only one in the study that
goes through it, and in 3-D that is immediately visible rather than a number in
a table.

Run:  python plot_trajectories_3d.py
"""

import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d import Axes3D              # noqa: F401  (projection)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')

import injection_catalogue as ic       # noqa: E402
import campaign as cp                  # noqa: E402

SURFACE = '#fcfcfb'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8985'
STATUS = {'land': '#0ca30c', 'gate_miss': '#fab219', 'subsurface': '#2b2b6b',
          'no_recovery': '#d03b3b', 'already_lost': '#8a8985'}
OUT_LABEL = {'land': 'landed', 'gate_miss': 'flew, missed the gate',
             'subsurface': 'path goes below the surface',
             'no_recovery': 'no trajectory found (injection point marked ×)'}

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'axes.labelcolor': INK2, 'text.color': INK,
    'xtick.color': INK2, 'ytick.color': INK2, 'font.size': 9,
})


def load(name):
    rows = cp.read_csv(os.path.join(RESULTS, name))
    for r in rows:
        r['point'] = int(float(r['point']))
        r['lands'] = str(r.get('lands')) in ('True', 'true', '1')
        for k in ('t_f', 'alt', 'rng', 'margin', 'alt_min'):
            if k in r:
                try:
                    r[k] = float(r[k])
                except (TypeError, ValueError):
                    r[k] = np.nan
    return rows


def path_of(tj, point, fault):
    """The full path: the powered arc plus the ballistic settle after cutoff."""
    k = f'X|{point}|{fault}'
    if k not in tj:
        return None
    F = tj.get(f'F|{point}|{fault}')
    P = np.hstack([tj[k], F]) if F is not None else tj[k]
    return P[0], P[1], -P[2]                 # north, east, up


def frame(ax, nom, lim):
    """The three references every panel shares: surface, pad, nominal.

    The nominal is clipped to the panel's own limits.  A zoomed panel - the L5
    case is injected 87 m from the pad - would otherwise be drawn round a
    2.7 km line that has nothing to do with it, and matplotlib would rescale
    the view to contain the whole thing.
    """
    n_n, e_n, u_n = nom
    keep = ((n_n >= lim['x'][0]) & (n_n <= lim['x'][1]) &
            (u_n >= lim['z'][0]) & (u_n <= lim['z'][1]))
    n_n, e_n, u_n = n_n[keep], e_n[keep], u_n[keep]
    # the lunar surface, z = 0
    gx = np.linspace(-lim['x'][1] * 0.05, lim['x'][1], 2)
    gy = np.linspace(lim['y'][0], lim['y'][1], 2)
    GX, GY = np.meshgrid(gx, gy)
    ax.plot_surface(GX, GY, np.zeros_like(GX), color='#e8e7e1', alpha=0.55,
                    linewidth=0, shade=False, zorder=0)
    ax.plot(n_n, e_n, u_n, color=MUTED, lw=1.8, alpha=0.9, zorder=3)
    ax.scatter([0], [0], [0], color=INK, s=26, marker='s', zorder=5)


def style(ax, lim, title, color=INK):
    ax.set_xlim(lim['x']); ax.set_ylim(lim['y']); ax.set_zlim(lim['z'])
    ax.set_xlabel('north [m]', labelpad=-4, fontsize=8)
    ax.set_ylabel('east [m]', labelpad=-4, fontsize=8)
    ax.set_zlabel('altitude [m]', labelpad=-6, fontsize=8)
    ax.tick_params(labelsize=7, pad=-2)
    ax.set_title(title, fontsize=9, loc='left', color=color, pad=0)
    ax.view_init(elev=22, azim=-58)
    ax.set_box_aspect((2.1, 1.0, 1.0))
    for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane.pane.set_facecolor(SURFACE)
        pane.pane.set_edgecolor('#e7e6e1')
        pane._axinfo['grid']['color'] = '#e7e6e1'


def limits(nom, paths, floor=0.0, focus=False):
    """Panel limits.  `focus` sizes the box on the trajectories alone, for a
    close-up; otherwise the whole nominal is included for context."""
    n_n, e_n, u_n = nom
    xs = [p[0] for p in paths] + ([] if focus else [n_n])
    ys = [p[1] for p in paths] + ([] if focus else [e_n])
    zs = [p[2] for p in paths] + ([] if focus else [u_n])
    X, Y, Z = (np.concatenate(a) for a in (xs, ys, zs))
    if focus:
        padx = max(40.0, (X.max() - X.min()) * 0.18)
        padz = max(15.0, (Z.max() - Z.min()) * 0.18)
        ey = max(20.0, np.abs(Y).max() * 1.3)
        return dict(x=(X.min() - padx, max(X.max() + padx, 40.0)),
                    y=(-ey, ey),
                    z=(min(Z.min() - padz, floor), Z.max() + padz))
    ey = max(60.0, np.abs(Y).max() * 1.15)
    return dict(x=(min(X.min() * 1.05, -50.0), 60.0), y=(-ey, ey),
                z=(min(floor, min(Z.min(), 0.0) * 1.1),
                   max(Z.max() * 1.08, 10.0)))


# ══════════════════════════════════════════════════════════════════════
#  one figure per campaign: a panel per fault
# ══════════════════════════════════════════════════════════════════════

def fig_by_fault(rows, tj, nom, path, title, subtitle, ncol=4, marks=True):
    faults = [k for k in ic.ordered_keys()
              if any(r['fault'] == k for r in rows)]
    if not faults:
        return
    paths = [p for r in rows
             if (p := path_of(tj, r['point'], r['fault'])) is not None]
    if not paths:
        return
    lim = limits(nom, paths)

    nrow = int(np.ceil(len(faults) / ncol))
    fig = plt.figure(figsize=(4.0 * ncol, 3.5 * nrow))
    for i, f in enumerate(faults):
        ax = fig.add_subplot(nrow, ncol, i + 1, projection='3d')
        frame(ax, nom, lim)
        for r in [r for r in rows if r['fault'] == f]:
            p = path_of(tj, r['point'], r['fault'])
            if p is None:
                if marks:      # a fault with no trajectory still has a state
                    ax.scatter([-r['rng']], [0], [r['alt']],
                               color=STATUS['no_recovery'], marker='x', s=26,
                               linewidths=1.5, zorder=6)
                continue
            ax.plot(*p, color=STATUS.get(r['outcome'], MUTED), lw=1.25,
                    alpha=0.95, zorder=4)
        style(ax, lim, ic.CASES[f].label)
    for i in range(len(faults), nrow * ncol):
        fig.add_subplot(nrow, ncol, i + 1).axis('off')

    fig.suptitle(title, fontsize=12.5, weight='bold', color=INK, x=0.01,
                 ha='left', y=0.995)
    fig.text(0.01, 0.966, subtitle, fontsize=9, color=INK2, ha='left')
    seen = {r['outcome'] for r in rows}
    fig.legend(handles=[Line2D([0], [0], color=STATUS[o], lw=2.4,
                               label=OUT_LABEL[o])
                        for o in ('land', 'gate_miss', 'subsurface',
                                  'no_recovery') if o in seen] +
                       [Line2D([0], [0], color=MUTED, lw=2.4,
                               label='the nominal descent')],
               loc='lower center', ncol=5, frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=[0, 0.035, 1, 0.955])
    fig.savefig(path, dpi=135)
    plt.close(fig)
    print(f'[saved] {path}')


# ══════════════════════════════════════════════════════════════════════
#  the three campaigns side by side, for the faults the relaxation moved
# ══════════════════════════════════════════════════════════════════════

def fig_campaigns(base_rows, hr_rows, tjH, tjR, nom, path):
    """One column per case that changed: what the baseline could not do, and
    what the relaxed problem did instead, from the same state."""
    moved = [r for r in hr_rows if r['level'] != 'none']
    if not moved:
        return
    paths = [p for r in moved
             if (p := path_of(tjR, r['point'], r['fault'])) is not None]
    lim = limits(nom, paths, focus=True)

    ncol = len(moved)
    fig = plt.figure(figsize=(4.3 * ncol, 4.6))
    for i, r in enumerate(moved):
        ax = fig.add_subplot(1, ncol, i + 1, projection='3d')
        frame(ax, nom, lim)
        p = path_of(tjR, r['point'], r['fault'])
        if p is not None:
            ax.plot(*p, color=STATUS.get(r['outcome'], MUTED), lw=1.9,
                    zorder=4)
        ax.scatter([-r['rng']], [0], [r['alt']], color=INK, s=30, zorder=6)
        lvl = {'L1': 'relaxed cone (L1)', 'L2': 'relaxed attitude (L2)',
               'L3': 'relaxed speed (L3)', 'L4': 'corridor off (L4)',
               'L5': 'no state constraints (L5)'}[r['level']]
        style(ax, lim,
              f"{ic.CASES[r['fault']].short} @{r['t_f']:.0f} s\n{lvl}"
              f"  ->  {OUT_LABEL[r['outcome']].split(' (')[0]}")
    fig.suptitle('What the relaxation bought, in three dimensions',
                 fontsize=12.5, weight='bold', color=INK, x=0.01, ha='left')
    fig.text(0.01, 0.915,
             'Each of these states had no trajectory inside Study H\'s '
             'corridor.\nBlack dot = the injection point, grey = the nominal, '
             'the shaded plane is the lunar surface.',
             fontsize=9, color=INK2, ha='left', va='top')
    fig.tight_layout(rect=[0, 0.02, 1, 0.86])
    fig.savefig(path, dpi=140)
    plt.close(fig)
    print(f'[saved] {path}')


def fig_subsurface(hr_rows, tjR, nom, path):
    """The L5 trajectory on its own: the one path in the study that leaves the
    surface behind, which is why it is not counted as a landing."""
    sub = [r for r in hr_rows if r['outcome'] == 'subsurface']
    if not sub:
        return
    r = sub[0]
    p = path_of(tjR, r['point'], r['fault'])
    if p is None:
        return
    lim = limits(nom, [p], focus=True)

    fig = plt.figure(figsize=(12.6, 5.2))
    for i, (elev, azim, name) in enumerate([(22, -58, 'oblique'),
                                            (4, -90, 'from the side'),
                                            (60, -70, 'from above')]):
        ax = fig.add_subplot(1, 3, i + 1, projection='3d')
        frame(ax, nom, lim)
        below = p[2] < 0
        ax.plot(*p, color=STATUS['subsurface'], lw=1.9, zorder=4)
        ax.plot(p[0][below], p[1][below], p[2][below], color='#d03b3b', lw=2.6,
                zorder=5)
        ax.scatter([-r['rng']], [0], [r['alt']], color=INK, s=32, zorder=6)
        style(ax, lim, name)
        ax.view_init(elev=elev, azim=azim)
    fig.suptitle('L5 — the trajectory that exists only without the altitude '
                 'floor', fontsize=12.5, weight='bold', color=INK, x=0.01,
                 ha='left')
    fig.text(0.01, 0.885,
             f"{ic.CASES[r['fault']].short} injected at {r['t_f']:.0f} s. With "
             f"every state constraint removed the solver finds a path to the "
             f"pad, but it reaches {abs(r['alt_min']):.0f} m below the surface "
             f"(red) before returning.\nIts touchdown still scores a clean "
             f"gate margin of {r['margin']:.2f} — which is why the gate alone "
             f"cannot say whether a trajectory is a landing.",
             fontsize=9, color=INK2, ha='left', va='top')
    fig.tight_layout(rect=[0, 0.02, 1, 0.84])
    fig.savefig(path, dpi=140)
    plt.close(fig)
    print(f'[saved] {path}')


def main():
    nom_npz = np.load(os.path.join(RESULTS, 'nominal.npz'))
    Xn = nom_npz['X']
    nom = (Xn[0], Xn[1], -Xn[2])

    H = load('H_samples.csv')
    R = load('HR_samples.csv')
    tjH = np.load(os.path.join(RESULTS, 'H_trajectories.npz'))
    tjR = np.load(os.path.join(RESULTS, 'HR_trajectories.npz'))

    fig_by_fault(
        H, tjH, nom, os.path.join(FIGURES, '3D1_baseline_by_fault.png'),
        'Study H — every recovery, in three dimensions',
        f'{len(H)} injections, one panel per plant. Cross-range is invisible '
        'in the range-altitude plots; here it is not.')

    fig_campaigns(H, R, tjH, tjR, nom,
                  os.path.join(FIGURES, '3D2_relaxed_by_case.png'))
    fig_subsurface(R, tjR, nom,
                   os.path.join(FIGURES, '3D3_subsurface.png'))


if __name__ == '__main__':
    main()
