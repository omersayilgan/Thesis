"""
STUDY H — hardening pass
════════════════════════
Re-attacks every case the campaign recorded as `no_recovery`, with a wider
search, and keeps the result if any seed finds a trajectory.

Why this is legitimate, and why it is only applied to the failures
──────────────────────────────────────────────────────────────────
The question each solve asks is *does a landing trajectory exist from this
state with this plant*.  The NLP is nonconvex, so a converged solve proves
existence but a failed one proves nothing — it is evidence about the solver's
starting point, not about the vehicle.  Extra search can therefore only convert
a false "no" into a true "yes"; it can never invalidate a "yes" already found.
Spending it on the failures alone is not cherry-picking, it is putting the
effort where the uncertainty is.

The campaign's own numbers said the effort was needed.  A `no_recovery` that
gives up in 23-60 iterations, sitting between neighbours that land in 160-200,
is a bad local corner: the solver declared local infeasibility from one seed and
was believed.  A `no_recovery` that burns the whole 400-iteration budget is a
different animal and usually survives this pass, which is the point — after it,
the failures that remain are the ones that mean something.

Seeds tried, in order: the original horizon at a much larger iteration budget,
then five neighbouring horizons.  Changing N re-discretises the same problem
and moves the warm start, which is the cheapest independent seed available.

Run:  python harden.py        (rewrites H_samples.csv and H_trajectories.npz)
"""

import os
import sys
import shutil

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')

import campaign as cp             # noqa: E402
import apollo_nominal as an       # noqa: E402
import injection_catalogue as ic  # noqa: E402
import fault_lib as fl            # noqa: E402
import run_injection_study as ri  # noqa: E402

HARD_ITER = 1200
DELTAS = [0, -4, +4, -8, +12, +20]


def attack(job):
    point, key, x, N0 = job
    case = ic.CASES[key]
    cfg = an.make_cfg()
    plant = case.lm()
    for d in DELTAS:
        N = int(np.clip(N0 + d, ri.N_MIN, ri.N_MAX))
        res = fl.solve_ocp(plant, cfg, x, N, failed=case.failed,
                           max_iter=HARD_ITER, n_relax=6, n_cone=3, n_sub=2)
        if not res['ok']:
            continue
        Xff, _ = fl.cutoff_freefall_safe(res['X'][:, -1], plant)
        m = fl.touchdown_metrics(Xff[:, -1])
        out = dict(m)
        out['margin'] = fl.gate_margin(m)
        out['lands'] = out['margin'] <= 1.0
        out['outcome'] = 'land' if out['lands'] else 'gate_miss'
        out.update(iters=res['iters'], wall=res['wall'], N_rem=N, seed=d)
        return point, key, out, np.asarray(res['X'], float), np.asarray(Xff,
                                                                        float)
    return point, key, None, None, None


def main():
    csv_path = os.path.join(RESULTS, 'H_samples.csv')
    npz_path = os.path.join(RESULTS, 'H_trajectories.npz')
    rows = cp.read_csv(csv_path)
    nom = np.load(os.path.join(RESULTS, 'nominal.npz'))
    X_nom = nom['X']

    todo = [r for r in rows if r['outcome'] == 'no_recovery']
    print(f'{len(todo)} of {len(rows)} rows recorded no_recovery; '
          f'retrying each with {len(DELTAS)} seeds at {HARD_ITER} iterations')
    if not todo:
        return

    jobs = [(int(r['point']), r['fault'],
             X_nom[:, int(round(float(r['t_f'])))].copy(), int(r['N_rem']))
            for r in todo]
    out = cp.pmap(attack, jobs, label='harden')

    old = dict(np.load(npz_path))
    by = {(int(r['point']), r['fault']): r for r in rows}
    flipped = []
    for point, key, res, X, Xff in out:
        if res is None:
            continue
        r = by[(point, key)]
        r.update({k: v for k, v in res.items() if k != 'seed'})
        old[f'X|{point}|{key}'] = X
        old[f'F|{point}|{key}'] = Xff
        flipped.append((point, key, res['outcome'], res['seed'], res['iters']))

    shutil.copy(csv_path, csv_path.replace('.csv', '_prehardening.csv'))
    cp.write_csv(csv_path, rows)
    np.savez_compressed(npz_path, **old)

    print(f'\n{len(flipped)} of {len(todo)} flipped once searched harder:')
    for point, key, oc, seed, iters in sorted(flipped):
        print(f'  point {point:2d}  {key:16s} -> {oc:10s} '
              f'(N{seed:+d}, {iters} iterations)')
    still = len(todo) - len(flipped)
    print(f'\n{still} remained infeasible across all {len(DELTAS)} seeds.')
    print('[saved] H_samples.csv (previous version kept as '
          'H_samples_prehardening.csv)')


if __name__ == '__main__':
    main()
