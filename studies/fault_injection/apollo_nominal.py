"""
STUDY H — the Apollo-anchored nominal descent
═════════════════════════════════════════════
Stage 1 of the injection study: fly a healthy vehicle down a single reference
trajectory, and keep every state of it.  Everything else in the study is
injected onto points of *this* trajectory, so it has to be defensible on its own
before any fault is discussed.

Where the initial state comes from
──────────────────────────────────
It is anchored on the published Apollo approach-phase (P64) geometry rather
than invented.  Two points of that phase are well documented:

    high gate  ~7,500 ft (2,286 m) altitude, ~4.5 nmi (8,300 m) to the target,
               ~500 ft/s (152 m/s) horizontal, ~145 ft/s (44 m/s) descent
    low gate   ~500 ft (152 m) altitude, ~2,000 ft (610 m) to the target,
               ~60 ft/s (18 m/s) horizontal, ~16 ft/s (5 m/s) descent

The approach between them is flown essentially straight at the landing point:
the line-of-sight depression from high gate is atan(2286/8300) = 15.4 deg, and
from low gate atan(152/610) = 14.0 deg — the same path.  Interpolating along it
gives a one-parameter family of Apollo-consistent states, and this study picks
the point where the horizontal speed has bled to 55 m/s, because that is the
fastest state this vehicle model's own path constraint (V_max = 60 m/s per
axis) admits with margin:

    altitude 740 m,  range 2,730 m,  55 m/s horizontal,  16 m/s descent

Two independent checks that the interpolation is self-consistent: the resulting
line-of-sight depression is atan(740/2730) = 15.2 deg, and the flight-path
angle is atan(16/55) = 16.2 deg.  A vehicle whose velocity vector points at the
landing site is what "flying the approach phase" means, and these agree to
within a degree, which they would not if the interpolation were nonsense.

This is a *reconstruction of the geometry*, not telemetry.  It reproduces where
an Apollo LM was and how fast it was going at 740 m on final approach; it is not
a replay of any specific mission's recorded state vector.

What differs from the earlier studies
─────────────────────────────────────
  * engines at y = +-0.25 m instead of +-1.5 m.  This is the roll-authority
    threshold from Study A: a single gimbal can trim a one-engine-out
    asymmetry only while y_eng <= dz_eng * tan(gimbal_max) = 0.263 m.  At 1.5 m
    the vehicle could never survive an engine failure; at 0.25 m it sits just
    inside the limit, so engine-out becomes a survivable fault and the study
    can actually measure it.
  * glide-slope floor lowered from 30 deg to 12 deg.  Apollo's real approach is
    a ~15 deg path, which a 30 deg cone forbids outright — the old constraint
    was chosen for a much steeper, closer-in scenario.  12 deg admits the
    Apollo geometry with margin while still ruling out the dive-and-crawl-back
    trajectory family the cone exists to prevent.
  * a spherical speed cap of 60 m/s.  The model's V_max is a *per-axis* box,
    which on a near-vertical descent is harmless (only w is large) but on a
    2.7 km shallow approach lets the speed norm reach 104 m/s: the first solve
    accelerated downrange, rode the 45 deg pitch limit, overshot the pad and
    came back.  No lunar descent flies that.  The cap is a new optional
    OCPConfig field and defaults to off, so the earlier studies are untouched.
  * the horizon is *fitted*, not chosen.  A probe solve measures how long the
    descent actually takes, and the trajectory is then re-solved on a horizon
    just long enough to contain it.  Surplus horizon is not free: it leaves the
    optimiser time to spend, and it spends it wandering near the pad.

Run:  python apollo_nominal.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(FIGURES, exist_ok=True)

import apollo_full as af      # noqa: E402
import fault_lib as fl        # noqa: E402


# ══════════════════════════════════════════════════════════════════════
#  1. THE APOLLO APPROACH-PHASE ANCHOR
# ══════════════════════════════════════════════════════════════════════

FT = 0.3048
NMI = 1852.0

GATES = {                        # published P64 approach-phase endpoints
    'high': dict(alt=7500 * FT, rng=4.5 * NMI, v_h=500 * FT, v_v=145 * FT),
    'low':  dict(alt=500 * FT,  rng=2000 * FT, v_h=60 * FT,  v_v=16 * FT),
}

V_H_ANCHOR = 55.0                # horizontal speed we anchor on  [m/s]


def apollo_anchor(v_h=V_H_ANCHOR):
    """Interpolate the documented approach path to a chosen horizontal speed.

    Returns (alt, range, v_h, v_v) plus the two consistency angles.  Linear in
    the speed parameter, which is what makes the two angles agree — the real
    approach is close to a straight line in the range-altitude plane.
    """
    hi, lo = GATES['high'], GATES['low']
    s = (v_h - lo['v_h']) / (hi['v_h'] - lo['v_h'])      # 0 at low gate, 1 at high
    alt = lo['alt'] + s * (hi['alt'] - lo['alt'])
    rng = lo['rng'] + s * (hi['rng'] - lo['rng'])
    v_v = lo['v_v'] + s * (hi['v_v'] - lo['v_v'])
    los = np.degrees(np.arctan2(alt, rng))               # line-of-sight depression
    fpa = np.degrees(np.arctan2(v_v, v_h))               # flight-path angle
    return dict(alt=alt, rng=rng, v_h=v_h, v_v=v_v, los=los, fpa=fpa, s=s)


def anchor_state(a, theta_deg=15.0):
    """The 12-state at the anchor.

    The vehicle sits `rng` metres due south of the pad, flying north at v_h and
    descending at v_v, pitched nose-up by theta (the braking attitude: with
    thrust along body -z, a positive pitch tilts it aft, which is what
    decelerates the approach).  Earth-frame velocity is specified and rotated
    into the body frame, so the pitch attitude does not silently change the
    trajectory the state represents.
    """
    phi, th, psi = 0.0, np.deg2rad(theta_deg), 0.0
    v_E = np.array([a['v_h'], 0.0, a['v_v']])            # north, east, down
    v_B = af.dcm_eb(phi, th, psi).T @ v_E
    return np.array([-a['rng'], 0.0, -a['alt'],
                     v_B[0], v_B[1], v_B[2],
                     phi, th, psi, 0.0, 0.0, 0.0])


# ══════════════════════════════════════════════════════════════════════
#  2. VEHICLE AND PROBLEM CONFIGURATION
# ══════════════════════════════════════════════════════════════════════

Y_ENG = 0.25              # engine half-spacing  [m]  (was 1.5)
GLIDE_DEG = 12.0          # approach-cone floor  [deg]  (was 30)
V_NORM = 60.0             # spherical speed cap  [m/s]
N_PROBE = 80              # first-pass horizon, only used to time the descent


def make_lm(**kw):
    return af.LMParams(y_eng=Y_ENG, **kw)


def make_cfg(N=N_PROBE):
    cfg = af.OCPConfig()
    cfg.N = N
    cfg.glide_slope = np.deg2rad(GLIDE_DEG)
    cfg.V_norm_max = V_NORM
    return cfg


def roll_limit(lm):
    """Largest engine half-spacing a single gimbal can trim one-engine-out."""
    return lm.dz_eng * np.tan(lm.gimbal_max)


# ══════════════════════════════════════════════════════════════════════
#  3. SOLVE
# ══════════════════════════════════════════════════════════════════════

def main():
    a = apollo_anchor()
    lm, cfg = make_lm(), make_cfg()
    x12 = anchor_state(a)

    print('Apollo approach-phase anchor')
    print(f"  altitude        {a['alt']:8.1f} m   ({a['alt'] / FT:.0f} ft)")
    print(f"  range to pad    {a['rng']:8.1f} m   ({a['rng'] / FT:.0f} ft)")
    print(f"  horizontal      {a['v_h']:8.1f} m/s ({a['v_h'] / FT:.0f} ft/s)")
    print(f"  descent rate    {a['v_v']:8.1f} m/s ({a['v_v'] / FT:.0f} ft/s)")
    print(f"  LOS depression  {a['los']:8.2f} deg")
    print(f"  flight-path     {a['fpa']:8.2f} deg   (agree to "
          f"{abs(a['los'] - a['fpa']):.2f} deg)")
    print(f"\nVehicle: y_eng = {lm.y_eng:.2f} m, roll-trim limit "
          f"{roll_limit(lm):.3f} m -> engine-out is "
          f"{'TRIMMABLE' if lm.y_eng <= roll_limit(lm) else 'untrimmable'}")
    print(f"Problem: {cfg.N} x {cfg.dt:.0f} s horizon, "
          f"{np.rad2deg(cfg.glide_slope):.0f} deg glide cone\n")

    # ── pass 1: how long does this descent actually take? ────────────────
    probe = fl.run_nominal(x12, lm, cfg, max_iter=600)
    if not probe['ok']:
        print('!! probe did not converge:', probe['status'])
        return
    N_fit = int(np.clip(round(probe['t_contact'] / cfg.dt) + 2, 30, N_PROBE))
    print(f"probe: contact at {probe['t_contact']:.0f} s "
          f"-> re-solving on a {N_fit} s horizon\n")

    # ── pass 2: the trajectory the study actually uses ───────────────────
    cfg = make_cfg(N_fit)
    res = fl.run_nominal(x12, lm, cfg, max_iter=600)
    if not res['ok']:
        print('!! nominal did not converge:', res['status'])
        return

    X, U = res['X'], res['U']
    t_c = res['t_contact']
    m = res['metrics']
    print(f"nominal converged in {res['iters']} iterations, {res['wall']:.0f} s")
    print(f"  contact at t = {t_c:.0f} s, touchdown margin {res['margin']:.2f} "
          f"-> {'LANDS' if res['lands'] else 'MISSES GATE'}")
    print(f"  v_vert {m['v_vert']:.2f} m/s, v_horiz {m['v_horiz']:.2f} m/s, "
          f"tilt {m['tilt_deg']:.2f} deg, {m['pos_err']:.1f} m from the pad")

    np.savez(os.path.join(RESULTS, 'nominal.npz'),
             X=X, U=U, x0=x12, t_contact=t_c, margin=res['margin'],
             lands=res['lands'], y_eng=Y_ENG, glide_deg=GLIDE_DEG,
             N=cfg.N, dt=cfg.dt, v_norm=V_NORM,
             anchor=np.array([a['alt'], a['rng'], a['v_h'], a['v_v'],
                              a['los'], a['fpa']]))
    print(f"\n[saved] {os.path.join(RESULTS, 'nominal.npz')}")


if __name__ == '__main__':
    main()
