"""
STUDY E — Landing feasibility over a continuous initial-condition space
═══════════════════════════════════════════════════════════════════════
Study D asks "does a fault at t_f kill *this* descent?".  Study E asks the
wider question: given that the vehicle can arrive at the start of powered
descent anywhere inside a 12-dimensional dispersion box, for what fraction of
those arrivals is a landing possible at all — and for what fraction is it still
possible after a mid-descent fault?

The box is continuous, so the answer is a *volume fraction* and can only be
estimated.  The estimate is built in three layers, each with its own honest
error statement:

  1. SAMPLING       Sobol (low-discrepancy) points in the 12-D box, rejected
                    against the admissibility constraints (glide cone, velocity
                    envelope).  Sobol beats plain Monte Carlo here: its star
                    discrepancy gives ~O(log^d N / N) integration error instead
                    of O(N^-1/2), which matters when N is a few hundred.
  2. DIRECT ESTIMATE the raw success fraction with a Wilson score interval —
                    assumption-free, but wide at N ~ 200.
  3. SURROGATE      a gradient-boosted classifier fitted to the samples,
                    cross-validated, then integrated over 200 000 cheap points.
                    This sharpens the estimate and, more usefully, says *which*
                    of the twelve dimensions decide the outcome and where the
                    boundary lies.  Its cross-validated accuracy is reported
                    alongside, because a surrogate volume is only as good as
                    the classifier.

Each sampled initial condition costs two NLP solves: the healthy plan (is a
landing possible at all?) and, if that succeeds, the replan after a randomly
drawn mid-descent fault (is it still possible once something breaks?).

Run:  python run_study_E.py            (~35 min on 10 cores)
      python run_study_E.py 300        (n samples)
"""

import os
import sys

import numpy as np

import campaign as cp
from campaign import RESULTS

import fault_lib as fl
import apollo_full as af
import run_study_D as D


# ══════════════════════════════════════════════════════════════════════
#  the initial-condition box
# ══════════════════════════════════════════════════════════════════════
#  Centred on the design scenario and widened to a realistic high-gate
#  dispersion: +-900 m cross-/downrange, a 1 km altitude band, and
#  attitude/rate errors several times the nominal.  The horizontal range is
#  deliberately wide enough that the 30 deg glide cone actually bites — with a
#  +-500 m box the cone rejects essentially nothing and the admissibility test
#  would be a formality rather than a real constraint on where the vehicle may
#  arrive.
# ══════════════════════════════════════════════════════════════════════

#  Study E is flown on the DE-RATED reference profile.  Study D establishes
#  that the design profile has no fault margin whatever — every fault at every
#  onset is unrecoverable — so running the fault half of Study E on it would
#  estimate a quantity already known to be zero.  The de-rated profile is the
#  one on which "can it still land?" has a non-degenerate answer, and the box
#  below is clipped to its (tighter) flight envelope.
PROFILE = 'derated'

IC_NAMES = ['x_E', 'y_E', 'alt', 'u', 'v', 'w',
            'phi', 'theta', 'psi', 'p', 'q', 'r']
IC_UNITS = ['m', 'm', 'm', 'm/s', 'm/s', 'm/s',
            'deg', 'deg', 'deg', 'deg/s', 'deg/s', 'deg/s']
IC_LO = np.array([-900., -900.,  400., -25., -12.,  -5., -20., -20., -40., -4., -4., -4.])
IC_HI = np.array([ 900.,  900., 1400.,  10.,  12.,  28.,  20.,  20.,  40.,  4.,  4.,  4.])

FAULT_TAU_MAX = 0.5        # reaction-delay draw  [s]
P_ENGINE_OUT = 0.20        # share of draws that are a hard engine-out
MAX_ITER = 1500
N_DEFAULT = 220


def to_state(row, cfg):
    """Box coordinates -> the 12-state used by the OCP (alt -> z_E = -alt,
    angles deg -> rad)."""
    x = np.zeros(12)
    x[0], x[1], x[2] = row[0], row[1], -row[2]
    x[3:6] = row[3:6]
    x[6:9] = np.deg2rad(row[6:9])
    x[9:12] = np.deg2rad(row[9:12])
    return x


def admissible(row, cfg):
    """Is this point a legal initial condition for the OCP at all?  Rejecting
    here rather than counting it as a failure keeps the estimate a statement
    about *flyable* dispersions instead of about the box's corners."""
    r = np.hypot(row[0], row[1])
    if np.tan(cfg.glide_slope) * r > row[2]:
        return False, 'outside_glide_cone'
    if np.abs(row[3:6]).max() > cfg.V_max:
        return False, 'velocity_envelope'
    if np.abs(np.deg2rad(row[6:9])).max() > cfg.euler_max:
        return False, 'attitude_envelope'
    if np.abs(np.deg2rad(row[9:12])).max() > cfg.omega_max:
        return False, 'rate_envelope'
    return True, ''


def sample_box(n, seed=20260811):
    """Sobol points in the box, plus the fault-parameter draws that go with
    them (drawn from the same low-discrepancy stream, dimensions 13-15)."""
    from scipy.stats import qmc
    cfg = D.profile_cfg(PROFILE)
    # oversample: admissibility rejects a good share of the raw box
    m = int(2 ** np.ceil(np.log2(max(n * 4, 16))))
    pts = qmc.Sobol(d=15, scramble=True, seed=seed).random(m)
    ic = qmc.scale(pts[:, :12], IC_LO, IC_HI)
    out, n_adm = [], 0
    for i in range(m):
        ok, why = admissible(ic[i], cfg)
        if not ok:
            continue
        n_adm += 1                       # counted over the *whole* stream, so
        if len(out) >= n:                # the admissible fraction stays an
            continue                     # unbiased estimate of the box volume
        out.append(dict(idx=len(out), row=ic[i],
                        t_f_frac=float(pts[i, 12]),
                        sev=float(pts[i, 13]),
                        tau_d=float(pts[i, 14]) * FAULT_TAU_MAX))
    return out, m, n_adm


# ══════════════════════════════════════════════════════════════════════
#  one sample = one healthy solve (+ one faulted replan)
# ══════════════════════════════════════════════════════════════════════

def evaluate(job):
    lm, cfg = af.LMParams(), D.profile_cfg(PROFILE)
    row = job['row']
    rec = {f'ic_{n}': float(v) for n, v in zip(IC_NAMES, row)}
    rec['idx'] = job['idx']

    x12 = to_state(row, cfg)
    nom = fl.run_nominal(x12, lm, cfg, max_iter=MAX_ITER)
    rec.update(nom_status=nom['status'], nom_iters=nom['iters'],
               nom_ipopt=nom.get('ipopt_status', ''),
               nom_wall=round(nom['wall'], 1), nom_J=nom['J'],
               nom_lands=bool(nom['lands']),
               nom_margin=float(min(nom['margin'], 99.0)),
               nom_t_contact=nom['t_contact'])
    if nom['metrics']:
        rec.update({f'nom_{k}': v for k, v in nom['metrics'].items()})

    if not nom['ok'] or not nom['lands']:
        rec.update(fault_outcome='not_run', fault_success=False,
                   kind='', eta=np.nan, t_f=np.nan, tau_d=np.nan)
        return rec

    # fault draw: engine-out for a share of the samples, otherwise a
    # continuous efficiency loss
    t_f = job['t_f_frac'] * 0.95 * nom['t_contact']
    if job['sev'] < P_ENGINE_OUT:
        kind, eta = 'engine_out', 0.0
    else:
        kind = 'efficiency'
        eta = (job['sev'] - P_ENGINE_OUT) / (1.0 - P_ENGINE_OUT)
    f = fl.Fault(kind, eng=1, eta=eta, t_f=t_f, tau_d=job['tau_d'])
    fr = fl.run_fault(f, nom['X'], nom['U'], lm, cfg, max_iter=MAX_ITER,
                      t_contact_nom=nom['t_contact'])
    rec.update(profile=PROFILE, kind=kind, eta=eta, t_f=t_f, tau_d=job['tau_d'],
               fault_outcome=fr['outcome'], fault_success=bool(fr['success']),
               fault_margin=float(min(fr['margin'], 99.0)),
               fault_iters=fr.get('iters', 0),
               fault_ipopt=fr.get('ipopt_status', ''),
               fault_wall=round(fr.get('wall', 0.0), 1),
               alt_at_fault=fr['alt_at_fault'],
               rate_after_delay_deg=fr['rate_after_delay_deg'],
               violation=fr.get('violation') or '')
    return rec


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else N_DEFAULT
    jobs, n_raw, n_ok = sample_box(n)
    print(f'Study E: {len(jobs)} initial conditions to fly.  '
          f'{n_ok}/{n_raw} raw Sobol points were admissible '
          f'(the admissible region is {n_ok / n_raw:.3f} of the raw box)')
    recs = cp.pmap(evaluate, jobs, label='E')
    recs.sort(key=lambda r: r['idx'])
    cp.write_csv(os.path.join(RESULTS, 'E_samples.csv'), recs)

    k = sum(r['nom_lands'] for r in recs)
    p, lo, hi = fl.wilson(k, len(recs))
    print(f'\nP(landing possible | healthy)  = {p:.3f}  '
          f'[{lo:.3f}, {hi:.3f}] 95% Wilson   ({k}/{len(recs)})')
    sub = [r for r in recs if r['nom_lands']]
    k2 = sum(r['fault_success'] for r in sub)
    p2, lo2, hi2 = fl.wilson(k2, len(sub))
    print(f'P(landing possible | faulted)  = {p2:.3f}  '
          f'[{lo2:.3f}, {hi2:.3f}] 95% Wilson   ({k2}/{len(sub)})')
