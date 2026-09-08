"""
STUDY H-R — analysis
════════════════════
Turns results/HR_samples.csv into results/headline_HR.json and the relaxed
report's figures.  The organising axis is no longer *when* the fault arrived
(Study H answered that) but *how much corridor* the recovery needed: every
figure is drawn against the ladder level or the excursion beyond the baseline
limits.
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

import injection_catalogue as ic       # noqa: E402
import apollo_nominal as an            # noqa: E402
import campaign as cp                  # noqa: E402
import run_relaxed_study as rr         # noqa: E402

SURFACE = '#fcfcfb'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8985'
CLASS_COLOR = {'none': '#9a9994', 'additive': '#2a78d6',
               'multiplicative': '#eb6834', 'structural': '#1baf7a'}
STATUS = {'land': '#0ca30c', 'gate_miss': '#fab219',
          'subsurface': '#2b2b6b',
          'no_recovery': '#d03b3b', 'already_lost': '#8a8985'}
# one colour per ladder level, darkening as the corridor is given away
LEVEL_COLOR = {'L1': '#7fc97f', 'L2': '#fab219', 'L3': '#eb6834',
               'L4': '#8b2f8b', 'L5': '#2b2b6b', 'none': '#d03b3b'}
OUT_LABEL = {'land': 'landed', 'gate_miss': 'flew, missed the gate',
             'subsurface': 'path goes below the surface (not a landing)',
             'no_recovery': 'no trajectory found'}

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE, 'axes.edgecolor': '#d8d7d2',
    'axes.labelcolor': INK2, 'text.color': INK,
    'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': '#e7e6e1', 'grid.linewidth': 0.8,
    'axes.axisbelow': True, 'font.size': 9,
})

FLOATS = ('alt_min', 'floor_ratio', 't_f', 'alt', 'rng', 'margin', 'v_horiz_0', 'v_desc_0', 'tilt_0',
          'wall', 'v_vert', 'v_horiz', 'tilt_deg', 'pos_err', 'rate_deg',
          'binding_ratio', 'cone_ratio', 'path_min_deg', 'att_ratio',
          'att_max_deg', 'rate_ratio', 'rate_max_dps', 'vax_ratio', 'vax_max',
          'vnorm_ratio', 'vnorm_max', 'iters', 'seed')


def load(name):
    rows = cp.read_csv(os.path.join(RESULTS, name))
    for r in rows:
        r['lands'] = str(r.get('lands')) in ('True', 'true', '1')
        r['point'] = int(r['point'])
        for k in FLOATS:
            if k in r:
                try:
                    r[k] = float(r[k])
                except (TypeError, ValueError):
                    r[k] = np.nan
    return rows


N_RAMP = 6          # solve_ocp's n_relax: the corridor is wider than the
                    # nominal envelope only over nodes 0..n_relax-1


def rescore_excursions(rows):
    """Recompute every excursion over the POST-TRANSIENT trajectory.

    The campaign measured them over the whole trajectory, which flatters the
    relaxation: `solve_ocp` opens a corridor over the first `n_relax` nodes
    (ALLOW = 3.0x on rate, 1.35x on attitude, 1.2x on speed) that shrinks to
    the nominal envelope by node n_relax - and it does so in the BASELINE
    problem as well.  An excursion inside that window is therefore something
    Study H already permitted, not something the relaxation bought, and
    reporting it as the binding constraint attributes the recovery to the
    wrong limit: all three recoveries here solved at L1, where only the cone
    was relaxed, yet the whole-trajectory measure named `body rate` for two of
    them purely on their opening transient.

    The peak inside the ramp is kept as `*_transient` for context.
    """
    npz = os.path.join(RESULTS, 'HR_trajectories.npz')
    if not os.path.exists(npz):
        return
    tj = np.load(npz)
    cfg0 = an.make_cfg()
    for r in rows:
        k = f"X|{r['point']}|{r['fault']}"
        if k not in tj:
            continue
        X = tj[k]
        whole = rr.excursions(X, cfg0)
        post = rr.excursions(X[:, N_RAMP:], cfg0, n_cone=0)
        r.update(post)
        for key in ('cone_ratio', 'att_ratio', 'rate_ratio', 'vax_ratio',
                    'vnorm_ratio'):
            r[key + '_transient'] = whole[key]
        r['binding'], r['binding_ratio'] = rr.binding_constraint(post)
        # A trajectory that leaves the surface behind is not a landing however
        # good its touchdown state looks.  gate_margin only inspects the final
        # state, so the L5 solves - the only ones allowed below the floor -
        # can score a clean 0.60 margin on a path that spent 27 of 40 nodes
        # dozens of metres underground.  Relabel them rather than let the
        # headline count them as recoveries.
        if r['alt_min'] <= 0.0:
            r['outcome'] = 'subsurface'
            r['lands'] = False
            r['subsurface_depth'] = float(-r['alt_min'])


def label(r):
    return f"{ic.CASES[r['fault']].short}  @{r['t_f']:.0f} s"


# ══════════════════════════════════════════════════════════════════════
#  HR1 — which level unlocked each case
# ══════════════════════════════════════════════════════════════════════

def fig_ladder(rows, path):
    rows = sorted(rows, key=lambda r: (r['fault'], r['t_f']))
    levels = rr.LEVELS
    fig, ax = plt.subplots(figsize=(1.6 + 1.15 * len(levels),
                                    1.9 + 0.42 * len(rows)))
    for i, r in enumerate(rows):
        won = r['level']
        for j, lv in enumerate(levels):
            # everything up to the winning level was tried and failed
            if won == 'none':
                fc, txt = '#f0dcdc', ''
            elif lv == won:
                fc = LEVEL_COLOR[lv]
                txt = {'land': 'L', 'gate_miss': 'G',
                       'subsurface': 'S'}.get(r['outcome'], '?')
            elif levels.index(lv) < levels.index(won):
                fc, txt = '#f0dcdc', ''
            else:
                fc, txt = '#f2f1ec', ''          # never needed
            ax.add_patch(plt.Rectangle((j + 0.04, i + 0.08), 0.92, 0.84,
                                       facecolor=fc, edgecolor=SURFACE,
                                       linewidth=1.4))
            if txt:
                ax.text(j + 0.5, i + 0.5, txt, ha='center', va='center',
                        fontsize=8.5, weight='bold', color='white')
        if r['level'] == 'none':
            ax.text(len(levels) + 0.12, i + 0.5, 'infeasible throughout',
                    va='center', fontsize=8, color=STATUS['no_recovery'])
        else:
            # an inf ratio is a trajectory that went under the surface; there
            # is no multiple of the floor to quote for it
            ratio = ('below the surface' if not np.isfinite(r['binding_ratio'])
                     else f"{r['binding_ratio']:.2f}x")
            ax.text(len(levels) + 0.12, i + 0.5,
                    f"binding: {r['binding']}, {ratio}",
                    va='center', fontsize=8, color=INK2)
    ax.set_xlim(0, len(levels) + 2.6); ax.set_ylim(len(rows), 0)
    ax.set_xticks(np.arange(len(levels)) + 0.5)
    ax.set_xticklabels([f"{l['key']}\n{l['short']}" for l in rr.LADDER],
                       fontsize=8)
    ax.set_yticks(np.arange(len(rows)) + 0.5)
    ax.set_yticklabels([label(r) for r in rows], fontsize=8.5)
    for tl, r in zip(ax.get_yticklabels(), rows):
        tl.set_color(CLASS_COLOR[ic.CASES[r['fault']].klass])
    ax.grid(False); ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    # the S key only belongs on the figure if such a case can occur, which it
    # cannot while z > 0 is enforced at every level
    key = 'L = lands in the Apollo gate, G = flies but misses it'
    if any(r['outcome'] == 'subsurface' for r in rows):
        key += ', S = path goes below the surface'
    ax.set_title('Weakest relaxation that admits a trajectory\n' + key,
                 fontsize=10.5, weight='bold', color=INK, loc='left')
    ax.legend(handles=[Patch(facecolor='#f0dcdc', label='tried, still infeasible'),
                       *[Patch(facecolor=LEVEL_COLOR[l['key']],
                               label=f"solved at {l['key']} ({l['short']})")
                         for l in rr.LADDER],
                       Patch(facecolor='#f2f1ec', label='not needed')],
              loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=3,
              frameon=False, fontsize=8.2)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight'); plt.close(fig)
    print(f'[saved] {path}')


# ══════════════════════════════════════════════════════════════════════
#  HR2 — how far outside the baseline corridor the recoveries went
# ══════════════════════════════════════════════════════════════════════

def fig_excursions(rows, path):
    got = [r for r in sorted(rows, key=lambda r: -r.get('binding_ratio', 0))
           if r['level'] != 'none']
    if not got:
        return
    keys = [('floor_ratio', 'altitude floor'), ('cone_ratio', 'glide cone'),
            ('vnorm_ratio', 'speed (norm)'), ('vax_ratio', 'speed (axis)'),
            ('att_ratio', 'attitude'), ('rate_ratio', 'body rate')]
    CLIP = 3.0        # a trajectory that goes under the surface has an
                      # infinite floor ratio; clip so one bar cannot flatten
                      # every other bar in the chart
    fig, ax = plt.subplots(figsize=(9.4, 1.6 + 0.46 * len(got)))
    h = 0.74 / len(keys)
    cols = ['#2b2b6b', '#2a78d6', '#eb6834', '#f0a35e', '#1baf7a', '#8b2f8b']
    for j, (k, name) in enumerate(keys):
        vals = [min(r.get(k, 0.0) or 0.0, CLIP) for r in got]
        ys = [i + 0.13 + j * h for i in range(len(got))]
        ax.barh(ys, vals, height=h * 0.86, color=cols[j], label=name, zorder=3)
        for y, v, r in zip(ys, vals, got):
            if (r.get(k) or 0.0) > CLIP:      # say so rather than mislead
                ax.text(CLIP * 1.01, y + h * 0.43,
                        'below the surface' if k == 'floor_ratio' else '>3x',
                        va='center', fontsize=7.2, color=cols[j])
    ax.axvline(1.0, color=INK, lw=1.4, zorder=4)
    ax.text(1.02, len(got) - 0.15, 'baseline limit', fontsize=8.5, color=INK)
    ax.set_yticks([i + 0.5 for i in range(len(got))])
    ax.set_yticklabels([label(r) for r in got], fontsize=8.5)
    ax.set_ylim(len(got), 0)
    ax.set_xlabel('peak excursion, as a multiple of the Study H limit')
    ax.set_title('What the relaxation actually bought\n'
                 'peak after the post-fault transient; bars past 1.0 are '
                 'limits the recovery could not have respected',
                 fontsize=10.5, weight='bold', color=INK, loc='left')
    ax.legend(loc='lower right', frameon=False, fontsize=8.4, ncol=2)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight'); plt.close(fig)
    print(f'[saved] {path}')


# ══════════════════════════════════════════════════════════════════════
#  HR3 — the relaxed trajectories, against the nominal and the cone
# ══════════════════════════════════════════════════════════════════════

def fig_traj(rows, nom, path):
    npz = os.path.join(RESULTS, 'HR_trajectories.npz')
    if not os.path.exists(npz):
        return
    tj = np.load(npz)
    X = nom['X']
    alt_n, rng_n = -X[2], np.hypot(X[0], X[1])
    got = [r for r in sorted(rows, key=lambda r: (r['fault'], r['t_f']))
           if r['level'] != 'none']
    if not got:
        return

    ncol = 3
    nrow = int(np.ceil(len(got) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(12.4, 3.0 * nrow),
                             squeeze=False, sharex=True, sharey=True)
    rmax = max(rng_n.max(), 1.0)
    cone_r = np.linspace(0, rmax, 60)
    tan12 = np.tan(np.deg2rad(float(nom['glide_deg'])))
    for i, r in enumerate(got):
        ax = axes[i // ncol][i % ncol]
        ax.plot(rng_n, alt_n, color=MUTED, lw=1.5, alpha=0.85, zorder=2)
        ax.plot(cone_r, tan12 * cone_r, color='#c9c8c2', lw=1.0, ls='--',
                zorder=1)
        ax.fill_between(cone_r, 0, tan12 * cone_r, color='#efeee8', zorder=0)
        k = f"X|{r['point']}|{r['fault']}"
        if k in tj:
            P = np.hstack([tj[k], tj[f"F|{r['point']}|{r['fault']}"]])
            ax.plot(np.hypot(P[0], P[1]), -P[2],
                    color=STATUS.get(r['outcome'], MUTED), lw=1.5, zorder=3)
        ax.plot(r['rng'], r['alt'], 'o', color=INK, ms=4.5, zorder=5)
        ax.set_title(f"{label(r)}   [{r['level']}]", fontsize=8.5, loc='left',
                     color=CLASS_COLOR[ic.CASES[r['fault']].klass])
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        if i // ncol == nrow - 1:
            ax.set_xlabel('distance to pad [m]')
        if i % ncol == 0:
            ax.set_ylabel('altitude [m]')
    for i in range(len(got), nrow * ncol):
        axes[i // ncol][i % ncol].axis('off')
    axes[0][0].invert_xaxis()
    fig.suptitle('Relaxed recoveries  (grey = the nominal, shaded = below the '
                 '12 deg glide cone Study H enforced)',
                 fontsize=11, weight='bold', color=INK, x=0.012, ha='left')
    fig.legend(handles=[Line2D([0], [0], color=STATUS[o], lw=2.4,
                               label=OUT_LABEL[o])
                        for o in ('land', 'gate_miss')] +
                       [Line2D([0], [0], marker='o', color=INK, lw=0,
                               label='injection point')],
               loc='lower center', ncol=3, frameon=False, fontsize=9,
               bbox_to_anchor=(0.5, -0.004))
    fig.tight_layout(rect=[0, 0.035, 1, 0.95])
    fig.savefig(path, dpi=145); plt.close(fig)
    print(f'[saved] {path}')


def main():
    rows = load('HR_samples.csv')
    rescore_excursions(rows)
    base = {(r['fault'], int(r['point'])): r for r in load('H_samples.csv')}
    nom = np.load(os.path.join(RESULTS, 'nominal.npz'))

    got = [r for r in rows if r['level'] != 'none']
    landed = [r for r in got if r['lands']]
    subsurface = [r for r in got if r['outcome'] == 'subsurface']
    by_level = {l['key']: [f"{r['fault']}@{r['t_f']:.0f}"
                           for r in rows if r['level'] == l['key']]
                for l in rr.LADDER}
    by_level['none'] = [f"{r['fault']}@{r['t_f']:.0f}"
                        for r in rows if r['level'] == 'none']
    by_binding = {}
    for r in got:
        by_binding.setdefault(r['binding'], []).append(f"{r['fault']}@{r['t_f']:.0f}")

    head = dict(
        n_cases=len(rows),
        n_no_recovery=sum(r['base_outcome'] == 'no_recovery' for r in rows),
        n_gate_miss=sum(r['base_outcome'] == 'gate_miss' for r in rows),
        n_solved=len(got), n_landed=len(landed),
        n_subsurface=len(subsurface),
        n_unsolved=len(rows) - len(got),
        ladder=[dict(key=l['key'], label=l['label'], short=l['short'],
                     relax=list(l['relax'])) for l in rr.LADDER],
        seeds=rr.SEEDS, terminal_seeds=rr.TERMINAL_SEEDS,
        iters=rr.RELAX_ITER,
        by_level=by_level, by_binding=by_binding,
        n_ramp=N_RAMP,
        baseline=dict(glide_deg=float(nom['glide_deg']),
                      v_norm=float(nom['v_norm']),
                      euler_deg=45.0, rate_dps=10.0, v_axis=60.0),
        cases=[dict(fault=r['fault'], short=ic.CASES[r['fault']].short,
                    label=ic.CASES[r['fault']].label, klass=r['klass'],
                    point=r['point'], t_f=r['t_f'], alt=r['alt'], rng=r['rng'],
                    base_outcome=r['base_outcome'], level=r['level'],
                    level_label=r['level_label'], outcome=r['outcome'],
                    lands=bool(r['lands']), margin=r['margin'],
                    binding=r['binding'], binding_ratio=r.get('binding_ratio'),
                    cone_ratio=r.get('cone_ratio'),
                    path_min_deg=r.get('path_min_deg'),
                    att_max_deg=r.get('att_max_deg'),
                    rate_max_dps=r.get('rate_max_dps'),
                    vax_max=r.get('vax_max'), vnorm_max=r.get('vnorm_max'),
                    alt_min=r.get('alt_min'), floor_ratio=r.get('floor_ratio'),
                    subsurface_depth=r.get('subsurface_depth'),
                    cone_transient=r.get('cone_ratio_transient'),
                    rate_transient=r.get('rate_ratio_transient'),
                    att_transient=r.get('att_ratio_transient'),
                    base_margin=base.get((r['fault'], r['point']), {}).get('margin'),
                    iters=r.get('iters'), wall=r.get('wall'))
               for r in sorted(rows, key=lambda r: (r['fault'], r['t_f']))],
        wall_hours=float(np.nansum([r.get('wall', np.nan) for r in rows]) / 3600.0))
    with open(os.path.join(RESULTS, 'headline_HR.json'), 'w') as fh:
        json.dump(head, fh, indent=1, default=float)
    print(f"[saved] {os.path.join(RESULTS, 'headline_HR.json')}")

    fig_ladder(rows, os.path.join(FIGURES, 'HR1_ladder.png'))
    fig_excursions(rows, os.path.join(FIGURES, 'HR2_excursions.png'))
    fig_traj(rows, nom, os.path.join(FIGURES, 'HR3_trajectories.png'))


if __name__ == '__main__':
    main()
