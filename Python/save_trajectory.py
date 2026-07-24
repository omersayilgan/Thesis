"""
Save the Apollo LM landing trajectory for animation
════════════════════════════════════════════════════
Runs the OCP (via apollo_full, unmodified) once, appends the analytic
engine-off touchdown, and dumps the positions + attitudes to a .npz file.
The companion `animate_landing.py` reads that file — so the (slow) solve only
has to happen once and the animation can be re-rendered instantly.

    python save_trajectory.py            # -> apollo_trajectory.npz
"""

import numpy as np
import apollo_full as A


def main(out='apollo_trajectory.npz'):
    lm, cfg, sc = A.LMParams(), A.OCPConfig(), A.Scenario()

    # powered descent (open-loop OCP) + analytic engine-off settle
    Xs, Us = A.solve_landing(lm, cfg, sc)
    Xff, tff = A.cutoff_freefall(Xs[:, -1], lm)

    # timestamps: powered on the OCP grid, free-fall continuing from cut-off
    t_pow = np.arange(Xs.shape[1]) * cfg.dt
    t_ff  = t_pow[-1] + tff

    # stitch the two phases (skip the duplicated contact node of the free-fall)
    pos = np.hstack([Xs[0:3, :], Xff[0:3, 1:]])     # (3, M)  x_E, y_E, z_E
    att = np.hstack([Xs[6:9, :], Xff[6:9, 1:]])     # (3, M)  phi, theta, psi
    t   = np.concatenate([t_pow, t_ff[1:]])         # (M,)
    M   = pos.shape[1]
    engine_on = np.concatenate([np.ones(Xs.shape[1], bool),
                                np.zeros(Xff.shape[1] - 1, bool)])

    # actuator activity per frame (from the actual state; zero during free-fall)
    thrust = np.concatenate([Xs[A.IDX_T,  :], Xff[A.IDX_T,  1:]])   # DPS thrust [N]
    gimbal = np.vstack([                                            # (2, M) dp, dy
        np.concatenate([Xs[A.IDX_DP, :], Xff[A.IDX_DP, 1:]]),
        np.concatenate([Xs[A.IDX_DY, :], Xff[A.IDX_DY, 1:]])])

    # 16 RCS thruster firings aligned to frames: control k acts over interval k;
    # the contact node and the free-fall carry no RCS (engine-off settle).
    rcs = np.zeros((lm.n_rcs, M))
    rcs[:, :Us.shape[1]] = Us[3:3 + lm.n_rcs, :]

    # constant RCS geometry (body frame) so the animator stays dependency-light
    rcs_pos, rcs_dir, _ = lm.rcs_geometry()

    np.savez(out, pos=pos, att=att, t=t, engine_on=engine_on,
             thrust=thrust, gimbal=gimbal, rcs=rcs,
             rcs_pos=rcs_pos, rcs_dir=rcs_dir,
             T_max=lm.T_max, F_rcs=lm.F_rcs_per,
             x0=np.asarray(sc.x0[:3], float), pad=np.zeros(3),
             cut_index=Xs.shape[1] - 1)
    print(f"[saved] {out}  —  {M} frames, t = 0..{t[-1]:.1f} s, "
          f"cut-off at frame {Xs.shape[1]-1}")


if __name__ == '__main__':
    main()
