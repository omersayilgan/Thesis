"""
STUDY I — figures
═════════════════
Six figures, in the order the argument runs: what the sets look like, what the
faults do to them, whether that predicts survival, what redundancy buys, where
the trim threshold is, and how a drifting fault walks across capability space.
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
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_injection'))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')

import apollo_nominal as an            # noqa: E402
import injection_catalogue as ic       # noqa: E402
import capability_lib as cl            # noqa: E402
import outcome_grid as og              # noqa: E402

SURFACE = '#fcfcfb'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8985'
CLASS_COLOR = {'none': '#9a9994', 'additive': '#2a78d6',
               'multiplicative': '#eb6834', 'structural': '#1baf7a'}
EFFECT_COLOR = {'unchanged': '#9a9994', 'shrunk': '#d03b3b',
                'enlarged': '#2a78d6', 'deformed': '#fab219',
                'punctured': '#8b2f8b'}

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE, 'axes.edgecolor': '#d8d7d2',
    'axes.labelcolor': INK2, 'text.color': INK,
    'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': '#e7e6e1', 'grid.linewidth': 0.8,
    'axes.axisbelow': True, 'font.size': 9,
})

SHOW = ['healthy', 'engine_out', 'thrust_loss_85', 'valve_stuck_open',
        'tvc_bias']


def fig_grid(h, path):
    """I0 — the overview grid: what each fault leaves of each capability.

    The same figure Study H uses for outcomes, asking the capability question
    instead: one cell per fault and per test, coloured by what survived.
    """
    tests = [('F_vol_frac', 'force set\nvolume'),
             ('M_vol_frac', 'moment set\nvolume'),
             ('C_vol_frac', 'moment while\nholding hover'),
             ('F_origin', 'zero net\nforce'), ('M_origin', 'zero net\nmoment'),
             ('hover_ok', 'hover wrench\nattainable'),
             ('trim_ok', 'trim on the\ngimbal + RCS')]

    def cell(r, key):
        v = r[key]
        if isinstance(v, bool):
            return 'retained' if v else 'lost'
        if v > 1.02:
            return 'gained'
        if v > 0.98:
            return 'retained'
        return 'lost' if v <= 0.01 else 'reduced'

    rows = sorted(h['faults'], key=lambda r: (r['klass'], -r['C_vol_frac']))
    og.outcome_grid(
        [[cell(r, k) for k, _ in tests] for r in rows],
        row_labels=[r['short'] for r in rows],
        col_labels=[lab for _, lab in tests],
        row_colors=[CLASS_COLOR.get(r['klass'], INK2) for r in rows],
        path=path, mode='categorical', cell_w=1.5, cell_h=0.44,
        title='What each fault leaves of the vehicle\'s capability',
        subtitle='one cell per fault and per capability test, on the '
                 'Study H vehicle at $y_{eng}$ = 0.25 m',
        note='"Reduced" is any loss of more than 2 %; "lost" is a capability '
             'the vehicle no longer has at all.\nThe last three columns are '
             'yes/no questions, and they are the ones that decide whether the '
             'vehicle can hold itself up.')


def head():
    return json.load(open(os.path.join(RESULTS, 'headline_I.json')))


def hull_panel(ax, P, hull, color, lim, title, ref=None, origin_ok=True):
    """One set. `lim` is per-axis, because the force set is six times taller
    than it is wide and a cube aspect renders it as an unreadable spike."""
    if ref is not None:
        # facecolor='none' leaves the collection with no face array, which
        # the 3-D projection cannot unpack; a transparent face works
        ax.add_collection3d(Poly3DCollection(
            [ref[0][s] for s in ref[1].simplices], facecolors=(1, 1, 1, 0.0),
            edgecolors='#c9c8c2', linewidths=0.25))
    if hull is not None:
        ax.add_collection3d(Poly3DCollection(
            [P[s] for s in hull.simplices], facecolors=color, alpha=0.30,
            edgecolors=color, linewidths=0.25))
    ax.scatter([0], [0], [0], color='#d03b3b' if not origin_ok else INK,
               s=26 if not origin_ok else 14,
               marker='x' if not origin_ok else 'o', zorder=6,
               linewidths=1.8)
    (lx, ly, lz) = lim
    ax.set_xlim(-lx, lx); ax.set_ylim(-ly, ly); ax.set_zlim(lz[0], lz[1])
    ax.set_box_aspect((1, 1, 1.35))
    ax.view_init(elev=20, azim=-58)
    ax.tick_params(labelsize=6, pad=-3)
    ax.set_title(title, fontsize=8.5, loc='left', pad=0)
    for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane.pane.set_facecolor(SURFACE)
        pane.pane.set_edgecolor('#e7e6e1')
        pane._axinfo['grid']['color'] = '#ecebe6'


def fig_sets(path):
    """I1 — the attainable force and moment sets, healthy and damaged."""
    lm0 = an.make_lm()
    ref = {}
    m_h = cl.model_from_lm(lm0, None, 'healthy')
    for mom in (False, True):
        P, h = cl.attainable_set(m_h, moment=mom, n_dirs=900)
        ref[mom] = (P, h)
    def box(P):
        a = np.abs(P).max(axis=0) * 1.08
        return (a[0], a[1], (P[:, 2].min() * 1.08, max(P[:, 2].max(), 0) + a[2] * 0.12))
    limF, limM = box(ref[False][0]), box(ref[True][0])

    fig = plt.figure(figsize=(3.1 * len(SHOW), 6.6))
    for j, key in enumerate(SHOW):
        case = ic.CASES[key]
        m = cl.model_from_lm(case.lm(), case, key)
        for i, mom in enumerate((False, True)):
            P, h = cl.attainable_set(m, moment=mom, n_dirs=900)
            ax = fig.add_subplot(2, len(SHOW), i * len(SHOW) + j + 1,
                                 projection='3d')
            ok = cl.contains_origin(m, mom)
            hull_panel(ax, P, h, CLASS_COLOR.get(case.klass, MUTED),
                       limM if mom else limF,
                       ('AMS  ' if mom else 'AFS  ') + case.short +
                       ('' if ok else '   — origin excluded'),
                       ref=None if key == 'healthy' else ref[mom],
                       origin_ok=ok)
    fig.suptitle('Attainable force (top) and moment (bottom) sets under fault',
                 fontsize=12.5, weight='bold', color=INK, x=0.01, ha='left',
                 y=0.995)
    fig.text(0.01, 0.952,
             'Grey wireframe = the healthy set the damaged one is drawn '
             'inside. The dot is the origin — a red × marks a set that no '
             'longer contains it and so cannot produce zero net wrench.',
             fontsize=9, color=INK2, ha='left', va='top')
    fig.tight_layout(rect=[0, 0, 1, 0.925])
    fig.savefig(path, dpi=135)
    plt.close(fig)
    print(f'[saved] {path}')


def fig_metrics(h, path):
    """I2 — what each fault costs, in three capability measures."""
    rows = sorted(h['faults'], key=lambda r: r['C_vol_frac'])
    y = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(9.6, 1.6 + 0.42 * len(rows)))
    hgt = 0.26
    for k, (key, name, col) in enumerate([
            ('F_vol_frac', 'AFS volume', '#2a78d6'),
            ('M_vol_frac', 'AMS volume', '#eb6834'),
            ('C_vol_frac', 'AMS while holding hover thrust', '#1baf7a')]):
        ax.barh(y + (k - 1) * hgt, [r[key] for r in rows], height=hgt * 0.9,
                color=col, label=name, zorder=3)
    ax.axvline(1.0, color=INK, lw=1.3, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels([r['short'] for r in rows], fontsize=8.5)
    for tl, r in zip(ax.get_yticklabels(), rows):
        tl.set_color(CLASS_COLOR.get(r['klass'], INK2))
    ax.set_xlabel('fraction of the healthy vehicle')
    ax.set_title('What each fault costs in capability space\n'
                 'the third bar is the one an allocator feels: moment '
                 'authority left while the vehicle holds itself up',
                 fontsize=11, weight='bold', color=INK, loc='left')
    ax.legend(loc='lower right', frameon=False, fontsize=8.6)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def fig_capability_vs_survival(h, path, land):
    """I3 — capability against survivability: the study's central figure."""
    rows = [r for r in h['faults'] if r['fault'] in land]
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    anns = []
    for r in rows:
        c = CLASS_COLOR.get(r['klass'], MUTED)
        ax.scatter(r['C_vol_frac'], land[r['fault']], s=130, color=c,
                   edgecolors=SURFACE, linewidths=1.5, zorder=4)
        anns.append(ax.annotate(
            r['short'], (r['C_vol_frac'], land[r['fault']]),
            textcoords='offset points', xytext=(9, 5), fontsize=8, color=INK2,
            arrowprops=dict(arrowstyle='-', lw=0.6, color='#c2c1ba',
                            shrinkA=1, shrinkB=5)))
    ax.set_xlabel('moment authority retained while holding hover thrust '
                  '(fraction of healthy)')
    ax.set_ylabel("share of Study H's 15 injection points that landed")
    ax.set_xlim(0.45, 1.18)
    lo = min(land[r['fault']] for r in rows)
    ax.set_ylim(lo - 0.09, 1.05)          # the points live in the top third
    ax.axhline(1.0, color='#d8d7d2', lw=1.0, zorder=1)
    ax.set_title('Capability does not predict survivability\n'
                 'faults with a full-size capability set are among the least '
                 'survivable in Study H',
                 fontsize=11.5, weight='bold', color=INK, loc='left')
    ax.legend(handles=[Line2D([0], [0], marker='o', lw=0, color=c, label=k)
                       for k, c in CLASS_COLOR.items()],
              loc='lower left', frameon=False, fontsize=8.6,
              title='fault class')
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    _spread(fig, ax, anns, [(r['C_vol_frac'], land[r['fault']]) for r in rows])
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def _spread(fig, ax, anns, pts, pad=2.0):
    """Nudge point labels off each other and off the markers.

    Six of the twelve faults sit within a hundredth of each other at the top
    right - that clustering IS the result, so the labels cannot simply be
    dropped, and they cannot be left overlapping either.
    """
    offsets = [(dx, dy, ha) for dy in (5, -11, 15, -21, 25, -31)
               for dx, ha in ((9, 'left'), (-9, 'right'))]
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    taken = []
    for x, y in pts:
        px, py = ax.transData.transform((x, y))
        taken.append(matplotlib.transforms.Bbox.from_bounds(
            px - 8, py - 8, 16, 16))

    def overlap(b):
        return sum(max(0, min(b.x1, t.x1) - max(b.x0, t.x0)) *
                   max(0, min(b.y1, t.y1) - max(b.y0, t.y0)) for t in taken)

    for i in sorted(range(len(anns)), key=lambda i: -len(anns[i].get_text())):
        ann, best = anns[i], None
        for dx, dy, ha in offsets:
            ann.xyann = (dx, dy)
            ann.set_horizontalalignment(ha)
            b = ann.get_window_extent(renderer=rend)
            box = matplotlib.transforms.Bbox.from_bounds(
                b.x0 - pad, b.y0 - pad, b.width + 2 * pad, b.height + 2 * pad)
            c = overlap(box)
            if best is None or c < best[0]:
                best = (c, dx, dy, ha, box)
            if c == 0.0:
                break
        _, dx, dy, ha, box = best
        ann.xyann = (dx, dy)
        ann.set_horizontalalignment(ha)
        taken.append(box)
        if ann.arrow_patch is not None:
            ann.arrow_patch.set_visible(abs(dy) > 12)


def fig_redundancy(h, path):
    """I4 — what one lost actuator costs, unit by unit."""
    rows = h['redundancy']
    fig, ax = plt.subplots(figsize=(10.2, 4.4))
    xs = np.arange(len(rows))
    cols = ['#1baf7a' if r['kind'] == 'rcs' else '#d03b3b' for r in rows]
    ax.bar(xs, [r['C_vol_frac'] for r in rows], color=cols, zorder=3)
    ax.axhline(1.0, color=INK, lw=1.2, zorder=4)
    ax.set_xticks(xs)
    ax.set_xticklabels([r['unit'] for r in rows], rotation=90, fontsize=7.5)
    ax.set_ylabel('moment authority retained\n(holding hover thrust)')
    ax.set_title('The price of one actuator\n'
                 'sixteen thrusters are close to interchangeable; two engines '
                 'are not',
                 fontsize=11.5, weight='bold', color=INK, loc='left')
    ax.legend(handles=[Patch(facecolor='#1baf7a', label='one RCS thruster lost'),
                       Patch(facecolor='#d03b3b', label='one engine lost')],
              loc='lower left', frameon=False, fontsize=8.6)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def fig_spacing(h, path):
    """I5 — engine-out trim against engine spacing."""
    sp = h['spacing']
    y = [r['y_eng'] for r in sp]
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.plot(y, [r['trim_slack_no_rcs'] for r in sp], color='#d03b3b', lw=1.8,
            label='gimbal alone', zorder=3)
    ax.plot(y, [r['trim_slack'] for r in sp], color='#1baf7a', lw=1.8,
            label='gimbal + RCS', zorder=3)
    ax.axvline(h['y_trim_limit'], color=INK, ls='--', lw=1.2, zorder=4)
    ax.text(h['y_trim_limit'] * 1.03, ax.get_ylim()[1] * 0.72,
            f"$dz\\,\\tan\\delta_{{max}}$ = {h['y_trim_limit']:.3f} m",
            fontsize=8.6, color=INK)
    ax.axvline(h['y_eng'], color='#2a78d6', ls=':', lw=1.4, zorder=4)
    ax.text(h['y_eng'] * 1.03, ax.get_ylim()[1] * 0.5,
            f"the studies' vehicle\n$y_{{eng}}$ = {h['y_eng']:.2f} m",
            fontsize=8.6, color='#2a78d6')
    ax.set_xlabel('engine half-spacing $y_{eng}$ [m]')
    ax.set_ylabel('residual wrench after trim  [N m]')
    ax.set_yscale('symlog', linthresh=1.0)
    ax.set_title('Engine-out trim against engine spacing\n'
                 'capability space recovers the analytic roll-trim limit '
                 'without being told it',
                 fontsize=11.5, weight='bold', color=INK, loc='left')
    ax.legend(frameon=False, fontsize=8.8, loc='upper left')
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def fig_erosion(h, path):
    """I6 — a drifting fault walking across capability space."""
    er = h['erosion']
    t = [r['t'] for r in er]
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    for key, name, col in [('F_vol_frac', 'AFS volume', '#2a78d6'),
                           ('M_vol_frac', 'AMS volume', '#eb6834'),
                           ('C_vol_frac', 'AMS while holding hover', '#1baf7a')]:
        ax.plot(t, [r[key] for r in er], 'o-', color=col, lw=1.8, label=name)
    ax.set_xlabel('seconds since the fault appeared')
    ax.set_ylabel('fraction of the healthy vehicle')
    ax.set_title('Throat-erosion drift: one fault, a moving capability set\n'
                 'the static snapshot at onset is indistinguishable from '
                 'healthy',
                 fontsize=11.5, weight='bold', color=INK, loc='left')
    ax.legend(frameon=False, fontsize=8.8)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def landing_shares():
    """Study H's landing share per fault, for the cross-study figure."""
    p = os.path.join(ROOT, 'studies', 'fault_injection', 'results',
                     'headline_H.json')
    if not os.path.exists(p):
        return {}
    H = json.load(open(p))
    return {f: H['survive_to'][f]['n_land'] / H['n_points']
            for f in H['faults']}


def main():
    h = head()
    fig_grid(h, os.path.join(FIGURES, 'I0_capability_grid.png'))
    fig_sets(os.path.join(FIGURES, 'I1_sets.png'))
    fig_metrics(h, os.path.join(FIGURES, 'I2_metrics.png'))
    land = landing_shares()
    if land:
        fig_capability_vs_survival(
            h, os.path.join(FIGURES, 'I3_capability_vs_survival.png'), land)
    fig_redundancy(h, os.path.join(FIGURES, 'I4_redundancy.png'))
    fig_spacing(h, os.path.join(FIGURES, 'I5_spacing.png'))
    fig_erosion(h, os.path.join(FIGURES, 'I6_erosion.png'))


if __name__ == '__main__':
    main()
