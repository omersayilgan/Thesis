"""
Actuator geometry & inertia database
════════════════════════════════════════════════════════════════════════
Everything the achievable-force / achievable-moment analysis needs that the
`spacecraft_values.xlsx` workbook does NOT contain.

The workbook supplies thrust magnitudes, actuator counts and masses. It has no
thruster positions, no thrust-direction vectors, no gimbal limits and no
inertia tensors — all five were checked for and are absent. Those quantities
are supplied here.

PROVENANCE IS TRACKED PER VALUE.  Every vehicle carries a `flags` dict mapping
a quantity to one of:

    SOURCED   — taken from the workbook, or from this repository's own
                validated Apollo LM model (apollo_full.py)
    ESTIMATED — a documented engineering assumption made here, with the basis
                written out in the flag string

The flags propagate into the figures and into every row of the summary
workbook, so no derived number can be mistaken for a measured one. To upgrade
a vehicle, replace its layout and move its flag to SOURCED with a citation.

Body frame convention (shared by all vehicles):
    +x  forward / along the primary instrument or docking axis
    +y  right
    +z  down, i.e. the direction the main engine pushes the vehicle *away*
        from — the main engine thrust vector on the vehicle is -z

Note on `dir`: the stored unit vector is the FORCE APPLIED TO THE VEHICLE,
not the direction the exhaust leaves. A thruster that vents its plume in +z
therefore has dir = -z.
"""

import numpy as np
from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════════
#  Data model
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Thruster:
    """A fixed on/off thruster. Throttle level f is free in [0, F]."""
    pos: np.ndarray          # body-frame position of the nozzle [m]
    dir: np.ndarray          # unit vector of the force applied to the vehicle
    F:   float               # maximum thrust [N]


@dataclass
class GimbalEngine:
    """A main engine, optionally gimballed within a cone of half-angle
    `gimbal_max` about its nominal axis. Throttle is free in [0, T_max]:
    the achievable set is a convex hull and shutdown is always available,
    so a non-zero minimum throttle does not enlarge or shrink the hull."""
    pos:        np.ndarray   # body-frame position of the gimbal pivot [m]
    axis:       np.ndarray   # nominal unit force direction (undeflected)
    T_max:      float        # maximum thrust [N]
    gimbal_max: float = 0.0  # cone half-angle [rad]; 0.0 = rigidly mounted


@dataclass
class Vehicle:
    name:      str
    category:  str
    mass:      float                       # [kg]
    inertia:   np.ndarray                  # principal (Ixx, Iyy, Izz) [kg m^2]
    rcs:       list = field(default_factory=list)
    engines:   list = field(default_factory=list)
    flags:     dict = field(default_factory=dict)
    shape:     str = ''                    # inertia shape model description
    notes:     str = ''
    # Some vehicles cannot fire every installed engine at once (Europa Clipper
    # has 24 installed but a maximum of 8 simultaneously, per the workbook).
    # None = no restriction.
    max_engines_on: int = None

    @property
    def n_rcs(self):     return len(self.rcs)
    @property
    def n_engines(self): return len(self.engines)

    def provenance(self, key):
        return self.flags.get(key, 'ESTIMATED (undocumented)')

    def is_estimated(self, key):
        return self.provenance(key).startswith('ESTIMATED')


# ══════════════════════════════════════════════════════════════════════
#  Inertia shape models
# ══════════════════════════════════════════════════════════════════════

def inertia_cylinder(m, radius, height):
    """Uniform solid cylinder, symmetry axis along body z."""
    Ixx = Iyy = m * (3.0 * radius**2 + height**2) / 12.0
    Izz = m * radius**2 / 2.0
    return np.array([Ixx, Iyy, Izz])


def inertia_box(m, a, b, c):
    """Uniform solid rectangular box with side lengths a(x), b(y), c(z)."""
    return np.array([m * (b*b + c*c) / 12.0,
                     m * (a*a + c*c) / 12.0,
                     m * (a*a + b*b) / 12.0])


# ══════════════════════════════════════════════════════════════════════
#  Reusable actuator layouts
# ══════════════════════════════════════════════════════════════════════

def quad_ring(n_quads, radius, z, F, azimuth_offset=45.0):
    """Apollo-style RCS: `n_quads` clusters on a ring of the given radius in
    the body x-y plane, each cluster carrying four thrusters — one pushing
    +z, one -z, and two tangential (+/-) in the plane. Firing any single
    thruster produces a coupled force *and* moment.

    This is the layout validated in apollo_full.py for the Apollo LM.
    """
    out = []
    az = np.deg2rad(azimuth_offset + 360.0 * np.arange(n_quads) / n_quads)
    for a in az:
        c, s = np.cos(a), np.sin(a)
        r = np.array([radius * c, radius * s, z])
        tang = np.array([-s, c, 0.0])
        for d in (np.array([0., 0., 1.]), np.array([0., 0., -1.]), tang, -tang):
            out.append(Thruster(r.copy(), d.copy(), F))
    return out


def face_pairs(half, F, n_per_face=2):
    """Cold-gas / small-satellite layout: `n_per_face` thrusters on each of the
    six faces of a box, each pushing along its outward face normal. `half` is
    the (hx, hy, hz) half-extent of the bus.

    Pairs on a face are offset along an in-plane axis so that firing one of a
    pair produces a torque as well as a force (a single centred thruster per
    face would give pure force and no attitude authority).

    Offsets on different faces use DIFFERENT in-plane axes. Offsetting every
    face along one axis makes each face contribute a moment about a single
    axis only, and with all six offset the same way the layout ends up with no
    roll authority at all. Alternating the offset axis face-by-face spans all
    three.
    """
    hx, hy, hz = half
    ex, ey, ez = np.eye(3)
    out = []
    #        face normal, in-plane offset axis, normal extent, offset extent
    axes = [( ex, ey, hx, hy), (-ex, ez, hx, hz),
            ( ey, ez, hy, hz), (-ey, ex, hy, hx),
            ( ez, ex, hz, hx), (-ez, ey, hz, hy)]
    for n, t, d_n, d_t in axes:
        for k in range(n_per_face):
            off = (2.0 * k / max(n_per_face - 1, 1) - 1.0) if n_per_face > 1 else 0.0
            pos = n * d_n + t * (off * 0.8 * d_t)
            out.append(Thruster(pos, n.copy(), F))
    return out


def canted_ring(n, radius, z, F, cant_deg, axial=-1.0):
    """`n` thrusters equally spaced on a ring, each canted `cant_deg` outward
    from the body axis. Used for clustered abort/main motors (Crew Dragon
    SuperDracos) and for RCS branches mounted around a bus.

    `axial` = -1 puts the resultant force along -z (i.e. the cluster pushes
    the vehicle 'up' in the body frame), +1 reverses it.
    """
    out = []
    ca, sa = np.cos(np.deg2rad(cant_deg)), np.sin(np.deg2rad(cant_deg))
    for a in 2.0 * np.pi * np.arange(n) / n:
        c, s = np.cos(a), np.sin(a)
        pos = np.array([radius * c, radius * s, z])
        d = np.array([sa * c, sa * s, axial * ca])
        out.append(Thruster(pos, d / np.linalg.norm(d), F))
    return out


def branch_clusters(n_total, radius, z, F, n_clusters=4, azimuth_offset=45.0,
                    cant_deg=35.0):
    """Distribute `n_total` small thrusters over `n_clusters` clusters spaced
    around a bus (Cassini, Juno, Voyager, New Horizons, and the generic case).

    Two design rules matter here, both learned from getting them wrong:

    1) FOUR clusters, not n_total//4. Deriving the cluster count from the
       thruster count puts 8 thrusters into 2 clusters, which land at azimuth
       0 and 180 — collinear. Every moment arm r x d is then perpendicular to
       that line and the layout has *exactly zero roll authority*, which no
       real attitude-control system has. Four clusters at 45/135/225/315 is
       the near-universal arrangement and spans all three axes.

    2) The direction pool ROTATES per cluster. With only 2 thrusters per
       cluster a fixed pool order would give every cluster the same axial
       pair and no cluster any tangential jet, losing yaw authority for the
       same reason. Rotating means clusters alternate axial / tangential and
       the set stays three-axis whatever the count.

    3) Thrusters are CANTED, not purely axial or purely tangential. A purely
       axial jet at radius R produces a moment arm lying in the body x-y plane,
       and two such jets at diametrically opposite clusters produce COLLINEAR
       arms. With only two thrusters per cluster that collapses the moment cone
       to rank 2: the layout cannot produce a moment about one whole axis and
       fails to positively span R^3 even with every thruster working - which no
       real attitude-control system does. Canting mixes each thruster's axial
       and tangential components so the columns are in general position, and a
       Farkas positive-spanning test then passes for the intact set.
    """
    out = []
    az = np.deg2rad(azimuth_offset + 360.0 * np.arange(n_clusters) / n_clusters)
    per = [n_total // n_clusters + (1 if i < n_total % n_clusters else 0)
           for i in range(n_clusters)]
    ca, sa = np.cos(np.deg2rad(cant_deg)), np.sin(np.deg2rad(cant_deg))
    for i, a in enumerate(az):
        c, s = np.cos(a), np.sin(a)
        r = np.array([radius * c, radius * s, z])
        tang = np.array([-s, c, 0.0])
        ax = np.array([0., 0., 1.])
        # four canted directions: axial +/- blended with tangential +/-
        pool = [ca * ax + sa * tang, -ca * ax + sa * tang,
                sa * ax + ca * tang, -sa * ax - ca * tang]
        pool = [p / np.linalg.norm(p) for p in pool]
        pool = pool[i % 4:] + pool[:i % 4]          # rotate per cluster
        for j in range(per[i]):
            out.append(Thruster(r.copy(), pool[j % 4].copy(), F))
    return out
