"""
Achievable force and moment sets
════════════════════════════════════════════════════════════════════════
Computes, for a Vehicle, the set of net forces and the set of net moments
its actuators can produce, and the per-axis maxima that follow.

WHAT IS COMPUTED
────────────────
Each RCS thruster i is an on/off (really: throttleable-to-zero) unit with
throttle f in [0, F_i], contributing force  f d_i  and moment  f (r_i x d_i).
Over all thrusters that is a Minkowski sum of line segments — a *zonotope*.

Each gimballed engine e contributes  T d,  with T in [0, T_max] and d ranging
over a spherical cap of half-angle delta about its nominal axis. That piece is
curved, not a polytope, so the two are combined numerically.

The reported set is the CONVEX HULL of the achievable set. This is the standard
object for control-authority analysis: any point in the hull is reachable as a
time-average of achievable instantaneous wrenches, and the hull is exactly what
a support-function sweep recovers.

Support functions (h(u) = max over the set of u . x) are used because they are
exact and cheap for every piece:

    RCS force   :  h(u) = sum_i F_i * max(0, u . d_i)
    RCS moment  :  h(u) = sum_i F_i * max(0, u . (r_i x d_i))
    engine force:  h(u) = T_max * max(0, max_{d in cap} u . d)
    engine moment: using  u . (r x d) = d . (u x r),  maximise d . (u x r)
                   over the same cap.

Sweeping u over a Fibonacci sphere and collecting the maximising points gives
boundary points whose convex hull is an inner approximation, exact in every
sampled direction.

PER-AXIS MAXIMA
───────────────
The maximum force the vehicle can produce along +x is h_F(+x) — the support
function evaluated on that axis — and the maximum along -x is h_F(-x). These
are reported separately because actuator layouts are frequently asymmetric.
Linear acceleration is h_F(e)/m; angular acceleration about axis j is
h_M(e_j)/I_jj, which neglects gyroscopic and product-of-inertia coupling and
is therefore an instantaneous, small-rate figure.
"""

import numpy as np
from scipy.spatial import ConvexHull

AXES = [('+x', np.array([1., 0., 0.])), ('-x', np.array([-1., 0., 0.])),
        ('+y', np.array([0., 1., 0.])), ('-y', np.array([0., -1., 0.])),
        ('+z', np.array([0., 0., 1.])), ('-z', np.array([0., 0., -1.]))]


# ══════════════════════════════════════════════════════════════════════
#  Gimbal cone geometry
# ══════════════════════════════════════════════════════════════════════

def best_dir_in_cone(u, axis, half_angle):
    """Unit vector d inside the cone of half-angle `half_angle` about `axis`
    that maximises u . d.

    If u already lies inside the cone the answer is u itself; otherwise it is
    axis rotated toward u by exactly the cone limit — the deflection saturates.
    """
    nu = np.linalg.norm(u)
    if nu < 1e-15:
        return axis.copy()
    u = u / nu
    if half_angle <= 0.0:
        return axis.copy()

    c = float(np.clip(u @ axis, -1.0, 1.0))
    if np.arccos(c) <= half_angle:
        return u

    perp = u - c * axis
    n = np.linalg.norm(perp)
    if n < 1e-12:                       # u is antiparallel to axis: any edge
        tmp = np.array([1., 0., 0.])
        if abs(axis @ tmp) > 0.9:
            tmp = np.array([0., 1., 0.])
        perp = np.cross(axis, tmp)
        n = np.linalg.norm(perp)
    return np.cos(half_angle) * axis + np.sin(half_angle) * (perp / n)


# ══════════════════════════════════════════════════════════════════════
#  Support points
# ══════════════════════════════════════════════════════════════════════

def _engine_terms(u, veh, moment):
    """(value, vector) contribution of each engine for direction u."""
    terms = []
    for e in veh.engines:
        if moment:
            w = np.cross(u, e.pos)               # u.(r x d) == d.(u x r)
            d = best_dir_in_cone(w, e.axis, e.gimbal_max)
            vec = e.T_max * np.cross(e.pos, d)
        else:
            d = best_dir_in_cone(u, e.axis, e.gimbal_max)
            vec = e.T_max * d
        terms.append((float(u @ vec), vec))
    return terms


def support_point(u, veh, moment=False):
    """Point of the achievable set maximising u . x."""
    x = np.zeros(3)
    for t in veh.rcs:
        g = t.F * (np.cross(t.pos, t.dir) if moment else t.dir)
        if u @ g > 0.0:
            x += g

    terms = _engine_terms(u, veh, moment)
    if veh.max_engines_on is not None and len(terms) > veh.max_engines_on:
        # only the k best-aligned engines may burn at once
        terms = sorted(terms, key=lambda tv: -tv[0])[:veh.max_engines_on]
    for val, vec in terms:
        if val > 0.0:
            x += vec
    return x


def fibonacci_sphere(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    theta = np.pi * (1.0 + 5.0 ** 0.5) * i
    return np.column_stack([np.cos(theta) * np.sin(phi),
                            np.sin(theta) * np.sin(phi),
                            np.cos(phi)])


def achievable_set(veh, moment=False, n_dirs=1600):
    """Boundary point cloud and its convex hull (or None if degenerate)."""
    U = fibonacci_sphere(n_dirs)
    P = np.array([support_point(u, veh, moment) for u in U])
    P = np.vstack([P, np.zeros(3)])          # shutdown is always achievable

    if np.abs(P).max() < 1e-12:
        return P, None
    try:
        return P, ConvexHull(P)
    except Exception:
        return P, None                       # flat/degenerate (e.g. coplanar)


# ══════════════════════════════════════════════════════════════════════
#  Per-axis capability
# ══════════════════════════════════════════════════════════════════════

def axis_maxima(veh):
    """Max force [N], linear acceleration [m/s^2], moment [N m] and angular
    acceleration [rad/s^2] along each of the six body-axis directions."""
    out = {}
    for label, e in AXES:
        F = float(e @ support_point(e, veh, moment=False))
        M = float(e @ support_point(e, veh, moment=True))
        j = 'xyz'.index(label[1])
        out[label] = dict(
            force_N=F,
            accel_ms2=F / veh.mass if np.isfinite(veh.mass) and veh.mass > 0 else np.nan,
            moment_Nm=M,
            ang_accel_rads2=(M / veh.inertia[j]
                             if np.isfinite(veh.inertia[j]) and veh.inertia[j] > 0
                             else np.nan))
    return out


def set_metrics(veh, n_dirs=1600):
    """Volume and extent of both sets — a compact measure of how much authority
    the layout actually delivers, and how isotropic it is."""
    m = {}
    for key, mom in (('force', False), ('moment', True)):
        P, hull = achievable_set(veh, moment=mom, n_dirs=n_dirs)
        r = np.linalg.norm(P, axis=1)
        m[key] = dict(volume=(hull.volume if hull is not None else 0.0),
                      max_norm=float(r.max()),
                      # isotropy: smallest over largest axis-support, 1 = a ball
                      isotropy=_isotropy(veh, mom))
    return m


def _isotropy(veh, moment):
    vals = [abs(e @ support_point(e, veh, moment=moment)) for _, e in AXES]
    hi = max(vals)
    return (min(vals) / hi) if hi > 0 else 0.0
