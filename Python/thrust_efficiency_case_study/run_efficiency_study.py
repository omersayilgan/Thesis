"""
Thrust-Efficiency Case Study — Apollo LM Powered Descent
═══════════════════════════════════════════════════════
Engine 2 delivers only a fraction eta of its commanded thrust as useful force:

    F_delivered = eta * T ,      eta in (0, 1]

while its actuator dynamics — and therefore its propellant draw — still act on
the full T.  The shortfall is lost power, not saved fuel.  Engine 1 is healthy.
Implemented via LMParams.thrust_eff_eng; everything else is held at the baseline.

The interesting consequence is not the lost thrust but the *asymmetry*: the two
engines sit at y = -1.5 m and +1.5 m, so unequal delivered thrust is a roll
moment.  Balanced hover needs each engine to deliver T_hover/2, which means
commanding the weak one at (T_hover/2)/eta — and that command is bounded by
T_max_eng.  Three regimes follow:

    eta >= 0.278   trimmable by differential throttling alone
    0.198..0.278   trimmable only with the gimbal and RCS committed to static
                   roll trim, leaving little for manoeuvring
    eta <  0.198   the roll moment exceeds all available authority -> infeasible

E6 (eta = 0.15) is the deliberate excursion below the predicted boundary, and is
expected not to converge; its iteration budget is capped accordingly.

Run:  python run_efficiency_study.py          (all six, ~15 min)
      python run_efficiency_study.py 4        (just E4)
"""

import os

# Pin BLAS/OpenMP to one thread BEFORE numpy/casadi import — this NLP is
# nonconvex and multithreaded reductions make the solve land in different local
# minima run to run (see the gimbal study's README for the measurement).
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')

import re
import sys
import json
import contextlib

import numpy as np
import matplotlib
matplotlib.use('Agg')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import apollo_full as af

WEAK = 1                          # engine index with reduced efficiency

CASES = {
    1: dict(dirname='E1_eta1.00', eta=1.00, label='baseline'),
    2: dict(dirname='E2_eta0.85', eta=0.85, label='mild'),
    3: dict(dirname='E3_eta0.65', eta=0.65, label='moderate'),
    4: dict(dirname='E4_eta0.40', eta=0.40, label='severe'),
    5: dict(dirname='E5_eta0.25', eta=0.25, label='beyond throttle-only trim'),
    6: dict(dirname='E6_eta0.15', eta=0.15, label='beyond all authority',
            max_iter=400),
}


def trim_budget(lm, eta):
    """Static roll-trim arithmetic for the asymmetric-thrust condition [N, N*m].

    Balanced hover wants both engines to *deliver* T_hover/2.  If the weak
    engine's required command exceeds its limit it saturates, and the leftover
    delivered-thrust asymmetry shows up as a roll moment the gimbal and RCS have
    to absorb.
    """
    Th, Tmax, y, z = lm.T_hover, lm.T_max_eng, lm.y_eng, lm.dz_eng
    T_req = (Th / 2) / eta                       # command for balanced hover
    saturated = T_req > Tmax
    if saturated:
        T_weak_cmd = Tmax
        F_weak = eta * Tmax
        F_strong = Th - F_weak                   # healthy engine makes up hover
        L_resid = 2 * y * (F_strong - F_weak) / 2   # = y*(F_strong - F_weak)
    else:
        T_weak_cmd, F_weak, F_strong, L_resid = T_req, Th / 2, Th / 2, 0.0

    L_gimbal = Th * z * np.tan(lm.gimbal_max)
    L_rcs = np.clip(lm.rcs_geometry()[2][3, :], 0.0, None).sum() * lm.F_rcs_per
    return dict(T_weak_cmd=T_weak_cmd, saturated=saturated,
                F_weak=F_weak, F_strong=F_strong, L_resid=abs(L_resid),
                L_gimbal=L_gimbal, L_rcs=L_rcs,
                deficit=abs(L_resid) - L_gimbal - L_rcs,
                F_max_total=lm.T_max_eng * (1.0 + eta))


def metrics(Xs, Us, lm, cfg):
    N = Us.shape[1]
    T = Xs[af.IDX_T]                                   # internal thrust states
    F = np.array([lm.eta_of(i) * T[i] for i in range(lm.n_eng)])   # delivered
    f_rcs = Us[af.N_U_DPS:af.N_U_DPS + lm.n_rcs, :]
    L_tvc = sum(lm.eng_pos(i)[1] *
                (-F[i] * np.cos(Xs[af.IDX_DP[i]]) * np.cos(Xs[af.IDX_DY[i]]))
                for i in range(lm.n_eng))
    return {
        'peak_delivered_total_N':  F.sum(axis=0).max(),
        'mean_delivered_total_N':  F.sum(axis=0).mean(),
        'peak_cmd_weak_N':         T[WEAK].max(),
        'mean_cmd_weak_N':         T[WEAK].mean(),
        'mean_cmd_strong_N':       T[1 - WEAK].mean(),
        # propellant proxies: impulse on commanded thrust (what is burnt) vs
        # delivered force (what the vehicle got)
        'dps_impulse_cmd_Ns':      T.sum() * cfg.dt,
        'dps_impulse_delivered_Ns': F.sum() * cfg.dt,
        'wasted_impulse_Ns':       (T.sum() - F.sum()) * cfg.dt,
        'peak_tvc_roll_moment_Nm': np.abs(L_tvc).max(),
        'mean_abs_tvc_roll_Nm':    np.abs(L_tvc).mean(),
        'mean_abs_gimbal_dy_deg':  np.rad2deg(np.abs(Xs[af.IDX_DY]).mean()),
        'rcs_impulse_Ns':          f_rcs.sum() * cfg.dt,
        'peak_roll_deg':           np.abs(np.rad2deg(Xs[6])).max(),
        'peak_p_degs':             np.abs(np.rad2deg(Xs[9])).max(),
        'time_to_contact_s':       float(np.argmax(-Xs[2] <= cfg.h_contact + 1e-6)
                                         * cfg.dt),
        'terminal_speed_ms':       np.linalg.norm(Xs[3:6, -1]),
        'terminal_pos_err_m':      np.linalg.norm(Xs[0:2, -1]),
        'terminal_att_err_deg':    np.rad2deg(np.linalg.norm(Xs[6:8, -1])),
    }


def scrape_log(path):
    txt = open(path).read()
    obj = re.search(r'^Objective\.+:\s+\S+\s+(\S+)', txt, re.M)
    it = re.search(r'^Number of Iterations\.+:\s+(\d+)', txt, re.M)
    return (float(obj.group(1)) if obj else float('nan'),
            int(it.group(1)) if it else -1)


def run_case(key):
    spec = CASES[key]
    outdir = os.path.join(HERE, spec['dirname'])
    os.makedirs(outdir, exist_ok=True)

    lm = af.LMParams(thrust_eff_eng={WEAK: spec['eta']})
    cfg = af.OCPConfig(max_iter=spec.get('max_iter', 5000))
    sc = af.Scenario()

    logpath = os.path.join(outdir, 'console_log.txt')
    status = 'solved'
    with open(logpath, 'w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            b = trim_budget(lm, spec['eta'])
            print('#' * 70)
            print(f"#  {spec['dirname']}  —  eta = {spec['eta']:.2f}  "
                  f"({spec['label']})")
            print('#' * 70)
            print(f"  engine {WEAK+1} delivers {100*spec['eta']:.0f}% of its "
                  f"commanded thrust as force")
            print(f"  max total delivered thrust = {b['F_max_total']:.0f} N "
                  f"(hover needs {lm.T_hover:.0f} N, "
                  f"T/W = {b['F_max_total']/lm.T_hover:.2f})")
            print("\n  Static roll-trim budget at hover:")
            print(f"    weak-engine command for balanced hover = "
                  f"{b['T_weak_cmd']:.0f} N  "
                  f"(limit {lm.T_max_eng:.0f} N"
                  f"{' — SATURATED' if b['saturated'] else ''})")
            print(f"    delivered thrust  weak {b['F_weak']:.0f} N  vs  "
                  f"strong {b['F_strong']:.0f} N")
            print(f"    residual roll moment  = {b['L_resid']:.0f} N.m")
            print(f"    gimbal + RCS can absorb = "
                  f"{b['L_gimbal'] + b['L_rcs']:.0f} N.m "
                  f"({b['L_gimbal']:.0f} + {b['L_rcs']:.0f})")
            print(f"    -> {'TRIMMABLE' if b['deficit'] <= 0 else 'NOT TRIMMABLE'}"
                  f"  (deficit {b['deficit']:+.0f} N.m)\n")

            try:
                Xs, Us = af.solve_landing(lm, cfg, sc)
            except af.SolveFailure as exc:
                status = 'FAILED'
                print(f"\n>>> SOLVER FAILED <<<\n{exc}\n")
                print("Plotting the final non-converged iterate for diagnosis "
                      "— NOT a flyable trajectory.\n")
                Xs, Us = exc.Xs, exc.Us

            af.print_report(Xs)
            M = metrics(Xs, Us, lm, cfg)
            print('Performance metrics:')
            for k, v in M.items():
                print(f'  {k:28s} = {v:14.4f}')

            if status == 'solved':
                Xff, tff = af.cutoff_freefall(Xs[:, -1], lm)
                af.print_cutoff_report(Xs, Xff, tff)
                traj = np.hstack([Xs, Xff])
            else:
                traj = Xs

            af.plot_states(Xs, cfg, os.path.join(outdir, 'states.png'))
            af.plot_controls(Us, cfg, lm, os.path.join(outdir, 'controls.png'))
            af.plot_actuators(Xs, Us, cfg, lm,
                              os.path.join(outdir, 'actuators.png'))
            af.plot_thrusters(Us, cfg, lm,
                              os.path.join(outdir, 'thrusters.png'))
            af.plot_trajectory_with_axes(
                traj, sc, cfg, os.path.join(outdir, 'trajectory_with_axes.png'))
            print(f"\n=== {spec['dirname']} status: {status} ===")

    obj, iters = scrape_log(logpath)
    M.update(objective=obj, iterations=iters, status=status,
             eta=spec['eta'], label=spec['label'],
             **{f'budget_{k}': (float(v) if not isinstance(v, bool) else v)
                for k, v in trim_budget(lm, spec['eta']).items()})
    np.savez(os.path.join(outdir, 'solution.npz'), Xs=Xs, Us=Us)
    with open(os.path.join(outdir, 'metrics.json'), 'w') as fh:
        json.dump(M, fh, indent=2)
    print(f"[{spec['dirname']}] {status:6s} obj={obj:.4e} iters={iters}",
          flush=True)
    return M


if __name__ == '__main__':
    keys = [int(a) for a in sys.argv[1:]] or sorted(CASES)
    all_M = {k: run_case(k) for k in keys}
    with open(os.path.join(HERE, 'summary.json'), 'w') as fh:
        json.dump({str(k): v for k, v in all_M.items()}, fh, indent=2)

    show = [('status', 'status', '{}'),
            ('objective', 'objective J', '{:.4e}'),
            ('peak_delivered_total_N', 'peak delivered thrust [N]', '{:.0f}'),
            ('mean_cmd_weak_N', 'mean weak-engine command [N]', '{:.0f}'),
            ('wasted_impulse_Ns', 'wasted impulse [N.s]', '{:.3e}'),
            ('mean_abs_tvc_roll_Nm', 'mean |TVC roll moment| [N.m]', '{:.0f}'),
            ('rcs_impulse_Ns', 'RCS impulse [N.s]', '{:.0f}'),
            ('time_to_contact_s', 'time to contact [s]', '{:.0f}'),
            ('terminal_speed_ms', 'terminal speed [m/s]', '{:.2e}')]
    print('\n' + '=' * 92)
    print(f"{'metric':32s}" + ''.join(f"{f'eta={all_M[k]['eta']:.2f}':>12s}"
                                      for k in all_M))
    for key, name, fmt in show:
        print(f'{name:32s}' + ''.join(f'{fmt.format(all_M[k][key]):>12s}'
                                      for k in all_M))
