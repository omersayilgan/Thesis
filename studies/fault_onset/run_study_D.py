"""
STUDY D — Faults that arrive mid-descent, over a continuous parameter space
═══════════════════════════════════════════════════════════════════════════
The vehicle flies the nominal reference from the design initial condition.  At
a continuous onset time t_f it breaks: one engine either dies outright or drops
to a continuous efficiency eta.  Nobody notices for a continuous reaction delay
tau_d, during which the stale nominal command keeps being applied to a now
asymmetric vehicle.  Then the trajectory is replanned on whatever time is left
before the 80 s mission deadline, and the touchdown is scored.

The space (t_f, eta, tau_d) in [0, 25] x [0, 1] x [0, 2] is uncountable, so it
is attacked three ways, each doing something the others cannot:

  D1  BISECTION in tau_d at eight onset times (engine-out).
      1-D root-finding on the axis that decides survival.  Bisection buys
      ~2^-n boundary resolution for n solves — a grid could not resolve tau*
      to 8 ms in 7 solves.  Yields the critical reaction delay tau*(t_f).

  D2  BISECTION in tau_d across a continuous sweep of severities eta.
      Yields tau*(eta), i.e. how much reaction time a partial fault buys you.

  D3  SOBOL sampling of the full 3-D cube.
      Bisection presumes monotone survival in tau_d.  D3 does not presume
      anything: it is a low-discrepancy sample of the whole box, used both to
      *test* that monotonicity and to fit the surrogate boundary.

Run:  python run_study_D.py            (all three, ~25 min on 10 cores)
      python run_study_D.py D1         (one part)
"""

import os
import sys

import numpy as np

import campaign as cp
from campaign import RESULTS

# fault_lib pulls in casadi; import after campaign has pinned the BLAS threads
import fault_lib as fl
import apollo_full as af


# ── design space ──────────────────────────────────────────────────────
T_F_MAX_FRAC = 0.95        # onset window as a fraction of nominal contact time
TAU_LO, TAU_HI = 0.0, 2.0  # reaction-delay bracket  [s]
BISECT_ITERS = 7           # -> tau* resolved to (TAU_HI-TAU_LO)/2^7 = 16 ms
MAX_ITER = 1000

ETA_SWEEP = [0.90, 0.75, 0.60, 0.45, 0.35, 0.28, 0.20, 0.10]
# onset times are swept as a *fraction* of each profile's own contact time, so
# 'a fault a third of the way down' means the same thing on both profiles even
# though one takes 26 s to reach contact and the other 42 s
T_F_FRACS = [0.04, 0.15, 0.27, 0.38, 0.50, 0.62, 0.73, 0.85]
ETA_ONSET_FRAC = 0.31
N_SOBOL = 96
N_SOBOL_DESIGN = 32

# ══════════════════════════════════════════════════════════════════════
#  reference profiles
# ══════════════════════════════════════════════════════════════════════
#  'design'  — the descent as flown in Studies A-C.  It is a maximum-effort
#              trajectory: it rides V_max on every axis and saturates all three
#              body-rate channels simultaneously, so it carries essentially no
#              attitude-control margin.
#  'derated' — the same problem with the velocity and rate limits pulled in, so
#              the reference no longer sits on its own constraints.  D4 asks
#              whether fault tolerance is a property of the *vehicle* or of the
#              *trajectory it is flying* — which the design profile alone
#              cannot answer.
# ══════════════════════════════════════════════════════════════════════

PROFILES = {
    'design':  dict(),
    'derated': dict(V_max=30.0, omega_max=np.deg2rad(5.0)),
}


def profile_cfg(profile):
    return af.OCPConfig(**PROFILES[profile])


def nom_cache(profile):
    return os.path.join(RESULTS, f'nominal_{profile}.npz')


def nominal_reference(profile='design'):
    p = nom_cache(profile)
    if os.path.exists(p):
        d = np.load(p)
        return d['X'], d['U'], float(d['t_contact'])
    lm, cfg, sc = af.LMParams(), profile_cfg(profile), af.Scenario()
    print(f'solving the {profile} reference descent ...')
    nom = fl.run_nominal(sc.x0, lm, cfg, max_iter=2000)
    if not nom['ok']:
        raise RuntimeError(f'{profile} reference did not converge')
    np.savez(p, X=nom['X'], U=nom['U'], t_contact=nom['t_contact'])
    print(f"  contact at {nom['t_contact']:.1f} s, "
          f"gate margin {nom['margin']:.3f}")
    return nom['X'], nom['U'], nom['t_contact']


# ══════════════════════════════════════════════════════════════════════
#  one sample
# ══════════════════════════════════════════════════════════════════════

_CACHE = {}


def _ctx(profile):
    if profile not in _CACHE:
        X, U, tc = nominal_reference(profile)
        _CACHE[profile] = dict(lm=af.LMParams(), cfg=profile_cfg(profile),
                               X=X, U=U, tc=tc)
    return _CACHE[profile]


def evaluate(job):
    """job = (kind, eta, t_f, tau_d[, profile]).  Returns a result record."""
    kind, eta, t_f, tau_d = job[:4]
    profile = job[4] if len(job) > 4 else 'design'
    c = _ctx(profile)
    f = fl.Fault(kind, eng=1, eta=eta, t_f=t_f, tau_d=tau_d)
    rec = fl.run_fault(f, c['X'], c['U'], c['lm'], c['cfg'], max_iter=MAX_ITER,
                       t_contact_nom=c['tc'])
    rec['t_f_frac'] = t_f / c['tc']
    rec['profile'] = profile
    return rec


# ══════════════════════════════════════════════════════════════════════
#  D1 / D2 — bisection on the reaction delay
# ══════════════════════════════════════════════════════════════════════

def bisect_slice(job):
    """Find tau*(t_f, eta) = the largest reaction delay from which the vehicle
    still lands.  Returns (summary, [all records evaluated]).

    Bracketing first: if it cannot survive an *instant* response the fault is
    unrecoverable in itself (tau* = 0, and the delay is irrelevant); if it
    survives the largest delay tested, tau* is reported as >= TAU_HI.
    """
    kind, eta, t_f = job[:3]
    profile = job[3] if len(job) > 3 else 'design'
    base = dict(kind=kind, eta=eta, t_f=t_f, profile=profile)
    recs = []

    r_lo = evaluate((kind, eta, t_f, TAU_LO, profile)); recs.append(r_lo)
    if not r_lo['success']:
        return dict(**base, tau_star=0.0, bracket='unrecoverable',
                    n_solves=len(recs), outcome_lo=r_lo['outcome']), recs

    r_hi = evaluate((kind, eta, t_f, TAU_HI, profile)); recs.append(r_hi)
    if r_hi['success']:
        return dict(**base, tau_star=TAU_HI, bracket='censored_high',
                    n_solves=len(recs), outcome_lo=r_lo['outcome']), recs

    lo, hi = TAU_LO, TAU_HI
    for _ in range(BISECT_ITERS):
        mid = 0.5 * (lo + hi)
        r = evaluate((kind, eta, t_f, mid, profile)); recs.append(r)
        if r['success']:
            lo = mid
        else:
            hi = mid
    return dict(**base, tau_star=lo, tau_upper=hi, bracket='bracketed',
                n_solves=len(recs), outcome_lo=r_lo['outcome']), recs


# ══════════════════════════════════════════════════════════════════════
#  D5 — bisection on SEVERITY, across onset time
# ══════════════════════════════════════════════════════════════════════
#  D1/D2 bisect the reaction delay.  But a hard engine-out turns out to be
#  unrecoverable at any delay on either profile (Study A's static roll budget
#  already said so: 18.8 kN.m required against 5.4 kN.m available), so tau* = 0
#  everywhere and the delay axis carries no information for that fault.
#  The axis that *does* carry information is severity.  D5 therefore bisects
#  eta at a fixed, short reaction delay, once per onset time, giving the
#  critical severity eta*(t_f) — the direct answer to "does it matter when the
#  fault arrives?".
# ══════════════════════════════════════════════════════════════════════

ETA_BISECT_ITERS = 7           # -> eta* resolved to 1/128
D5_TAU = 0.10                  # a realistic detection+reaction delay  [s]


def bisect_eta_slice(job):
    """Smallest surviving delivered-thrust fraction eta*(t_f).  Survival is
    monotone increasing in eta (more delivered thrust is never worse), so the
    same bracket-then-bisect applies."""
    t_f, tau_d, profile = job
    base = dict(kind='efficiency', t_f=t_f, tau_d=tau_d, profile=profile)
    recs = []

    r_hi = evaluate(('efficiency', 1.0, t_f, tau_d, profile)); recs.append(r_hi)
    if not r_hi['success']:
        # even a null fault does not survive: the reference itself has no
        # margin at this onset, and no severity threshold exists
        return dict(**base, eta_star=float('nan'), bracket='no_margin',
                    n_solves=len(recs)), recs

    r_lo = evaluate(('efficiency', 0.0, t_f, tau_d, profile)); recs.append(r_lo)
    if r_lo['success']:
        return dict(**base, eta_star=0.0, bracket='censored_low',
                    n_solves=len(recs)), recs

    lo, hi = 0.0, 1.0                      # lo fails, hi lands
    for _ in range(ETA_BISECT_ITERS):
        mid = 0.5 * (lo + hi)
        r = evaluate(('efficiency', mid, t_f, tau_d, profile)); recs.append(r)
        if r['success']:
            hi = mid
        else:
            lo = mid
    return dict(**base, eta_star=hi, eta_lower=lo, bracket='bracketed',
                n_solves=len(recs)), recs


def run_D5():
    print('\n== D5: critical severity vs onset time ==')
    jobs = []
    for prof in ('design', 'derated'):
        _, _, tc = nominal_reference(prof)
        jobs += [(f * tc, D5_TAU, prof) for f in T_F_FRACS]
    out = cp.pmap(bisect_eta_slice, jobs, label='D5')
    summ = [dict(s, part='D5') for s, _ in out]
    recs = [dict(r, part='D5') for _, rs in out for r in rs]
    cp.write_csv(os.path.join(RESULTS, 'D5_eta_star.csv'), summ)
    cp.write_csv(os.path.join(RESULTS, 'D5_samples.csv'), recs)
    return summ, recs


def run_bisection(part, jobs):
    out = cp.pmap(bisect_slice, jobs, label=part)
    summ = [s for s, _ in out]
    recs = [r for _, rs in out for r in rs]
    for s in summ:
        s['part'] = part
    for r in recs:
        r['part'] = part
    cp.write_csv(os.path.join(RESULTS, f'{part}_tau_star.csv'), summ)
    cp.write_csv(os.path.join(RESULTS, f'{part}_samples.csv'), recs)
    return summ, recs


def run_D1():
    """tau*(t_f) for a hard engine-out, on BOTH reference profiles.  Running
    the design profile alone would only establish that it has no margin; the
    pair is what shows the margin belongs to the trajectory."""
    print('\n== D1: critical reaction delay vs onset time (engine-out) ==')
    jobs = []
    for prof in ('design', 'derated'):
        _, _, tc = nominal_reference(prof)
        jobs += [('engine_out', 0.0, f * tc, prof) for f in T_F_FRACS]
    return run_bisection('D1', jobs)


def run_D2():
    """tau*(eta) across a continuous severity sweep, on both profiles."""
    print('\n== D2: critical reaction delay vs severity ==')
    jobs = []
    for prof in ('design', 'derated'):
        _, _, tc = nominal_reference(prof)
        jobs += [('efficiency', e, ETA_ONSET_FRAC * tc, prof)
                 for e in ETA_SWEEP]
    return run_bisection('D2', jobs)


# ══════════════════════════════════════════════════════════════════════
#  D3 — Sobol coverage of the whole cube
# ══════════════════════════════════════════════════════════════════════

def _sobol_jobs(profile, n, seed):
    from scipy.stats import qmc
    _, _, tc = nominal_reference(profile)
    pts = qmc.Sobol(d=3, scramble=True, seed=seed).random(n)
    pts = qmc.scale(pts, np.array([0.0, 0.0, 0.0]),
                    np.array([T_F_MAX_FRAC * tc, 1.0, 1.2]))
    return [('efficiency', float(e), float(t), float(d), profile)
            for t, e, d in pts]


def run_D3():
    """Sobol coverage of the whole cube.  Weighted towards the de-rated
    profile, which is where the boundary has structure worth resolving; a
    smaller design-profile set documents that its degeneracy is not an artefact
    of the bisection's bracketing."""
    print(f'\n== D3: Sobol coverage of (t_f, eta, tau_d) ==')
    jobs = (_sobol_jobs('derated', N_SOBOL, 20260811)
            + _sobol_jobs('design', N_SOBOL_DESIGN, 20260812))
    recs = cp.pmap(evaluate, jobs, label='D3')
    for r in recs:
        r['part'] = 'D3'
    cp.write_csv(os.path.join(RESULTS, 'D3_samples.csv'), recs)
    return recs


# ══════════════════════════════════════════════════════════════════════

PARTS = {'D1': run_D1, 'D2': run_D2, 'D5': run_D5, 'D3': run_D3}

if __name__ == '__main__':
    nominal_reference('design')
    want = sys.argv[1:] or list(PARTS)
    for p in want:
        PARTS[p]()
    print('\nStudy D complete.')
