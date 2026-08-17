"""
STUDY G — analysis
══════════════════
Turns results/G_samples.csv into results/headline_G.json and the figures the
report is built from.  Every number quoted in the report comes out of the JSON,
so the prose cannot drift from the campaign it describes.

Three questions are answered, in order of how much they are worth:

  1. MARGINAL   what does each fault cost, pooled over all four regimes?
                A Wilson interval on the pooled landing rate.
  2. PAIRED     of the initial conditions from which the *healthy* vehicle
                lands, how many does the faulted vehicle still land from?
                This is the fault's own contribution, with the state dispersion
                differenced out — the pairing makes it a McNemar test.
  3. CONDITIONAL how the fault's cost varies with where the vehicle started:
                the fault x regime matrix, and landing rate against initial
                altitude across the whole campaign.
"""

import os
import sys
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')

import fault_catalogue as fc      # noqa: E402
import fault_lib as fl            # noqa: E402
import campaign as cp             # noqa: E402


# ══════════════════════════════════════════════════════════════════════
#  PALETTE
# ══════════════════════════════════════════════════════════════════════
#  Colour carries the FTC fault structure of framework section 3 — additive,
#  multiplicative, structural — because that is the classification which decides
#  what a controller has to *do* about the fault, and it is the one comparison
#  the reader makes across every figure.  Three hues (the validated all-pairs
#  set) plus neutral grey for the healthy control; the multiplicative variants
#  (coupled, time-varying) stay inside the multiplicative hue and are separated
#  by their labels, not by a fourth colour.
# ══════════════════════════════════════════════════════════════════════

SURFACE = '#fcfcfb'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8985'
CLASS_COLOR = {'none': '#9a9994',
               'additive': '#2a78d6',
               'multiplicative': '#eb6834',
               'structural': '#1baf7a'}
STATUS = {'land': '#0ca30c', 'gate_miss': '#fab219',
          'no_recovery': '#d03b3b', 'already_lost': '#8a8985'}
SEQ = ['#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7',
       '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281',
       '#0d366b']

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE,
    'axes.edgecolor': '#d8d7d2', 'axes.labelcolor': INK2,
    'text.color': INK, 'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': '#e7e6e1', 'grid.linewidth': 0.8,
    'axes.axisbelow': True, 'font.size': 9,
})


def klass(structure):
    """Collapse the catalogue's structure label onto the framework's own
    three-way taxonomy.  'multiplicative (coupled)' and 'time-varying
    multiplicative' are multiplicative faults with a rider, not new kinds."""
    if structure == 'none':
        return 'none'
    if 'multiplicative' in structure:
        return 'multiplicative'
    return structure


# ══════════════════════════════════════════════════════════════════════
#  LOAD
# ══════════════════════════════════════════════════════════════════════

def load():
    rows = cp.read_csv(os.path.join(RESULTS, 'G_samples.csv'))
    for r in rows:
        r['lands'] = r['lands'] in ('True', 'true', '1')
        r['sample'] = int(r['sample'])
        for k in ('margin', 'alt', 'wall', 'v_vert', 'v_horiz', 'tilt_deg',
                  'pos_err', 'rate_deg'):
            try:
                r[k] = float(r[k])
            except (ValueError, KeyError, TypeError):
                r[k] = np.nan
        r['klass'] = klass(r['structure'])
    return rows


def rate(rows):
    k, n = sum(r['lands'] for r in rows), len(rows)
    p, lo, hi = fl.wilson(k, n)
    return dict(k=int(k), n=int(n), p=p, lo=lo, hi=hi)


def mcnemar(rows, base):
    """Paired healthy-vs-fault comparison over the shared initial conditions.

    n10 = healthy lands, fault does not (the fault's cost)
    n01 = fault lands, healthy does not (should be ~0; a non-zero count is
          either a genuinely helpful asymmetry or solver noise, and either way
          the test is two-sided so it is not swept under the rug)
    Exact binomial on the discordant pairs — the sample sizes here are far too
    small for the chi-square approximation.
    """
    from scipy.stats import binomtest
    key = lambda r: (r['regime'], r['sample'])
    b = {key(r): r['lands'] for r in base}
    n10 = n01 = both = neither = 0
    for r in rows:
        h = b.get(key(r))
        if h is None:
            continue
        if h and not r['lands']:
            n10 += 1
        elif r['lands'] and not h:
            n01 += 1
        elif h:
            both += 1
        else:
            neither += 1
    d = n01 + n10
    p = 1.0 if d == 0 else binomtest(n01, d, 0.5).pvalue
    surv = both / (both + n10) if (both + n10) else float('nan')
    return dict(n10=n10, n01=n01, both=both, neither=neither,
                n_disc=d, p=float(p), survival=surv,
                n_healthy_lands=both + n10)


# ══════════════════════════════════════════════════════════════════════
#  FIGURES
# ══════════════════════════════════════════════════════════════════════

def order_faults(rows):
    """Catalogue order, but grouped by fault class so the figures read as the
    taxonomy rather than as an arbitrary list."""
    present = {r['fault'] for r in rows}
    out = []
    for cl in ('none', 'additive', 'multiplicative', 'structural'):
        out += [k for k in fc.KEYS
                if k in present and klass(fc.CASES[k].structure) == cl]
    return out


def seq_color(p):
    return SEQ[int(np.clip(round(p * (len(SEQ) - 1)), 0, len(SEQ) - 1))]


def fig_heatmap(rows, faults, regs, path):
    """Landing probability over the fault x regime product — the study's
    primary result.  Every cell carries its own number, which is also the
    relief the light sequential steps require."""
    M = np.full((len(faults), len(regs) + 1), np.nan)
    K = np.zeros_like(M)
    for i, f in enumerate(faults):
        for j, g in enumerate(regs):
            rs = [r for r in rows if r['fault'] == f and r['regime'] == g]
            if rs:
                M[i, j] = sum(r['lands'] for r in rs) / len(rs)
                K[i, j] = len(rs)
        rs = [r for r in rows if r['fault'] == f]
        M[i, -1] = sum(r['lands'] for r in rs) / len(rs)
        K[i, -1] = len(rs)

    fig, ax = plt.subplots(figsize=(8.4, 0.42 * len(faults) + 2.4))
    for i in range(len(faults)):
        for j in range(M.shape[1]):
            if np.isnan(M[i, j]):
                continue
            xo = j + (0.22 if j == M.shape[1] - 1 else 0.0)
            ax.add_patch(plt.Rectangle((xo + 0.02, i + 0.02), 0.96, 0.96,
                                       facecolor=seq_color(M[i, j]),
                                       edgecolor=SURFACE, linewidth=1.6))
            ax.text(xo + 0.5, i + 0.5, f'{M[i, j]:.2f}', ha='center',
                    va='center', fontsize=8.5,
                    color='#ffffff' if M[i, j] > 0.55 else INK)
    ax.set_xlim(0, M.shape[1] + 0.22); ax.set_ylim(len(faults), 0)
    ax.set_xticks(np.arange(M.shape[1]) + 0.5 +
                  np.r_[np.zeros(M.shape[1] - 1), 0.22])
    ax.set_xticklabels([fc.REG[g].label for g in regs] +
                       [f'all\n(n={int(K[0, -1])})'], fontsize=8.5)
    ax.set_yticks(np.arange(len(faults)) + 0.5)
    ax.set_yticklabels([fc.CASES[f].label for f in faults], fontsize=8.5)
    for t, f in zip(ax.get_yticklabels(), faults):
        t.set_color(CLASS_COLOR[klass(fc.CASES[f].structure)])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title('Landing probability by fault and initial-condition regime\n'
                 f'{int(K[0, 0])} shared initial conditions per cell; '
                 'label colour = FTC fault structure',
                 fontsize=10.5, weight='bold', color=INK, loc='left')
    handles = [Patch(facecolor=CLASS_COLOR[c], label=c)
               for c in ('additive', 'multiplicative', 'structural')]
    ax.legend(handles=handles, loc='upper center', ncol=3, frameon=False,
              bbox_to_anchor=(0.5, -0.06), fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def fig_forest(stats, faults, path, healthy_p):
    """Pooled landing rate per fault with its Wilson interval.  Sorted, so the
    ranking is the message; the healthy control is the reference line."""
    ks = sorted(faults, key=lambda f: stats[f]['p'])
    y = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(7.6, 0.36 * len(ks) + 1.8))
    ax.axvline(healthy_p, color=MUTED, lw=1.4, ls='--', zorder=1)
    ax.text(healthy_p, -0.9, f' healthy {healthy_p:.2f}', color=INK2,
            fontsize=8, va='bottom')
    for i, f in enumerate(ks):
        s = stats[f]
        c = CLASS_COLOR[klass(fc.CASES[f].structure)]
        ax.plot([s['lo'], s['hi']], [i, i], color=c, lw=2.0,
                solid_capstyle='round', alpha=0.55)
        ax.plot([s['p']], [i], 'o', ms=8, color=c, mec=SURFACE, mew=1.5)
        ax.text(1.02, i, f"{s['p']:.2f}  ({s['k']}/{s['n']})", fontsize=8,
                va='center', color=INK2, transform=ax.get_yaxis_transform())
    ax.set_yticks(y)
    ax.set_yticklabels([fc.CASES[f].label for f in ks], fontsize=8.5)
    for t, f in zip(ax.get_yticklabels(), ks):
        t.set_color(CLASS_COLOR[klass(fc.CASES[f].structure)])
    ax.set_ylim(-1.2, len(ks) - 0.4)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel('Landing probability, pooled over all regimes '
                  '(bar = 95 % Wilson interval)')
    ax.grid(axis='y', visible=False)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.set_title('What each fault costs', fontsize=10.5, weight='bold',
                 color=INK, loc='left')
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def fig_paired(mc, faults, path):
    """The paired view: of the initial conditions the healthy vehicle lands
    from, the share the faulted vehicle still lands from.  The state dispersion
    is differenced out, so what is left is the fault."""
    ks = [f for f in faults if f != 'healthy']
    ks = sorted(ks, key=lambda f: mc[f]['survival'])
    y = np.arange(len(ks))
    fig, ax = plt.subplots(figsize=(7.6, 0.36 * len(ks) + 1.8))
    for i, f in enumerate(ks):
        m = mc[f]
        c = CLASS_COLOR[klass(fc.CASES[f].structure)]
        ax.barh(i, m['survival'], height=0.62, color=c, edgecolor=SURFACE,
                linewidth=1.2)
        star = ' *' if m['p'] < 0.05 else ''
        ax.text(m['survival'] + 0.012, i,
                f"{m['survival']:.2f}   lost {m['n10']}/{m['n_healthy_lands']}"
                f"{star}", fontsize=8, va='center', color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels([fc.CASES[f].label for f in ks], fontsize=8.5)
    for t, f in zip(ax.get_yticklabels(), ks):
        t.set_color(CLASS_COLOR[klass(fc.CASES[f].structure)])
    ax.set_xlim(0, 1.35)
    ax.set_xticks(np.arange(0, 1.01, 0.25))
    ax.set_xlabel('Share of healthy-landable initial conditions still landed')
    ax.grid(axis='y', visible=False)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.set_title('Paired survival: the same states, a different vehicle\n'
                 '* marks a McNemar $p$ < 0.05 against the healthy control',
                 fontsize=10.5, weight='bold', color=INK, loc='left')
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


OUTCOMES = ['land', 'gate_miss', 'no_recovery', 'already_lost']
OUT_LABEL = {'land': 'landed', 'gate_miss': 'flew but missed the gate',
             'no_recovery': 'no trajectory found',
             'already_lost': 'lost before the planner ran'}


def fig_outcomes(rows, faults, path):
    """How the failures fail.  'gate_miss' and 'no_recovery' are different
    engineering problems: the first is a vehicle that arrives too hard, the
    second is a vehicle for which no arrival exists."""
    fig, ax = plt.subplots(figsize=(8.0, 0.38 * len(faults) + 2.0))
    for i, f in enumerate(faults):
        rs = [r for r in rows if r['fault'] == f]
        n = len(rs)
        left = 0.0
        for o in OUTCOMES:
            w = sum(r['outcome'] == o for r in rs) / n
            if w <= 0:
                continue
            ax.barh(i, w, left=left, height=0.62, color=STATUS[o],
                    edgecolor=SURFACE, linewidth=1.4)
            if w > 0.09:
                ax.text(left + w / 2, i, f'{100 * w:.0f}', ha='center',
                        va='center', fontsize=7.5,
                        color='#ffffff' if o != 'gate_miss' else INK)
            left += w
    ax.set_yticks(np.arange(len(faults)))
    ax.set_yticklabels([fc.CASES[f].label for f in faults], fontsize=8.5)
    for t, f in zip(ax.get_yticklabels(), faults):
        t.set_color(CLASS_COLOR[klass(fc.CASES[f].structure)])
    ax.set_ylim(len(faults) - 0.4, -0.6)
    ax.set_xlim(0, 1)
    ax.set_xlabel('Share of the 4 x n initial conditions  [%/100]')
    ax.grid(axis='y', visible=False)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.legend(handles=[Patch(facecolor=STATUS[o], label=OUT_LABEL[o])
                       for o in OUTCOMES],
              loc='upper center', bbox_to_anchor=(0.5, -0.10), ncol=2,
              frameon=False, fontsize=8.5)
    ax.set_title('Outcome composition', fontsize=10.5, weight='bold',
                 color=INK, loc='left')
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def fig_altitude(rows, path, nbin=5):
    """Landing rate against the one initial-condition coordinate that turns out
    to matter most, with the fault classes separated.  The regimes are boxes;
    this is the continuous cut through them."""
    alt = np.array([r['alt'] for r in rows])
    edges = np.quantile(alt, np.linspace(0, 1, nbin + 1))
    edges[-1] += 1.0
    ctr = 0.5 * (edges[:-1] + edges[1:])

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ends = []
    for cl in ('none', 'additive', 'multiplicative', 'structural'):
        sub = [r for r in rows if r['klass'] == cl]
        if not sub:
            continue
        ps, los, his = [], [], []
        for a, b in zip(edges[:-1], edges[1:]):
            rs = [r for r in sub if a <= r['alt'] < b]
            p, lo, hi = fl.wilson(sum(r['lands'] for r in rs), len(rs))
            ps.append(p); los.append(lo); his.append(hi)
        c = CLASS_COLOR[cl]
        ax.fill_between(ctr, los, his, color=c, alpha=0.13, lw=0)
        ax.plot(ctr, ps, '-o', color=c, lw=2.0, ms=6, mec=SURFACE, mew=1.2)
        ends.append(('healthy' if cl == 'none' else cl, ps[-1], c))

    # Direct labels at the right-hand end, nudged apart: healthy and additive
    # finish on top of each other at 1.00, and two labels in the same place is
    # the same as no label at all.
    ends.sort(key=lambda e: -e[1])
    y_prev = None
    for name, y, c in ends:
        y_lab = y if y_prev is None else min(y, y_prev - 0.052)
        if y_prev is not None and y_lab != y:
            ax.plot([ctr[-1], ctr[-1] + 14], [y, y_lab], color=c, lw=0.8,
                    alpha=0.6)
        ax.text(ctr[-1] + 18, y_lab, name, color=c, fontsize=8.5, va='center')
        y_prev = y_lab
    ax.set_xlabel('Initial altitude  [m]   (equal-count bins over the campaign)')
    ax.set_ylabel('Landing probability')
    ax.set_ylim(0, 1)
    ax.set_xlim(edges[0] - 20, edges[-1] + 300)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.set_title('Altitude buys recovery — for some fault classes more than '
                 'others', fontsize=10.5, weight='bold', color=INK, loc='left')
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


def fig_margin(rows, path):
    """Gate margin over the cases where a trajectory *was* found.  A margin of
    1.0 is the landing gate itself: left of it the vehicle lands, and how far
    left says how much of the gate it had to spend."""
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.axvline(1.0, color=MUTED, lw=1.4, ls='--')
    ax.text(1.03, 0.03, 'landing gate', color=INK2, fontsize=8.5)
    for cl in ('none', 'additive', 'multiplicative', 'structural'):
        m = np.array([r['margin'] for r in rows
                      if r['klass'] == cl
                      and r['outcome'] in ('land', 'gate_miss')
                      and np.isfinite(r['margin'])])
        if m.size < 3:
            continue
        m = np.sort(m)
        ax.step(m, np.arange(1, m.size + 1) / m.size, where='post',
                color=CLASS_COLOR[cl], lw=2.0,
                label=f"{'healthy' if cl == 'none' else cl}  (n={m.size})")
    ax.set_xscale('log')
    # Clipped deliberately: a handful of gate misses land at margins in the
    # thousands (a vehicle arriving sideways at 40 m/s scores badly on every
    # criterion at once), and letting them set the axis compresses the entire
    # interesting range — 0.1 to a few times the gate — into one pixel column.
    ax.set_xlim(0.05, 20)
    ax.set_xlabel('Worst normalised gate margin at touchdown  '
                  '(1.0 = the gate; axis clipped at 20)')
    ax.set_ylabel('Cumulative share of solved cases')
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8.5, loc='lower right')
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.set_title('How close the ones that flew came to the gate',
                 fontsize=10.5, weight='bold', color=INK, loc='left')
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    rows = load()
    faults = order_faults(rows)
    regs = [g for g in fc.REG_KEYS if any(r['regime'] == g for r in rows)]
    base = [r for r in rows if r['fault'] == 'healthy']

    stats = {f: rate([r for r in rows if r['fault'] == f]) for f in faults}
    by_reg = {g: rate([r for r in rows if r['regime'] == g]) for g in regs}
    cell = {f: {g: rate([r for r in rows if r['fault'] == f
                         and r['regime'] == g]) for g in regs}
            for f in faults}
    mc = {f: mcnemar([r for r in rows if r['fault'] == f], base)
          for f in faults}
    by_class = {cl: rate([r for r in rows if r['klass'] == cl])
                for cl in ('none', 'additive', 'multiplicative', 'structural')}
    class_reg = {cl: {g: rate([r for r in rows if r['klass'] == cl
                               and r['regime'] == g]) for g in regs}
                 for cl in ('none', 'additive', 'multiplicative', 'structural')}
    outcomes = {f: {o: sum(r['outcome'] == o for r in rows
                           if r['fault'] == f) for o in OUTCOMES}
                for f in faults}

    n_cell = len([r for r in rows if r['fault'] == 'healthy'
                  and r['regime'] == regs[0]])
    head = dict(
        n_solves=len(rows), n_per_cell=n_cell,
        n_faults=len(faults), n_regimes=len(regs),
        faults=faults, regimes=regs,
        catalogue={f: dict(label=fc.CASES[f].label, short=fc.CASES[f].short,
                           section=fc.CASES[f].section,
                           structure=fc.CASES[f].structure,
                           klass=klass(fc.CASES[f].structure),
                           temporal=fc.CASES[f].temporal,
                           detail=fc.CASES[f].detail) for f in faults},
        regime_info={g: dict(label=fc.REG[g].label, blurb=fc.REG[g].blurb)
                     for g in regs},
        rates=stats, cells=cell, by_regime=by_reg, by_class=by_class,
        class_regime=class_reg, mcnemar=mc, outcomes=outcomes,
        wall_hours=sum(r['wall'] for r in rows) / 3600.0,
    )
    with open(os.path.join(RESULTS, 'headline_G.json'), 'w') as fh:
        json.dump(head, fh, indent=1, default=float)
    print(f"[saved] {os.path.join(RESULTS, 'headline_G.json')}")

    fig_heatmap(rows, faults, regs, os.path.join(FIGURES, 'G1_heatmap.png'))
    fig_forest(stats, faults, os.path.join(FIGURES, 'G2_forest.png'),
               stats['healthy']['p'])
    fig_paired(mc, faults, os.path.join(FIGURES, 'G3_paired.png'))
    fig_outcomes(rows, faults, os.path.join(FIGURES, 'G4_outcomes.png'))
    fig_altitude(rows, os.path.join(FIGURES, 'G5_altitude.png'))
    fig_margin(rows, os.path.join(FIGURES, 'G6_margin.png'))


if __name__ == '__main__':
    main()
