"""
Engine-Out Case Study — Apollo LM Powered Descent
═════════════════════════════════════════════════
Runs the same OCP from apollo_full.py under three engine configurations and
writes each case's figures + console log into its own sub-directory:

  01_nominal_2_engines            both engines healthy, y_eng = 1.5 m  (baseline)
  02_engine_out_nominal_geometry  engine 2 dead, y_eng = 1.5 m  (as designed)
  03_engine_out_survivable_geometry
                                  engine 2 dead, y_eng = 0.2 m  (re-spaced)

Case 02 is expected to be infeasible: a single engine 1.5 m off the centreline
applies a roll moment far beyond what the gimbal + RCS can trim.  The failure
is captured rather than swallowed, and the last iterate is still plotted so the
divergence is visible.

Run:  python run_case_study.py            (all three cases, ~2-3 min)
      python run_case_study.py 3          (just case 3)
"""

import os
import sys
import contextlib

import numpy as np
import matplotlib
matplotlib.use('Agg')                      # batch: no display needed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'src', 'apollo_gnc'))  # shared engine

import apollo_full as af


# ══════════════════════════════════════════════════════════════════════
#  CASE DEFINITIONS
# ══════════════════════════════════════════════════════════════════════
#  y_eng = 0.2 m for case 3 is not arbitrary.  With one engine out, the
#  surviving engine's roll moment about the CG is
#      L = T cos(dp) * ( -y_eng cos(dy) + dz_eng sin(dy) )
#  so the gimbal alone can null it iff  y_eng <= dz_eng * tan(gimbal_max)
#                                             = 2.5 * tan 6 deg = 0.263 m.
#  0.2 m sits inside that with margin (required dy = 4.57 deg of 6 deg), which
#  leaves the RCS free for manoeuvring instead of being spent on static trim.
# ══════════════════════════════════════════════════════════════════════

CASES = {
    1: dict(dirname='01_nominal_2_engines',
            title='Nominal — 2 engines, y_eng = 1.5 m',
            y_eng=1.5, failed=()),
    # case 2 is untrimmable, so IPOPT never converges — cap the iterations so the
    # run establishes that in minutes instead of grinding to the 5000 default
    2: dict(dirname='02_engine_out_nominal_geometry',
            title='Engine 2 out — nominal geometry, y_eng = 1.5 m',
            y_eng=1.5, failed=(1,), max_iter=400),
    3: dict(dirname='03_engine_out_survivable_geometry',
            title='Engine 2 out — re-spaced geometry, y_eng = 0.2 m',
            y_eng=0.2, failed=(1,)),
}


def roll_budget(lm, n_failed=1):
    """Static roll-trim budget for the engine-out condition, all in N*m.

    required  — roll moment the surviving engine applies with its gimbal
                centred, which the vehicle has to cancel
    gimbal    — best cancellation the gimbal can contribute at its 6 deg limit
    rcs       — total roll moment available from the 16 RCS thrusters
    """
    T = lm.T_hover / (lm.n_eng - n_failed)          # survivor carries hover trim
    y_e, z_e = lm.y_eng, lm.dz_eng
    required = T * y_e                              # |L| at dy = 0
    gimbal   = T * z_e * np.tan(lm.gimbal_max)      # counter-moment at the limit
    pos, dirs, B = lm.rcs_geometry()
    # each thruster's roll contribution is (r x d)_x = B[3, i].  The most roll
    # the box f in [0, F]^16 can deliver is the LP optimum: fire exactly the
    # thrusters with a positive coefficient, at full thrust.  (Summing
    # |B[3, :]| would double-count — a quad's up- and down-firing jets sit at
    # the same r and produce equal-and-opposite roll, so only one helps.)
    rcs = np.clip(B[3, :], 0.0, None).sum() * lm.F_rcs_per
    return dict(required=required, gimbal=gimbal, rcs=rcs,
                deficit=required - gimbal - rcs,
                y_crit=z_e * np.tan(lm.gimbal_max) + rcs / T)


def run_case(key):
    spec = CASES[key]
    outdir = os.path.join(HERE, spec['dirname'])
    os.makedirs(outdir, exist_ok=True)

    lm  = af.LMParams(y_eng=spec['y_eng'])
    cfg = af.OCPConfig(max_iter=spec.get('max_iter', 5000))
    sc  = af.Scenario(failed_eng=spec['failed'])

    logpath = os.path.join(outdir, 'console_log.txt')
    # line-buffered so a long or interrupted solve still leaves a readable log
    with open(logpath, 'w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            print('#' * 70)
            print(f"#  CASE {key}: {spec['title']}")
            print('#' * 70)
            print(f"  engines           : {lm.n_eng}  "
                  f"(failed: {spec['failed'] or 'none'})")
            print(f"  lateral spacing   : y_eng = {lm.y_eng} m")
            print(f"  total thrust range: {lm.T_min:.0f} .. {lm.T_max:.0f} N")
            print(f"  hover thrust      : {lm.T_hover:.0f} N")

            if spec['failed']:
                b = roll_budget(lm, len(spec['failed']))
                print("\n  Static roll-trim budget (engine-out):")
                print(f"    moment to cancel        = {b['required']:9.1f} N.m")
                print(f"    gimbal can cancel       = {b['gimbal']:9.1f} N.m "
                      f"(at {np.rad2deg(lm.gimbal_max):.0f} deg)")
                print(f"    RCS can cancel          = {b['rcs']:9.1f} N.m")
                print(f"    deficit                 = {b['deficit']:9.1f} N.m "
                      f"({'TRIMMABLE' if b['deficit'] <= 0 else 'NOT TRIMMABLE'})")
                print(f"    critical spacing y_crit = {b['y_crit']:9.3f} m")
            print()

            status, Xs, Us, Xff, tff = 'solved', None, None, None, None
            try:
                Xs, Us = af.solve_landing(lm, cfg, sc)
            except af.SolveFailure as exc:
                # IPOPT gave up (infeasible / out of iterations).  The last
                # iterate rides along on the exception, so the divergence can
                # still be plotted and reported.
                status = 'FAILED'
                print(f"\n>>> SOLVER FAILED <<<\n{exc}\n")
                Xs, Us = exc.Xs, exc.Us
                print("Plotting the final (non-converged) iterate for "
                      "diagnosis — this is NOT a flyable trajectory.\n")

            if Xs is not None:
                af.print_report(Xs)
                af.plot_states(Xs, cfg, os.path.join(outdir, 'states.png'))
                af.plot_controls(Us, cfg, lm,
                                 os.path.join(outdir, 'controls.png'))
                af.plot_actuators(Xs, Us, cfg, lm,
                                  os.path.join(outdir, 'actuators.png'))
                af.plot_thrusters(Us, cfg, lm,
                                  os.path.join(outdir, 'thrusters.png'))

                # the ballistic settle and the 3-D scene only mean something for
                # a converged trajectory
                if status == 'solved':
                    Xff, tff = af.cutoff_freefall(Xs[:, -1], lm)
                    af.print_cutoff_report(Xs, Xff, tff)
                    traj = np.hstack([Xs, Xff])
                else:
                    traj = Xs
                af.plot_trajectory_with_axes(
                    traj, sc, cfg,
                    os.path.join(outdir, 'trajectory_with_axes.png'))

            print(f"\n=== case {key} status: {status} ===")

    print(f"[case {key}] {status:8s} -> {spec['dirname']}/")
    if Xs is not None:
        np.savez(os.path.join(outdir, 'solution.npz'),
                 Xs=Xs, Us=Us, Xff=Xff, tff=tff)
    return status, lm, Xs, Us


if __name__ == '__main__':
    keys = [int(a) for a in sys.argv[1:]] or sorted(CASES)
    results = {k: run_case(k) for k in keys}
    print('\nSummary:')
    for k, (status, *_ ) in results.items():
        print(f'  case {k}  {CASES[k]["title"]:55s}  {status}')
