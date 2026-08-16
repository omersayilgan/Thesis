"""
Degraded-Gimbal Case Study — Apollo LM Powered Descent
══════════════════════════════════════════════════════
Engine 2's gimbal actuator is made progressively more sluggish while engine 1
stays healthy.  Everything else — vehicle, scenario, grid, weights — is held at
the baseline, so every difference between runs is attributable to that one
actuator.

The gimbal is modelled in apollo_full.py as a second-order servo per axis,

    d_ddot = wn^2 (d_cmd - d) - 2 zeta wn d_dot ,

so a degradation is a change to (wn, zeta) for that engine only, via
LMParams.gimbal_wn_eng / gimbal_zeta_eng.

  G1  wn = 4.0, zeta = 0.70   baseline, both engines healthy (0.64 Hz)
  G2  wn = 1.5, zeta = 0.70   mild loss of bandwidth        (0.24 Hz)
  G3  wn = 0.6, zeta = 0.70   severe loss of bandwidth      (0.10 Hz)
  G4  wn = 1.0, zeta = 0.25   sluggish *and* underdamped — a worn servo that
                              overshoots and rings rather than just lagging

Run:  python run_gimbal_study.py          (all four, ~5 min)
      python run_gimbal_study.py 3        (just G3)
"""

import os

# Pin BLAS/OpenMP to a single thread BEFORE numpy/casadi are imported.
# This NLP is nonconvex, and with multithreaded BLAS the reduction order varies
# run to run; that is enough to steer IPOPT into a *different local minimum*.
# Measured on the nominal problem: three unpinned runs gave J = 2.8675e8,
# 2.8670e8 and 2.8391e8 (a 1.0% spread), while three pinned runs all gave
# 2.867018e8 to every printed digit.  Since this study compares objectives
# between cases, that noise has to be off the table.
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
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'src', 'apollo_gnc'))  # shared engine

import apollo_full as af

DEGRADED = 1                      # engine index whose gimbal is degraded

CASES = {
    1: dict(dirname='G1_nominal',
            title='G1 — baseline, both gimbals healthy',
            wn=4.0, zeta=0.70),
    2: dict(dirname='G2_mild_wn1.5',
            title='G2 — engine 2 gimbal mild (wn = 1.5 rad/s)',
            wn=1.5, zeta=0.70),
    3: dict(dirname='G3_severe_wn0.6',
            title='G3 — engine 2 gimbal severe (wn = 0.6 rad/s)',
            wn=0.6, zeta=0.70),
    4: dict(dirname='G4_underdamped_wn1.0_zeta0.25',
            title='G4 — engine 2 gimbal sluggish + underdamped '
                  '(wn = 1.0, zeta = 0.25)',
            wn=1.0, zeta=0.25),
}


def actuator_descriptors(wn, zeta):
    """Textbook second-order descriptors of one gimbal axis."""
    d = dict(wn=wn, zeta=zeta, f_hz=wn / (2 * np.pi),
             t_settle=4.0 / (zeta * wn))            # 2% settling, rule of thumb
    if zeta < 1.0:
        d['overshoot_pct'] = 100 * np.exp(-np.pi * zeta / np.sqrt(1 - zeta**2))
        d['wd'] = wn * np.sqrt(1 - zeta**2)         # damped frequency
    else:
        d['overshoot_pct'] = 0.0
        d['wd'] = 0.0
    return d


def metrics(Xs, Us, lm, cfg):
    """Physical performance metrics from one converged solution."""
    N = Us.shape[1]
    out = {}

    # gimbal command-tracking error per engine: the actuator state against the
    # command that was in force over that interval (zero-order hold)
    for i in range(lm.n_eng):
        err = []
        for sx, cu in ((af.IDX_DP[i], af.IDX_U_DP[i]),
                       (af.IDX_DY[i], af.IDX_U_DY[i])):
            err.append(Xs[sx, :N] - Us[cu, :])
        err = np.concatenate(err)
        out[f'gimbal_rms_err_E{i+1}_deg'] = np.rad2deg(np.sqrt((err**2).mean()))
        out[f'gimbal_max_err_E{i+1}_deg'] = np.rad2deg(np.abs(err).max())
        # how hard the optimiser actually leans on this engine's gimbal
        out[f'gimbal_rms_cmd_E{i+1}_deg'] = np.rad2deg(np.sqrt(
            (np.concatenate([Us[af.IDX_U_DP[i]], Us[af.IDX_U_DY[i]]])**2).mean()))

    f = Us[af.N_U_DPS:af.N_U_DPS + lm.n_rcs, :]
    T_tot = Xs[af.IDX_T].sum(axis=0)
    out.update({
        'peak_roll_deg':      np.abs(np.rad2deg(Xs[6])).max(),
        'peak_pitch_deg':     np.abs(np.rad2deg(Xs[7])).max(),
        'peak_p_degs':        np.abs(np.rad2deg(Xs[9])).max(),
        'peak_q_degs':        np.abs(np.rad2deg(Xs[10])).max(),
        'rcs_impulse_Ns':     f.sum() * cfg.dt,
        'dps_impulse_Ns':     T_tot.sum() * cfg.dt,
        'peak_diff_thrust_N': np.abs(Xs[af.IDX_T[1]] - Xs[af.IDX_T[0]]).max(),
        'terminal_speed_ms':  np.linalg.norm(Xs[3:6, -1]),
        'terminal_pos_err_m': np.linalg.norm(Xs[0:2, -1]),
        'terminal_att_err_deg': np.rad2deg(np.linalg.norm(Xs[6:8, -1])),
    })
    return out


def scrape_log(path):
    """Pull IPOPT's final objective and iteration count out of the transcript."""
    txt = open(path).read()
    obj = re.search(r'^Objective\.+:\s+\S+\s+(\S+)', txt, re.M)
    it  = re.search(r'^Number of Iterations\.+:\s+(\d+)', txt, re.M)
    return (float(obj.group(1)) if obj else float('nan'),
            int(it.group(1)) if it else -1)


def run_case(key):
    spec = CASES[key]
    outdir = os.path.join(HERE, spec['dirname'])
    os.makedirs(outdir, exist_ok=True)

    # only override the degraded engine; engine 0 keeps the nominal actuator
    lm = af.LMParams(gimbal_wn_eng={DEGRADED: spec['wn']},
                     gimbal_zeta_eng={DEGRADED: spec['zeta']})
    cfg = af.OCPConfig()
    sc  = af.Scenario()

    logpath = os.path.join(outdir, 'console_log.txt')
    status, M = 'solved', None
    with open(logpath, 'w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            print('#' * 70)
            print(f"#  {spec['title']}")
            print('#' * 70)
            for i in range(lm.n_eng):
                d = actuator_descriptors(lm.wn_of(i), lm.zeta_of(i))
                flag = '  <-- DEGRADED' if lm.gimbal_is_degraded(i) else ''
                print(f"  engine {i+1} gimbal: wn = {d['wn']:.2f} rad/s "
                      f"({d['f_hz']:.3f} Hz), zeta = {d['zeta']:.2f}, "
                      f"settle ~{d['t_settle']:.1f} s, "
                      f"overshoot {d['overshoot_pct']:.0f}%{flag}")
            print(f"  grid: N = {cfg.N}, dt = {cfg.dt} s "
                  f"(horizon {cfg.N * cfg.dt:.0f} s)\n")

            try:
                Xs, Us = af.solve_landing(lm, cfg, sc)
            except af.SolveFailure as exc:
                status = 'FAILED'
                print(f"\n>>> SOLVER FAILED <<<\n{exc}\n")
                Xs, Us = exc.Xs, exc.Us

            af.print_report(Xs)
            M = metrics(Xs, Us, lm, cfg)
            print('Performance metrics:')
            for k, v in M.items():
                print(f'  {k:26s} = {v:12.4f}')

            if status == 'solved':
                Xff, tff = af.cutoff_freefall(Xs[:, -1], lm)
                af.print_cutoff_report(Xs, Xff, tff)
                traj = np.hstack([Xs, Xff])
            else:
                Xff = tff = None
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
             wn=spec['wn'], zeta=spec['zeta'], title=spec['title'])
    np.savez(os.path.join(outdir, 'solution.npz'), Xs=Xs, Us=Us)
    with open(os.path.join(outdir, 'metrics.json'), 'w') as fh:
        json.dump(M, fh, indent=2)
    print(f"[{spec['dirname']}] {status}  obj={obj:.4e}  iters={iters}")
    return M


if __name__ == '__main__':
    keys = [int(a) for a in sys.argv[1:]] or sorted(CASES)
    all_M = {k: run_case(k) for k in keys}
    with open(os.path.join(HERE, 'summary.json'), 'w') as fh:
        json.dump({str(k): v for k, v in all_M.items()}, fh, indent=2)

    print('\n' + '=' * 78)
    keys_show = [('objective', 'objective J'),
                 ('gimbal_rms_err_E2_deg', 'E2 gimbal RMS track err [deg]'),
                 ('gimbal_rms_cmd_E2_deg', 'E2 gimbal RMS command [deg]'),
                 ('gimbal_rms_cmd_E1_deg', 'E1 gimbal RMS command [deg]'),
                 ('peak_diff_thrust_N', 'peak differential thrust [N]'),
                 ('rcs_impulse_Ns', 'RCS impulse [N.s]'),
                 ('terminal_speed_ms', 'terminal speed [m/s]')]
    hdr = ''.join(f'{f"G{k}":>14s}' for k in all_M)
    print(f'{"metric":34s}{hdr}')
    for k, name in keys_show:
        row = ''.join(f'{all_M[c][k]:14.4g}' for c in all_M)
        print(f'{name:34s}{row}')
