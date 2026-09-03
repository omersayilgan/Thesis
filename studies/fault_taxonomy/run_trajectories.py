"""
STUDY G — trajectory pass
═════════════════════════
The campaign records *outcomes*, not paths: 800 trajectories were never worth
carrying through a multi-hour run when the question was landing probability.
This pass re-solves the cases that produced a trajectory and keeps it, so the
result can be looked at rather than only counted.

Only the rows whose outcome was `land` or `gate_miss` are re-solved — the rest
have no trajectory by definition. That is also where the saving is: a
`no_recovery` row is the *expensive* kind (it is retried from a second
independent guess before being believed), so skipping them cuts far more than
their 28 % share of the row count.

The re-solve is deterministic — same state, same plant, same solver options,
one BLAS thread — so it must reproduce the campaign's own verdict. Any row that
comes back with a different outcome is reported at the end rather than quietly
kept: a mismatch would mean the campaign is not reproducible, which is a bigger
finding than any plot.

Run:  python run_trajectories.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')

import campaign as cp          # noqa: E402  (pins BLAS threads first)
import fault_catalogue as fc   # noqa: E402
import fault_lib as fl         # noqa: E402
import apollo_full as af       # noqa: E402

MAX_ITER = 350
FLYABLE = ('land', 'gate_miss')


def run_one(job):
    reg, idx, key, row, want = job
    case = fc.CASES[key]
    cfg = af.OCPConfig()
    plant = case.lm()
    x = fc.to_state(row)

    res = fl.recover(x, plant, cfg, failed=case.failed, max_iter=MAX_ITER)
    if res.get('X') is None:
        return dict(regime=reg, sample=idx, fault=key, outcome=res['outcome'],
                    want=want, X=None, Xff=None)

    # the powered arc, then the engine-off ballistic settle that scores it
    Xff, _ = fl.cutoff_freefall_safe(res['X'][:, -1], plant)
    return dict(regime=reg, sample=idx, fault=key, outcome=res['outcome'],
                want=want, X=np.asarray(res['X'], float),
                Xff=np.asarray(Xff, float))


def main():
    rows = cp.read_csv(os.path.join(RESULTS, 'G_samples.csv'))
    st = np.load(os.path.join(RESULTS, 'G_states.npz'), allow_pickle=True)
    states = {str(g): st[f'rows_{g}'] for g in st['regimes']}

    jobs = [(r['regime'], int(r['sample']), r['fault'],
             states[r['regime']][int(r['sample'])], r['outcome'])
            for r in rows if r['outcome'] in FLYABLE]
    print(f'{len(jobs)} of {len(rows)} rows produced a trajectory; re-solving '
          f'those to keep it')

    out = cp.pmap(run_one, jobs, label='traj')

    store, mismatch = {}, []
    for r in out:
        if r['outcome'] != r['want']:
            mismatch.append((r['regime'], r['sample'], r['fault'],
                             r['want'], r['outcome']))
        if r['X'] is None:
            continue
        tag = f"{r['regime']}|{r['sample']}|{r['fault']}"
        store[f'X|{tag}'] = r['X']
        store[f'F|{tag}'] = r['Xff']

    np.savez_compressed(os.path.join(RESULTS, 'G_trajectories.npz'), **store)
    print(f"\n[saved] results/G_trajectories.npz  "
          f"({len(store) // 2} trajectories)")

    if mismatch:
        print(f'\n!! {len(mismatch)} of {len(jobs)} re-solves disagreed with '
              f'the campaign — the run is not bit-reproducible:')
        for m in mismatch[:20]:
            print('   ', m)
    else:
        print(f'\nAll {len(jobs)} re-solves reproduced the campaign outcome.')


if __name__ == '__main__':
    main()
