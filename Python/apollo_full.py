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
#  0. PROBLEM LAYOUT
# ══════════════════════════════════════════════════════════════════════
#
#  Two independently gimballed TVC engines, each sized at half the nominal
#  DPS thrust, mounted symmetrically either side of the centreline.  Defined
#  up here because both LMParams and OCPConfig are sized from N_ENG.
#
#  Augmented state (12 + 5*N_ENG = 22):
#     0- 2  position   x_E, y_E, z_E
#     3- 5  velocity   u, v, w        (body)
#     6- 8  attitude   phi, theta, psi
#     9-11  rates      p, q, r
#    then per engine i:  T_i, dp_i, dp_dot_i, dy_i, dy_dot_i
#      12-16  engine 0        17-21  engine 1
#
#  Control (3*N_ENG + 16 = 22):
#     per engine i:  T_cmd_i, dp_cmd_i, dy_cmd_i     (0-2, 3-5)
#     then           f_rcs(16)                       (6-21)
# ══════════════════════════════════════════════════════════════════════

N_RIGID       = 12               # rigid-body states
N_ENG         = 2                # gimballed TVC engines
N_ACT_PER_ENG = 5                # T, dp, dp_dot, dy, dy_dot
N_U_PER_ENG   = 3                # T_cmd, dp_cmd, dy_cmd
N_ACT         = N_ENG * N_ACT_PER_ENG   # 10 actuator states
N_U_DPS       = N_ENG * N_U_PER_ENG     # 6 DPS commands, RCS follows

# Per-engine state indices — IDX_T[i] is engine i's thrust state, etc.
IDX_T, IDX_DP, IDX_DPD, IDX_DY, IDX_DYD = [
    [N_RIGID + i * N_ACT_PER_ENG + j for i in range(N_ENG)] for j in range(5)]

# Per-engine control indices
IDX_U_T, IDX_U_DP, IDX_U_DY = [
    [i * N_U_PER_ENG + j for i in range(N_ENG)] for j in range(3)]

IDX_ACT_ALL = sorted(IDX_T + IDX_DP + IDX_DPD + IDX_DY + IDX_DYD)


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

    # DPS — T_max/T_min are the *nominal total* (both engines together), so the
    # vehicle's overall thrust envelope is unchanged from the single-engine model
    T_max:      float = 45040.0
    T_min:      float = 4560.0
    gimbal_max: float = np.deg2rad(6.0)
    dz_eng:     float = 2.5      # engine plane below the CG (body +z)  [m]
    n_eng:      int   = N_ENG    # gimballed TVC engines
    y_eng:      float = 1.5      # lateral half-spacing of the engines (body y) [m]

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
    # per-engine thrust envelope: each of the N_ENG engines carries 1/N_ENG of
    # the nominal DPS rating, so the summed envelope matches T_min..T_max
    @property
    def T_max_eng(self): return self.T_max / self.n_eng
    @property
    def T_min_eng(self): return self.T_min / self.n_eng
    @property
    def T_hover_eng(self): return self.T_hover / self.n_eng

    def eng_pos(self, i):
        """Body-frame position of engine i's gimbal pivot (x fwd, y right,
        z down). Engines sit in the z = dz_eng plane, spread symmetrically
        along the body y-axis: engine 0 at -y_eng, engine 1 at +y_eng.

        The lateral offset is what gives differential throttling direct roll
        authority — with both engines at equal thrust their roll moments
        cancel exactly, so trimmed flight is unaffected."""
        off = (0.0 if self.n_eng == 1 else
               self.y_eng * (2.0 * i / (self.n_eng - 1) - 1.0))
        return np.array([0.0, off, self.dz_eng])

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
    # iteration (~quadratically). dt=1 s is about as coarse as the gimbal
    # actuator (wn=4 rad/s) tolerates before its 2nd-order response is
    # under-resolved. Since the NLP is now scaled (see nlp_scales) the solve is
    # ~34 s here, so a finer grid is affordable again if the thesis wants one.
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

    # Glide-slope (approach-cone) constraint, measured up from the horizontal:
    #     tan(glide_slope) * sqrt(x_E^2 + y_E^2)  <=  altitude
    # i.e. the vehicle must stay inside a cone whose apex is the landing pad.
    #
    # Without it the descent is pathological. The stage cost penalises distance
    # to the target at *every* node, and the target sits at h_contact, so the
    # cheapest trajectory dives at the velocity limit to 1 m altitude, overshoots
    # the pad horizontally (it cannot decelerate that fast), touches the ground
    # ~58 m downrange, then crawls back and hovers — the sharp hook seen in the
    # 3-D plot. The cone rules that family out: being low is only allowed when
    # already close, which forces a straight-in approach.
    #
    # Feasibility: the start (323 m downrange, 1000 m up) sits at 72 deg, so any
    # value below that admits the initial state; 30 deg leaves ample margin.
    glide_slope: float = np.deg2rad(30.0)

    Qs: np.ndarray = field(default_factory=lambda: np.array(
        [20, 20, 30, 60, 60, 60, 20, 20, 1, 30, 30, 30], dtype=float))
    Qf: np.ndarray = field(default_factory=lambda: np.array(
        [5000,  5000,  8000,  4000,  4000,  4000,
         6000,  6000,  400,   10000, 10000, 10000], dtype=float))
    # control weights: [T, dp, dy] per engine, then 16 RCS thruster commands
    Rw: np.ndarray = field(default_factory=lambda: np.array(
        [1e-7, 8.0, 8.0] * N_ENG + [5e-4] * 16, dtype=float))
    # control-rate weights: penalise step-to-step change Δu = u_k - u_{k-1}
    # (heavy on the gimbals to damp their oscillation; light on T & RCS)
    Rd: np.ndarray = field(default_factory=lambda: np.array(
        [1e-6, 4000.0, 4000.0] * N_ENG + [1e-3] * 16, dtype=float))


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
#  State/control layout is defined in section 0 (N_ENG engines, 22 states,
#  22 controls).
# ══════════════════════════════════════════════════════════════════════


def flat_moon_6dof(x, u, lm):
    ub, vb, wb  = x[3], x[4], x[5]
    phi, th, ps = x[6], x[7], x[8]
    p, q, r     = x[9], x[10], x[11]

    # RCS: 16 individual thruster commands -> coupled force & moment via B
    f_rcs = u[N_U_DPS:N_U_DPS + lm.n_rcs]
    wrench = lm.B_rcs @ f_rcs
    Frx, Fry, Frz = wrench[0], wrench[1], wrench[2]
    Lr,  Mr,  Nr  = wrench[3], wrench[4], wrench[5]

    cp = ca.cos(phi); sp = ca.sin(phi)
    ct = ca.cos(th);  st = ca.sin(th); tt = ca.tan(th)
    cs = ca.cos(ps);  ss = ca.sin(ps)

    # ── TVC engines: each contributes a gimballed force at its own mount ──
    Fx = Frx;  Fy = Fry;  Fz = Frz
    L_tot = Lr;  M_tot = Mr;  N_tot = Nr
    act_dot = []                       # actuator derivatives, engine by engine

    for i in range(lm.n_eng):
        # actual actuator states (what this engine really applies)
        T_ = x[IDX_T[i]]
        dp = x[IDX_DP[i]];  dp_dot = x[IDX_DPD[i]]
        dy = x[IDX_DY[i]];  dy_dot = x[IDX_DYD[i]]

        # commanded values (set by the optimiser)
        T_cmd  = u[IDX_U_T[i]]
        dp_cmd = u[IDX_U_DP[i]]
        dy_cmd = u[IDX_U_DY[i]]

        Tx =  T_ * ca.sin(dp)
        Ty = -T_ * ca.sin(dy) * ca.cos(dp)
        Tz = -T_ * ca.cos(dp) * ca.cos(dy)

        Fx += Tx;  Fy += Ty;  Fz += Tz

        # moment about the CG:  M_i = r_i x F_i  with r_i = (x_e, y_e, dz_eng)
        x_e, y_e, z_e = lm.eng_pos(i)
        L_tot += y_e * Tz - z_e * Ty
        M_tot += z_e * Tx - x_e * Tz
        N_tot += x_e * Ty - y_e * Tx

        # ── actuator dynamics ──
        # thrust: first order      Tdot = (T_cmd - T)/tau
        Tdot = (T_cmd - T_) / lm.tau_T
        # gimbals: second order     d̈ = wn^2 (cmd - d) - 2 zeta wn ḋ
        wn, z = lm.gimbal_wn, lm.gimbal_zeta
        dp_ddot = wn*wn * (dp_cmd - dp) - 2*z*wn * dp_dot
        dy_ddot = wn*wn * (dy_cmd - dy) - 2*z*wn * dy_dot
        act_dot += [Tdot, dp_dot, dp_ddot, dy_dot, dy_ddot]

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

    return ca.vertcat(rdot, vdot, edot, pdot, qdot, rdot_w, *act_dot)


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

def nlp_scales(lm, cfg):
    """Per-variable scale factors so every decision variable — and every
    dynamics-defect row — is O(1).

    The raw NLP spans ~7 decades (thrust ~4.5e4 N next to gimbal rates ~1e-2
    rad/s), which wrecks the conditioning of the KKT system and forces IPOPT
    into hundreds of small, badly-scaled steps.  Each entry below is the
    natural magnitude of that variable (usually its own bound), so in scaled
    coordinates the box constraints are roughly +-1.
    """
    sx = np.ones(N_RIGID + N_ACT)
    sx[0:3]     = 100.0                 # position          [m]
    sx[3:6]     = 10.0                  # body velocity     [m/s]
    sx[6:9]     = cfg.euler_max         # attitude          [rad]
    sx[9:12]    = cfg.omega_max         # body rates        [rad/s]
    sx[IDX_T]   = lm.T_max_eng          # per-engine thrust [N]
    sx[IDX_DP]  = sx[IDX_DY]  = lm.gimbal_max                  # gimbal  [rad]
    sx[IDX_DPD] = sx[IDX_DYD] = lm.gimbal_wn * lm.gimbal_max   # rate  [rad/s]

    su = np.concatenate([[lm.T_max_eng, lm.gimbal_max, lm.gimbal_max] * lm.n_eng,
                         np.full(lm.n_rcs, lm.F_rcs_per)])
    return sx, su


def solve_landing(lm, cfg, sc):
    nx, nu = N_RIGID + N_ACT, N_U_DPS + lm.n_rcs   # 22 states, 22 commands

    # augment the 12-state scenario / weights with the actuator states:
    # every engine starts at its share of hover thrust, gimbals centred
    act_x0     = np.array([lm.T_hover_eng, 0.0, 0.0, 0.0, 0.0] * lm.n_eng)
    act_target = np.zeros(N_ACT)
    x0     = np.concatenate([sc.x0,       act_x0])
    x_targ = np.concatenate([sc.x_target, act_target])
    # target the contact altitude (not the ground): the powered descent settles
    # at h_contact over the pad, where the engine is cut and an analytic
    # ballistic phase carries the vehicle the last stretch down to z_E = 0.
    x_targ[2] = -cfg.h_contact
    Qs     = np.concatenate([cfg.Qs, np.zeros(N_ACT)])        # actuator states free
    Qf     = np.concatenate([cfg.Qf, np.zeros(N_ACT)])

    # ── scaling ──────────────────────────────────────────────────────────
    # Xv, Uv are the *scaled* decision variables actually handed to IPOPT;
    # X = Sx*Xv and U = Su*Uv are the physical quantities used by the dynamics
    # and the cost, so the problem being solved is unchanged.
    Sx, Su = nlp_scales(lm, cfg)
    Sx_dm, Su_dm = ca.DM(Sx), ca.DM(Su)

    opti = ca.Opti()
    Xv = opti.variable(nx, cfg.N + 1)
    Uv = opti.variable(nu, cfg.N)

    xs = [Sx_dm * Xv[:, k] for k in range(cfg.N + 1)]   # physical states
    us = [Su_dm * Uv[:, k] for k in range(cfg.N)]       # physical controls

    # initial condition
    opti.subject_to(Xv[:, 0] == x0 / Sx)

    # dynamics (multiple shooting) — integrator chosen by cfg.integrator.
    # The defect is written in scaled coordinates (divided by Sx) so every row
    # of the constraint Jacobian carries comparable magnitude.
    step = INTEGRATORS[cfg.integrator]
    for k in range(cfg.N):
        opti.subject_to(Xv[:, k+1] == step(xs[k], us[k], cfg.dt, lm) / Sx_dm)

    # glide slope: tan(g)*||(x,y)|| <= -z_E, squared to keep it differentiable
    # at the pad (the sqrt has a kink at the origin, exactly where the vehicle
    # ends up). Squaring is exact here because z_E <= 0 is enforced below, so
    # only the physical branch of the cone is reachable. Normalised by the
    # position scale to keep the Jacobian row O(1).
    tan2 = np.tan(cfg.glide_slope) ** 2
    for k in range(cfg.N + 1):
        xk = xs[k] / Sx[2]
        opti.subject_to(tan2 * (xk[0]**2 + xk[1]**2) <= xk[2]**2)

    # state bounds — expressed on the scaled variables so that IPOPT's
    # detect_simple_bounds can lift them out of g and into plain lbx/ubx
    for k in range(cfg.N + 1):
        # altitude floor at the contact height, not at the ground: the powered
        # phase ends where the engine is cut, so dipping below h_contact is
        # meaningless. It also stops the vehicle riding the glide-slope cone
        # (whose apex is the pad) down to ~0 m and then having to climb back to
        # the target altitude — the small bounce that survives the cone alone.
        opti.subject_to(Xv[2, k] <= -cfg.h_contact / Sx[2])
        for j in [3, 4, 5]:
            opti.subject_to(opti.bounded(-cfg.V_max / Sx[j], Xv[j, k],
                                          cfg.V_max / Sx[j]))
        for j in [6, 7, 8]:
            opti.subject_to(opti.bounded(-cfg.euler_max / Sx[j], Xv[j, k],
                                          cfg.euler_max / Sx[j]))
        for j in [9, 10, 11]:
            opti.subject_to(opti.bounded(-cfg.omega_max / Sx[j], Xv[j, k],
                                          cfg.omega_max / Sx[j]))
        # actuator-state limits, per engine: each engine's actual thrust and
        # gimbal angles stay in that engine's own (half-nominal) range
        for i in range(lm.n_eng):
            jt = IDX_T[i]
            opti.subject_to(opti.bounded(lm.T_min_eng / Sx[jt], Xv[jt, k],
                                         lm.T_max_eng / Sx[jt]))
            for j in (IDX_DP[i], IDX_DY[i]):
                opti.subject_to(opti.bounded(-lm.gimbal_max / Sx[j], Xv[j, k],
                                              lm.gimbal_max / Sx[j]))

    # control bounds  (commanded values)
    for k in range(cfg.N):
        for i in range(lm.n_eng):
            jt = IDX_U_T[i]
            opti.subject_to(opti.bounded(lm.T_min_eng / Su[jt], Uv[jt, k],
                                         lm.T_max_eng / Su[jt]))
            for j in (IDX_U_DP[i], IDX_U_DY[i]):
                opti.subject_to(opti.bounded(-lm.gimbal_max / Su[j], Uv[j, k],
                                              lm.gimbal_max / Su[j]))
        # each RCS thruster fires one way only: 0 <= f_i <= F_rcs_per
        for j in range(N_U_DPS, N_U_DPS + lm.n_rcs):
            opti.subject_to(opti.bounded(0.0, Uv[j, k], lm.F_rcs_per / Su[j]))

    # cost  (thruster commands are penalised toward 0 -> minimum-fuel RCS use)
    u_ref = ca.vertcat(*([lm.T_hover_eng, 0, 0] * lm.n_eng), *([0] * lm.n_rcs))
    cost = 0.0
    for k in range(cfg.N):
        dx = xs[k] - x_targ
        du = us[k] - u_ref
        cost += ca.dot(Qs * dx, dx) + ca.dot(cfg.Rw * du, du)
        # control-rate penalty: punish rapidly changing actuator commands
        if k > 0:
            dU = us[k] - us[k-1]
            cost += ca.dot(cfg.Rd * dU, dU)
    dxN = xs[cfg.N] - x_targ
    cost += ca.dot(Qf * dxN, dxN)
    opti.minimize(cost)

    # warm start (built densely in physical units, then scaled in one shot)
    lam = np.linspace(0.0, 1.0, cfg.N + 1)
    X_init = x0[:, None] + (x_targ - x0)[:, None] * lam[None, :]
    # hold actuator warm-start at their initial values (don't ramp T -> 0)
    X_init[IDX_T, :] = lm.T_hover_eng
    X_init[IDX_DP + IDX_DPD + IDX_DY + IDX_DYD, :] = 0.0
    U_init = np.zeros((nu, cfg.N))
    U_init[IDX_U_T, :] = lm.T_hover_eng
    opti.set_initial(Xv, X_init / Sx[:, None])
    opti.set_initial(Uv, U_init / Su[:, None])

    # solve  (exact Hessian: costlier per iteration but converges in far fewer
    #  iterations — limited-memory L-BFGS failed to converge on this large NLP)
    #
    # 'expand' rewrites the MX problem graph as SX: cost, constraints and their
    # derivatives then evaluate ~2x faster (measured), all ops here being
    # SX-compatible, for a slightly longer one-time build.
    #
    # The bulk of the solve time is IPOPT's KKT factorisation (MUMPS) times the
    # iteration count, so both factors are attacked above: variable/constraint
    # scaling cuts the iterations (1803 -> 85, measured at N=80), and
    # 'detect_simple_bounds' shrinks each factorisation. Together: ~690 s -> 34 s
    # for a solution within 0.03% of the unscaled one's cost.
    #
    # With iterations that cheap, tol can stay tight: 1e-6 costs one extra
    # iteration over 1e-4 here. The 'acceptable' criteria remain only as a
    # fallback so a hard scenario stops at a good feasible point rather than
    # grinding to max_iter.
    # 'detect_simple_bounds' recognises the ~2.6k box constraints above as
    # plain variable bounds and moves them from g into lbx/ubx. IPOPT then
    # handles them in the barrier term instead of carrying 2.6k extra rows
    # through every MUMPS factorisation — the single biggest per-iteration win.
    opts = {'expand': True, 'detect_simple_bounds': True,
            'ipopt.max_iter': 5000, 'ipopt.tol': 1e-6,
            'ipopt.acceptable_tol': 1e-4, 'ipopt.acceptable_iter': 15,
            'ipopt.mu_strategy': 'adaptive',
            'ipopt.print_level': 3, 'print_time': True}
    opti.solver('ipopt', opts)

    print("=" * 60)
    print("  Apollo LM  —  One-Shot Motion-Planning OCP")
    print("=" * 60)
    sol = opti.solve()
    print("\n>>> IPOPT converged <<<\n")

    # back to physical units
    return sol.value(Xv) * Sx[:, None], sol.value(Uv) * Su[:, None]


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
    x[IDX_ACT_ALL] = 0.0            # hard cut-off of every engine, gimbals zeroed
    u0 = np.zeros(N_U_DPS + lm.n_rcs)                 # no DPS command, no RCS

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
    per_eng = "  +  ".join(f"E{i+1} {contact[j]:.0f} N"
                           for i, j in enumerate(IDX_T))
    print(f"  Thrust at cut-off = {contact[IDX_T].sum():.0f} N  ->  0 N"
          f"   ({per_eng})")
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

    f_rcs  = Us[N_U_DPS:N_U_DPS + lm.n_rcs, :]   # (16, N) thruster firings
    wrench = lm.rcs_geometry()[2] @ f_rcs        # (6, N): Fx,Fy,Fz,L,M,N

    # one row per TVC engine (T, dp, dy commands), then the net RCS wrench
    labels, data, lo, hi = [], [], [], []
    for i in range(lm.n_eng):
        labels += [f'E{i+1} thrust cmd $T_c$ [N]',
                   rf'E{i+1} gimbal cmd $\delta_{{p,c}}$ [°]',
                   rf'E{i+1} gimbal cmd $\delta_{{y,c}}$ [°]']
        data   += [Us[IDX_U_T[i]], np.rad2deg(Us[IDX_U_DP[i]]),
                   np.rad2deg(Us[IDX_U_DY[i]])]
        lo     += [lm.T_min_eng, -gd, -gd]
        hi     += [lm.T_max_eng,  gd,  gd]
    # only T and the gimbals have simple box limits; the RCS wrench set is
    # a coupled zonotope (image of B), so no axis-aligned bound line is drawn.
    labels += ['RCS $F_x$ [N]','RCS $F_y$ [N]','RCS $F_z$ [N]',
               'RCS $L$ [N·m]','RCS $M$ [N·m]','RCS $N$ [N·m]']
    data   += [wrench[j] for j in range(6)]
    lo     += [None] * 6
    hi     += [None] * 6

    nrow = lm.n_eng + 2
    fig, axes = plt.subplots(nrow, 3, figsize=(16, 3.7 * nrow))
    fig.suptitle('Apollo LM — Control Histories '
                 f'({lm.n_eng} TVC engines + net RCS wrench)',
                 fontsize=14, weight='bold')
    for i, ax in enumerate(axes.flat):
        ax.step(t, data[i], 'b-', lw=1.3, where='post')
        if hi[i] is not None: ax.axhline(hi[i], ls='--', c='r', alpha=0.5)
        if lo[i] is not None: ax.axhline(lo[i], ls='--', c='r', alpha=0.5)
        ax.set_ylabel(labels[i]); ax.grid(True, alpha=0.3)
        if i >= 3 * (nrow - 1): ax.set_xlabel('Time [s]')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(save_path, dpi=150); print(f'[saved] {save_path}')


def plot_actuators(Xs, Us, cfg, lm, save_path='actuators.png'):
    """TVC actuator dynamics — commanded (control) vs actual (state) for the
    thrust (1st-order lag) and the two gimbal angles (2nd-order), one row per
    engine, plus a summary row comparing the engines against each other."""
    t  = np.arange(Xs.shape[1]) * cfg.dt
    tu = np.arange(Us.shape[1]) * cfg.dt
    gd = np.rad2deg(lm.gimbal_max)
    r2d = np.rad2deg(1)

    nrow = lm.n_eng + 1
    fig, axes = plt.subplots(nrow, 3, figsize=(16, 4.6 * nrow), squeeze=False)
    fig.suptitle(f'Apollo LM — TVC Actuator Dynamics, {lm.n_eng} engines '
                 '(command vs actual)', fontsize=14, weight='bold')

    for i in range(lm.n_eng):
        y_i = lm.eng_pos(i)[1]
        specs = [  # (actual state row, cmd control row, label, scale, ylimit)
            (IDX_T[i],  IDX_U_T[i],  f'E{i+1} thrust $T$ [N]', 1.0,
             (lm.T_min_eng, lm.T_max_eng)),
            (IDX_DP[i], IDX_U_DP[i], rf'E{i+1} gimbal $\delta_p$ [°]', r2d,
             (-gd, gd)),
            (IDX_DY[i], IDX_U_DY[i], rf'E{i+1} gimbal $\delta_y$ [°]', r2d,
             (-gd, gd)),
        ]
        for ax, (sx, cu, lbl, sc_, (lo, hi)) in zip(axes[i], specs):
            ax.step(tu, Us[cu] * sc_, 'r--', lw=1.3, where='post',
                    label='commanded')
            ax.plot(t,  Xs[sx] * sc_, 'b-',  lw=1.8, label='actual')
            ax.axhline(hi, ls=':', c='gray', alpha=0.7)
            ax.axhline(lo, ls=':', c='gray', alpha=0.7)
            ax.set_ylabel(lbl); ax.set_xlabel('Time [s]')
            ax.grid(True, alpha=0.3); ax.legend(fontsize=9, title=f'$y_B$={y_i:+.2f} m',
                                                title_fontsize=8)

    # summary row: engines overlaid, plus the differential that drives roll
    ax = axes[-1][0]
    for i in range(lm.n_eng):
        ax.plot(t, Xs[IDX_T[i]], lw=1.6, label=f'E{i+1}')
    ax.plot(t, Xs[IDX_T].sum(axis=0), 'k-', lw=1.8, label='total')
    ax.axhline(lm.T_max, ls=':', c='gray', alpha=0.7)
    ax.axhline(lm.T_min, ls=':', c='gray', alpha=0.7)
    ax.set_ylabel('Thrust $T$ [N]'); ax.set_xlabel('Time [s]')
    ax.grid(True, alpha=0.3); ax.legend(fontsize=9)

    ax = axes[-1][1]
    dT = Xs[IDX_T[1]] - Xs[IDX_T[0]] if lm.n_eng > 1 else np.zeros_like(t)
    ax.plot(t, dT, 'm-', lw=1.6)
    ax.axhline(0.0, ls=':', c='gray', alpha=0.7)
    ax.set_ylabel(r'Differential thrust $T_2-T_1$ [N]')
    ax.set_xlabel('Time [s]'); ax.grid(True, alpha=0.3)

    ax = axes[-1][2]
    # roll moment produced purely by throttling asymmetry: sum_i y_i * Tz_i
    L_diff = sum(lm.eng_pos(i)[1] *
                 (-Xs[IDX_T[i]] * np.cos(Xs[IDX_DP[i]]) * np.cos(Xs[IDX_DY[i]]))
                 for i in range(lm.n_eng))
    ax.plot(t, L_diff, 'g-', lw=1.6)
    ax.axhline(0.0, ls=':', c='gray', alpha=0.7)
    ax.set_ylabel('TVC roll moment $L$ [N·m]')
    ax.set_xlabel('Time [s]'); ax.grid(True, alpha=0.3)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(save_path, dpi=150); print(f'[saved] {save_path}')


def plot_thrusters(Us, cfg, lm, save_path='thrusters.png'):
    """The 16 individual RCS thruster firings f_i in [0, F_rcs_per]."""
    t = np.arange(Us.shape[1]) * cfg.dt
    f = Us[N_U_DPS:N_U_DPS + lm.n_rcs, :]

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


def plot_trajectory_with_axes(Xs, sc, cfg=None, save_path='trajectory_with_axes.png'):
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

    # glide-slope cone the descent is constrained to stay inside
    if cfg is not None:
        # clip the cone to the trajectory's own horizontal extent — drawn in
        # full it reaches r = h/tan(30 deg) = 1.7 km at the start altitude and
        # would flatten the descent to a vertical line on the plot
        r_max = 1.10 * np.hypot(Xs[0], Xs[1]).max()
        h_max = min(alt.max(), r_max * np.tan(cfg.glide_slope))
        th = np.linspace(0, 2*np.pi, 60)
        hh = np.linspace(0, h_max, 2)
        TH, HH = np.meshgrid(th, hh)
        RR = HH / np.tan(cfg.glide_slope)          # cone radius at each altitude
        ax.plot_surface(RR*np.cos(TH), RR*np.sin(TH), HH,
                        alpha=0.07, color='orange', shade=False)
        ax.plot_wireframe(RR*np.cos(TH), RR*np.sin(TH), HH,
                          rstride=1, cstride=10, color='orange',
                          alpha=0.25, linewidth=0.6)

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

    handles = ([Line2D([0],[0], color='orange', lw=2, alpha=0.6,
                      label=f'Glide slope {np.rad2deg(cfg.glide_slope):.0f}°')]
               if cfg is not None else []) + [
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
    plot_trajectory_with_axes(np.hstack([Xs, Xff]), sc, cfg)

    print("\nAll done.")