"""
Analysis & figures for Studies D and E.
═══════════════════════════════════════
Reads results/*.csv, writes figures/*.png and results/headline.json — the
latter is what the report is built from, so every number quoted in the PDF
traces back to a campaign record rather than to prose.
"""

import os
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
os.makedirs(FIGURES, exist_ok=True)

import campaign as cp
import fault_lib as fl

# consistent outcome colouring across every figure
OUTCOME_COLOR = {
    'land':          '#2E7D32',   # green  — recovered and landed
    'gate_miss':     '#F9A825',   # amber  — reached the ground, out of gate
    'no_replan':     '#C62828',   # red    — no recovery trajectory exists
    'lost_in_delay': '#4A148C',   # purple — gone before anyone could react
    'no_time':       '#546E7A',   # grey   — no horizon left
    'not_run':       '#BDBDBD',
}
OUTCOME_LABEL = {
    'land': 'lands',
    'gate_miss': 'reaches ground, gate missed',
    'no_replan': 'no recovery trajectory',
    'lost_in_delay': 'lost during reaction delay',
    'no_time': 'no time left',
    'not_run': 'not run',
}
ORDER = ['land', 'gate_miss', 'no_replan', 'lost_in_delay', 'no_time', 'not_run']


def load(name):
    p = os.path.join(RESULTS, name)
    if not os.path.exists(p):
        return []
    rows = cp.read_csv(p)
    for r in rows:
        for k, v in list(r.items()):
            if v in ('', None):
                r[k] = np.nan
                continue
            if v in ('True', 'False'):
                r[k] = (v == 'True')
                continue
            try:
                r[k] = float(v)
            except (TypeError, ValueError):
                pass
    return rows


def _style(ax, title=None, xlabel=None, ylabel=None):
    ax.grid(True, alpha=0.25, lw=0.6)
    ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    if title:  ax.set_title(title, fontsize=11, weight='bold')
    if xlabel: ax.set_xlabel(xlabel)
    if ylabel: ax.set_ylabel(ylabel)


def outcome_legend(ax, present, **kw):
    h = [Patch(facecolor=OUTCOME_COLOR[o], label=OUTCOME_LABEL[o])
         for o in ORDER if o in present]
    ax.legend(handles=h, fontsize=8, framealpha=0.9, **kw)


# ══════════════════════════════════════════════════════════════════════
#  Shared helpers for the two-profile bisection figures
# ══════════════════════════════════════════════════════════════════════

PROF_COLOR = {'design': '#C62828', 'derated': '#1565C0'}
PROF_LABEL = {'design': 'design reference (max effort)',
              'derated': 'de-rated reference'}


def _by_profile(rows):
    out = {}
    for r in rows:
        out.setdefault(r.get('profile', 'design'), []).append(r)
    return out


def _bisect_figure(summ, samp, xkey, ykey, xlabel, ylabel, title, path,
                   head, key, ylog=True, yscale=1.0, extras=None):
    """One figure for a bisected boundary: the boundary per profile on the
    left, every solve behind it on the right."""
    allzero = all((r.get(ykey, 0) or 0) == 0 for r in summ)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
    ax = axes[0]
    store = {}
    for prof, rows in sorted(_by_profile(summ).items()):
        rows = sorted(rows, key=lambda r: r[xkey])
        x = np.array([r[xkey] for r in rows], float)
        y = np.array([r[ykey] if np.isfinite(r.get(ykey, np.nan)) else 0.0
                      for r in rows], float) * yscale
        brk = [r['bracket'] for r in rows]
        c = PROF_COLOR.get(prof, '#555')
        ax.plot(x, y, 'o-', color=c, lw=2, ms=7, label=PROF_LABEL.get(prof, prof))
        dead = np.array([b in ('unrecoverable', 'no_margin') for b in brk])
        if dead.any():
            ax.plot(x[dead], y[dead], 'X', color=c, ms=13, mew=2,
                    markerfacecolor='none')
        store[prof] = dict(x=x.tolist(), y=y.tolist(), bracket=brk,
                           n_solves=int(sum(r['n_solves'] for r in rows)))
    if allzero:
        # everything is unrecoverable: a log axis over an all-zero series
        # autoscales to a meaningless 1e-2 range, so say it in words instead
        ax.set_ylim(-0.15, 1.0)
        ax.text(0.5, 0.55, 'no surviving value anywhere\non either reference',
                transform=ax.transAxes, ha='center', fontsize=12,
                weight='bold', color='#C62828')
    elif ylog:
        ax.set_yscale('symlog', linthresh=10)
    _style(ax, title, xlabel, ylabel)
    h, l = ax.get_legend_handles_labels()
    h.append(Line2D([0], [0], marker='X', ls='', color='k', ms=10,
                    markerfacecolor='none', label='no surviving value'))
    ax.legend(handles=h, fontsize=8)
    if extras:
        extras(ax)

    ax = axes[1]
    for r in samp:
        o = r.get('outcome', 'no_replan')
        m = 'o' if r.get('profile', 'design') == 'derated' else 's'
        ax.plot(r[xkey if xkey in r else 't_f'],
                r.get('tau_d', 0) * (1e3 if 'delay' in ylabel else 1),
                m, ms=5, color=OUTCOME_COLOR.get(o, '#999'), alpha=0.8)
    _style(ax, 'every solve behind the boundary', xlabel,
           r'reaction delay $\tau_d$ [ms]')
    if allzero:
        ax.set_ylim(-0.1, 1.0)     # every sample sits at tau_d = 0
    else:
        ax.set_yscale('symlog', linthresh=10)
        ax.set_ylim(bottom=-1)
    outcome_legend(ax, {r.get('outcome') for r in samp}, loc='upper right')
    fig.tight_layout()
    fig.savefig(path, dpi=160); plt.close(fig); print('[saved]', path)
    head[key] = store
    return store


# ══════════════════════════════════════════════════════════════════════
#  FIG 1 — critical reaction delay vs onset time  (D1, engine-out)
# ══════════════════════════════════════════════════════════════════════

def fig_tau_vs_tf(head):
    summ, samp = load('D1_tau_star.csv'), load('D1_samples.csv')
    if not summ:
        return
    _bisect_figure(
        summ, samp, 't_f', 'tau_star',
        'fault onset $t_f$ [s]', r'critical reaction delay $\tau^*$ [ms]',
        'D1 — how long can the vehicle stay unaware?\n(hard engine-out, both references)',
        os.path.join(FIGURES, 'D1_critical_delay.png'), head, 'D1',
        yscale=1e3)


# ══════════════════════════════════════════════════════════════════════
#  FIG 2 — critical reaction delay vs severity  (D2)
# ══════════════════════════════════════════════════════════════════════

def fig_tau_vs_eta(head):
    summ, samp = load('D2_tau_star.csv'), load('D2_samples.csv')
    if not summ:
        return
    import apollo_full as af
    lm = af.LMParams()
    eta_sat = (lm.T_hover / 2) / lm.T_max_eng

    def mark(ax):
        ax.axvline(eta_sat, ls='--', c='#455A64', lw=1.3)
        ax.text(eta_sat, ax.get_ylim()[1] * 0.9,
                fr'  $\eta_{{sat}}$={eta_sat:.3f}', color='#455A64', fontsize=8)

    st = _bisect_figure(
        summ, samp, 'eta', 'tau_star',
        r'delivered thrust fraction $\eta$', r'critical delay $\tau^*$ [ms]',
        'D2 — reaction time bought by a partial fault',
        os.path.join(FIGURES, 'D2_critical_delay_vs_eta.png'), head, 'D2',
        yscale=1e3, extras=mark)
    head['D2']['eta_sat'] = float(eta_sat)


# ══════════════════════════════════════════════════════════════════════
#  FIG 3 — critical severity vs onset time  (D5)
# ══════════════════════════════════════════════════════════════════════

def fig_eta_vs_tf(head):
    summ, samp = load('D5_eta_star.csv'), load('D5_samples.csv')
    if not summ:
        return
    import apollo_full as af
    lm = af.LMParams()
    eta_sat = (lm.T_hover / 2) / lm.T_max_eng

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
    ax = axes[0]
    store = {}
    for prof, rows in sorted(_by_profile(summ).items()):
        rows = sorted(rows, key=lambda r: r['t_f'])
        x = np.array([r['t_f'] for r in rows], float)
        y = np.array([r.get('eta_star', np.nan) for r in rows], float)
        brk = [r['bracket'] for r in rows]
        c = PROF_COLOR.get(prof, '#555')
        finite = np.isfinite(y)
        ax.plot(x[finite], y[finite], 'o-', color=c, lw=2, ms=7,
                label=PROF_LABEL.get(prof, prof))
        if (~finite).any():
            ax.plot(x[~finite], np.full((~finite).sum(), 1.02), 'X', color=c,
                    ms=13, mew=2, markerfacecolor='none')
        if finite.any():
            ax.fill_between(x[finite], y[finite], 1.0, color=c, alpha=0.10)
        store[prof] = dict(t_f=x.tolist(), eta_star=y.tolist(), bracket=brk,
                           n_solves=int(sum(r['n_solves'] for r in rows)),
                           # 'no_margin' means the eta = 1 NULL-FAULT CONTROL
                           # failed.  A null fault changes nothing about the
                           # vehicle, so that slice tested the solver, not the
                           # physics, and is reported as an excluded control
                           # failure rather than as an unrecoverable fault.
                           n_control_fail=int(sum(1 for b in brk
                                                  if b == 'no_margin')))
    ax.axhline(eta_sat, ls='--', c='#455A64', lw=1.3)
    ax.text(ax.get_xlim()[1], eta_sat, f'$\\eta_{{sat}}$={eta_sat:.3f}  ',
            ha='right', va='bottom', fontsize=8, color='#455A64')
    ax.set_ylim(0, 1.12)
    nfail = sum(v.get('n_control_fail', 0) for v in store.values()
                if isinstance(v, dict))
    if nfail:
        ax.text(0.98, 1.06, f'\u2715 = null-fault control failed '
                            f'({nfail} slices, excluded)',
                transform=ax.get_yaxis_transform(), ha='right', va='center',
                fontsize=7.5, color='#555')
    _style(ax, 'D5 — mildest survivable fault, against when it arrives\n'
               r'(reaction delay fixed at 100 ms)',
           'fault onset $t_f$ [s]',
           r'critical delivered fraction $\eta^*$')
    h, l = ax.get_legend_handles_labels()
    h.append(Line2D([0], [0], marker='X', ls='', color='k', ms=10,
                    markerfacecolor='none', label='no survivable $\\eta$'))
    ax.legend(handles=h, fontsize=8, loc='lower right')

    ax = axes[1]
    for r in samp:
        o = r.get('outcome', 'no_replan')
        m = 'o' if r.get('profile', 'design') == 'derated' else 's'
        ax.plot(r['t_f'], r['eta'], m, ms=5,
                color=OUTCOME_COLOR.get(o, '#999'), alpha=0.85)
    _style(ax, 'every solve behind the boundary\n(circles de-rated, squares design)',
           'fault onset $t_f$ [s]', r'severity $\eta$')
    outcome_legend(ax, {r.get('outcome') for r in samp}, loc='center right')
    fig.tight_layout()
    p = os.path.join(FIGURES, 'D5_critical_severity.png')
    fig.savefig(p, dpi=160); plt.close(fig); print('[saved]', p)
    store['eta_sat'] = float(eta_sat)
    head['D5'] = store


# ══════════════════════════════════════════════════════════════════════
#  FIG 3 — Sobol coverage of the 3-D cube  (D3)
# ══════════════════════════════════════════════════════════════════════

def fig_sobol_cube(head):
    allrows = load('D3_samples.csv')
    if not allrows:
        return
    head['D3'] = {}
    for prof, rows in sorted(_by_profile(allrows).items()):
        _sobol_panel(rows, prof, head)


def _sobol_panel(s, prof, head):
    tf = np.array([r['t_f'] for r in s])
    eta = np.array([r['eta'] for r in s])
    td = np.array([r['tau_d'] for r in s])
    out = [r.get('outcome', 'no_replan') for r in s]
    ok = np.array([o == 'land' for o in out])

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    pairs = [(tf, eta, 'fault onset $t_f$ [s]', r'severity $\eta$'),
             (tf, td, 'fault onset $t_f$ [s]', r'reaction delay $\tau_d$ [s]'),
             (eta, td, r'severity $\eta$', r'reaction delay $\tau_d$ [s]')]
    for ax, (a, b, la, lb) in zip(axes, pairs):
        for o in ORDER:
            m = np.array([x == o for x in out])
            if m.any():
                ax.scatter(a[m], b[m], s=26, c=OUTCOME_COLOR[o],
                           edgecolors='none', alpha=0.85)
        _style(ax, None, la, lb)
    axes[0].set_title(f'D3 — Sobol coverage of the fault cube, {prof} '
                      f'reference, n = {len(s)}\n{ok.sum()} land '
                      f'({100*ok.mean():.1f} %)',
                      fontsize=11, weight='bold', loc='left')
    outcome_legend(axes[2], set(out), loc='upper right')
    fig.tight_layout()
    p = os.path.join(FIGURES, f'D3_sobol_cube_{prof}.png')
    fig.savefig(p, dpi=160); plt.close(fig); print('[saved]', p)

    p_, lo, hi = fl.wilson(int(ok.sum()), len(ok))
    head['D3'][prof] = dict(n=len(s), n_land=int(ok.sum()), p=p_, lo=lo, hi=hi,
                            breakdown={o: int(sum(1 for x in out if x == o))
                                       for o in ORDER if any(x == o for x in out)})


# ══════════════════════════════════════════════════════════════════════
#  Monotonicity audit — the premise bisection rests on
# ══════════════════════════════════════════════════════════════════════

def monotonicity_audit(head, t_tol=2.0):
    """Count dominance violations among the Sobol samples.

    Bisection assumes survival is monotone: more delivered thrust is never
    worse, more blind time is never better.  Sample A *dominates* B when it is
    no worse on every axis (eta_A >= eta_B, tau_A <= tau_B) at a comparable
    onset time.  A violation is then A failing while B lands — which the
    assumption forbids.  This is checked over every ordered pair rather than
    asserted from a scatter plot, because reading monotonicity off a projected
    scatter is exactly the kind of claim that looks true and is not.
    """
    rows = load('D3_samples.csv')
    if not rows:
        return
    res = {}
    for prof, rs in sorted(_by_profile(rows).items()):
        eta = np.array([r['eta'] for r in rs], float)
        tau = np.array([r['tau_d'] for r in rs], float)
        tf = np.array([r['t_f'] for r in rs], float)
        ok = np.array([r.get('outcome') == 'land' for r in rs])
        n = len(rs)
        pairs = viol = 0
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if (abs(tf[i] - tf[j]) <= t_tol and eta[i] >= eta[j]
                        and tau[i] <= tau[j]):
                    pairs += 1                      # i dominates j
                    if ok[j] and not ok[i]:
                        viol += 1
        res[prof] = dict(n=n, comparable_pairs=pairs, violations=viol,
                         t_tol=t_tol)
    head['monotonicity'] = res
    for k, v in res.items():
        print(f'[monotonicity] {k}: {v["violations"]} violations '
              f'in {v["comparable_pairs"]} comparable pairs')


# ══════════════════════════════════════════════════════════════════════
#  FIG 4 — mechanism of loss
# ══════════════════════════════════════════════════════════════════════

def fig_mechanism(head):
    s = (load('D3_samples.csv') + load('D1_samples.csv')
         + load('D2_samples.csv') + load('D5_samples.csv'))
    if not s:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))

    ax = axes[0]
    out = [r.get('outcome', 'no_replan') for r in s]
    counts = [(o, sum(1 for x in out if x == o)) for o in ORDER]
    counts = [c for c in counts if c[1]]
    ax.barh([OUTCOME_LABEL[o] for o, _ in counts][::-1],
            [n for _, n in counts][::-1],
            color=[OUTCOME_COLOR[o] for o, _ in counts][::-1])
    for i, (_, n) in enumerate(counts[::-1]):
        ax.text(n, i, f'  {n}  ({100*n/len(s):.0f} %)', va='center', fontsize=9)
    ax.set_xlim(0, max(n for _, n in counts) * 1.35)
    _style(ax, f'How the vehicle is lost — all {len(s)} fault solves',
           'samples', None)

    ax = axes[1]
    rate = np.array([r.get('rate_after_delay_deg', np.nan) for r in s], float)
    td = np.array([r.get('tau_d', np.nan) for r in s], float)
    good = np.isfinite(rate) & np.isfinite(td)
    for o in ORDER:
        m = good & np.array([r.get('outcome') == o for r in s])
        if m.any():
            ax.scatter(td[m] * 1e3, rate[m], s=22, c=OUTCOME_COLOR[o],
                       edgecolors='none', alpha=0.8)
    import apollo_full as af
    ax.axhline(np.rad2deg(af.OCPConfig().omega_max), ls='--', c='#455A64',
               lw=1.2)
    ax.text(ax.get_xlim()[1], np.rad2deg(af.OCPConfig().omega_max),
            'planner rate limit  ', ha='right', va='bottom', fontsize=8,
            color='#455A64')
    ax.axhline(fl.LOSS['rate_deg'], ls='--', c='#C62828', lw=1.2)
    ax.text(ax.get_xlim()[1], fl.LOSS['rate_deg'], 'hard tumble limit  ',
            ha='right', va='bottom', fontsize=8, color='#C62828')
    ax.set_xscale('symlog', linthresh=10)
    ax.set_xlim(left=-1)          # delays are non-negative; symlog would
    ax.set_yscale('log')          # otherwise draw a mirrored negative decade
    _style(ax, 'Body rate reached before anyone reacts',
           r'reaction delay $\tau_d$ [ms]',
           r'peak body rate at end of delay [$^\circ$/s]')
    fig.tight_layout()
    p = os.path.join(FIGURES, 'D_mechanism.png')
    fig.savefig(p, dpi=160); plt.close(fig); print('[saved]', p)

    head['mechanism'] = {o: n for o, n in counts}
    head['n_fault_solves'] = len(s)


# ══════════════════════════════════════════════════════════════════════
#  STUDY E — feasibility over the initial-condition box
# ══════════════════════════════════════════════════════════════════════

def _ic_matrix(rows, names):
    return np.array([[r[f'ic_{n}'] for n in names] for r in rows], float)


def fig_ic_montecarlo(head):
    from run_study_E import IC_NAMES, IC_UNITS, IC_LO, IC_HI
    s = load('E_samples.csv')
    if not s:
        return
    X = _ic_matrix(s, IC_NAMES)
    y_nom = np.array([bool(r['nom_lands']) for r in s])
    y_f = np.array([bool(r['fault_success']) for r in s])

    p_n, lo_n, hi_n = fl.wilson(int(y_nom.sum()), len(s))
    sub = y_nom
    p_f, lo_f, hi_f = fl.wilson(int(y_f[sub].sum()), int(sub.sum()))

    # ── the surrogate is fitted to the FAULTED outcome, not the healthy one.
    # Healthy feasibility came out near 1, leaving too few negatives for a
    # classifier to learn anything: an all-positive predictor would score ~0.98
    # and mean nothing.  The faulted outcome is where the structure is, and its
    # feature set is the 12 arrival dimensions *plus* the three fault
    # parameters, since those are part of what decides survival.
    FNAMES = IC_NAMES + ['eta', 't_f', 'tau_d']
    FUNITS = IC_UNITS + ['-', 's', 's']
    idx = np.where(sub)[0]
    XF = np.column_stack([
        X[idx],
        np.array([[float(s[i].get('eta', np.nan)),
                   float(s[i].get('t_f', np.nan)),
                   float(s[i].get('tau_d', np.nan))] for i in idx])])
    keep = np.all(np.isfinite(XF), axis=1)
    XF, YF = XF[keep], y_f[idx][keep]
    imp, acc, auc, clf, scaler = _surrogate(XF, YF)
    order = np.argsort(imp)

    fig = plt.figure(figsize=(13, 8.6))
    gs = fig.add_gridspec(2, 3, hspace=0.5, wspace=0.32)

    # (a) running estimates + Wilson bands
    ax = fig.add_subplot(gs[0, 0])
    n = np.arange(1, len(s) + 1)
    for lab, y, c in (('healthy', y_nom, '#1565C0'),
                      ('after a fault', y_f, '#6A1B9A')):
        run = np.cumsum(y) / n
        band = np.array([fl.wilson(int(np.sum(y[:i])), i)[1:] for i in n])
        ax.plot(n, run, color=c, lw=1.8, label=lab)
        ax.fill_between(n, band[:, 0], band[:, 1], color=c, alpha=0.15)
    _style(ax, '(a) estimates converging', 'samples drawn', 'P(landing possible)')
    ax.set_ylim(0, 1); ax.legend(fontsize=8, loc='center right')

    # (b) outcome breakdown
    ax = fig.add_subplot(gs[0, 1])
    out = [r.get('fault_outcome', 'not_run') for r in s]
    cats = [('healthy plan infeasible', int((~y_nom).sum()), '#B0BEC5')]
    for o in ORDER:
        if o == 'not_run':
            continue
        k = sum(1 for i, x in enumerate(out) if x == o and y_nom[i])
        if k:
            cats.append((OUTCOME_LABEL[o], k, OUTCOME_COLOR[o]))
    ax.barh([c[0] for c in cats][::-1], [c[1] for c in cats][::-1],
            color=[c[2] for c in cats][::-1])
    for i, c in enumerate(cats[::-1]):
        ax.text(c[1], i, f'  {c[1]}', va='center', fontsize=8)
    ax.set_xlim(0, max(c[1] for c in cats) * 1.25)
    _style(ax, f'(b) fate of {len(s)} dispersed arrivals', 'samples', None)

    # (c) what decides survival after a fault
    ax = fig.add_subplot(gs[0, 2])
    ax.barh([f'{FNAMES[i]} [{FUNITS[i]}]' for i in order], imp[order],
            color='#00838F')
    _style(ax, f'(c) what decides fault survival\nCV accuracy {acc:.2f}, '
               f'AUC {auc:.2f}', 'permutation importance', None)

    # (d,e) the two most informative projections over the surrogate surface
    top = list(order[::-1])
    pairs = [(top[0], top[1]),
             (top[0], top[2]) if len(top) > 2 else (top[1], top[0])]
    flo = np.concatenate([IC_LO, [0.0, 0.0, 0.0]])
    fhi = np.concatenate([IC_HI, [1.0, float(np.nanmax(XF[:, 13])), 0.5]])
    mid = 0.5 * (flo + fhi)
    for j, (ia, ib) in enumerate(pairs):
        ax = fig.add_subplot(gs[1, j])
        ga = np.linspace(flo[ia], fhi[ia], 90)
        gb = np.linspace(flo[ib], fhi[ib], 90)
        GA, GB = np.meshgrid(ga, gb)
        G = np.tile(mid, (GA.size, 1))
        G[:, ia] = GA.ravel(); G[:, ib] = GB.ravel()
        try:
            P = clf.predict_proba(scaler.transform(G))[:, 1].reshape(GA.shape)
            ax.contourf(GA, GB, P, levels=np.linspace(0, 1, 11),
                        cmap='RdYlGn', alpha=0.35)
            ax.contour(GA, GB, P, levels=[0.5], colors='k', linewidths=1.2,
                       linestyles='--')
        except Exception:
            pass
        ax.scatter(XF[YF, ia], XF[YF, ib], s=20, c='#2E7D32',
                   edgecolors='white', linewidths=0.4, label='survives fault')
        ax.scatter(XF[~YF, ia], XF[~YF, ib], s=20, c='#C62828',
                   edgecolors='white', linewidths=0.4, label='lost')
        _style(ax, f'({"de"[j]}) {FNAMES[ia]} vs {FNAMES[ib]}'
                   '\nshading = surrogate P(survive)',
               f'{FNAMES[ia]} [{FUNITS[ia]}]', f'{FNAMES[ib]} [{FUNITS[ib]}]')
        ax.legend(fontsize=7, loc='best')

    # (f) the three estimates side by side
    ax = fig.add_subplot(gs[1, 2])
    vol, vlo, vhi = _surrogate_volume_f(clf, scaler, flo, fhi)
    bars = [('healthy\n(direct)', p_n, lo_n, hi_n, '#1565C0'),
            ('after a fault\n(direct)', p_f, lo_f, hi_f, '#6A1B9A'),
            ('after a fault\n(surrogate)', vol, vlo, vhi, '#00838F')]
    for i, (lbl, v, l, hh, c) in enumerate(bars):
        ax.bar(i, v, color=c, width=0.6)
        ax.errorbar(i, v, yerr=[[max(v - l, 0)], [max(hh - v, 0)]], color='k',
                    capsize=5, lw=1.2)
        ax.text(i, hh + 0.03, f'{v:.3f}', ha='center', fontsize=9)
    ax.set_xticks(range(3)); ax.set_xticklabels([b[0] for b in bars], fontsize=7.5)
    ax.set_ylim(0, 1.15)
    _style(ax, '(f) fraction of the box that lands', None, 'fraction')

    fig.suptitle('Study E — landing feasibility over a 12-D initial-condition box',
                 fontsize=13, weight='bold')
    p = os.path.join(FIGURES, 'E_initial_conditions.png')
    fig.savefig(p, dpi=160, bbox_inches='tight'); plt.close(fig)
    print('[saved]', p)

    head['E'] = dict(
        n=len(s), n_nom_land=int(y_nom.sum()),
        p_nom=p_n, lo_nom=lo_n, hi_nom=hi_n,
        n_fault_ok=int(y_f[sub].sum()), n_fault_run=int(sub.sum()),
        p_fault=p_f, lo_fault=lo_f, hi_fault=hi_f,
        surrogate_volume=vol, surrogate_lo=vlo, surrogate_hi=vhi,
        surrogate_target='fault survival',
        cv_accuracy=acc, auc=auc,
        importance={FNAMES[i]: float(imp[i]) for i in order[::-1]},
        outcome={c[0]: c[1] for c in cats})


def _surrogate_volume_f(clf, scaler, lo, hi, n=200_000, seed=7):
    """Integrate the fitted fault-survival classifier over the admissible
    arrival box crossed with the fault-parameter box.

    The interval is the *integration* error of this Monte-Carlo sum only.  The
    classifier's own error (1 - CV accuracy) is the larger term and is reported
    separately rather than folded in, so the two are never confused.
    """
    import apollo_full as af
    from run_study_E import admissible
    import run_study_D as D
    cfg = D.profile_cfg('derated')
    rng = np.random.default_rng(seed)
    pts = rng.uniform(lo, hi, size=(n, len(lo)))
    keep = np.array([admissible(p[:12], cfg)[0] for p in pts])
    P = pts[keep]
    pred = clf.predict(scaler.transform(P))
    return fl.wilson(int(pred.sum()), len(P))


def _surrogate(X, y):
    """Gradient-boosted classifier + permutation importance, cross-validated.

    Reported honestly: a surrogate volume is only meaningful next to the
    classifier's out-of-fold accuracy, so both are returned.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.inspection import permutation_importance
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    clf = HistGradientBoostingClassifier(max_depth=3, max_iter=200,
                                         learning_rate=0.1, random_state=0)
    if len(np.unique(y)) < 2:
        clf.fit(Xs, y)
        return np.zeros(X.shape[1]), 1.0, 0.5, clf, scaler
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    acc = float(cross_val_score(clf, Xs, y, cv=cv).mean())
    try:
        auc = float(cross_val_score(clf, Xs, y, cv=cv, scoring='roc_auc').mean())
    except ValueError:
        auc = float('nan')
    clf.fit(Xs, y)
    pi = permutation_importance(clf, Xs, y, n_repeats=20, random_state=0)
    return pi.importances_mean, acc, auc, clf, scaler


def _surrogate_volume(clf, scaler, lo, hi, n=200_000, seed=7):
    """Integrate the fitted classifier over the admissible part of the box.

    The interval is the *sampling* error of this integration only; the
    classifier's own error (1 - CV accuracy) is the larger term and is
    reported separately rather than folded in, so the two are not confused.
    """
    import apollo_full as af
    from run_study_E import admissible
    cfg = af.OCPConfig()
    rng = np.random.default_rng(seed)
    pts = rng.uniform(lo, hi, size=(n, len(lo)))
    keep = np.array([admissible(p, cfg)[0] for p in pts])
    P = pts[keep]
    pred = clf.predict(scaler.transform(P))
    k, m = int(pred.sum()), len(P)
    return fl.wilson(k, m)


# ══════════════════════════════════════════════════════════════════════

def main():
    head = {}
    fig_tau_vs_tf(head)
    fig_tau_vs_eta(head)
    fig_eta_vs_tf(head)
    fig_sobol_cube(head)
    monotonicity_audit(head)
    fig_mechanism(head)
    fig_ic_montecarlo(head)
    p = os.path.join(RESULTS, 'headline.json')
    with open(p, 'w') as fh:
        json.dump(head, fh, indent=2, default=float)
    print('[saved]', p)
    return head


if __name__ == '__main__':
    h = main()
    print(json.dumps({k: v for k, v in h.items() if k != 'D3'},
                     indent=2, default=float)[:3000])
