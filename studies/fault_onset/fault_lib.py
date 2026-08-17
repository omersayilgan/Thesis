"""
Fault-Onset & Initial-Condition Study — core library
════════════════════════════════════════════════════
The three existing case studies all assume the fault is *known from t = 0*:
they answer "how well can a known-degraded vehicle be flown?".  This module
answers the other question — "what happens when a healthy vehicle breaks
mid-descent?" — over a *continuous* (infinite) parameter space:

    fault onset time  t_f  in [0, t_land_nom]      (continuous)
    fault severity    eta  in [0, 1]               (continuous)
    initial condition x0   in a 12-D box           (continuous)

Since only a finite number of NLP solves is affordable (~20 s each), the space
is *estimated*, not enumerated: quasi-random (Sobol) sampling for coverage,
bisection for the boundary, and a surrogate classifier for the volume estimate.

Fault-response protocol (one sample)
────────────────────────────────────
  1. NOMINAL PLAN   solve the healthy OCP from x0  ->  (X_nom, U_nom).
                    If that fails, the IC itself is infeasible — no fault
                    question to ask.
  2. FLY TO t_f     replay U_nom on the healthy dynamics from the nearest grid
                    node up to the exact (off-grid) onset time t_f.
  3. FAULT + DELAY  the fault engages; the vehicle keeps flying the *stale*
                    nominal command for a reaction delay tau_d, now on the
                    faulted dynamics.  This is where a late fault hurts: nobody
                    is compensating yet.
  4. ENVELOPE CHECK if the delay drives the state outside the flight envelope
                    (rate/attitude/velocity limits), the vehicle is lost before
                    any replan can help — recorded without spending a solve.
  5. REPLAN         re-solve the OCP from the post-delay state with the degraded
                    vehicle, over the time remaining to the fixed 80 s deadline.
  6. TOUCHDOWN GATE cut the engine at contact, settle ballistically, and score
                    the touchdown state against the landing gate.

Every stage can fail, and the failure mode is recorded — that distinction is
the point of the study.
"""

import os
import sys
import time
import contextlib
import io

import numpy as np
import casadi as ca

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'src', 'apollo_gnc'))  # shared engine

import apollo_full as af
from apollo_full import (N_RIGID, N_ACT, N_U_DPS, N_ENG,
                         IDX_T, IDX_DP, IDX_DPD, IDX_DY, IDX_DYD, IDX_ACT_ALL,
                         IDX_U_T, IDX_U_DP, IDX_U_DY)


# ══════════════════════════════════════════════════════════════════════
#  1. LANDING GATE
# ══════════════════════════════════════════════════════════════════════
#  Scored on the *touchdown* state (after the engine-off ballistic settle),
#  not on the powered terminal state.  Thresholds are the Apollo LM landing-
#  gear / abort-criteria envelope, rounded:
#      vertical touchdown speed   <= 3.0 m/s   (gear stroke design case)
#      horizontal touchdown speed <= 1.2 m/s   (tip-over on a 1:6 slope)
#      tilt from vertical         <= 6 deg
#      distance from pad          <= 15 m
#      body rates                 <= 5 deg/s
# ══════════════════════════════════════════════════════════════════════

GATE = dict(v_vert=3.0, v_horiz=1.2, tilt_deg=6.0, pos_err=15.0, rate_deg=5.0)


def touchdown_metrics(x_td):
    """Scalar metrics of a touchdown state (12- or 22-vector)."""
    return dict(
        v_vert  = abs(float(x_td[5])),
        v_horiz = float(np.hypot(x_td[3], x_td[4])),
        tilt_deg= float(np.rad2deg(np.hypot(x_td[6], x_td[7]))),
        pos_err = float(np.hypot(x_td[0], x_td[1])),
        rate_deg= float(np.rad2deg(np.linalg.norm(x_td[9:12]))),
    )


def gate_margin(m):
    """Worst-case normalised gate margin.  <= 1 means every criterion is met;
    the value is how far the *binding* criterion is from its limit, so it is a
    continuous severity measure rather than a bare pass/fail bit."""
    return max(m[k] / GATE[k] for k in GATE)


def lands(m):
    return gate_margin(m) <= 1.0


# ══════════════════════════════════════════════════════════════════════
#  2. HARD LOSS OF CONTROL
# ══════════════════════════════════════════════════════════════════════
#  Deliberately *not* the OCP's path constraints.  omega_max = 10 deg/s and
#  euler_max = 45 deg are planner comfort limits; exceeding them mid-transient
#  is not the same as losing the vehicle.  The criteria below are the ones a
#  vehicle genuinely does not come back from, and everything short of them is
#  handed to the replan (through the recovery corridor, section 4) so that the
#  optimiser — not an arbitrary threshold — decides whether recovery exists.
# ══════════════════════════════════════════════════════════════════════

LOSS = dict(tilt_deg=90.0,        # past horizontal: thrust no longer decelerates
            rate_deg=120.0,       # tumbling far beyond any RCS de-spin authority
            v_axis_factor=1.5)    # per-axis speed, as a multiple of cfg.V_max
                                  # (the nominal descent already rides V_max on
                                  #  every axis, so an absolute norm would flag
                                  #  a perfectly healthy trajectory)


def hard_loss(x, cfg):
    """(name, value) of the worst hard-loss criterion, or None if survivable."""
    x = np.asarray(x, float)
    if not np.all(np.isfinite(x)):
        return ('divergence', np.inf)
    checks = [
        ('tilt',   np.rad2deg(np.hypot(x[6], x[7])) / LOSS['tilt_deg']),
        ('tumble', np.rad2deg(np.abs(x[9:12]).max()) / LOSS['rate_deg']),
        ('speed',  float(np.abs(x[3:6]).max())
                   / (LOSS['v_axis_factor'] * cfg.V_max)),
        ('impact', cfg.h_contact / max(-float(x[2]), 1e-9)),
    ]
    name, val = max(checks, key=lambda c: c[1])
    return (name, float(val)) if val > 1.0 else None


# ══════════════════════════════════════════════════════════════════════
#  3. FAULT DEFINITION
# ══════════════════════════════════════════════════════════════════════

class Fault:
    """A single-engine fault that engages at t_f.

    kind='efficiency' : engine `eng` delivers only eta * T from t_f onward.
                        eta = 0 is a thrust loss with the gimbal still alive.
    kind='engine_out' : engine `eng` is completely dead from t_f — thrust and
                        both gimbals pinned to zero (the Study-A fault, but now
                        arriving mid-flight).
    """

    def __init__(self, kind='efficiency', eng=1, eta=0.0, t_f=0.0, tau_d=1.0):
        self.kind, self.eng, self.eta, self.t_f, self.tau_d = \
            kind, eng, float(eta), float(t_f), float(tau_d)

    def apply(self, lm):
        """Return a copy of lm with the fault active."""
        import copy
        f = copy.deepcopy(lm)
        f._B_rcs_cached = None
        if self.kind == 'efficiency':
            f.thrust_eff_eng = dict(f.thrust_eff_eng)
            f.thrust_eff_eng[self.eng] = self.eta
        return f

    @property
    def failed(self):
        return (self.eng,) if self.kind == 'engine_out' else ()

    def __repr__(self):
        s = f'{self.kind}(E{self.eng + 1}'
        if self.kind == 'efficiency':
            s += f', eta={self.eta:.3f}'
        return s + f') @ t_f={self.t_f:.2f}s, tau_d={self.tau_d:.2f}s'


# ══════════════════════════════════════════════════════════════════════
#  4. OCP SOLVER  (generalised from apollo_full.solve_landing)
# ══════════════════════════════════════════════════════════════════════
#  Differences from the original:
#    * takes a full 22-state initial condition (the post-fault state), not a
#      12-state scenario with actuators re-trimmed from scratch;
#    * takes an explicit horizon N (the time left to the mission deadline);
#    * path bounds are imposed from k = 1, since k = 0 is pinned to a *given*
#      state that the vehicle already occupies — bounding it would make an
#      already-degraded state an NLP infeasibility rather than a flight result;
#    * a RECOVERY CORRIDOR: if the post-fault state already sits outside the
#      attitude/rate envelope, the bound at node k is relaxed to the initial
#      excursion and tightened linearly back to the nominal envelope over
#      n_relax steps.  The planner is therefore required to *monotonically*
#      recover into the envelope within n_relax seconds — which is a real
#      requirement, not a free pass — instead of being handed an NLP that is
#      infeasible at k = 1 purely because a 1 s grid cannot undo a transient;
#    * silent, and returns a status instead of raising.
# ══════════════════════════════════════════════════════════════════════

#  Transient allowances, as multiples of the corresponding OCP path bound.
#  These are not slack for its own sake.  The reference descent saturates
#  V_max and *all three* body-rate channels simultaneously, so a corridor that
#  only relaxed to the state's existing excursion would forbid the recovery any
#  rate excursion at all — and would then report "infeasible" for every fault,
#  however mild, because the planner is not allowed to trade a two-second rate
#  transient for a recovered trajectory.  A real vehicle would take that trade;
#  omega_max = 10 deg/s is a planner comfort limit, not a structural one.  The
#  allowances stay far inside the hard-loss thresholds of section 2.
ALLOW = dict(rate=3.0,        # 30 deg/s transient vs a 120 deg/s tumble limit
             attitude=1.35,   # 61 deg tilt vs the 90 deg hard limit
             velocity=1.2)    # 72 m/s vs the 90 m/s hard limit


def _corridor(x0_val, nom_bound, k, n_relax, allow=1.0):
    """Bound on |state| at node k.

    Starts at the larger of the initial excursion and `allow` x the nominal
    bound, then shrinks linearly to the nominal envelope at k = n_relax.  The
    planner is therefore required to be back inside the design envelope within
    n_relax seconds of the fault — a demand, not a dispensation.
    """
    if n_relax <= 0:
        return nom_bound
    start = max(x0_val, allow * nom_bound)
    if k >= n_relax or start <= nom_bound:
        return nom_bound
    lam = k / n_relax
    return start + lam * (nom_bound - start)


def delayed_controls(us, x0, lm, nu):
    """Per-node effective control, honouring per-engine transport delay.

    A dead time of d control intervals means engine i at node k responds to the
    command issued at node k-d (framework §2.6).  On a zero-order-hold grid that
    shift is *exact*, not a Pade approximation — the price is that the delay can
    only be a whole number of intervals.

    For k < d the pipe is primed with the engine's own initial actuator state:
    whatever it is currently holding is, by definition, what was last commanded
    to it.  Returns a function k -> control vector; with no delayed engine it is
    just `us[k]`, and the graph is unchanged.
    """
    delays = {i: lm.u_delay_of(i) for i in range(lm.n_eng)
              if lm.u_delay_of(i) > 0}
    if not delays:
        return lambda k: us[k]

    prime = {}
    for i, d in delays.items():
        prime[IDX_U_T[i]]  = float(x0[IDX_T[i]])
        prime[IDX_U_DP[i]] = float(x0[IDX_DP[i]])
        prime[IDX_U_DY[i]] = float(x0[IDX_DY[i]])

    def u_at(k):
        rows = [us[k][j] for j in range(nu)]
        for i, d in delays.items():
            for j in (IDX_U_T[i], IDX_U_DP[i], IDX_U_DY[i]):
                rows[j] = us[k - d][j] if k - d >= 0 else prime[j]
        return ca.vertcat(*rows)

    return u_at


def substep(x, u, dt, lm, n_sub, step, t=0.0):
    """Integrate one control interval with n_sub RK4 sub-steps.

    The control grid and the decision variables are unchanged — only the
    accuracy of each defect constraint improves.  This matters because the
    gimbal actuator is a second-order mode at wn = 4 rad/s, and on the 1 s
    control grid wn*dt = 4.0 sits **beyond RK4's stability limit** (~2.79 for
    an oscillatory eigenvalue).  A single RK4 step per interval therefore
    amplifies that mode instead of damping it.

    It went unnoticed in every earlier study because they all start the gimbal
    rate states at zero and the optimiser has no reason to excite them hard.
    Study F samples those states directly, which is exactly the condition that
    makes an unstable discretisation visible: with the gimbal rates zeroed the
    same problems solve, and with them sampled they do not.  Four sub-steps put
    wn*dt_sub = 1.0 comfortably inside the stability region.
    """
    h = dt / n_sub
    for j in range(n_sub):
        x = step(x, u, h, lm, t + j * h)
    return x


def solve_ocp(lm, cfg, x0_aug, N, failed=(), max_iter=300, quiet=True,
              n_relax=0, n_cone=1, warm=None, relax=(), n_sub=1):
    nx, nu = N_RIGID + N_ACT, N_U_DPS + lm.n_rcs
    failed = tuple(failed)
    n_live = lm.n_eng - len(failed)
    if n_live < 1:
        return dict(status='no_engines', X=None, U=None, J=np.nan, iters=0)

    T_trim = lm.T_hover / n_live

    def live_T(i):
        """Trim thrust *command* for engine i.  A partially efficient engine
        must be commanded 1/eta higher to deliver its share, capped at its own
        limit.  At eta = 0 the engine delivers nothing however hard it is
        commanded, so the cap is the only sensible value (and 1/eta is not)."""
        if i in failed:
            return 0.0
        eta = lm.eta_of(i)
        if eta <= 1e-9:
            return lm.T_max_eng
        return min(lm.T_max_eng, T_trim / eta)

    x0 = np.asarray(x0_aug, float).copy()
    for i in failed:                       # a dead engine holds nothing
        x0[[IDX_T[i], IDX_DP[i], IDX_DPD[i], IDX_DY[i], IDX_DYD[i]]] = 0.0
    for i in range(lm.n_eng):
        # A seized gimbal is frozen, not coasting: the seizure arrests the
        # motion, so the rate states are zero from the fault onward and the
        # deflection stays exactly where it was caught.  Zeroing them here
        # rather than damping them in the dynamics keeps the freeze exact and
        # keeps the integrator stable (see flat_moon_6dof).
        if lm.gimbal_locked(i):
            x0[[IDX_DPD[i], IDX_DYD[i]]] = 0.0

    x_targ = np.zeros(nx)
    x_targ[2] = -cfg.h_contact
    Qs = np.concatenate([cfg.Qs, np.zeros(N_ACT)])
    Qf = np.concatenate([cfg.Qf, np.zeros(N_ACT)])

    Sx, Su = af.nlp_scales(lm, cfg)
    Sx_dm, Su_dm = ca.DM(Sx), ca.DM(Su)

    opti = ca.Opti()
    Xv = opti.variable(nx, N + 1)
    Uv = opti.variable(nu, N)
    xs = [Sx_dm * Xv[:, k] for k in range(N + 1)]
    us = [Su_dm * Uv[:, k] for k in range(N)]

    opti.subject_to(Xv[:, 0] == x0 / Sx)

    step = af.INTEGRATORS[cfg.integrator]
    # `u_at` folds in any per-engine transport delay; `t_k` carries trajectory
    # time into the dynamics so time-varying faults (parametric drift, forced
    # oscillation) evolve along the horizon instead of being frozen at t = 0.
    # Both reduce to the identity on a healthy plant.
    u_at = delayed_controls(us, x0, lm, nu)
    for k in range(N):
        t_k = k * cfg.dt
        uk = u_at(k)
        xn = (step(xs[k], uk, cfg.dt, lm, t_k) if n_sub <= 1 else
              substep(xs[k], uk, cfg.dt, lm, n_sub, step, t_k))
        opti.subject_to(Xv[:, k+1] == xn / Sx_dm)

    tan2 = np.tan(cfg.glide_slope) ** 2
    if 'cone' not in relax:
        for k in range(max(n_cone, 1), N + 1):   # cone (skipped over transient)
            xk = xs[k] / Sx[2]
            opti.subject_to(tan2 * (xk[0]**2 + xk[1]**2) <= xk[2]**2)

    # Initial excursions the corridor has to shrink away.  Velocity is included
    # for a concrete reason: the nominal descent rides w = V_max exactly, so
    # *any* perturbation puts the post-fault state marginally outside the
    # velocity box and a hard bound at k = 1 would report "infeasible" for a
    # 0.001 m/s overshoot — a solver artefact, not a lost vehicle.
    v0 = float(np.abs(x0[3:6]).max())
    e0 = float(np.abs(x0[6:9]).max())
    w0 = float(np.abs(x0[9:12]).max())
    for k in range(1, N + 1):
        if 'alt' not in relax:
            opti.subject_to(Xv[2, k] <= -cfg.h_contact / Sx[2])
        vb = _corridor(v0, cfg.V_max, k, n_relax, ALLOW['velocity'])
        if 'vel' not in relax:
            for j in [3, 4, 5]:
                opti.subject_to(opti.bounded(-vb / Sx[j], Xv[j, k], vb / Sx[j]))
        eb = _corridor(e0, cfg.euler_max, k, n_relax, ALLOW['attitude'])
        if 'att' not in relax:
            for j in [6, 7, 8]:
                opti.subject_to(opti.bounded(-eb / Sx[j], Xv[j, k], eb / Sx[j]))
        wb = _corridor(w0, cfg.omega_max, k, n_relax, ALLOW['rate'])
        if 'rate' not in relax:
            for j in [9, 10, 11]:
                opti.subject_to(opti.bounded(-wb / Sx[j], Xv[j, k], wb / Sx[j]))
        for i in range(lm.n_eng):
            if i in failed:
                for j in (IDX_T[i], IDX_DP[i], IDX_DPD[i],
                          IDX_DY[i], IDX_DYD[i]):
                    opti.subject_to(Xv[j, k] == 0.0)
                continue
            jt = IDX_T[i]
            opti.subject_to(opti.bounded(lm.T_min_of(i) / Sx[jt], Xv[jt, k],
                                         lm.T_max_eng / Sx[jt]))
            for j in (IDX_DP[i], IDX_DY[i]):
                opti.subject_to(opti.bounded(-lm.gimbal_max / Sx[j], Xv[j, k],
                                              lm.gimbal_max / Sx[j]))

    for k in range(N):
        for i in range(lm.n_eng):
            if i in failed:
                for j in (IDX_U_T[i], IDX_U_DP[i], IDX_U_DY[i]):
                    opti.subject_to(Uv[j, k] == 0.0)
                continue
            jt = IDX_U_T[i]
            opti.subject_to(opti.bounded(lm.T_min_of(i) / Su[jt], Uv[jt, k],
                                         lm.T_max_eng / Su[jt]))
            for j in (IDX_U_DP[i], IDX_U_DY[i]):
                opti.subject_to(opti.bounded(-lm.gimbal_max / Su[j], Uv[j, k],
                                              lm.gimbal_max / Su[j]))
        for j in range(N_U_DPS, N_U_DPS + lm.n_rcs):
            opti.subject_to(opti.bounded(0.0, Uv[j, k], lm.F_rcs_per / Su[j]))

    u_ref = ca.vertcat(*[v for i in range(lm.n_eng)
                           for v in (live_T(i), 0, 0)], *([0] * lm.n_rcs))
    cost = 0.0
    for k in range(N):
        dx = xs[k] - x_targ
        du = us[k] - u_ref
        cost += ca.dot(Qs * dx, dx) + ca.dot(cfg.Rw * du, du)
        if k > 0:
            dU = us[k] - us[k-1]
            cost += ca.dot(cfg.Rd * dU, dU)
    dxN = xs[N] - x_targ
    cost += ca.dot(Qf * dxN, dxN)
    opti.minimize(cost)

    if warm is not None:
        # Seed the replan with the *nominal* trajectory over the same window.
        # A recovery is a perturbation of the descent it interrupts, so this is
        # a far better guess than a straight line from x0 to the pad, and it is
        # what makes a campaign of several hundred solves affordable at all.
        X_init, U_init = np.array(warm[0], float), np.array(warm[1], float)
        X_init[:, 0] = x0
        for i in failed:
            X_init[[IDX_T[i], IDX_DP[i], IDX_DPD[i],
                    IDX_DY[i], IDX_DYD[i]], :] = 0.0
            U_init[[IDX_U_T[i], IDX_U_DP[i], IDX_U_DY[i]], :] = 0.0
    else:
        lam = np.linspace(0.0, 1.0, N + 1)
        X_init = x0[:, None] + (x_targ - x0)[:, None] * lam[None, :]
        for i in range(lm.n_eng):
            X_init[IDX_T[i], :] = live_T(i)
        X_init[IDX_DP + IDX_DPD + IDX_DY + IDX_DYD, :] = 0.0
        U_init = np.zeros((nu, N))
        for i in range(lm.n_eng):
            U_init[IDX_U_T[i], :] = live_T(i)
    opti.set_initial(Xv, X_init / Sx[:, None])
    opti.set_initial(Uv, U_init / Su[:, None])

    opts = {'expand': True, 'detect_simple_bounds': True,
            'ipopt.max_iter': max_iter, 'ipopt.tol': 1e-6,
            'ipopt.acceptable_tol': 1e-4, 'ipopt.acceptable_iter': 15,
            'ipopt.mu_strategy': 'adaptive',
            'ipopt.print_level': 0 if quiet else 3, 'print_time': not quiet}
    opti.solver('ipopt', opts)

    t0 = time.time()
    sink = io.StringIO()
    try:
        with (contextlib.redirect_stdout(sink) if quiet
              else contextlib.nullcontext()):
            sol = opti.solve()
        X, U, ok = sol.value(Xv) * Sx[:, None], sol.value(Uv) * Su[:, None], True
        J = float(sol.value(cost))
        status = 'solved'
    except RuntimeError:
        dbg = opti.debug
        try:
            X, U = dbg.value(Xv) * Sx[:, None], dbg.value(Uv) * Su[:, None]
            J = float(dbg.value(cost))
        except Exception:
            X = U = None
            J = np.nan
        ok = False
        status = 'infeasible'
    st = opti.stats()
    # keep IPOPT's own verdict: 'Infeasible_Problem_Detected' means the solver
    # *proved* local infeasibility, whereas 'Maximum_Iterations_Exceeded' means
    # it merely ran out of budget.  Conflating the two would turn an iteration
    # cap into a physics result, so the distinction is carried through to the
    # campaign CSVs and audited afterwards.
    return dict(status=status, X=X, U=U, J=J, ok=ok, N=N,
                wall=time.time() - t0,
                ipopt_status=str(st.get('return_status', '?')),
                iters=int(st.get('iter_count', -1)))


# ══════════════════════════════════════════════════════════════════════
#  5. PROPAGATION HELPERS
# ══════════════════════════════════════════════════════════════════════

def propagate(x, u, T, lm, dt=0.02, t0=0.0):
    """Integrate the 22-state forward by T seconds holding u (zero-order hold).

    t0 is the trajectory time at the start of the interval, which only matters
    for time-varying faults; it defaults to 0 so every existing call site is
    unchanged."""
    x = np.asarray(x, float).copy()
    u = ca.DM(np.asarray(u, float))
    n = max(int(round(T / dt)), 0)
    h = T / n if n else 0.0
    for j in range(n):
        x = np.array(af.rk4_step(ca.DM(x), u, h, lm, t0 + j * h)).ravel()
        if not np.all(np.isfinite(x)):
            break
    return x


def state_at(X_nom, U_nom, t, cfg, lm):
    """Nominal state at an arbitrary (off-grid) time t, obtained by re-integrating
    from the grid node below t — so the continuous onset axis is genuinely
    continuous, not snapped to the 1 s control grid."""
    k = int(np.floor(t / cfg.dt))
    k = min(max(k, 0), U_nom.shape[1] - 1)
    frac = t - k * cfg.dt
    if frac <= 1e-9:
        return X_nom[:, k].copy()
    return propagate(X_nom[:, k], U_nom[:, k], frac, lm)


def contact_time(X_nom, cfg, h_tol=0.05):
    """First time the nominal plan reaches the contact altitude."""
    alt = -X_nom[2, :]
    below = np.where(alt <= cfg.h_contact + h_tol)[0]
    return float(below[0] * cfg.dt) if below.size else float(X_nom.shape[1] - 1) * cfg.dt


def nominal_warm(X_nom, U_nom, t_start, N, dt):
    """The nominal trajectory resampled onto the replan's grid, used as the
    replan's initial guess.  Past the end of the nominal record the last node is
    held (the nominal is hovering at contact altitude there anyway)."""
    ks = np.round((t_start + np.arange(N + 1) * dt) / dt).astype(int)
    ku = np.round((t_start + np.arange(N) * dt) / dt).astype(int)
    Xw = X_nom[:, np.clip(ks, 0, X_nom.shape[1] - 1)].copy()
    Uw = U_nom[:, np.clip(ku, 0, U_nom.shape[1] - 1)].copy()
    return Xw, Uw


def augment_x0(x12, lm, failed=()):
    """12-state scenario -> 22-state with engines trimmed at hover share."""
    n_live = lm.n_eng - len(failed)
    T_trim = lm.T_hover / max(n_live, 1)
    act = []
    for i in range(lm.n_eng):
        Ti = 0.0 if i in failed else min(lm.T_max_eng, T_trim / lm.eta_of(i))
        act += [Ti, 0.0, 0.0, 0.0, 0.0]
    return np.concatenate([np.asarray(x12, float), np.array(act)])


# ══════════════════════════════════════════════════════════════════════
#  6. THE FAULT-RESPONSE EXPERIMENT
# ══════════════════════════════════════════════════════════════════════

def run_nominal(x12, lm, cfg, max_iter=300):
    """Stage 1: healthy plan from x0.  Returns the solve dict plus touchdown."""
    res = solve_ocp(lm, cfg, augment_x0(x12, lm), cfg.N, max_iter=max_iter)
    if res['ok']:
        Xff, tff = af.cutoff_freefall(res['X'][:, -1], lm)
        res['x_td'] = Xff[:, -1]
        res['metrics'] = touchdown_metrics(Xff[:, -1])
        res['margin'] = gate_margin(res['metrics'])
        res['lands'] = res['margin'] <= 1.0
        res['t_contact'] = contact_time(res['X'], cfg)
    else:
        res.update(x_td=None, metrics=None, margin=np.inf, lands=False,
                   t_contact=np.nan)
    return res


# Extra time the replan is granted beyond the nominal's own remaining descent
# time.  The replan is NOT simply given every second up to the mission
# deadline: doing so forces it to hover on the h_contact floor for the whole
# unused tail (~50 s on this reference), which is a pathological arc to ask a
# 1 s RK4 grid to hold exactly on a constraint boundary, and it was observed to
# turn otherwise-recoverable faults infeasible.  The vehicle must instead land
# within the nominal's remaining time plus this reserve — a real deadline, and
# one that is still capped by the 80 s mission limit.
T_RESERVE = 20.0


def run_fault(fault, X_nom, U_nom, lm, cfg, max_iter=300, T_deadline=None,
              n_relax=6, t_contact_nom=None):
    """Stages 2-6: inject `fault` into a nominal descent and try to recover.

    Returns a record whose 'outcome' is one of
        'land'              recovered and met the touchdown gate
        'gate_miss'         replan converged but the touchdown is out of gate
        'no_replan'         replan did not converge — no recovery trajectory exists
        'lost_in_delay'     hard loss of control before any replan could act
        'no_time'           fault so late that no horizon is left
    """
    T_deadline = cfg.N * cfg.dt if T_deadline is None else T_deadline
    lm_f = fault.apply(lm)
    rec = dict(kind=fault.kind, eng=fault.eng, eta=fault.eta,
               t_f=fault.t_f, tau_d=fault.tau_d)

    # ── stage 2/3: fly to onset, then coast on the stale command ──────────
    x_f = state_at(X_nom, U_nom, fault.t_f, cfg, lm)
    k_f = min(int(np.floor(fault.t_f / cfg.dt)), U_nom.shape[1] - 1)
    u_stale = U_nom[:, k_f].copy()
    if fault.kind == 'engine_out':
        i = fault.eng
        x_f = x_f.copy()
        x_f[[IDX_T[i], IDX_DP[i], IDX_DPD[i], IDX_DY[i], IDX_DYD[i]]] = 0.0
        u_stale[[IDX_U_T[i], IDX_U_DP[i], IDX_U_DY[i]]] = 0.0
    x_d = propagate(x_f, u_stale, fault.tau_d, lm_f)

    rec['rate_after_delay_deg'] = float(np.rad2deg(np.abs(x_d[9:12]).max()))
    rec['tilt_after_delay_deg'] = float(np.rad2deg(np.hypot(x_d[6], x_d[7])))
    rec['alt_at_fault'] = float(-x_f[2])

    # ── stage 4: hard loss of control before anyone can react? ────────────
    viol = hard_loss(x_d, cfg)
    if viol is not None:
        rec.update(outcome='lost_in_delay', violation=viol[0],
                   violation_val=float(viol[1]), margin=np.inf,
                   iters=0, wall=0.0, J=np.nan, success=False)
        return rec
    rec['violation'] = None

    # ── stage 5: replan on the time that is left ──────────────────────────
    t_start = fault.t_f + fault.tau_d
    t_c = contact_time(X_nom, cfg) if t_contact_nom is None else t_contact_nom
    need = max(t_c - t_start, 0.0) + T_RESERVE
    N_rem = int(min(np.ceil(need / cfg.dt),
                    np.floor((T_deadline - t_start) / cfg.dt)))
    rec['N_rem'] = N_rem
    if N_rem < 10:
        rec.update(outcome='no_time', margin=np.inf, iters=0, wall=0.0,
                   J=np.nan, success=False)
        return rec

    # Two attempts from different initial guesses.  The NLP is nonconvex, so
    # IPOPT's 'Infeasible_Problem_Detected' proves infeasibility only *locally*,
    # from the guess it was given.  The null-fault control case (eta = 1, which
    # changes nothing about the vehicle) exposed this: it must reproduce the
    # nominal continuation, and occasionally did not from the nominal seed.
    # A failure is therefore only reported after a second attempt from an
    # independent guess — the straight-line ramp — has also failed.
    warm = nominal_warm(X_nom, U_nom, t_start, N_rem, cfg.dt)
    res = solve_ocp(lm_f, cfg, x_d, N_rem, failed=fault.failed,
                    max_iter=max_iter, n_relax=n_relax, n_cone=3, warm=warm)
    rec['attempts'] = 1
    if not res['ok']:
        res2 = solve_ocp(lm_f, cfg, x_d, N_rem, failed=fault.failed,
                         max_iter=max_iter, n_relax=n_relax, n_cone=3,
                         warm=None)
        rec['attempts'] = 2
        if res2['ok']:
            res = res2
        rec['retry_status'] = res2.get('ipopt_status', '')
    rec.update(iters=res['iters'], wall=res['wall'], J=res['J'],
               status=res['status'], ipopt_status=res.get('ipopt_status', ''))
    if not res['ok']:
        rec.update(outcome='no_replan', margin=np.inf, success=False)
        return rec

    # ── stage 6: cut, settle, score ───────────────────────────────────────
    Xff, tff = af.cutoff_freefall(res['X'][:, -1], lm_f)
    m = touchdown_metrics(Xff[:, -1])
    rec.update(m)
    rec['margin'] = gate_margin(m)
    rec['success'] = rec['margin'] <= 1.0
    rec['outcome'] = 'land' if rec['success'] else 'gate_miss'
    rec['t_contact_replan'] = t_start + contact_time(res['X'], cfg)
    return rec


# ══════════════════════════════════════════════════════════════════════
#  7. STATISTICS
# ══════════════════════════════════════════════════════════════════════

def wilson(k, n, z=1.96):
    """Wilson score interval for a binomial proportion — the right interval for
    a Monte-Carlo success rate at these sample sizes (Wald breaks near 0 and 1)."""
    if n == 0:
        return (0.0, 0.0, 1.0)
    p = k / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (p, max(c - h, 0.0), min(c + h, 1.0))


# ══════════════════════════════════════════════════════════════════════
#  8. THE RECOVERY PLANNER  (the algorithmic deliverable)
# ══════════════════════════════════════════════════════════════════════
#  Everything above is measurement apparatus.  This is the thing that would
#  actually fly: given *where the vehicle is now* and *what it has become*, it
#  returns a landing trajectory or an honest refusal.
#
#  It takes no nominal trajectory, no fault onset time, and no fault history.
#  That is deliberate and it is the whole point of the Study-F framing: the
#  post-fault problem is fully specified by
#
#        x  — the current 22-state (rigid body AND actuator states)
#        P  — the plant the vehicle now is (LMParams with the damage baked in)
#
#  and nothing else.  How the vehicle got to x is irrelevant to what it can do
#  from x; the Markov property of the dynamics guarantees it.  Two vehicles at
#  the same x with the same P have identical futures whether one arrived there
#  by a nominal descent plus an engine failure or the other simply started
#  there.
#
#  What canNOT be folded into x is P.  See the Study-F report: a damaged plant
#  is a different dynamical system for the whole remaining flight, not an
#  initial condition, and the two are not interchangeable.
# ══════════════════════════════════════════════════════════════════════

def horizon_for(x, cfg, t_extra=20.0, v_desc=25.0, lo=30, hi=70):
    """How many grid steps to give the planner, from the altitude it must lose.

    Without a nominal there is no "time already flown", so the horizon has to
    come from the state.  Too short is an artificial infeasibility; too long is
    worse — it forces the planner to hold the 1 m contact floor for the unused
    tail, which is a pathological arc on a 1 s grid and was observed to turn
    otherwise-feasible problems infeasible (Study D, Section 2.4).
    """
    alt = max(-float(x[2]), cfg.h_contact)
    return int(np.clip(round(alt / v_desc + t_extra), lo, hi))


def recover(x, plant, cfg, failed=(), max_iter=400, n_relax=6, retry=True,
            n_sub=2):
    """Plan a landing from state `x` for the (possibly damaged) vehicle `plant`.

    Returns a dict with 'lands' (bool), the touchdown metrics, and the
    trajectory.  A refusal is a result, not an error: 'no_recovery' means no
    landing trajectory was found from this state with this plant.
    """
    loss = hard_loss(x, cfg)
    if loss is not None:
        return dict(outcome='already_lost', lands=False, margin=np.inf,
                    violation=loss[0], iters=0, wall=0.0)

    N = horizon_for(x, cfg)
    res = solve_ocp(plant, cfg, x, N, failed=failed, max_iter=max_iter,
                    n_relax=n_relax, n_cone=3, n_sub=n_sub)
    if not res['ok'] and retry:
        # second seed: the straight-line ramp is the default warm start, so the
        # retry perturbs the horizon instead — a different discretisation of the
        # same problem, which is enough to escape a bad local corner.
        res2 = solve_ocp(plant, cfg, x, min(N + 8, 78), failed=failed,
                         max_iter=max_iter, n_relax=n_relax, n_cone=3,
                         n_sub=n_sub)
        if res2['ok']:
            res, N = res2, min(N + 8, 78)
    if not res['ok']:
        return dict(outcome='no_recovery', lands=False, margin=np.inf,
                    iters=res['iters'], wall=res['wall'], N=N)

    Xff, tff = cutoff_freefall_safe(res['X'][:, -1], plant)
    m = touchdown_metrics(Xff[:, -1])
    out = dict(outcome='land', margin=gate_margin(m), iters=res['iters'],
               wall=res['wall'], N=N, J=res['J'], X=res['X'], U=res['U'])
    out.update(m)
    out['lands'] = out['margin'] <= 1.0
    if not out['lands']:
        out['outcome'] = 'gate_miss'
    return out


def cutoff_freefall_safe(x_contact, lm, **kw):
    """cutoff_freefall that cannot raise on a divergent terminal state."""
    try:
        return af.cutoff_freefall(x_contact, lm, **kw)
    except Exception:
        x = np.asarray(x_contact, float).copy()
        return x[:, None], np.array([0.0])
