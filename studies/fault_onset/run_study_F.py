"""
STUDY F — Is a fault an initial condition?
══════════════════════════════════════════
Studies A–E all inject a fault into a *nominal trajectory*: solve the healthy
descent, fly it to t_f, break something, replan.  This study drops the nominal
trajectory entirely and asks the question a different way.

The claim under test
────────────────────
    "A fault only changes the vehicle's states.  So instead of computing a
     nominal trajectory and injecting a fault into it, just sample the initial
     condition space widely — including the control/actuator states — and ask
     from where a landing is possible."

Half of that is exactly right, and it is the better half.  The dynamics are
Markovian: what the vehicle can do from state x depends on x and on the plant,
never on the history that produced x.  A post-fault state is just a state.  So
the nominal-trajectory scaffolding is *not* needed to generate the states a
fault produces — you can sample them directly, and cover far more of the space
for the same compute.  Study F therefore samples the full **22-dimensional**
state (12 rigid + 10 actuator), which is where the "and control states" part of
the claim matters: a fault deflects gimbals and moves thrust, and those states
are exactly what Studies A–E could only reach by simulating forwards.

The other half is what this study measures.  A fault also changes *the plant* —
engine 2 delivers eta*T, or its gimbal actuator is sluggish, or it is dead —
and that change persists for the entire remaining flight.  That is not an
initial condition, and the experiment below is built to find out whether it can
be treated as one.

The design that settles it: PAIRED SAMPLES
──────────────────────────────────────────
One set of initial conditions, drawn once.  Every plant configuration is then
solved from *the same* initial conditions.  Because the states are held fixed
across configurations, any difference in landing rate between two
configurations is attributable to the plant alone — the state distribution is
literally identical.  If a fault were expressible as an initial condition, the
healthy plant and the damaged plant would land from the same set of states, and
the paired difference would be zero.

Pairing also buys precision.  The comparison is McNemar's within-sample test on
discordant pairs, not two independent proportions, so it detects a plant effect
with far fewer solves than unpaired sampling would need.

The engine-spacing question
───────────────────────────
Every configuration is run at both y_eng = 1.5 m (as designed) and
y_eng = 0.25 m.  Study A's roll budget says the gimbal alone can trim a
one-engine-out asymmetry iff y_eng <= dz_eng * tan(gimbal_max) = 0.263 m, so
0.25 m sits just inside it.  The pair isolates *loss of thrust* from *loss of
roll authority*: at 0.25 m the vehicle loses the same thrust and keeps the
ability to trim it.  Whatever survives at 0.25 m but not at 1.5 m is a roll-
authority failure, not a thrust failure.

Run:  python run_study_F.py            (default n, all configurations)
      python run_study_F.py 120        (n initial conditions per configuration)
"""

import os
import sys

import numpy as np

import campaign as cp
from campaign import RESULTS

import fault_lib as fl
import apollo_full as af


# ══════════════════════════════════════════════════════════════════════
#  1. THE PLANT CONFIGURATIONS
# ══════════════════════════════════════════════════════════════════════
#  Three fault families, at two engine spacings.  'healthy' at each spacing is
#  the control: it shares the initial conditions with every damaged plant, so
#  it measures what the state dispersion alone costs, with no fault at all.
# ══════════════════════════════════════════════════════════════════════

class Plant:
    """A vehicle configuration — the LMParams a fault leaves behind."""

    def __init__(self, key, label, family, y_eng=1.5, failed=(), eta=None,
                 wn=None, zeta=None, eng=1):
        self.key, self.label, self.family = key, label, family
        self.y_eng, self.eng = y_eng, eng
        self.failed = tuple(failed)
        self.eta, self.wn, self.zeta = eta, wn, zeta

    def lm(self):
        p = af.LMParams(y_eng=self.y_eng)
        if self.eta is not None:
            p.thrust_eff_eng = {self.eng: self.eta}
        if self.wn is not None:
            p.gimbal_wn_eng = {self.eng: self.wn}
        if self.zeta is not None:
            p.gimbal_zeta_eng = {self.eng: self.zeta}
        return p

    def __repr__(self):
        return f'Plant({self.key})'


def build_plants():
    P = []
    for y in (1.5, 0.25):
        t = f'{y:g}'
        P += [
            Plant(f'healthy_y{t}', f'healthy, $y_{{eng}}$={y:g} m',
                  'healthy', y_eng=y),
            Plant(f'engout_y{t}', f'engine 2 out, $y_{{eng}}$={y:g} m',
                  'engine_out', y_eng=y, failed=(1,)),
            Plant(f'eta50_y{t}', rf'$\eta$=0.50, $y_{{eng}}$={y:g} m',
                  'thrust_eff', y_eng=y, eta=0.50),
            Plant(f'eta15_y{t}', rf'$\eta$=0.15, $y_{{eng}}$={y:g} m',
                  'thrust_eff', y_eng=y, eta=0.15),
            Plant(f'gimbal_slow_y{t}',
                  rf'gimbal $\omega_n$=0.6, $y_{{eng}}$={y:g} m',
                  'gimbal', y_eng=y, wn=0.6, zeta=0.70),
            Plant(f'gimbal_undamped_y{t}',
                  rf'gimbal $\zeta$=0.25, $y_{{eng}}$={y:g} m',
                  'gimbal', y_eng=y, wn=1.0, zeta=0.25),
        ]
    return P


PLANTS = {p.key: p for p in build_plants()}


# ══════════════════════════════════════════════════════════════════════
#  2. THE 22-DIMENSIONAL STATE BOX
# ══════════════════════════════════════════════════════════════════════
#  The 12 rigid dimensions are Study E's box with the *rate* range widened
#  from +-4 to +-25 deg/s.  That widening is the point: Study D measured what a
#  fault actually does to the body rates before anyone reacts (12 to 360 deg/s
#  within one second), so a box that stops at 4 deg/s cannot contain a
#  post-fault state.  This one can.
#
#  The 10 actuator dimensions are new and are the "control states" half of the
#  claim under test.  A fault leaves the gimbals deflected and the thrust
#  somewhere other than trim; sampling them directly reaches those states
#  without simulating a descent to get there.
# ══════════════════════════════════════════════════════════════════════

RIGID_NAMES = ['x_E', 'y_E', 'alt', 'u', 'v', 'w',
               'phi', 'theta', 'psi', 'p', 'q', 'r']
RIGID_UNITS = ['m', 'm', 'm', 'm/s', 'm/s', 'm/s',
               'deg', 'deg', 'deg', 'deg/s', 'deg/s', 'deg/s']
RIGID_LO = np.array([-900., -900.,  300., -25., -12.,  -5.,
                     -25., -25., -40., -25., -25., -25.])
RIGID_HI = np.array([ 900.,  900., 1400.,  10.,  12.,  28.,
                      25.,  25.,  40.,  25.,  25.,  25.])

ACT_NAMES = ['T1', 'dp1', 'dy1', 'dp1_dot', 'dy1_dot',
             'T2', 'dp2', 'dy2', 'dp2_dot', 'dy2_dot']
ACT_UNITS = ['N', 'deg', 'deg', 'deg/s', 'deg/s',
             'N', 'deg', 'deg', 'deg/s', 'deg/s']

ALL_NAMES = RIGID_NAMES + ACT_NAMES
ALL_UNITS = RIGID_UNITS + ACT_UNITS

MAX_ITER = 400
N_DEFAULT = 48


def act_bounds(lm):
    """Sampling box for the 10 actuator states, from the vehicle's own limits."""
    gd = np.rad2deg(lm.gimbal_max)
    rate = 0.6 * np.rad2deg(lm.gimbal_wn * lm.gimbal_max)   # deg/s
    lo, hi = [], []
    for _ in range(af.N_ENG):
        lo += [lm.T_min_eng, -gd, -gd, -rate, -rate]
        hi += [lm.T_max_eng,  gd,  gd,  rate,  rate]
    return np.array(lo), np.array(hi)


def admissible(row, cfg):
    """A legal *starting* state — not a comfortable one.

    Only two things disqualify a sample: it is already lost (tumbling, past
    horizontal, on the ground), or it is outside the approach cone, which is a
    mission constraint rather than a dynamical one.  Everything else is kept,
    including states well outside the planner's own comfort envelope, because
    those are precisely the states a fault produces and the study exists to
    find out which of them are recoverable.
    """
    r = np.hypot(row[0], row[1])
    if np.tan(cfg.glide_slope) * r > row[2]:
        return False, 'outside_glide_cone'
    x = to_state(row)
    if fl.hard_loss(x, cfg) is not None:
        return False, 'already_lost'
    return True, ''


def to_state(row):
    """Sampled row (deg, m, altitude-up) -> the 22-state the dynamics use."""
    x = np.zeros(af.N_RIGID + af.N_ACT)
    x[0], x[1] = row[0], row[1]
    x[2] = -row[2]                                  # altitude -> z_E (down)
    x[3:6] = row[3:6]
    x[6:9] = np.deg2rad(row[6:9])
    x[9:12] = np.deg2rad(row[9:12])
    for i in range(af.N_ENG):
        b = 12 + 5 * i
        x[af.IDX_T[i]] = row[b]
        x[af.IDX_DP[i]] = np.deg2rad(row[b + 1])
        x[af.IDX_DY[i]] = np.deg2rad(row[b + 2])
        x[af.IDX_DPD[i]] = np.deg2rad(row[b + 3])
        x[af.IDX_DYD[i]] = np.deg2rad(row[b + 4])
    return x


def sample_states(n, seed=20260812):
    """Sobol points in the 22-D box, rejected against admissibility.

    Drawn ONCE and reused for every plant configuration — that common-random-
    numbers pairing is what makes the plant comparison a within-sample test.
    """
    from scipy.stats import qmc
    lm, cfg = af.LMParams(), af.OCPConfig()
    a_lo, a_hi = act_bounds(lm)
    lo = np.concatenate([RIGID_LO, a_lo])
    hi = np.concatenate([RIGID_HI, a_hi])

    m = int(2 ** np.ceil(np.log2(max(n * 4, 16))))
    pts = qmc.Sobol(d=22, scramble=True, seed=seed).random(m)
    rows = qmc.scale(pts, lo, hi)

    out, n_adm, why = [], 0, {}
    for i in range(m):
        ok, w = admissible(rows[i], cfg)
        if not ok:
            why[w] = why.get(w, 0) + 1
            continue
        n_adm += 1
        if len(out) < n:
            out.append(rows[i])
    frac = n_adm / m
    print(f'  admissible fraction {frac:.3f} of the raw box '
          f'({n_adm}/{m}); rejects: {why}')
    return np.array(out), frac, why, lo, hi


# ══════════════════════════════════════════════════════════════════════
#  3. ONE SAMPLE  =  one state, one plant, one solve
# ══════════════════════════════════════════════════════════════════════

def run_one(job):
    idx, row, key = job
    plant = PLANTS[key]
    cfg = af.OCPConfig()
    lm = plant.lm()
    x = to_state(row)

    res = fl.recover(x, lm, cfg, failed=plant.failed, max_iter=MAX_ITER)

    rec = dict(sample=idx, plant=key, family=plant.family, y_eng=plant.y_eng,
               outcome=res['outcome'], lands=bool(res.get('lands', False)),
               margin=res.get('margin', np.inf), iters=res.get('iters', -1),
               wall=res.get('wall', 0.0), N=res.get('N', -1))
    for k in ('v_vert', 'v_horiz', 'tilt_deg', 'pos_err', 'rate_deg'):
        rec[k] = res.get(k, np.nan)
    for nm, v in zip(ALL_NAMES, row):
        rec[nm] = float(v)
    return rec


# ══════════════════════════════════════════════════════════════════════
#  4. CAMPAIGN
# ══════════════════════════════════════════════════════════════════════

def main(n=N_DEFAULT, keys=None):
    keys = keys or list(PLANTS)
    print(f'Study F — {n} initial conditions x {len(keys)} plants '
          f'= {n * len(keys)} solves')
    rows, frac, why, lo, hi = sample_states(n)
    np.savez(os.path.join(RESULTS, 'F_states.npz'),
             rows=rows, lo=lo, hi=hi, admissible_fraction=frac)

    jobs = [(i, rows[i], k) for k in keys for i in range(len(rows))]
    out = cp.pmap(run_one, jobs, label='F')
    out.sort(key=lambda r: (r['plant'], r['sample']))
    cp.write_csv(os.path.join(RESULTS, 'F_samples.csv'), out)
    print(f"\n[saved] results/F_samples.csv  ({len(out)} rows)")

    print('\nlanding rate by plant:')
    for k in keys:
        rs = [r for r in out if r['plant'] == k]
        if not rs:
            continue
        p, a, b = fl.wilson(sum(r['lands'] for r in rs), len(rs))
        print(f'  {k:24s} {p:.3f}  [{a:.3f}, {b:.3f}]  '
              f'({sum(r["lands"] for r in rs)}/{len(rs)})')
    print('\nStudy F complete.')


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else N_DEFAULT
    main(n)
