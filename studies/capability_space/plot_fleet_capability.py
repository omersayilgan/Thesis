"""
STUDY I-F — figures
═══════════════════
Four figures: the fleet-wide map of what each fault costs each vehicle, whether
the spacecraft classes respond alike, how similar any two vehicles' responses
actually are, and what the damaged sets look like for one exemplar per class.
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
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')

import vehicles as vh                     # noqa: E402
import capability_lib as cl               # noqa: E402
import run_fleet_capability as rf         # noqa: E402

SURFACE = '#fcfcfb'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8985'
CAT_COLOR = {'Boosters': '#2a78d6', 'LEO Satellites': '#1baf7a',
             'GEO Satellites': '#eda100', 'Crewed Vehicles': '#e87ba4',
             'Deep Space Probes': '#4a3aa7'}
CAT_ORDER = ['Boosters', 'LEO Satellites', 'GEO Satellites',
             'Crewed Vehicles', 'Deep Space Probes']
RET = LinearSegmentedColormap.from_list(
    'ret', ['#8b1a1a', '#d03b3b', '#fab219', '#cfe8bf', '#0ca30c'])

SHORT = {'Solar Dynamics Observatory (SDO)': 'SDO',
         'Meteosat Second Generation (MSG)': 'MSG',
         'Orion (CM + European Service Module)': 'Orion',
         'Apollo Command & Service Module': 'Apollo CSM',
         'Apollo Lunar Module': 'Apollo LM',
         'Crew Dragon (Dragon 2)': 'Crew Dragon',
         'Cassini (Cassini-Huygens)': 'Cassini',
         'GRACE-FO (per satellite)': 'GRACE-FO'}

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE, 'axes.edgecolor': '#d8d7d2',
    'axes.labelcolor': INK2, 'text.color': INK,
    'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': '#e7e6e1', 'grid.linewidth': 0.8,
    'axes.axisbelow': True, 'font.size': 9,
})


def head():
    return json.load(open(os.path.join(RESULTS, 'headline_IF.json')))


def short(n):
    return SHORT.get(n, n)


def ordered_vehicles(rows):
    seen = []
    for c in CAT_ORDER:
        for r in rows:
            if r['category'] == c and r['vehicle'] not in seen:
                seen.append(r['vehicle'])
    return seen


def fig_map(h, path):
    """IF1 — the fleet map: what each fault costs each vehicle."""
    rows = [r for r in h['rows'] if r['fault'] != 'healthy']
    vehicles = ordered_vehicles(rows)
    faults = [f['key'] for f in h['faults']]
    labels = {f['key']: f['label'] for f in h['faults']}
    by = {(r['vehicle'], r['fault']): r for r in rows}

    fig, ax = plt.subplots(figsize=(2.6 + 1.05 * len(faults),
                                    2.0 + 0.40 * len(vehicles)))
    for i, v in enumerate(vehicles):
        for j, k in enumerate(faults):
            r = by.get((v, k))
            val = r.get('M_auth_frac') if r and r.get('applicable') else None
            if val is None or not np.isfinite(val):
                ax.add_patch(plt.Rectangle((j + 0.03, i + 0.06), 0.94, 0.88,
                                           facecolor='#efeee9',
                                           edgecolor=SURFACE, linewidth=1.4))
                ax.text(j + 0.5, i + 0.5, 'n/a', ha='center', va='center',
                        fontsize=7, color=MUTED)
                continue
            ax.add_patch(plt.Rectangle(
                (j + 0.03, i + 0.06), 0.94, 0.88,
                facecolor=RET(min(val, 1.0)), edgecolor=SURFACE, linewidth=1.4))
            txt = f'{val:.2f}' if val < 10 else '>10'
            ax.text(j + 0.5, i + 0.5, txt, ha='center', va='center',
                    fontsize=7.2, weight='bold',
                    color='white' if val < 0.55 or val > 0.97 else INK2)
    ax.set_xlim(0, len(faults)); ax.set_ylim(len(vehicles), 0)
    ax.set_xticks(np.arange(len(faults)) + 0.5)
    ax.set_xticklabels([labels[k] for k in faults], fontsize=7.6, rotation=40,
                       ha='right')
    ax.set_yticks(np.arange(len(vehicles)) + 0.5)
    ax.set_yticklabels([short(v) for v in vehicles], fontsize=8.4)
    cats = {r['vehicle']: r['category'] for r in rows}
    for tl, v in zip(ax.get_yticklabels(), vehicles):
        tl.set_color(CAT_COLOR.get(cats[v], INK2))
    ax.grid(False); ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title('Moment authority retained after the worst single failure\n'
                 'mean reach of the moment set, as a fraction of the same '
                 'vehicle healthy; each fault applied to every unit in turn',
                 fontsize=11, weight='bold', color=INK, loc='left')
    ax.legend(handles=[Patch(facecolor=CAT_COLOR[c], label=c)
                       for c in CAT_ORDER] +
                      [Patch(facecolor='#efeee9',
                             label='the vehicle has no such actuator')],
              loc='upper center', bbox_to_anchor=(0.5, -0.13), ncol=3,
              frameon=False, fontsize=8.4)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def fig_by_category(h, path):
    """IF2 — do the classes respond alike?"""
    rows = [r for r in h['rows'] if r['fault'] != 'healthy'
            and r.get('applicable') and np.isfinite(r.get('M_auth_frac', np.nan))]
    faults = [f['key'] for f in h['faults']]
    labels = {f['key']: f['label'] for f in h['faults']}
    fig, ax = plt.subplots(figsize=(11.4, 5.4))
    w = 0.82 / len(CAT_ORDER)
    for c_i, c in enumerate(CAT_ORDER):
        xs, ys = [], []
        for j, k in enumerate(faults):
            vals = [r['M_auth_frac'] for r in rows
                    if r['fault'] == k and r['category'] == c]
            if not vals:
                continue
            x = j + 0.09 + (c_i + 0.5) * w
            ax.plot([x, x], [min(vals), max(vals)], color=CAT_COLOR[c],
                    lw=1.2, alpha=0.55, zorder=2)
            ax.scatter([x] * len(vals), vals, s=26, color=CAT_COLOR[c],
                       zorder=3, edgecolors=SURFACE, linewidths=0.6)
            xs.append(x); ys.append(float(np.mean(vals)))
        ax.plot(xs, ys, color=CAT_COLOR[c], lw=1.4, alpha=0.75, zorder=4,
                label=c)
    ax.axhline(1.0, color=INK, lw=1.1, zorder=1)
    ax.set_xticks(np.arange(len(faults)) + 0.5)
    ax.set_xticklabels([labels[k] for k in faults], fontsize=8, rotation=25,
                       ha='right')
    ax.set_ylabel('moment authority retained\n(fraction of that vehicle healthy)')
    ax.set_title('Fault response by spacecraft class\n'
                 'each dot is one vehicle; the line joins class means',
                 fontsize=11.5, weight='bold', color=INK, loc='left')
    ax.legend(frameon=False, fontsize=8.4, ncol=3, loc='lower left')
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def fig_similarity(h, path):
    """IF3 — how similar are two vehicles' fault responses, really?"""
    D, cats = h['distance'], h['categories']
    names = [v for c in CAT_ORDER for v in D if cats.get(v) == c]
    M = np.array([[D[a].get(b, np.nan) for b in names] for a in names])

    # the two panels carry independent titles, so they need real horizontal
    # separation rather than tight_layout's default
    fig, axes = plt.subplots(1, 2, figsize=(14.4, 6.0),
                             gridspec_kw=dict(width_ratios=[1.35, 1],
                                              wspace=0.42))
    ax = axes[0]
    im = ax.imshow(M, cmap='magma_r', vmin=0, vmax=np.nanmax(M))
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([short(n) for n in names], rotation=90, fontsize=7.4)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([short(n) for n in names], fontsize=7.4)
    for tl, n in zip(ax.get_yticklabels(), names):
        tl.set_color(CAT_COLOR.get(cats[n], INK2))
    for tl, n in zip(ax.get_xticklabels(), names):
        tl.set_color(CAT_COLOR.get(cats[n], INK2))
    # class boundaries
    edges, seen = [], None
    for i, n in enumerate(names):
        if cats[n] != seen:
            edges.append(i); seen = cats[n]
    for e in edges[1:]:
        ax.axhline(e - 0.5, color='#2b2b2b', lw=1.0)
        ax.axvline(e - 0.5, color='#2b2b2b', lw=1.0)
    ax.grid(False)
    ax.set_title('Distance between fault responses',
                 fontsize=10.5, weight='bold', color=INK, loc='left', pad=22)
    ax.text(0.0, 1.015, 'mean |difference| in retained moment authority, over '
            'the faults both vehicles can suffer', transform=ax.transAxes,
            fontsize=8.4, color=INK2, va='bottom')
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)

    ax2 = axes[1]
    w, b = h['within_mean'], h['between_mean']
    ax2.bar([0, 1], [w, b], color=['#1baf7a', '#d03b3b'], width=0.55, zorder=3)
    for x, v, n in ((0, w, h['within_n']), (1, b, h['between_n'])):
        ax2.text(x, v + 0.004, f'{v:.3f}\n({n} pairs)', ha='center',
                 fontsize=9, color=INK2)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(['same spacecraft class', 'different classes'],
                        fontsize=9.5)
    ax2.set_ylabel('mean distance between fault responses')
    ax2.set_ylim(0, max(w, b) * 1.35)
    same = abs(w - b) < 0.02
    ax2.set_title(('Class membership predicts little' if same else
                   'Same-class vehicles do respond more alike'),
                  fontsize=11, weight='bold', color=INK, loc='left')
    for s in ('top', 'right'):
        ax2.spines[s].set_visible(False)
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def fig_exemplars(h, path):
    """IF4 — the moment sets themselves, one exemplar per class."""
    rows = [r for r in h['rows'] if r['fault'] != 'healthy']
    fleet = {v.name: v for v in vh.build_all()}
    picks = []
    for c in CAT_ORDER:
        cand = [r for r in rows if r['category'] == c and r.get('applicable')
                and np.isfinite(r.get('M_auth_frac', np.nan))]
        if cand:
            picks.append(min(cand, key=lambda r: r['M_auth_frac']))
    if not picks:
        return

    fig = plt.figure(figsize=(3.2 * len(picks), 3.9))
    for i, r in enumerate(picks):
        veh = fleet[r['vehicle']]
        base = rf.to_model(veh)
        f = next(f for f in h['faults'] if f['key'] == r['fault'])
        m = rf.damaged(base, f, int(r['worst_unit']))
        Ph, hh = cl.attainable_set(base, moment=True, n_dirs=700)
        P, hu = cl.attainable_set(m, moment=True, n_dirs=700)
        ax = fig.add_subplot(1, len(picks), i + 1, projection='3d')
        if hh is not None:
            ax.add_collection3d(Poly3DCollection(
                [Ph[s] for s in hh.simplices], facecolors=(1, 1, 1, 0.0),
                edgecolors='#c9c8c2', linewidths=0.2))
        if hu is not None:
            col = CAT_COLOR.get(r['category'], MUTED)
            ax.add_collection3d(Poly3DCollection(
                [P[s] for s in hu.simplices], facecolors=col, alpha=0.3,
                edgecolors=col, linewidths=0.2))
        lim = np.abs(Ph).max() * 1.05
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=20, azim=-58)
        ax.tick_params(labelsize=6, pad=-3)
        ax.set_title(f"{short(r['vehicle'])}\n{f['label']} — "
                     f"{r['M_auth_frac']:.2f}×",
                     fontsize=8.5, loc='left', color=CAT_COLOR.get(r['category']))
        for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
            pane.pane.set_facecolor(SURFACE)
            pane.pane.set_edgecolor('#e7e6e1')
            pane._axinfo['grid']['color'] = '#ecebe6'
    fig.suptitle('Worst single failure per class — the moment set it leaves',
                 fontsize=12, weight='bold', color=INK, x=0.01, ha='left')
    fig.text(0.01, 0.90, 'grey wireframe = the same vehicle healthy',
             fontsize=9, color=INK2, ha='left', va='top')
    fig.tight_layout(rect=[0, 0, 1, 0.86])
    fig.savefig(path, dpi=140)
    plt.close(fig)
    print(f'[saved] {path}')


def main():
    h = head()
    fig_map(h, os.path.join(FIGURES, 'IF1_fleet_map.png'))
    fig_by_category(h, os.path.join(FIGURES, 'IF2_by_category.png'))
    fig_similarity(h, os.path.join(FIGURES, 'IF3_similarity.png'))
    fig_exemplars(h, os.path.join(FIGURES, 'IF4_exemplars.png'))


if __name__ == '__main__':
    main()
