"""
STUDY H-R — the same injections, with the state corridor relaxed
════════════════════════════════════════════════════════════════
Study H found that 11 of its 180 injections had **no recovery trajectory**:
IPOPT declared local infeasibility from seven independent seeds.  That is a
statement about the problem *as posed*, and the problem as posed carries a
corridor of path constraints that are not all physics:

    glide cone     12 deg   a scenario choice - it exists to rule out the
                            dive-and-crawl-back trajectory family, not because
                            a vehicle cannot fly below it
    attitude       45 deg   planner comfort.  fault_lib's own hard_loss() puts
                            genuine loss of control at 90 deg, twice this
    body rate      10 deg/s comfort again; hard_loss uses 120 deg/s
    speed          60 m/s   per axis and (here) as a norm.  The vehicle model
                            has no aerodynamic or structural speed limit at all

So "no trajectory exists" may mean "no trajectory exists that stays inside the
corridor".  Those are very different engineering statements: the first is a
lost vehicle, the second is a vehicle that could be saved by a guidance law
willing to leave the nominal envelope.  This script separates them.

THE LADDER
──────────
Every case Study H could not solve is re-attacked at four progressively weaker
corridors, stopping at the first that yields a trajectory:

    L1  cone       glide cone 12 -> 6 deg
    L2  + attitude euler 45 -> 60 deg, rate 10 -> 20 deg/s
    L3  + speed    per-axis and norm 60 -> 90 m/s
    L4  corridor removed entirely (cone, speed, attitude and rate dropped)

What is NEVER relaxed, because it is not a comfort limit:

    * the altitude floor - the vehicle may not fly through the surface;
    * thrust and gimbal bounds - actuator hardware, and relaxing them would
      answer a question about a vehicle that does not exist;
    * the landing gate - a relaxed solve still has to touch down inside the
      same Apollo gate to count as a landing, so L1..L4 change what the
      vehicle is allowed to do EN ROUTE, never what counts as success.

The weakest level that works is the measurement: it says *which* constraint was
the binding one.  For every trajectory found, the excursion beyond each
baseline limit is recorded, so the answer is quantitative - "feasible, but only
by pitching to 58 deg" rather than a bare yes.

EFFORT PARITY
─────────────
A relaxed solve that fails must fail for the same reason the baseline did, not
because it was tried less hard.  Study H spent 7 seeds at up to 1,200
iterations on each of these cases (2 in the campaign, 6 in hardening).  Each
level here gets 3 horizon seeds at 1,200 iterations, so a case that is
infeasible at L4 has now resisted 19 seeds in total.

Run:  python run_relaxed_study.py
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
import run_injection_study as ri  # noqa: E402

RELAX_ITER = 1200
N_RAMP = 6                        # solve_ocp's n_relax: the corridor is wider
                                  # than the nominal envelope only up to here
SEEDS = [0, +8, -4]               # horizon offsets tried at every level

# The ladder.  `cfg` entries overwrite fields of the baseline OCPConfig;
# `relax` names constraints solve_ocp drops altogether.
LADDER = [
    dict(key='L1', label='glide cone 12 to 6 deg',
         short='cone', cfg=dict(glide_slope=np.deg2rad(6.0)), relax=()),
    dict(key='L2', label='+ attitude 45 to 60 deg, rate 10 to 20 deg/s',
         short='attitude',
         cfg=dict(glide_slope=np.deg2rad(6.0), euler_max=np.deg2rad(60.0),
                  omega_max=np.deg2rad(20.0)), relax=()),
    dict(key='L3', label='+ speed 60 to 90 m/s (axis and norm)',
         short='speed',
         cfg=dict(glide_slope=np.deg2rad(6.0), euler_max=np.deg2rad(60.0),
                  omega_max=np.deg2rad(20.0), V_max=90.0, V_norm_max=90.0),
         relax=()),
    dict(key='L4', label='corridor removed (cone, speed, attitude, rate)',
         short='corridor off',
         cfg=dict(glide_slope=np.deg2rad(6.0), euler_max=np.deg2rad(60.0),
                  omega_max=np.deg2rad(20.0), V_max=90.0, V_norm_max=90.0),
         relax=('cone', 'vel', 'att', 'rate')),
    # L5 drops the last state constraint there is: the altitude floor that
    # keeps the vehicle above the surface.  Nothing about the STATE is
    # restricted any more - only the dynamics and the actuator bounds remain,
    # so a trajectory found here may fly through the ground and is not a
    # landing.  That is the point: it separates "the state constraints made
    # this infeasible" from "this plant cannot do it".  A case that fails even
    # at L5 fails on physics the relaxation cannot reach.
    dict(key='L5', label='all state constraints removed, altitude floor included',
         short='no states',
         cfg=dict(glide_slope=np.deg2rad(6.0), euler_max=np.deg2rad(60.0),
                  omega_max=np.deg2rad(20.0), V_max=90.0, V_norm_max=90.0),
         relax=('cone', 'vel', 'att', 'rate', 'alt')),
]
LEVELS = [l['key'] for l in LADDER]


def level_cfg(level):
    cfg = an.make_cfg()
    for k, v in level['cfg'].items():
        setattr(cfg, k, v)
    return cfg


# ══════════════════════════════════════════════════════════════════════
#  How far outside the BASELINE corridor a trajectory goes
# ══════════════════════════════════════════════════════════════════════

def excursions(X, cfg0, n_cone=3):
    """Peak excursion beyond each baseline path constraint, as a ratio.

    A ratio of 1.0 is exactly on the limit and <= 1.0 is inside it, so the
    largest ratio names the constraint the relaxation actually bought.  The
    cone is measured the way the OCP writes it, tan(slope)*horiz <= alt, and
    skips the first `n_cone` nodes for the same reason the OCP does: the
    post-fault transient is not what the cone is there to shape.
    """
    X = np.asarray(X, float)
    alt = -X[2, :]
    horiz = np.hypot(X[0, :], X[1, :])
    tan0 = np.tan(cfg0.glide_slope)

    with np.errstate(divide='ignore', invalid='ignore'):
        cone = tan0 * horiz[n_cone:] / np.maximum(alt[n_cone:], 1e-9)
    path = np.degrees(np.arctan2(alt[n_cone:], np.maximum(horiz[n_cone:], 1e-9)))
    eul = np.abs(np.degrees(X[6:9, :]))
    rate = np.abs(np.degrees(X[9:12, :]))
    v_ax = np.abs(X[3:6, :])
    v_nm = np.linalg.norm(X[3:6, :], axis=0)
    vn_lim = getattr(cfg0, 'V_norm_max', None) or cfg0.V_max

    alt_min = float(np.nanmin(alt))
    return dict(
        alt_min=alt_min,
        # >1 means the trajectory went below the contact altitude; inf means it
        # went under the surface entirely, which only L5 permits
        floor_ratio=float(cfg0.h_contact / alt_min) if alt_min > 0 else np.inf,
        cone_ratio=float(np.nanmax(cone)), path_min_deg=float(np.nanmin(path)),
        att_ratio=float(eul.max() / cfg0.euler_max / (180 / np.pi)),
        att_max_deg=float(eul.max()),
        rate_ratio=float(rate.max() / cfg0.omega_max / (180 / np.pi)),
        rate_max_dps=float(rate.max()),
        vax_ratio=float(v_ax.max() / cfg0.V_max), vax_max=float(v_ax.max()),
        vnorm_ratio=float(v_nm.max() / vn_lim), vnorm_max=float(v_nm.max()))


BINDING = [('floor_ratio', 'altitude floor'), ('cone_ratio', 'glide cone'),
           ('att_ratio', 'attitude'), ('rate_ratio', 'body rate'),
           ('vax_ratio', 'speed (axis)'), ('vnorm_ratio', 'speed (norm)')]


def binding_constraint(ex, tol=1.001):
    """Which baseline limit the trajectory leans on hardest, and by how much."""
    k, name = max(BINDING, key=lambda kn: ex[kn[0]])
    return (name, ex[k]) if ex[k] > tol else ('none', ex[k])


# ══════════════════════════════════════════════════════════════════════
#  One case, walked up the ladder
# ══════════════════════════════════════════════════════════════════════

def attack(job):
    point, t_f, key, x, N0, base_outcome, levels = job
    levels = [l for l in LADDER if l['key'] in levels]
    case = ic.CASES[key]
    plant = case.lm()
    cfg0 = an.make_cfg()

    rec = dict(point=point, t_f=float(t_f), fault=key, structure=case.structure,
               klass=case.klass, section=case.section,
               base_outcome=base_outcome, alt=float(-x[2]),
               rng=float(np.hypot(x[0], x[1])),
               v_horiz_0=float(np.hypot(x[3], x[4])), v_desc_0=float(x[5]),
               tilt_0=float(np.rad2deg(np.hypot(x[6], x[7]))))

    for level in levels:
        cfg = level_cfg(level)
        for d in SEEDS:
            N = int(np.clip(N0 + d, ri.N_MIN, ri.N_MAX))
            res = fl.solve_ocp(plant, cfg, x, N, failed=case.failed,
                               max_iter=RELAX_ITER, n_relax=6, n_cone=3,
                               n_sub=2, relax=level['relax'])
            if not res['ok']:
                continue
            # Touchdown is scored against the UNCHANGED Apollo gate: the
            # relaxation buys freedom en route, never an easier landing.
            Xff, _ = fl.cutoff_freefall_safe(res['X'][:, -1], plant)
            m = fl.touchdown_metrics(Xff[:, -1])
            rec.update(m)
            rec['margin'] = fl.gate_margin(m)
            rec['lands'] = rec['margin'] <= 1.0
            rec['outcome'] = 'land' if rec['lands'] else 'gate_miss'
            rec.update(level=level['key'], level_label=level['label'],
                       seed=d, N_rem=N, iters=res['iters'], wall=res['wall'])
            # measured after the corridor ramp: solve_ocp widens the envelope
            # over the first n_relax nodes in the BASELINE problem too, so an
            # excursion inside that window is not something this relaxation
            # bought.  The whole-trajectory peaks are kept as *_transient.
            whole = excursions(res['X'], cfg0)
            ex = excursions(res['X'][:, N_RAMP:], cfg0, n_cone=0)
            rec.update(ex)
            rec.update({k + '_transient': whole[k] for k in
                        ('cone_ratio', 'att_ratio', 'rate_ratio',
                         'vax_ratio', 'vnorm_ratio')})
            rec['binding'], rec['binding_ratio'] = binding_constraint(ex)
            return rec, np.asarray(res['X'], float), np.asarray(Xff, float)

    rec.update(level='none',
               level_label=f"infeasible at every level ({levels[0]['key']}"
                           f"-{levels[-1]['key']})",
               outcome='no_recovery', lands=False, margin=np.inf,
               binding='n/a', binding_ratio=np.nan, seed=np.nan,
               N_rem=N0, iters=np.nan, wall=np.nan)
    return rec, None, None


def _from_csv(r):
    """Rows read back from HR_samples.csv are all strings.  They are about to
    be sorted and re-written alongside freshly computed rows, so the numeric
    fields have to come back as numbers - a str point sorted against an int
    point raises, and a str margin would be re-written unchanged but compare
    wrongly anywhere else."""
    r = dict(r)
    r['point'] = int(float(r['point']))
    r['lands'] = str(r.get('lands')) in ('True', 'true', '1')
    for k in ('t_f', 'alt', 'rng', 'margin', 'binding_ratio', 'seed', 'iters',
              'wall', 'N_rem', 'v_horiz_0', 'v_desc_0', 'tilt_0', 'v_vert',
              'v_horiz', 'tilt_deg', 'pos_err', 'rate_deg', 'alt_min',
              'floor_ratio', 'cone_ratio', 'path_min_deg', 'att_ratio',
              'att_max_deg', 'rate_ratio', 'rate_max_dps', 'vax_ratio',
              'vax_max', 'vnorm_ratio', 'vnorm_max'):
        if k in r:
            try:
                r[k] = float(r[k])
            except (TypeError, ValueError):
                r[k] = np.nan
    return r


def main(extend_from=None):
    """Walk the ladder.

    `extend_from` re-attacks only the cases an earlier run left infeasible, at
    the levels from that key onward.  L1..L4 already failed for them, so
    re-solving those is pure cost: the ladder is monotone, a level that failed
    cannot start passing because a weaker one was added after it.
    """
    hr_path = os.path.join(RESULTS, 'HR_samples.csv')
    nom = np.load(os.path.join(RESULTS, 'nominal.npz'))
    X_nom = nom['X']

    if extend_from:
        prev = [_from_csv(r) for r in cp.read_csv(hr_path)]
        keep = [r for r in prev if r['level'] != 'none']
        todo = [dict(r, outcome=r['base_outcome'])
                for r in prev if r['level'] == 'none']
        levels = [l['key'] for l in LADDER
                  if LEVELS.index(l['key']) >= LEVELS.index(extend_from)]
    else:
        rows = cp.read_csv(os.path.join(RESULTS, 'H_samples.csv'))
        keep = []
        todo = [r for r in rows
                if r['outcome'] in ('no_recovery', 'gate_miss')]
        levels = LEVELS
    if not todo:
        print('nothing to relax: Study H landed everywhere')
        return
    n_nr = sum(r['outcome'] == 'no_recovery' for r in todo)
    print(f'Study H-R — relaxing {len(todo)} cases ({n_nr} no_recovery, '
          f'{len(todo) - n_nr} gate_miss) over {len(levels)} levels x '
          f'{len(SEEDS)} seeds at {RELAX_ITER} iterations')
    for l in LADDER:
        if l['key'] in levels:
            print(f"  {l['key']}  {l['label']}")
    if keep:
        print(f'  ({len(keep)} cases already solved at a stronger level are '
              f'carried over untouched)')

    jobs = [(int(r['point']), float(r['t_f']), r['fault'],
             X_nom[:, int(round(float(r['t_f'])))].copy(), int(r['N_rem']),
             r['outcome'], levels)
            for r in todo]
    out = cp.pmap(attack, jobs, label='H-R')

    recs, traj = list(keep), {}
    npz_path = os.path.join(RESULTS, 'HR_trajectories.npz')
    if keep and os.path.exists(npz_path):
        traj.update(dict(np.load(npz_path)))     # keep the earlier recoveries
    for rec, X, Xff in out:
        recs.append(rec)
        if X is not None:
            tag = f"{rec['point']}|{rec['fault']}"
            traj[f'X|{tag}'] = X
            traj[f'F|{tag}'] = Xff
    recs.sort(key=lambda r: (r['fault'], r['point']))

    cp.write_csv(hr_path, recs)
    np.savez_compressed(npz_path, **traj)
    print(f"\n[saved] results/HR_samples.csv, results/HR_trajectories.npz "
          f"({len(traj) // 2} trajectories)")

    print(f"\n{'case':30s} {'base':12s} {'level':6s} {'outcome':10s} "
          f"{'margin':>7s}  binding baseline limit")
    for r in recs:
        mg = '   inf' if not np.isfinite(r['margin']) else f"{r['margin']:7.2f}"
        br = ('' if not np.isfinite(r.get('binding_ratio', np.nan))
              else f" ({r['binding_ratio']:.2f}x)")
        print(f"  pt{r['point']:2d} {r['fault'][:24]:25s} "
              f"{r['base_outcome']:12s} {r['level']:6s} {r['outcome']:10s} "
              f"{mg}  {r['binding']}{br}")

    got = [r for r in recs if r['outcome'] != 'no_recovery']
    landed = [r for r in got if r['lands']]
    print(f"\n{len(got)} of {len(recs)} found a trajectory once relaxed; "
          f"{len(landed)} of those still land inside the Apollo gate.")
    for l in LADDER:
        n = sum(r['level'] == l['key'] for r in recs)
        if n:
            print(f"  {l['key']} ({l['short']}): {n}")
    n_none = sum(r['level'] == 'none' for r in recs)
    if n_none:
        print(f"  infeasible at every level: {n_none}")


if __name__ == '__main__':
    # --extend L5: re-attack only what is still infeasible, from that level on
    arg = sys.argv[1:]
    if arg and arg[0] == '--extend':
        main(extend_from=arg[1] if len(arg) > 1 else LEVELS[-1])
    else:
        main()
