"""
Study F analysis — figures, paired statistics, and the verdict on the claim.
═══════════════════════════════════════════════════════════════════════════
Every number the Study F report quotes is produced here and written to
results/headline_F.json, so the prose can never drift from the data.
"""

import os
import json
import csv

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import fault_lib as fl
from campaign import RESULTS, FIGURES
import run_study_F as F


OUTCOME_COLOR = {'land': '#2E7D32', 'gate_miss': '#F9A825',
                 'no_recovery': '#C62828', 'already_lost': '#4A148C'}
OUTCOME_LABEL = {'land': 'lands', 'gate_miss': 'reaches ground, gate missed',
                 'no_recovery': 'no recovery trajectory',
                 'already_lost': 'already lost at t=0'}
ORDER = ['land', 'gate_miss', 'no_recovery', 'already_lost']


def load():
    p = os.path.join(RESULTS, 'F_samples.csv')
    if not os.path.exists(p):
        return []
    out = []
    for r in csv.DictReader(open(p)):
        d = dict(r)
        d['lands'] = r['lands'] in ('True', 'true', '1')
        for k in ('sample', 'iters', 'N'):
            d[k] = int(float(r[k])) if r[k] else -1
        for k in ('margin', 'y_eng', 'wall'):
            d[k] = float(r[k]) if r[k] not in ('', 'inf') else np.inf
        for k in F.ALL_NAMES:
            if r.get(k):
                d[k] = float(r[k])
        out.append(d)
    return out


def _style(ax, title=None, xlabel=None, ylabel=None):
    if title:
        ax.set_title(title, fontsize=10.5, weight='bold')
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9.5)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9.5)
    ax.grid(True, alpha=0.25, lw=0.6)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)


# ══════════════════════════════════════════════════════════════════════
#  McNemar — the paired test
# ══════════════════════════════════════════════════════════════════════

def mcnemar(a, b):
    """Exact McNemar test on paired boolean outcomes a (control) vs b (treated).

    Only *discordant* pairs carry information: n01 = control lands & treated
    does not, n10 = the reverse.  Under the null that the plant change has no
    effect, each discordant pair is an independent coin flip, so the exact
    p-value is a two-sided binomial test on n10 out of (n01 + n10).

    This is the right test here precisely because the samples are paired by
    construction — the same initial conditions are fed to both plants, so the
    state distribution cancels out of the comparison entirely.
    """
    from scipy.stats import binomtest
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    n01 = int(np.sum(a & ~b))         # control lands, treated does not
    n10 = int(np.sum(~a & b))         # treated lands, control does not
    n = n01 + n10
    if n == 0:
        return dict(n01=0, n10=0, discordant=0, p=1.0, note='no discordant pairs')
    p = float(binomtest(n10, n, 0.5).pvalue)
    return dict(n01=n01, n10=n10, discordant=n, p=p)


# ══════════════════════════════════════════════════════════════════════
#  FIG F1 — landing rate by plant, both spacings
# ══════════════════════════════════════════════════════════════════════

def fig_rates(rows, head):
    plants = [k for k in F.PLANTS if any(r['plant'] == k for r in rows)]
    by = {k: [r for r in rows if r['plant'] == k] for k in plants}

    fams = ['healthy', 'engine_out', 'thrust_eff', 'gimbal']
    fam_label = {'healthy': 'healthy', 'engine_out': 'engine out',
                 'thrust_eff': 'thrust efficiency', 'gimbal': 'gimbal degraded'}

    # order: within each spacing, group by family
    keys15 = [k for k in plants if F.PLANTS[k].y_eng == 1.5]
    keys025 = [k for k in plants if F.PLANTS[k].y_eng == 0.25]
    keys15.sort(key=lambda k: (fams.index(F.PLANTS[k].family), k))
    keys025.sort(key=lambda k: (fams.index(F.PLANTS[k].family), k))

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6), sharex=True)
    stats = {}
    for ax, keys, y in ((axes[0], keys15, 1.5), (axes[1], keys025, 0.25)):
        labels, ps, los, his, cols = [], [], [], [], []
        for k in keys:
            rs = by[k]
            nk = sum(r['lands'] for r in rs)
            p, lo, hi = fl.wilson(nk, len(rs))
            stats[k] = dict(n=len(rs), n_land=nk, p=p, lo=lo, hi=hi,
                            family=F.PLANTS[k].family, y_eng=y,
                            label=F.PLANTS[k].label)
            labels.append(F.PLANTS[k].label.split(',')[0])
            ps.append(p); los.append(lo); his.append(hi)
            cols.append('#1565C0' if F.PLANTS[k].family == 'healthy'
                        else '#00838F')
        ypos = np.arange(len(keys))[::-1]
        ax.barh(ypos, ps, color=cols, height=0.6)
        ax.errorbar(ps, ypos,
                    xerr=[np.array(ps) - np.array(los),
                          np.array(his) - np.array(ps)],
                    fmt='none', ecolor='k', capsize=4, lw=1.1)
        for yy, p, n in zip(ypos, ps, [stats[k]['n_land'] for k in keys]):
            ax.text(min(p + 0.03, 0.9), yy, f'{p:.2f}', va='center', fontsize=9)
        ax.set_yticks(ypos); ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlim(0, 1.05)
        _style(ax, f'$y_{{eng}}$ = {y:g} m', 'P(landing possible)', None)

    fig.suptitle('Study F — landing rate by plant, from identical initial '
                 'conditions', fontsize=13, weight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    p = os.path.join(FIGURES, 'F_landing_rates.png')
    fig.savefig(p, dpi=160, bbox_inches='tight'); plt.close(fig)
    print('[saved]', p)
    head['rates'] = stats
    return stats


# ══════════════════════════════════════════════════════════════════════
#  FIG F2 — the claim under test
# ══════════════════════════════════════════════════════════════════════

def fig_claim(rows, head):
    """Is a fault an initial condition?

    Left: paired outcomes, healthy vs each damaged plant, on the SAME states.
    Right: the state-space projection, showing that the healthy and damaged
    landing sets are not the same set of states.
    """
    plants = [k for k in F.PLANTS if any(r['plant'] == k for r in rows)]
    by = {k: {r['sample']: r for r in rows if r['plant'] == k} for k in plants}

    tests = {}
    for y in (1.5, 0.25):
        ctrl = f'healthy_y{y:g}'
        if ctrl not in by:
            continue
        ids = sorted(by[ctrl])
        a = [by[ctrl][i]['lands'] for i in ids]
        for k in plants:
            if k == ctrl or F.PLANTS[k].y_eng != y:
                continue
            common = [i for i in ids if i in by[k]]
            aa = [by[ctrl][i]['lands'] for i in common]
            bb = [by[k][i]['lands'] for i in common]
            t = mcnemar(aa, bb)
            t['n_pairs'] = len(common)
            t['control'] = ctrl
            t['label'] = F.PLANTS[k].label
            tests[k] = t

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4))

    # (a) discordance: how often the plant flips the outcome
    ax = axes[0]
    keys = [k for k in plants if k in tests]
    keys.sort(key=lambda k: (-F.PLANTS[k].y_eng, k))
    ypos = np.arange(len(keys))[::-1]
    n01 = np.array([tests[k]['n01'] for k in keys])
    n10 = np.array([tests[k]['n10'] for k in keys])
    npair = np.array([tests[k]['n_pairs'] for k in keys])
    ax.barh(ypos, -n01 / npair, color='#C62828', height=0.6,
            label='healthy lands, damaged does not')
    ax.barh(ypos, n10 / npair, color='#2E7D32', height=0.6,
            label='damaged lands, healthy does not')
    for yy, x1, x2, k in zip(ypos, n01, n10, keys):
        if x1:
            ax.text(-x1 / tests[k]['n_pairs'] - 0.01, yy, str(x1), va='center',
                    ha='right', fontsize=8)
        if x2:
            ax.text(x2 / tests[k]['n_pairs'] + 0.01, yy, str(x2), va='center',
                    fontsize=8)
    ax.axvline(0, color='k', lw=0.8)
    ax.set_yticks(ypos)
    ax.set_yticklabels([F.PLANTS[k].label for k in keys], fontsize=8)
    _style(ax, '(a) outcome flips on identical states\n'
               'zero width = a fault would be an initial condition',
           'share of paired samples', None)
    ax.legend(fontsize=7.5, loc='upper center', bbox_to_anchor=(0.5, -0.12),
              ncol=2, frameon=False)

    # (b) the same states, coloured by outcome under two plants
    ax = axes[1]
    y = 1.5
    ctrl, dmg = f'healthy_y{y:g}', f'engout_y{y:g}'
    if ctrl in by and dmg in by:
        ids = [i for i in sorted(by[ctrl]) if i in by[dmg]]
        alt = np.array([by[ctrl][i].get('alt', np.nan) for i in ids])
        rr = np.array([np.hypot(by[ctrl][i].get('x_E', 0),
                                by[ctrl][i].get('y_E', 0)) for i in ids])
        ca_ = np.array([by[ctrl][i]['lands'] for i in ids])
        cb = np.array([by[dmg][i]['lands'] for i in ids])
        ax.scatter(rr[ca_ & cb], alt[ca_ & cb], s=42, c='#2E7D32',
                   edgecolors='white', lw=0.5, label='lands under both')
        ax.scatter(rr[ca_ & ~cb], alt[ca_ & ~cb], s=52, c='#C62828',
                   marker='X', edgecolors='white', lw=0.5,
                   label='healthy only — the plant effect')
        ax.scatter(rr[~ca_], alt[~ca_], s=30, c='#9E9E9E',
                   edgecolors='white', lw=0.4, label='healthy already fails')
        ax.legend(fontsize=8, loc='upper left')
    _style(ax, f'(b) identical states, two plants\n'
               f'healthy vs engine-out at $y_{{eng}}$={y:g} m',
           'horizontal range $r$ [m]', 'altitude [m]')

    fig.suptitle('Study F — can a fault be represented as an initial '
                 'condition?', fontsize=13, weight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p = os.path.join(FIGURES, 'F_claim.png')
    fig.savefig(p, dpi=160, bbox_inches='tight'); plt.close(fig)
    print('[saved]', p)
    head['mcnemar'] = tests
    return tests


# ══════════════════════════════════════════════════════════════════════
#  FIG F3 — outcome mix + what the spacing change buys
# ══════════════════════════════════════════════════════════════════════

def fig_outcomes(rows, head):
    plants = [k for k in F.PLANTS if any(r['plant'] == k for r in rows)]
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4))

    # (a) stacked outcome mix
    ax = axes[0]
    keys = sorted(plants, key=lambda k: (-F.PLANTS[k].y_eng, k))
    ypos = np.arange(len(keys))[::-1]
    left = np.zeros(len(keys))
    mix = {}
    for o in ORDER:
        v = []
        for k in keys:
            rs = [r for r in rows if r['plant'] == k]
            v.append(sum(1 for r in rs if r['outcome'] == o) / max(len(rs), 1))
        v = np.array(v)
        mix[o] = {k: float(x) for k, x in zip(keys, v)}
        ax.barh(ypos, v, left=left, color=OUTCOME_COLOR[o], height=0.62,
                label=OUTCOME_LABEL[o])
        left += v
    ax.set_yticks(ypos)
    ax.set_yticklabels([F.PLANTS[k].label for k in keys], fontsize=8)
    ax.set_xlim(0, 1)
    _style(ax, '(a) outcome mix by plant', 'share of samples', None)
    ax.legend(fontsize=7.5, loc='lower right')

    # (b) the spacing contrast, family by family
    ax = axes[1]
    fams, d15, d025 = [], [], []
    for k in [p for p in plants if F.PLANTS[p].y_eng == 1.5]:
        k2 = k.replace('y1.5', 'y0.25')
        if k2 not in plants:
            continue
        r1 = [r for r in rows if r['plant'] == k]
        r2 = [r for r in rows if r['plant'] == k2]
        fams.append(F.PLANTS[k].label.split(',')[0])
        d15.append(sum(r['lands'] for r in r1) / max(len(r1), 1))
        d025.append(sum(r['lands'] for r in r2) / max(len(r2), 1))
    x = np.arange(len(fams))
    ax.bar(x - 0.2, d15, width=0.4, color='#8E24AA',
           label='$y_{eng}$ = 1.5 m (as designed)')
    ax.bar(x + 0.2, d025, width=0.4, color='#00897B',
           label='$y_{eng}$ = 0.25 m')
    for xi, (a, b) in enumerate(zip(d15, d025)):
        if b - a > 0.02:
            ax.annotate('', xy=(xi + 0.2, b), xytext=(xi - 0.2, a),
                        arrowprops=dict(arrowstyle='->', color='k', lw=1.1))
            ax.text(xi, max(a, b) + 0.05, f'+{100*(b-a):.0f} pp',
                    ha='center', fontsize=8.5, weight='bold')
    ax.set_xticks(x); ax.set_xticklabels(fams, fontsize=8, rotation=12)
    ax.set_ylim(0, 1.12)
    _style(ax, '(b) what moving the engines in buys\n'
               'same thrust loss, roll authority restored',
           None, 'P(landing possible)')
    ax.legend(fontsize=8, loc='upper left')

    fig.suptitle('Study F — failure modes and the engine-spacing contrast',
                 fontsize=13, weight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p = os.path.join(FIGURES, 'F_outcomes.png')
    fig.savefig(p, dpi=160, bbox_inches='tight'); plt.close(fig)
    print('[saved]', p)
    head['outcome_mix'] = mix
    head['spacing'] = {f: dict(y15=a, y025=b)
                       for f, a, b in zip(fams, d15, d025)}


# ══════════════════════════════════════════════════════════════════════
#  Which state dimensions decide it
# ══════════════════════════════════════════════════════════════════════

def surrogate(rows, head):
    """Fit a classifier per spacing over the 22 state dimensions.

    Fitted on the pooled damaged plants, so it answers 'given something is
    broken, which parts of the state space are still recoverable?'.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.inspection import permutation_importance
    from sklearn.preprocessing import StandardScaler

    out = {}
    for y in (1.5, 0.25):
        rs = [r for r in rows
              if F.PLANTS[r['plant']].y_eng == y
              and F.PLANTS[r['plant']].family != 'healthy']
        if len(rs) < 40:
            continue
        X = np.array([[r.get(n, np.nan) for n in F.ALL_NAMES] for r in rs])
        yv = np.array([r['lands'] for r in rs])
        keep = np.all(np.isfinite(X), axis=1)
        X, yv = X[keep], yv[keep]
        if yv.sum() < 5 or (~yv).sum() < 5:
            out[f'y{y:g}'] = dict(note='too few of one class to fit',
                                  n=int(len(yv)), n_land=int(yv.sum()))
            continue
        sc = StandardScaler().fit(X)
        Xs = sc.transform(X)
        clf = HistGradientBoostingClassifier(max_iter=250, max_depth=3,
                                             random_state=0)
        cv = StratifiedKFold(5, shuffle=True, random_state=0)
        acc = float(cross_val_score(clf, Xs, yv, cv=cv).mean())
        clf.fit(Xs, yv)
        imp = permutation_importance(clf, Xs, yv, n_repeats=12,
                                     random_state=0).importances_mean
        order = np.argsort(imp)[::-1]
        out[f'y{y:g}'] = dict(
            n=int(len(yv)), n_land=int(yv.sum()), cv_accuracy=acc,
            importance={F.ALL_NAMES[i]: float(imp[i]) for i in order[:8]})
    head['surrogate'] = out
    for k, v in out.items():
        if 'cv_accuracy' in v:
            print(f'[surrogate] {k}: CV {v["cv_accuracy"]:.3f}, top '
                  f'{list(v["importance"])[:4]}')


def main():
    rows = load()
    if not rows:
        print('no F_samples.csv yet')
        return
    head = dict(n_solves=len(rows),
                n_states=len({r['sample'] for r in rows}),
                n_plants=len({r['plant'] for r in rows}))
    fig_rates(rows, head)
    fig_claim(rows, head)
    fig_outcomes(rows, head)
    try:
        surrogate(rows, head)
    except Exception as e:
        print('surrogate skipped:', e)
    p = os.path.join(RESULTS, 'headline_F.json')
    json.dump(head, open(p, 'w'), indent=1, default=float)
    print('[saved]', p)


if __name__ == '__main__':
    main()
