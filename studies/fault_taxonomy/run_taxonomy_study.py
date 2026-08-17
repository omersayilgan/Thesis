"""
STUDY G — campaign runner
═════════════════════════
Solves the full product

    16 fault cases  x  4 initial-condition regimes  x  n initial conditions

and writes one CSV row per solve.  Each solve is `fault_lib.recover`: given the
state the vehicle is in and the plant it has become, plan a landing or refuse.
There is no nominal trajectory and no fault onset time — Study F established
that the post-fault problem is fully specified by (state, plant), so the fault
enters only as the plant, which is exactly the part that is *not* an initial
condition.

Run:  python run_taxonomy_study.py            (default n per cell)
      python run_taxonomy_study.py 6          (n initial conditions per cell)
      python run_taxonomy_study.py 6 approach (one regime only)

Cost: a landing solve is ~20 s and a refusal ~2x that (it is retried from an
independent guess before being believed).  Budget ~40 s x cells / workers.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(FIGURES, exist_ok=True)

import campaign as cp          # noqa: E402  (pins BLAS threads before numpy)
import fault_catalogue as fc    # noqa: E402
import fault_lib as fl          # noqa: E402
import apollo_full as af        # noqa: E402


MAX_ITER = 350
N_DEFAULT = 14


# ══════════════════════════════════════════════════════════════════════
#  ONE SOLVE
# ══════════════════════════════════════════════════════════════════════

def run_one(job):
    reg_key, idx, row, case_key = job
    case = fc.CASES[case_key]
    cfg = af.OCPConfig()
    x = fc.to_state(row)

    res = fl.recover(x, case.lm(), cfg, failed=case.failed, max_iter=MAX_ITER)

    rec = dict(regime=reg_key, sample=idx, fault=case_key,
               structure=case.structure, section=case.section,
               outcome=res['outcome'], lands=bool(res.get('lands', False)),
               margin=res.get('margin', np.inf), iters=res.get('iters', -1),
               wall=res.get('wall', 0.0), N=res.get('N', -1))
    for k in ('v_vert', 'v_horiz', 'tilt_deg', 'pos_err', 'rate_deg'):
        rec[k] = res.get(k, np.nan)
    for nm, v in zip(fc.ALL_NAMES, row):
        rec[nm] = float(v)
    return rec


# ══════════════════════════════════════════════════════════════════════
#  CAMPAIGN
# ══════════════════════════════════════════════════════════════════════

def main(n=N_DEFAULT, regimes=None, faults=None):
    regimes = regimes or fc.REG_KEYS
    faults = faults or fc.KEYS
    print(f'Study G — {len(faults)} faults x {len(regimes)} regimes x {n} ICs '
          f'= {len(faults) * len(regimes) * n} solves')

    # one draw per regime, shared by every fault case in that regime
    states, meta = {}, {}
    for rk in regimes:
        rows, frac, why = fc.sample_regime(fc.REG[rk], n)
        states[rk] = rows
        meta[rk] = dict(admissible_fraction=frac, rejects=why)
    np.savez(os.path.join(RESULTS, 'G_states.npz'),
             **{f'rows_{k}': v for k, v in states.items()},
             **{f'lo_{k}': fc.REG[k].lo for k in regimes},
             **{f'hi_{k}': fc.REG[k].hi for k in regimes},
             admissible=np.array([meta[k]['admissible_fraction']
                                  for k in regimes]),
             regimes=np.array(regimes))

    jobs = [(rk, i, states[rk][i], ck)
            for rk in regimes for ck in faults for i in range(len(states[rk]))]
    out = cp.pmap(run_one, jobs, label='G')
    out.sort(key=lambda r: (r['regime'], r['fault'], r['sample']))

    path = os.path.join(RESULTS, 'G_samples.csv')
    cp.write_csv(path, out)

    print('\nlanding rate by fault x regime:')
    hdr = ' ' * 22 + ''.join(f'{rk:>14s}' for rk in regimes)
    print(hdr)
    for ck in faults:
        line = f'  {ck:20s}'
        for rk in regimes:
            rs = [r for r in out if r['fault'] == ck and r['regime'] == rk]
            k = sum(r['lands'] for r in rs)
            line += f'{k:>7d}/{len(rs):<7d}' if rs else ' ' * 14
        print(line)
    print('\nStudy G complete.')


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else N_DEFAULT
    regs = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    main(n, regs)
