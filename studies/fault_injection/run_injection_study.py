"""
STUDY H — the injection campaign
════════════════════════════════
Stage 2: take the healthy nominal descent, pick points along it, and ask what
each fault does *from that point onward*.

The design
──────────
For every injection point t_f on the nominal and every plant in the catalogue:

    x(t_f)  is read straight off the nominal trajectory — the exact state the
            healthy vehicle was in at that instant, all 22 of them, including
            the thrust and gimbal states the descent had it holding;
    the plant becomes the damaged plant from t_f onward;
    the vehicle re-plans over the time the nominal had left, plus a reserve,
    and is scored at touchdown against the Apollo landing gate.

The healthy plant is run from every injection point too.  It is the control:
because the state comes off a trajectory that lands, the healthy vehicle must
land from every point, and any point where it does not is a property of the
re-planning problem rather than of any fault.

What this does NOT model is the reaction gap — the seconds between the fault
occurring and the guidance responding, during which the vehicle flies a stale
command on a broken engine.  Detection here is instantaneous and perfect.  That
gap is Study D/E's subject; keeping it out makes this study a clean measurement
of *where on the descent* a fault is survivable at all.

Run:  python run_injection_study.py          (default injection points)
      python run_injection_study.py 21       (that many points)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')

import campaign as cp             # noqa: E402  (pins BLAS threads first)
import apollo_nominal as an       # noqa: E402
import injection_catalogue as ic  # noqa: E402
import fault_lib as fl            # noqa: E402
import apollo_full as af          # noqa: E402

MAX_ITER = 400
T_RESERVE = 20.0            # seconds granted beyond the nominal's own remainder
N_POINTS = 15
N_MIN, N_MAX = 25, 90


def injection_times(t_contact, n_points):
    """Grid nodes to inject at: evenly spread from lift-off of the reference
    arc to a few seconds before contact.  They are whole seconds so the state
    is read off a node rather than re-integrated to an off-grid instant."""
    last = max(t_contact - 6.0, 1.0)
    return sorted({int(round(t)) for t in np.linspace(0.0, last, n_points)})


def replan_horizon(t_f, t_contact):
    """The time the vehicle gets: what the nominal had left, plus a reserve.

    Not 'everything up to the mission deadline' — an over-long horizon forces
    the planner to hold the 1 m contact floor for the unused tail, which is a
    pathological arc on a 1 s grid and turns recoverable cases infeasible
    (Study D, section 2.4).
    """
    need = max(t_contact - t_f, 0.0) + T_RESERVE
    return int(np.clip(round(need), N_MIN, N_MAX))


def run_one(job):
    k, t_f, key, x, N_rem = job
    case = ic.CASES[key]
    cfg = an.make_cfg()
    plant = case.lm()

    rec = dict(t_f=float(t_f), point=k, fault=key, structure=case.structure,
               klass=case.klass, section=case.section, N_rem=N_rem,
               alt=float(-x[2]), rng=float(np.hypot(x[0], x[1])),
               v_horiz_0=float(np.hypot(x[3], x[4])), v_desc_0=float(x[5]),
               tilt_0=float(np.rad2deg(np.hypot(x[6], x[7]))))

    loss = fl.hard_loss(x, cfg)
    if loss is not None:
        rec.update(outcome='already_lost', lands=False, margin=np.inf,
                   iters=0, wall=0.0)
        return rec, None, None

    res = fl.solve_ocp(plant, cfg, x, N_rem, failed=case.failed,
                       max_iter=MAX_ITER, n_relax=6, n_cone=3, n_sub=2)
    if not res['ok']:
        # second seed: same problem, slightly different discretisation, which
        # is enough to escape a bad local corner
        N2 = int(np.clip(N_rem + 8, N_MIN, N_MAX))
        res2 = fl.solve_ocp(plant, cfg, x, N2, failed=case.failed,
                            max_iter=MAX_ITER, n_relax=6, n_cone=3, n_sub=2)
        if res2['ok']:
            res, N_rem = res2, N2
    if not res['ok']:
        rec.update(outcome='no_recovery', lands=False, margin=np.inf,
                   iters=res['iters'], wall=res['wall'])
        return rec, None, None

    Xff, _ = fl.cutoff_freefall_safe(res['X'][:, -1], plant)
    m = fl.touchdown_metrics(Xff[:, -1])
    rec.update(m)
    rec['margin'] = fl.gate_margin(m)
    rec['lands'] = rec['margin'] <= 1.0
    rec['outcome'] = 'land' if rec['lands'] else 'gate_miss'
    rec['iters'], rec['wall'] = res['iters'], res['wall']
    return rec, np.asarray(res['X'], float), np.asarray(Xff, float)


def main(n_points=N_POINTS):
    nom = np.load(os.path.join(RESULTS, 'nominal.npz'))
    X_nom, t_c = nom['X'], float(nom['t_contact'])
    ts = injection_times(t_c, n_points)
    faults = ic.KEYS

    print(f'Study H — nominal contacts at {t_c:.0f} s; injecting at '
          f'{len(ts)} points x {len(faults)} plants = '
          f'{len(ts) * len(faults)} solves')
    print('  injection times:', ts)

    jobs = [(k, t, key, X_nom[:, t].copy(), replan_horizon(t, t_c))
            for k, t in enumerate(ts) for key in faults]
    out = cp.pmap(run_one, jobs, label='H')

    recs, traj = [], {}
    for rec, X, Xff in out:
        recs.append(rec)
        if X is not None:
            tag = f"{rec['point']}|{rec['fault']}"
            traj[f'X|{tag}'] = X
            traj[f'F|{tag}'] = Xff
    recs.sort(key=lambda r: (r['fault'], r['point']))

    cp.write_csv(os.path.join(RESULTS, 'H_samples.csv'), recs)
    np.savez_compressed(os.path.join(RESULTS, 'H_trajectories.npz'),
                        times=np.array(ts), **traj)
    print(f"[saved] results/H_trajectories.npz  ({len(traj) // 2} trajectories)")

    print('\nlanding outcome by fault x injection time (L land, g gate miss, '
          '. no trajectory):')
    print(' ' * 30 + ''.join(f'{t:>4d}' for t in ts))
    mark = {'land': 'L', 'gate_miss': 'g', 'no_recovery': '.',
            'already_lost': 'x'}
    for key in faults:
        rs = {r['point']: r for r in recs if r['fault'] == key}
        line = f'  {ic.CASES[key].short[:26]:28s}'
        line += ''.join(f"{mark.get(rs[k]['outcome'], '?'):>4s}"
                        for k in range(len(ts)))
        n_land = sum(r['lands'] for r in rs.values())
        print(line + f'   {n_land}/{len(ts)}')
    print('\nStudy H complete.')


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else N_POINTS)
