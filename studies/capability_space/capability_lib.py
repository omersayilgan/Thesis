"""
STUDY I — fault impacts in capability space
═══════════════════════════════════════════
The fault studies (G, H, H-R) ask whether a damaged vehicle can still fly a
trajectory.  This one asks the question underneath that: **what can the damaged
vehicle still push and twist with at all**, before any trajectory is planned.

THE OBJECTS
───────────
For an actuator set, two sets in R^3 and one in R^6:

    AFS   attainable force set    { net force  the actuators can produce }
    AMS   attainable moment set   { net moment the actuators can produce }
    AWS   attainable wrench set   the 6-D set the two are projections of

Each RCS thruster is a one-sided segment: throttle f in [0, F], contributing
f*d to the force and f*(r x d) to the moment.  Each gimballed engine sweeps a
spherical cap: thrust T in [T_min, T_max] along any d within `gimbal_max` of
its axis.  The sum of these pieces is what the vehicle can do instantaneously,
and its convex hull is what a support-function sweep recovers exactly.

WHY T_min MATTERS HERE AND NOWHERE ELSE
───────────────────────────────────────
Everywhere else in this repository an engine can be shut down, so its minimum
throttle does not shape the achievable set: 0 is always available and the hull
contains the origin.  A valve stuck open removes exactly that.  The engine's
contribution becomes the shell { T d : T in [T_min, T_max] } with T_min > 0,
whose hull does NOT contain the origin, and the vehicle loses the ability to
produce zero net wrench at all.  That is a qualitative change in the capability
set - a hole where the origin used to be - and it is invisible to any metric
that only reports volume or per-axis maxima.

WHAT A FAULT DOES TO THESE SETS
───────────────────────────────
Only some faults touch them at all, which is the study's first result:

    SHRINK    thrust loss, mixture-ratio shift, engine out - the set is a
              subset of the healthy one
    DEFORM    TVC misalignment rotates the engine's cap; thrust excess
              enlarges one engine's contribution asymmetrically, which BUYS
              force and COSTS trim symmetry
    PUNCTURE  valve stuck open - the origin leaves the set
    NOTHING   transport delay, slow thrust response - the static set is
              identical to healthy, and the fault lives entirely in time

The last class is the interesting one, because Study H found those faults to be
among the least survivable.  Capability space cannot see them, and any FTC
scheme that reasons only about attainable sets will not see them either.
"""

import numpy as np
from scipy.optimize import linprog
from scipy.spatial import ConvexHull


# ══════════════════════════════════════════════════════════════════════
#  1.  THE ACTUATOR MODEL A FAULT LEAVES BEHIND
# ══════════════════════════════════════════════════════════════════════

class Engine:
    """One gimballed engine, as capability space sees it."""

    def __init__(self, pos, axis, T_min, T_max, gimbal_max):
        self.pos = np.asarray(pos, float)
        self.axis = np.asarray(axis, float) / np.linalg.norm(axis)
        self.T_min, self.T_max = float(T_min), float(T_max)
        self.gimbal_max = float(gimbal_max)


class Model:
    """The actuator set of one (possibly damaged) vehicle."""

    def __init__(self, name, engines, rcs_pos, rcs_dir, rcs_F, mass, inertia,
                 bias=None):
        self.name = name
        self.engines = list(engines)
        self.rcs_pos = np.asarray(rcs_pos, float).reshape(-1, 3)
        self.rcs_dir = np.asarray(rcs_dir, float).reshape(-1, 3)
        self.rcs_F = np.asarray(rcs_F, float).ravel()
        self.mass, self.inertia = float(mass), np.asarray(inertia, float)
        # A constant wrench the vehicle cannot switch off - a thruster stuck
        # open, or any always-on disturbance the actuators must live with.  It
        # translates the whole attainable set, which is why a vehicle can keep
        # every bit of its authority and still lose the origin.
        self.bias = np.zeros(6) if bias is None else np.asarray(bias, float)

    @property
    def n_rcs(self):
        return len(self.rcs_F)

    @property
    def n_eng(self):
        return len(self.engines)


def rot_pitch_yaw(axis, dp, dy):
    """The engine axis after a fixed pitch/yaw misalignment.

    Matches the convention the plant uses for gimbal deflections: pitch tilts
    the thrust vector in the x-z plane, yaw in the y-z plane, both small.
    """
    a = np.asarray(axis, float)
    cp, sp, cy, sy = np.cos(dp), np.sin(dp), np.cos(dy), np.sin(dy)
    Ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
    Rx = np.array([[1.0, 0.0, 0.0], [0.0, cy, -sy], [0.0, sy, cy]])
    d = Rx @ (Ry @ a)
    return d / np.linalg.norm(d)


def model_from_lm(lm, case=None, name='healthy', t=0.0):
    """Build the capability model of `lm` after applying fault `case`.

    `case` is an injection_catalogue.FaultCase; its plant overrides were
    already baked into `lm` by `case.lm()`, so what is read here is the damaged
    LMParams plus the two things that live outside it: which engines are dead
    (`case.failed`) and the time-varying erosion rate (`eta_rate_eng`), which
    is evaluated at `t` seconds after onset.
    """
    failed = set(getattr(case, 'failed', ()) or ())
    engines = []
    for i in range(lm.n_eng):
        if i in failed:
            continue                       # a dead engine contributes nothing
        eta = lm.thrust_eff_eng.get(i, 1.0)
        rate = lm.eta_rate_eng.get(i, 0.0)
        if rate:
            eta = float(np.clip(eta + rate * t, 0.0, None))
        axis = np.array([0.0, 0.0, -1.0])              # thrust pushes -z (up)
        dp, dy = lm.gimbal_bias_eng.get(i, (0.0, 0.0))
        if dp or dy:
            axis = rot_pitch_yaw(axis, dp, dy)
        # a seized gimbal keeps its axis but loses the cone
        cone = 0.0 if lm.gimbal_lock_eng.get(i) else lm.gimbal_max
        cone *= lm.gimbal_eff_eng.get(i, 1.0)          # partial TVC authority
        engines.append(Engine(
            pos=lm.eng_pos(i), axis=axis,
            # the floor is a *delivered* force, so it scales with eta too
            T_min=eta * lm.T_min_eng_ovr.get(i, 0.0),
            T_max=eta * lm.T_max_eng, gimbal_max=cone))

    pos, dirs, _ = lm.rcs_geometry()
    return Model(name, engines, pos, dirs,
                 np.full(len(pos), lm.F_rcs_per), lm.mass,
                 np.array([lm.Ixx, lm.Iyy, lm.Izz]))


def chugging_band(lm, case):
    """(amplitude fraction, engine) of a forced thrust oscillation, or None.

    Chugging does not move the boundary of the commanded set; it makes the
    DELIVERED thrust uncertain inside it.  The capability that survives is the
    part the vehicle can hold regardless of where in the ripple it is caught,
    which is the set computed with that engine's usable range shrunk by the
    amplitude at both ends.  Reporting the nominal set for a chugging engine
    would credit it with authority it cannot be relied on to have.
    """
    osc = getattr(case, 'plant', {}).get('thrust_osc_eng') or {}
    if not osc:
        return None
    i, (amp, _w) = next(iter(osc.items()))
    return i, float(amp) * lm.T_hover / lm.n_eng


# ══════════════════════════════════════════════════════════════════════
#  2.  SUPPORT FUNCTIONS AND THE SETS THEMSELVES
# ══════════════════════════════════════════════════════════════════════

def best_dir_in_cone(u, axis, half_angle):
    """Unit vector inside the cone about `axis` maximising u . d."""
    nu = np.linalg.norm(u)
    if nu < 1e-15 or half_angle <= 0.0:
        return axis.copy()
    u = u / nu
    c = float(np.clip(u @ axis, -1.0, 1.0))
    if np.arccos(c) <= half_angle:
        return u
    perp = u - c * axis
    n = np.linalg.norm(perp)
    if n < 1e-12:
        tmp = np.array([1.0, 0.0, 0.0])
        if abs(axis @ tmp) > 0.9:
            tmp = np.array([0.0, 1.0, 0.0])
        perp = np.cross(axis, tmp)
        n = np.linalg.norm(perp)
    return np.cos(half_angle) * axis + np.sin(half_angle) * (perp / n)


def support_point(u, m, moment=False):
    """The point of the attainable set that maximises u . x.

    RCS thrusters fire or do not, so each contributes when it helps.  An engine
    contributes T*d with T in [T_min, T_max]: if the best direction in its cone
    has a positive projection the engine goes to T_max, and if it does not the
    engine still has to burn T_min - it cannot be switched off - so it drags
    the set in the least harmful direction available.
    """
    x = (m.bias[3:] if moment else m.bias[:3]).copy()
    G = (np.cross(m.rcs_pos, m.rcs_dir) if moment else m.rcs_dir)
    proj = G @ u
    x += (m.rcs_F * np.maximum(np.sign(proj), 0.0)) @ G

    for e in m.engines:
        if moment:
            w = np.cross(u, e.pos)                  # u.(r x d) == d.(u x r)
            d = best_dir_in_cone(w, e.axis, e.gimbal_max)
            vec = np.cross(e.pos, d)
        else:
            d = best_dir_in_cone(u, e.axis, e.gimbal_max)
            vec = d
        val = float(u @ vec)
        x += (e.T_max if val > 0.0 else e.T_min) * vec
    return x


def fibonacci_sphere(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    theta = np.pi * (1.0 + 5.0 ** 0.5) * i
    return np.column_stack([np.cos(theta) * np.sin(phi),
                            np.sin(theta) * np.sin(phi),
                            np.cos(phi)])


def attainable_set(m, moment=False, n_dirs=1200):
    """Boundary cloud and hull of the AFS (moment=False) or AMS (True)."""
    U = fibonacci_sphere(n_dirs)
    P = np.array([support_point(u, m, moment) for u in U])
    if all(e.T_min <= 1e-9 for e in m.engines):
        # shutdown is available - but only back to the bias, not to zero
        P = np.vstack([P, (m.bias[3:] if moment else m.bias[:3])])
    if np.abs(P).max() < 1e-12:
        return P, None
    try:
        return P, ConvexHull(P)
    except Exception:
        return P, None


AXES = [('+x', np.array([1., 0., 0.])), ('-x', np.array([-1., 0., 0.])),
        ('+y', np.array([0., 1., 0.])), ('-y', np.array([0., -1., 0.])),
        ('+z', np.array([0., 0., 1.])), ('-z', np.array([0., 0., -1.]))]


def metrics(m, n_dirs=1200):
    """Volume, per-axis support, isotropy and origin containment, per set."""
    out = {}
    for key, mom in (('force', False), ('moment', True)):
        P, hull = attainable_set(m, moment=mom, n_dirs=n_dirs)
        axis_vals = {lab: float(e @ support_point(e, m, mom))
                     for lab, e in AXES}
        hi = max(abs(v) for v in axis_vals.values()) or 1.0
        out[key] = dict(
            volume=float(hull.volume) if hull is not None else 0.0,
            max_norm=float(np.linalg.norm(P, axis=1).max()),
            isotropy=min(abs(v) for v in axis_vals.values()) / hi,
            axes=axis_vals,
            contains_origin=contains_origin(m, mom))
    return out


def mean_support(m, moment=False, n_dirs=400):
    """Average of h(u) over the sphere - the set's mean reach.

    Volume is the natural size of a 3-D set and the wrong measure for a
    DEGENERATE one.  A vehicle with a single centreline gimballed engine has no
    roll authority at all, so its moment set is a flat disc: the volume is
    exactly zero, every retention ratio becomes 0/0, and the vehicle drops out
    of every comparison - not because it lacks authority but because its
    authority is planar.  That is a structural zero, and reporting it as
    missing data would hide the most interesting architectural fact about those
    vehicles.

    The mean support is defined for a set of any dimension, is positive
    whenever the set is, and scales linearly with the actuators - so it can be
    compared across vehicles four orders of magnitude apart in thrust once
    normalised by their own healthy value.
    """
    U = fibonacci_sphere(n_dirs)
    return float(np.mean([float(u @ support_point(u, m, moment)) for u in U]))


def set_measure(P, tol_rel=1e-8):
    """(size, dimension) of a point cloud's hull: volume, area or extent.

    Falls through the dimensions so a degenerate set still reports a size in
    its own dimension rather than a zero that means "not measured".
    """
    Q = P - P.mean(axis=0)
    sv = np.linalg.svd(Q, compute_uv=False)
    dim = int((sv > max(sv[0] * tol_rel, 1e-12)).sum()) if sv[0] > 0 else 0
    if dim >= 3:
        try:
            return float(ConvexHull(P).volume), 3
        except Exception:
            dim = 2
    if dim == 2:
        _, _, Vt = np.linalg.svd(Q)
        R = Q @ Vt[:2].T
        try:
            return float(ConvexHull(R).volume), 2      # 2-D "volume" = area
        except Exception:
            return 0.0, 2
    if dim == 1:
        _, _, Vt = np.linalg.svd(Q)
        r = Q @ Vt[0]
        return float(r.max() - r.min()), 1
    return 0.0, 0


def min_support(m, moment=False, n_dirs=400):
    """min over directions u of h(u), the support function of the set.

    Positive means the origin is in the INTERIOR: the set spans every
    direction, so the vehicle has authority about every axis with margin.
    Zero means the origin is on the boundary at best - authority in some
    direction is one-sided, which is the same degeneracy Farkas' Lemma detects
    in the RCS-redundancy study.  Negative means the origin is outside the set
    altogether and zero net wrench is unattainable.

    Reported as a magnitude it is the worst-case authority the vehicle has in
    ANY direction, which is a far better summary than volume: a set can be
    enormous and still be flat in one axis.
    """
    U = fibonacci_sphere(n_dirs)
    return float(min(float(u @ support_point(u, m, moment)) for u in U))


def contains_origin(m, moment=False, tol=1e-6):
    """Can the vehicle produce ZERO net force / moment?

    Every support direction must reach the far side of the origin; if some
    direction has a strictly positive minimum, the whole set sits on one side
    of that plane and zero is unattainable.  This is the test a stuck-open
    valve fails.
    """
    U = fibonacci_sphere(200)
    return bool(all(float(u @ support_point(-u, m, moment)) <= tol for u in U))


# ══════════════════════════════════════════════════════════════════════
#  3.  THE OPERATING POINT: IS THE REQUIRED WRENCH STILL ATTAINABLE?
# ══════════════════════════════════════════════════════════════════════
#  Volume is a summary; what a vehicle actually needs is one specific wrench -
#  enough force to hold itself up, with zero net moment so the attitude does
#  not run away.  A set can lose most of its volume and keep that point, or
#  keep most of its volume and lose it.  Only the second kills the vehicle.
# ══════════════════════════════════════════════════════════════════════

def _engine_vertices(e, n_az=16):
    """Vertices of the polytope approximating one engine's contribution.

    The cap is sampled at `n_az` azimuths on its rim plus the axis itself, at
    both throttle limits.  Sampling the rim is the conservative choice: the
    polytope is inscribed in the true cap, so a wrench this test calls
    attainable really is.
    """
    a = e.axis
    tmp = np.array([1.0, 0.0, 0.0])
    if abs(a @ tmp) > 0.9:
        tmp = np.array([0.0, 1.0, 0.0])
    u1 = np.cross(a, tmp); u1 /= np.linalg.norm(u1)
    u2 = np.cross(a, u1)
    dirs = [a]
    if e.gimbal_max > 0:
        for th in np.linspace(0, 2 * np.pi, n_az, endpoint=False):
            dirs.append(np.cos(e.gimbal_max) * a + np.sin(e.gimbal_max) *
                        (np.cos(th) * u1 + np.sin(th) * u2))
    levels = [e.T_max] + ([e.T_min] if e.T_min > 1e-9 else [0.0])
    return [T * d for d in dirs for T in levels]


def _wrench_program(m, n_az=16):
    """Columns, bounds and per-engine index blocks of the allocation LP."""
    cols, bounds = [], []
    for j in range(m.n_rcs):
        d = m.rcs_dir[j]
        cols.append(np.concatenate([d, np.cross(m.rcs_pos[j], d)]))
        bounds.append((0.0, m.rcs_F[j]))
    eng_blocks = []
    for e in m.engines:
        idx = []
        for v in _engine_vertices(e, n_az):
            cols.append(np.concatenate([v, np.cross(e.pos, v)]))
            bounds.append((0.0, 1.0))
            idx.append(len(cols) - 1)
        eng_blocks.append(idx)
    return cols, bounds, eng_blocks


def _engine_rows(n, eng_blocks, extra=0):
    """Each engine burns at exactly one point of its polytope."""
    A_ub, b_ub = [], []
    for idx in eng_blocks:
        row = np.zeros(n + extra)
        row[idx] = 1.0
        A_ub.append(row); b_ub.append(1.0)
        A_ub.append(-row); b_ub.append(-1.0)
    return A_ub, b_ub


def wrench_slack(m, w_req, n_az=16, free=()):
    """Smallest total wrench error the actuators can leave on `w_req`.

    A linear program over the RCS throttles and a convex combination per
    engine.  0 means the required wrench is exactly attainable; the value is
    otherwise how much wrench (N and N m, summed as an L1 residual) the vehicle
    is short by, which is a continuous measure of how far outside its
    capability the operating point has fallen.

    `free` names wrench rows to leave UNCONSTRAINED, which is not a
    convenience but the difference between two distinct questions.  Demanding
    all six rows asks for the full hover wrench, lateral force included.  A
    single offset engine can never satisfy that: to zero its roll moment the
    thrust vector must point through the CG, which tilts it and leaves a
    lateral force behind.  Freeing rows 0 and 1 asks the question Study A asks
    instead - can the gimbal trim the MOMENT while holding the vehicle up -
    and that one has the familiar answer y_eng <= dz_eng tan(delta_max).
    """
    w_req = np.asarray(w_req, float).ravel()
    rows = [r for r in range(6) if r not in set(free)]
    cols, bounds, eng_blocks = _wrench_program(m, n_az)
    n, k = len(cols), len(rows)
    A_w = np.array(cols).T[rows, :]
    A_eq = np.hstack([A_w, np.eye(k), -np.eye(k)])
    c = np.concatenate([np.zeros(n), np.ones(2 * k)])
    bnds = bounds + [(0.0, None)] * (2 * k)
    A_ub, b_ub = _engine_rows(n, eng_blocks, extra=2 * k)
    # the actuators only have to make up what the constant bias does not
    b_eq = (w_req - m.bias)[rows]
    res = linprog(c, A_ub=np.array(A_ub) if A_ub else None,
                  b_ub=np.array(b_ub) if b_ub else None,
                  A_eq=A_eq, b_eq=b_eq, bounds=bnds, method='highs')
    return float(res.fun) if res.status == 0 else np.inf


# ══════════════════════════════════════════════════════════════════════
#  4.  CONDITIONAL CAPABILITY: WHAT IS LEFT WHILE HOLDING YOURSELF UP
# ══════════════════════════════════════════════════════════════════════
#  The unconstrained AMS flatters every fault, because it is free to spend the
#  whole actuator set on one moment and let the vehicle fall.  A descending
#  vehicle cannot: most of its thrust is committed to not hitting the ground,
#  and the moment authority that matters is what remains AFTER that commitment.
#  This is the set an FTC allocator actually draws from, and it separates
#  faults the raw AMS cannot tell apart.
# ══════════════════════════════════════════════════════════════════════

def conditional_moment_set(m, F_z, n_dirs=120, n_az=16, tol=1e-6):
    """Moments attainable while producing vertical force `F_z` (lateral force
    free).  Returns the boundary cloud and its hull, or (None, None) if the
    vehicle cannot hold that force at all."""
    cols, bounds, eng_blocks = _wrench_program(m, n_az)
    n = len(cols)
    A = np.array(cols).T                                  # 6 x n
    A_eq = np.vstack([A[2:3, :]])                         # F_z row only
    b_eq = np.array([F_z - m.bias[2]])
    A_ub, b_ub = _engine_rows(n, eng_blocks)

    P = []
    for u in fibonacci_sphere(n_dirs):
        c = -(u @ A[3:6, :])                              # maximise u . M
        res = linprog(c, A_ub=np.array(A_ub) if A_ub else None,
                      b_ub=np.array(b_ub) if b_ub else None,
                      A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
        if res.status != 0:
            return None, None                             # F_z unattainable
        P.append(A[3:6, :] @ res.x + m.bias[3:])
    P = np.array(P)
    if np.abs(P).max() < tol:
        return P, None
    try:
        return P, ConvexHull(P)
    except Exception:
        return P, None


def hover_wrench(lm, sign=-1.0):
    """The wrench a hovering vehicle needs: weight held, no net moment."""
    return np.array([0.0, 0.0, sign * lm.mass * lm.g_moon, 0.0, 0.0, 0.0])
