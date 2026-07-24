"""
Apollo Lunar Module — One-Shot Motion-Planning OCP + Descent Plots
══════════════════════════════════════════════════════════════════
Self-contained: builds a single open-loop optimal control problem
(direct multiple shooting + RK4), solves the NLP once, and plots the
resulting state, control, and 3-D trajectory histories.

Requirements:  pip install casadi numpy matplotlib
"""

import numpy as np
import casadi as ca
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════════
#  1. PARAMETERS
# ══════════════════════════════════════════════════════════════════════

@dataclass
class LMParams:
    mass: float = 7711.0
    Ixx:  float = 5368.0
    Iyy:  float = 5368.0
    Izz:  float = 5040.0
    g_moon: float = 1.625

    # DPS
    T_max:      float = 45040.0
    T_min:      float = 4560.0
    gimbal_max: float = np.deg2rad(6.0)
    dz_eng:     float = 2.5

    # DPS actuator dynamics
    tau_T:       float = 0.4     # thrust first-order lag time constant  [s]
    gimbal_wn:   float = 4.0     # gimbal actuator natural frequency  [rad/s] (~0.6 Hz)
    gimbal_zeta: float = 0.7     # gimbal actuator damping ratio  [-]

    # RCS  —  4 quads, 4 thrusters each = 16 thrusters
    F_rcs_per: float = 445.0     # max thrust per single thruster  [N]
    n_quads:   int   = 4
    rcs_arm:   float = 1.7       # quad radius from centreline (x-y plane) [m]

    @property
    def n_rcs(self):   return 4 * self.n_quads          # 16 thrusters
    @property
    def T_hover(self): return self.mass * self.g_moon

    def rcs_geometry(self):
        """Thruster positions r_i and unit fire-directions d_i in the body
        frame (x fwd, y right, z down), and the 6xN allocation matrix B such
        that  [F_rcs; M_rcs] = B @ f,  f_i in [0, F_rcs_per].

        Layout: 4 quads on outriggers at azimuths 45/135/225/315 deg, radius
        rcs_arm in the body x-y plane.  Each quad has 4 thrusters — one firing
        +z (down), one -z (up), and two tangential (±) in the x-y plane — so
        that firing any thruster produces a coupled force *and* moment.
        """
        pos, dirs = [], []
        for az in np.deg2rad([45.0, 135.0, 225.0, 315.0]):
            c, s = np.cos(az), np.sin(az)
            r_quad = self.rcs_arm * np.array([c, s, 0.0])   # quad location
            tang   = np.array([-s, c, 0.0])                 # in-plane tangent
            for d in (np.array([0.0, 0.0,  1.0]),           # axial down (+z)
                      np.array([0.0, 0.0, -1.0]),           # axial up   (-z)
                      tang,                                  # tangential +
                      -tang):                                # tangential -
                pos.append(r_quad)
                dirs.append(d)
        pos  = np.array(pos)                                # (16, 3)
        dirs = np.array(dirs)                               # (16, 3)
        # B = [ d_i ; r_i x d_i ]  stacked as columns  -> (6, 16)
        B = np.vstack([dirs.T, np.cross(pos, dirs).T])
        return pos, dirs, B

    @property
    def B_rcs(self):
        """6x16 RCS allocation matrix as a CasADi constant (cached — this is
        queried 4*N times while the RK4 graph is built, so avoid rebuilding
        the NumPy geometry + DM on every call)."""
        B = getattr(self, '_B_rcs_cached', None)
        if B is None:
            B = ca.DM(self.rcs_geometry()[2])
            object.__setattr__(self, '_B_rcs_cached', B)
        return B


@dataclass
class OCPConfig:
    # 80-step / 1 s grid (80 s horizon). Coarsened from the old 200/0.5 s grid:
    # a smaller N shrinks the KKT system the linear solver factorises each
    # iteration (~quadratically), which is what makes the NLP converge in a few
    # minutes instead of stalling. dt=1 s is about as coarse as the gimbal
    # actuator (wn=4 rad/s) tolerates before its 2nd-order response is
    # under-resolved.
    N:  int   = 80
    dt: float = 1.0
    integrator: str = 'rk4'          # 'rk4' (recommended) or 'rk2' (Heun) — rk2 is
                                     # cheaper per step but tends to need more IPOPT
                                     # iterations here, so rk4 is faster end-to-end.
    V_max:     float = 60.0                  # translational velocity limit  [m/s]
    euler_max: float = np.deg2rad(45.0)      # roll/pitch/yaw angle limit
    omega_max: float = np.deg2rad(10.0)      # attitude-rate limit  (p, q, r)

    # DPS cut-off at touchdown: the powered OCP flies the vehicle down to a low
    # "contact" altitude (probes touch the surface); there the engine is cut and
    # the last stretch to the ground is an analytic engine-off ballistic settle.
    # This mirrors the real DPS shutdown at contact and keeps the OCP well-posed
    # (no thrust gating / hover pathology near z=0).
    h_contact: float = 1.0                    # altitude [m] at which the engine is cut off

    Qs: np.ndarray = field(default_factory=lambda: np.array(
        [20, 20, 30, 60, 60, 60, 20, 20, 1, 30, 30, 30], dtype=float))
    Qf: np.ndarray = field(default_factory=lambda: np.array(
        [5000,  5000,  8000,  4000,  4000,  4000,
         6000,  6000,  400,   10000, 10000, 10000], dtype=float))
    # control weights: [T, dp, dy, then 16 RCS thruster commands]
    Rw: np.ndarray = field(default_factory=lambda: np.array(
        [1e-7, 8.0, 8.0] + [5e-4] * 16, dtype=float))
    # control-rate weights: penalise step-to-step change Δu = u_k - u_{k-1}
    # (heavy on the gimbals to damp their oscillation; light on T & RCS)
    Rd: np.ndarray = field(default_factory=lambda: np.array(
        [1e-6, 4000.0, 4000.0] + [1e-3] * 16, dtype=float))


@dataclass
class Scenario:
    x0: np.ndarray = field(default_factory=lambda: np.array([
         300.0,  120.0, -1000.0,
          -8.0,   -2.0,    5.0,
        np.deg2rad(2.0), np.deg2rad(-3.0), np.deg2rad(10.0),
        np.deg2rad(0.3), np.deg2rad(-0.4), np.deg2rad(0.1)]))
    x_target: np.ndarray = field(default_factory=lambda: np.zeros(12))


# ══════════════════════════════════════════════════════════════════════
#  2. DYNAMICS
# ══════════════════════════════════════════════════════════════════════
#
#  Augmented state (17):
#     0- 2  position   x_E, y_E, z_E
#     3- 5  velocity   u, v, w        (body)
#     6- 8  attitude   phi, theta, psi
#     9-11  rates      p, q, r
#       12  thrust     T              (1st-order lag  -> T_cmd)
#    13,14  pitch gimbal  dp, dp_dot  (2nd-order       -> dp_cmd)
#    15,16  yaw   gimbal  dy, dy_dot  (2nd-order       -> dy_cmd)
#
#  Control (19):  [T_cmd, dp_cmd, dy_cmd, f_rcs(16)]
# ══════════════════════════════════════════════════════════════════════

N_RIGID = 12                 # rigid-body states
N_ACT   = 5                  # actuator states: T, dp, dp_dot, dy, dy_dot
IDX_T, IDX_DP, IDX_DPD, IDX_DY, IDX_DYD = 12, 13, 14, 15, 16


def flat_moon_6dof(x, u, lm):
    ub, vb, wb  = x[3], x[4], x[5]
    phi, th, ps = x[6], x[7], x[8]
    p, q, r     = x[9], x[10], x[11]

    # actual actuator states (what the vehicle really applies)
    T_     = x[IDX_T]
    dp     = x[IDX_DP];  dp_dot = x[IDX_DPD]
    dy     = x[IDX_DY];  dy_dot = x[IDX_DYD]

    # commanded values (set by the optimiser)
    T_cmd  = u[0]
    dp_cmd = u[1]
    dy_cmd = u[2]

    # RCS: 16 individual thruster commands -> coupled force & moment via B
    f_rcs = u[3:3 + lm.n_rcs]
    wrench = lm.B_rcs @ f_rcs
    Frx, Fry, Frz = wrench[0], wrench[1], wrench[2]
    Lr,  Mr,  Nr  = wrench[3], wrench[4], wrench[5]

    cp = ca.cos(phi); sp = ca.sin(phi)
    ct = ca.cos(th);  st = ca.sin(th); tt = ca.tan(th)
    cs = ca.cos(ps);  ss = ca.sin(ps)

    Tx =  T_ * ca.sin(dp)
    Ty = -T_ * ca.sin(dy) * ca.cos(dp)
    Tz = -T_ * ca.cos(dp) * ca.cos(dy)

    Fx = Tx + Frx;  Fy = Ty + Fry;  Fz = Tz + Frz

    L_tot = -lm.dz_eng * Ty + Lr
    M_tot =  lm.dz_eng * Tx + Mr
    N_tot =  Nr

    C_EB = ca.vertcat(
        ca.horzcat(ct*cs, sp*st*cs - cp*ss, cp*st*cs + sp*ss),
        ca.horzcat(ct*ss, sp*st*ss + cp*cs, cp*st*ss - sp*cs),
        ca.horzcat(-st,   sp*ct,            cp*ct))

    rdot = C_EB @ ca.vertcat(ub, vb, wb)

    grav_b = lm.g_moon * ca.vertcat(-st, sp*ct, cp*ct)
    vdot = ca.vertcat(r*vb - q*wb, p*wb - r*ub, q*ub - p*vb) \
           + grav_b + ca.vertcat(Fx, Fy, Fz) / lm.mass

    edot = ca.vertcat(p + (q*sp + r*cp)*tt,
                      q*cp - r*sp,
                      (q*sp + r*cp) / ct)

    pdot   = (L_tot - (lm.Izz - lm.Iyy)*q*r) / lm.Ixx
    qdot   = (M_tot - (lm.Ixx - lm.Izz)*p*r) / lm.Iyy
    rdot_w = (N_tot - (lm.Iyy - lm.Ixx)*p*q) / lm.Izz

    # ── actuator dynamics ──
    # thrust: first order      Tdot = (T_cmd - T)/tau
    Tdot = (T_cmd - T_) / lm.tau_T
    # gimbals: second order     d̈ = wn^2 (cmd - d) - 2 zeta wn ḋ
    wn, z = lm.gimbal_wn, lm.gimbal_zeta
    dp_ddot = wn*wn * (dp_cmd - dp) - 2*z*wn * dp_dot
    dy_ddot = wn*wn * (dy_cmd - dy) - 2*z*wn * dy_dot

    return ca.vertcat(rdot, vdot, edot, pdot, qdot, rdot_w,
                      Tdot, dp_dot, dp_ddot, dy_dot, dy_ddot)


def rk4_step(x, u, dt, lm):
    k1 = flat_moon_6dof(x,             u, lm)
    k2 = flat_moon_6dof(x + dt/2 * k1, u, lm)
    k3 = flat_moon_6dof(x + dt/2 * k2, u, lm)
    k4 = flat_moon_6dof(x + dt   * k3, u, lm)
    return x + dt/6 * (k1 + 2*k2 + 2*k3 + k4)


def rk2_step(x, u, dt, lm):
    """Heun / explicit-trapezoid: 2 dynamics evals per step vs RK4's 4, so the
    per-step constraint graph (and its Jacobian/Hessian) is ~half the size.
    Second-order accurate — a good speed/accuracy trade at this dt."""
    k1 = flat_moon_6dof(x,          u, lm)
    k2 = flat_moon_6dof(x + dt * k1, u, lm)
    return x + dt/2 * (k1 + k2)


# integrator registry — pick per OCPConfig.integrator
INTEGRATORS = {'rk4': rk4_step, 'rk2': rk2_step}


# ══════════════════════════════════════════════════════════════════════
#  3. OCP BUILD & SOLVE  (one-shot, open-loop)
# ══════════════════════════════════════════════════════════════════════

def solve_landing(lm, cfg, sc):
    nx, nu = N_RIGID + N_ACT, 3 + lm.n_rcs   # 17 states, 19 commands

    # augment the 12-state scenario / weights with the 5 actuator states
    act_x0     = np.array([lm.T_hover, 0.0, 0.0, 0.0, 0.0])   # T=hover, gimbals 0
    act_target = np.zeros(N_ACT)
    x0     = np.concatenate([sc.x0,       act_x0])
    x_targ = np.concatenate([sc.x_target, act_target])
    # target the contact altitude (not the ground): the powered descent settles
    # at h_contact over the pad, where the engine is cut and an analytic
    # ballistic phase carries the vehicle the last stretch down to z_E = 0.
    x_targ[2] = -cfg.h_contact
    Qs     = np.concatenate([cfg.Qs, np.zeros(N_ACT)])        # actuator states free
    Qf     = np.concatenate([cfg.Qf, np.zeros(N_ACT)])

    opti = ca.Opti()
    X = opti.variable(nx, cfg.N + 1)
    U = opti.variable(nu, cfg.N)

    # initial condition
    opti.subject_to(X[:, 0] == x0)

    # dynamics (multiple shooting) — integrator chosen by cfg.integrator
    step = INTEGRATORS[cfg.integrator]
    for k in range(cfg.N):
        opti.subject_to(X[:, k+1] == step(X[:, k], U[:, k], cfg.dt, lm))

    # state bounds
    for k in range(cfg.N + 1):
        opti.subject_to(X[2, k] <= 0)
        for j in [3, 4, 5]:
            opti.subject_to(opti.bounded(-cfg.V_max, X[j, k], cfg.V_max))
        for j in [6, 7, 8]:
            opti.subject_to(opti.bounded(-cfg.euler_max, X[j, k], cfg.euler_max))
        for j in [9, 10, 11]:
            opti.subject_to(opti.bounded(-cfg.omega_max, X[j, k], cfg.omega_max))
        # actuator-state limits: actual thrust & gimbal angles stay in range
        opti.subject_to(opti.bounded(lm.T_min,       X[IDX_T,  k], lm.T_max))
        opti.subject_to(opti.bounded(-lm.gimbal_max, X[IDX_DP, k], lm.gimbal_max))
        opti.subject_to(opti.bounded(-lm.gimbal_max, X[IDX_DY, k], lm.gimbal_max))

    # control bounds  (commanded values)
    for k in range(cfg.N):
        opti.subject_to(opti.bounded(lm.T_min,       U[0, k], lm.T_max))
        opti.subject_to(opti.bounded(-lm.gimbal_max, U[1, k], lm.gimbal_max))
        opti.subject_to(opti.bounded(-lm.gimbal_max, U[2, k], lm.gimbal_max))
        # each RCS thruster fires one way only: 0 <= f_i <= F_rcs_per
        for j in range(3, 3 + lm.n_rcs):
            opti.subject_to(opti.bounded(0.0, U[j, k], lm.F_rcs_per))

    # cost  (thruster commands are penalised toward 0 -> minimum-fuel RCS use)
    u_ref = ca.vertcat(lm.T_hover, 0, 0, *([0] * lm.n_rcs))
    cost = 0.0
    for k in range(cfg.N):
        dx = X[:, k] - x_targ
        du = U[:, k] - u_ref
        cost += ca.dot(Qs * dx, dx) + ca.dot(cfg.Rw * du, du)
        # control-rate penalty: punish rapidly changing actuator commands
        if k > 0:
            dU = U[:, k] - U[:, k-1]
            cost += ca.dot(cfg.Rd * dU, dU)
    dxN = X[:, cfg.N] - x_targ
    cost += ca.dot(Qf * dxN, dxN)
    opti.minimize(cost)

    # warm start
    for i in range(nx):
        for k in range(cfg.N + 1):
            opti.set_initial(X[i, k],
                             x0[i] + (x_targ[i] - x0[i]) * k / cfg.N)
    # hold actuator warm-start at their initial values (don't ramp T -> 0)
    for k in range(cfg.N + 1):
        opti.set_initial(X[IDX_T, k], lm.T_hover)
        for i in [IDX_DP, IDX_DPD, IDX_DY, IDX_DYD]:
            opti.set_initial(X[i, k], 0.0)
    for k in range(cfg.N):
        opti.set_initial(U[0, k], lm.T_hover)
        for j in range(1, nu):
            opti.set_initial(U[j, k], 0.0)

    # solve  (exact Hessian: costlier per iteration but converges in far fewer
    #  iterations — limited-memory L-BFGS failed to converge on this large NLP)
    #
    # 'expand' rewrites the MX problem graph as SX: cost, constraints and their
    # derivatives then evaluate ~2x faster (measured), all ops here being
    # SX-compatible, for a slightly longer one-time build.
    #
    # The bulk of the remaining solve time is IPOPT's KKT factorisation (MUMPS)
    # times the iteration count. The trajectory becomes feasible early; the many
    # extra iterations go into optimality polishing on a poorly-scaled problem,
    # so the 'acceptable' criteria let it stop at a good feasible solution
    # instead of grinding to the tight tol.
    opts = {'expand': True,
            'ipopt.max_iter': 5000, 'ipopt.tol': 1e-4,
            'ipopt.acceptable_tol': 1e-3, 'ipopt.acceptable_iter': 15,
            'ipopt.mu_strategy': 'adaptive',
            'ipopt.print_level': 3, 'print_time': True}
    opti.solver('ipopt', opts)

    print("=" * 60)
    print("  Apollo LM  —  One-Shot Motion-Planning OCP")
    print("=" * 60)
    sol = opti.solve()
    print("\n>>> IPOPT converged <<<\n")

    return sol.value(X), sol.value(U)


def cutoff_freefall(x_contact, lm, dt=0.02, max_t=8.0):
    """Analytic engine-off phase: at contact the DPS is cut and the vehicle
    settles ballistically the last stretch to the surface.

    Starting from the powered-descent terminal state, thrust is hard-cut
    (T := 0, gimbals zeroed, RCS off) and the full 6-DOF dynamics are integrated
    with fine steps under lunar gravity until z_E reaches 0 (touchdown). The
    final sub-step is linearly interpolated so the last sample sits exactly on
    the ground. Returns (Xff, tff) with Xff[:,0] the contact state (engine just
    cut) and Xff[:,-1] the touchdown state; tff is time since cut-off.
    """
    x = np.asarray(x_contact, dtype=float).copy()
    x[IDX_T] = 0.0                                   # hard engine cut-off
    x[IDX_DP] = x[IDX_DPD] = x[IDX_DY] = x[IDX_DYD] = 0.0
    u0 = np.zeros(3 + lm.n_rcs)                       # no DPS command, no RCS

    xs, ts, t = [x.copy()], [0.0], 0.0
    while x[2] < 0.0 and t < max_t:                   # z_E < 0  <=>  still airborne
        x_next = np.array(rk4_step(ca.DM(x), ca.DM(u0), dt, lm)).flatten()
        t += dt
        if x_next[2] >= 0.0:                          # crossed the ground this step
            frac = -x[2] / (x_next[2] - x[2])         # linear interp to z_E = 0
            x = x + frac * (x_next - x)
            ts.append(t - dt + frac * dt); xs.append(x.copy())
            break
        x = x_next
        ts.append(t); xs.append(x.copy())
    return np.array(xs).T, np.array(ts)


# ══════════════════════════════════════════════════════════════════════
#  4. LANDING REPORT
# ══════════════════════════════════════════════════════════════════════

def print_report(Xs):
    xf = Xs[:, -1]
    speed_f = np.linalg.norm(xf[3:6])
    att_err = np.linalg.norm(xf[6:8])
    pos_err = np.linalg.norm(xf[0:3])

    print("Terminal state:")
    print(f"  Position  (x,y)   = ({xf[0]:.2f}, {xf[1]:.2f}) m")
    print(f"  Altitude  (-z_E)  = {-xf[2]:.2f} m")
    print(f"  Velocity  (u,v,w) = ({xf[3]:.3f}, {xf[4]:.3f}, {xf[5]:.3f}) m/s")
    print(f"  Euler (φ,θ,ψ)     = ({np.rad2deg(xf[6]):.2f}, "
          f"{np.rad2deg(xf[7]):.2f}, {np.rad2deg(xf[8]):.2f})°")
    print(f"  Ang. rate (p,q,r) = ({np.rad2deg(xf[9]):.3f}, "
          f"{np.rad2deg(xf[10]):.3f}, {np.rad2deg(xf[11]):.3f})°/s")
    print(f"\n  Touchdown speed    = {speed_f:.3f} m/s")
    print(f"  Position error     = {pos_err:.2f} m")
    print(f"  Attitude error     = {np.rad2deg(att_err):.2f}°")

    if speed_f < 2.0 and pos_err < 15.0 and np.rad2deg(att_err) < 5.0:
        print("\n  ★  LANDING SUCCESS  ★\n")
    else:
        print("\n  ⚠  Landing criteria not fully met\n")


def print_cutoff_report(Xc, Xff, tff):
    """Report the engine cut-off event and the analytic touchdown that follows."""
    contact, td = Xc[:, -1], Xff[:, -1]
    print("=" * 60)
    print("  DPS CUT-OFF  &  BALLISTIC TOUCHDOWN")
    print("=" * 60)
    print("At engine cut-off (contact):")
    print(f"  Altitude          = {-contact[2]:.2f} m")
    print(f"  Descent rate w    = {contact[5]:.3f} m/s   "
          f"(speed {np.linalg.norm(contact[3:6]):.3f} m/s)")
    print(f"  Thrust at cut-off = {contact[IDX_T]:.0f} N  ->  0 N")
    print(f"\nAfter {tff[-1]:.2f} s of engine-off free-fall:")
    print(f"  Touchdown altitude = {-td[2]:.3f} m")
    print(f"  Touchdown speed    = {np.linalg.norm(td[3:6]):.3f} m/s "
          f"(vertical {td[5]:.3f} m/s)")
    print(f"  Horizontal drift   = ({td[0]-contact[0]:+.2f}, "
          f"{td[1]-contact[1]:+.2f}) m during settle\n")


# ══════════════════════════════════════════════════════════════════════
#  5. STATE & CONTROL PLOTS
# ══════════════════════════════════════════════════════════════════════

def plot_states(Xs, cfg, save_path='states.png'):
    t   = np.arange(Xs.shape[1]) * cfg.dt
    alt = -Xs[2, :]

    labels = ['$x_E$ [m]','$y_E$ [m]','Altitude [m]',
              '$u$ [m/s]','$v$ [m/s]','$w$ [m/s]',
              r'$\phi$ [°]', r'$\theta$ [°]', r'$\psi$ [°]',
              '$p$ [°/s]','$q$ [°/s]','$r$ [°/s]']
    data = [Xs[0], Xs[1], alt,
            Xs[3], Xs[4], Xs[5],
            np.rad2deg(Xs[6]), np.rad2deg(Xs[7]), np.rad2deg(Xs[8]),
            np.rad2deg(Xs[9]), np.rad2deg(Xs[10]), np.rad2deg(Xs[11])]

    fig, axes = plt.subplots(4, 3, figsize=(16, 14))
    fig.suptitle('Apollo LM — State Histories', fontsize=14, weight='bold')
    for i, ax in enumerate(axes.flat):
        ax.plot(t, data[i], 'b-', lw=1.5)
        ax.set_ylabel(labels[i]); ax.grid(True, alpha=0.3)
        if i >= 9:
            ax.set_xlabel('Time [s]')
            ax.axhline( np.rad2deg(cfg.omega_max), ls='--', c='r', alpha=0.4)
            ax.axhline(-np.rad2deg(cfg.omega_max), ls='--', c='r', alpha=0.4)
        if 3 <= i <= 5:
            ax.axhline( cfg.V_max, ls='--', c='r', alpha=0.4)
            ax.axhline(-cfg.V_max, ls='--', c='r', alpha=0.4)
        if 6 <= i <= 8:
            ax.axhline( np.rad2deg(cfg.euler_max), ls='--', c='r', alpha=0.4)
            ax.axhline(-np.rad2deg(cfg.euler_max), ls='--', c='r', alpha=0.4)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(save_path, dpi=150); print(f'[saved] {save_path}')


def plot_controls(Us, cfg, lm, save_path='controls.png'):
    """DPS thrust/gimbal plus the *net* RCS wrench reconstructed from the
    16 thruster commands via the allocation matrix B (F_rcs, M_rcs = B @ f)."""
    t  = np.arange(Us.shape[1]) * cfg.dt
    gd = np.rad2deg(lm.gimbal_max)

    f_rcs  = Us[3:3 + lm.n_rcs, :]          # (16, N) thruster firings
    wrench = lm.rcs_geometry()[2] @ f_rcs   # (6, N): Fx,Fy,Fz,L,M,N

    labels = ['Thrust cmd $T_c$ [N]',
              r'Gimbal cmd $\delta_{p,c}$ [°]', r'Gimbal cmd $\delta_{y,c}$ [°]',
              'RCS $F_x$ [N]','RCS $F_y$ [N]','RCS $F_z$ [N]',
              'RCS $L$ [N·m]','RCS $M$ [N·m]','RCS $N$ [N·m]']
    data = [Us[0], np.rad2deg(Us[1]), np.rad2deg(Us[2]),
            wrench[0], wrench[1], wrench[2],
            wrench[3], wrench[4], wrench[5]]
    # only T and the gimbals have simple box limits now; the RCS wrench set is
    # a coupled zonotope (image of B), so no axis-aligned bound line is drawn.
    lo = [lm.T_min, -gd, -gd, None, None, None, None, None, None]
    hi = [lm.T_max,  gd,  gd, None, None, None, None, None, None]

    fig, axes = plt.subplots(3, 3, figsize=(16, 11))
    fig.suptitle('Apollo LM — Control Histories (DPS + net RCS wrench)',
                 fontsize=14, weight='bold')
    for i, ax in enumerate(axes.flat):
        ax.step(t, data[i], 'b-', lw=1.3, where='post')
        if hi[i] is not None: ax.axhline(hi[i], ls='--', c='r', alpha=0.5)
        if lo[i] is not None: ax.axhline(lo[i], ls='--', c='r', alpha=0.5)
        ax.set_ylabel(labels[i]); ax.grid(True, alpha=0.3)
        if i >= 6: ax.set_xlabel('Time [s]')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(save_path, dpi=150); print(f'[saved] {save_path}')


def plot_actuators(Xs, Us, cfg, lm, save_path='actuators.png'):
    """DPS actuator dynamics — commanded (control) vs actual (state) for the
    thrust (1st-order lag) and the two gimbal angles (2nd-order)."""
    t  = np.arange(Xs.shape[1]) * cfg.dt
    tu = np.arange(Us.shape[1]) * cfg.dt
    gd = np.rad2deg(lm.gimbal_max)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Apollo LM — DPS Actuator Dynamics (command vs actual)',
                 fontsize=14, weight='bold')

    specs = [  # (actual state row, cmd control row, label, scale, ylimit)
        (IDX_T,  0, 'Thrust $T$ [N]',           1.0,        (lm.T_min, lm.T_max)),
        (IDX_DP, 1, r'Gimbal $\delta_p$ [°]',   np.rad2deg(1), (-gd, gd)),
        (IDX_DY, 2, r'Gimbal $\delta_y$ [°]',   np.rad2deg(1), (-gd, gd)),
    ]
    for ax, (sx, cu, lbl, sc_, (lo, hi)) in zip(axes, specs):
        ax.step(tu, Us[cu] * sc_, 'r--', lw=1.3, where='post', label='commanded')
        ax.plot(t,  Xs[sx] * sc_, 'b-',  lw=1.8,               label='actual')
        ax.axhline(hi, ls=':', c='gray', alpha=0.7)
        ax.axhline(lo, ls=':', c='gray', alpha=0.7)
        ax.set_ylabel(lbl); ax.set_xlabel('Time [s]')
        ax.grid(True, alpha=0.3); ax.legend(fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(save_path, dpi=150); print(f'[saved] {save_path}')


def plot_thrusters(Us, cfg, lm, save_path='thrusters.png'):
    """The 16 individual RCS thruster firings f_i in [0, F_rcs_per]."""
    t = np.arange(Us.shape[1]) * cfg.dt
    f = Us[3:3 + lm.n_rcs, :]

    fig, axes = plt.subplots(4, 4, figsize=(16, 12), sharex=True)
    fig.suptitle('Apollo LM — Individual RCS Thruster Firings',
                 fontsize=14, weight='bold')
    for i, ax in enumerate(axes.flat):
        quad, jet = i // 4 + 1, i % 4 + 1
        ax.step(t, f[i], 'b-', lw=1.2, where='post')
        ax.axhline(lm.F_rcs_per, ls='--', c='r', alpha=0.5)
        ax.axhline(0.0,          ls='--', c='r', alpha=0.5)
        ax.set_ylabel(f'Q{quad}·J{jet} [N]'); ax.grid(True, alpha=0.3)
        if i >= 12: ax.set_xlabel('Time [s]')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(save_path, dpi=150); print(f'[saved] {save_path}')


# ══════════════════════════════════════════════════════════════════════
#  6. STATIC TRAJECTORY WITH AXES SNAPSHOT
# ══════════════════════════════════════════════════════════════════════

def dcm_eb(phi, th, psi):
    """C_{E/B} — body-to-Earth DCM (3-2-1 Euler)."""
    cp, sp = np.cos(phi), np.sin(phi)
    ct, st = np.cos(th),  np.sin(th)
    cs, ss = np.cos(psi), np.sin(psi)
    return np.array([
        [ct*cs,  sp*st*cs - cp*ss,  cp*st*cs + sp*ss],
        [ct*ss,  sp*st*ss + cp*cs,  cp*st*ss - sp*cs],
        [-st,    sp*ct,             cp*ct]])


def plot_trajectory_with_axes(Xs, sc, save_path='trajectory_with_axes.png'):
    N   = Xs.shape[1] - 1
    alt = -Xs[2, :]

    fig = plt.figure(figsize=(14, 10))
    ax  = fig.add_subplot(111, projection='3d')

    # ground
    pad = 40
    xl = [min(Xs[0].min(), 0) - pad, max(Xs[0].max(), 0) + pad]
    yl = [min(Xs[1].min(), 0) - pad, max(Xs[1].max(), 0) + pad]
    gx, gy = np.meshgrid(np.linspace(*xl, 4), np.linspace(*yl, 4))
    ax.plot_surface(gx, gy, np.zeros_like(gx), alpha=0.10, color='gray')

    # landing pad
    ps = 15
    ax.plot([-ps, ps], [0, 0], [0, 0], 'r-', lw=2)
    ax.plot([0, 0], [-ps, ps], [0, 0], 'r-', lw=2)
    ax.scatter(0, 0, 0, c='red', s=150, marker='*', zorder=2)
    ax.scatter(*sc.x0[:2], -sc.x0[2], c='green', s=100, marker='^', zorder=5)

    # trajectory
    ax.plot(Xs[0], Xs[1], alt, 'b-', lw=1.8, alpha=0.5)

    # body axes at selected frames
    axis_len = 30
    colors   = ['#E03030', '#30B030', '#3060E0']
    frames   = np.linspace(0, N, 9, dtype=int)
    for k in frames:
        C = dcm_eb(Xs[6, k], Xs[7, k], Xs[8, k])
        px, py, pz = Xs[0, k], Xs[1, k], alt[k]
        for j in range(3):
            ax.quiver(px, py, pz,
                      axis_len * C[0, j],
                      axis_len * C[1, j],
                      axis_len * (-C[2, j]),
                      color=colors[j], linewidth=2,
                      arrow_length_ratio=0.12)

    ax.set_xlabel('North  $x_E$  [m]')
    ax.set_ylabel('East   $y_E$  [m]')
    ax.set_zlabel('Altitude  [m]')
    ax.set_title('Apollo LM — Body-Frame Axes Along Descent',
                 fontsize=14, weight='bold')
    ax.view_init(elev=28, azim=-50)

    handles = [
        Line2D([0],[0], color=colors[0], lw=2, label='$x_B$ (fwd)'),
        Line2D([0],[0], color=colors[1], lw=2, label='$y_B$ (right)'),
        Line2D([0],[0], color=colors[2], lw=2, label='$z_B$ (down)'),
        Line2D([0],[0], color='blue', lw=2, alpha=0.5, label='Trajectory'),
        Line2D([0],[0], color='green', marker='^', ls='', ms=10, label='Start'),
        Line2D([0],[0], color='red', marker='*', ls='', ms=12, label='Pad')]
    ax.legend(handles=handles, loc='upper right', fontsize=9)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150); print(f'[saved] {save_path}')


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    lm  = LMParams()
    cfg = OCPConfig()
    sc  = Scenario()

    # solve the powered descent down to the contact altitude
    Xs, Us = solve_landing(lm, cfg, sc)
    print_report(Xs)

    # analytic engine-off phase: cut the DPS at contact and settle to the ground
    Xff, tff = cutoff_freefall(Xs[:, -1], lm)
    print_cutoff_report(Xs, Xff, tff)

    # static plots (powered phase); the 3-D trajectory also shows the free-fall
    plot_states(Xs, cfg)
    plot_controls(Us, cfg, lm)
    plot_actuators(Xs, Us, cfg, lm)
    plot_thrusters(Us, cfg, lm)
    plot_trajectory_with_axes(np.hstack([Xs, Xff]), sc)

    print("\nAll done.")