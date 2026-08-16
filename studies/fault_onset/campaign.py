"""
Campaign infrastructure — parallel job execution + CSV bookkeeping.
═══════════════════════════════════════════════════════════════════
Every solve is pinned to a single BLAS thread (OMP_NUM_THREADS=1) *before*
numpy/casadi are imported in the worker: the earlier case studies established
that multithreaded BLAS makes this NLP's objective non-reproducible at the ~1 %
level, and here reproducibility matters more than per-solve speed — the
parallelism is across samples instead.
"""

import os

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')

import csv
import time
import multiprocessing as mp

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(FIGURES, exist_ok=True)

#  4 by default, not 10: Study F's sub-stepped defects roughly double the
#  CasADi graph, and a 10-worker campaign of them exhausted this machine's
#  memory.  Peak RSS is ~1.5 GB per worker, so 4 leaves comfortable headroom.
N_WORKERS = int(os.environ.get('FAULT_WORKERS', '4'))


def pmap(fn, jobs, n_workers=None, chunksize=1, label=''):
    """Parallel map with a progress line.  Falls back to serial when
    n_workers == 1, which keeps tracebacks readable while debugging."""
    n_workers = n_workers or N_WORKERS
    t0 = time.time()
    out = []
    if n_workers == 1:
        for i, j in enumerate(jobs):
            out.append(fn(j))
            print(f'  [{label}] {i+1}/{len(jobs)}  {time.time()-t0:.0f}s',
                  flush=True)
        return out
    with mp.Pool(n_workers) as pool:
        for i, r in enumerate(pool.imap_unordered(fn, jobs, chunksize)):
            out.append(r)
            print(f'  [{label}] {i+1}/{len(jobs)}  '
                  f'{time.time()-t0:.0f}s elapsed', flush=True)
    return out


def write_csv(path, rows, fieldnames=None):
    if not rows:
        return
    keys = fieldnames or sorted({k for r in rows for k in r})
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in keys})
    print(f'[saved] {path}  ({len(rows)} rows)')


def read_csv(path):
    with open(path) as fh:
        return [dict(r) for r in csv.DictReader(fh)]
