"""
STUDY I-F — the same fault questions, across the fleet
══════════════════════════════════════════════════════
Study I put twelve faults through one vehicle's actuator set.  This asks
whether what it found is a property of that vehicle or of the faults: the same
capability measures, applied to every spacecraft in the actuation-envelope
fleet, and then compared BETWEEN vehicles and between the classes they belong
to.

WHAT IS THE SAME AND WHAT HAS TO CHANGE
───────────────────────────────────────
The faults are the Study H catalogue, but that catalogue is written against one
plant (`LMParams`), so each fault is restated here as an actuator-level
perturbation any vehicle can suffer:

    engine tier   one engine dead; one engine at 15 %, 50 % or 130 % of rated
                  thrust; one nozzle misaligned by (3 deg, 2 deg); one gimbal
                  seized; one engine's valve stuck open at 30 % of rated
    RCS tier      one thruster dead; one thruster stuck full open

`stuck open` is the one that needs a fleet-wide convention, because Study I's
version was quoted as a multiple of the LM's hover share and most of this fleet
never hovers.  It is 30 % of the affected unit's own rated thrust here - a
floor the vehicle cannot throttle below, which is the structural content of the
fault, without borrowing an operating point that only a lander has.

WORST CASE, NOT FIRST CASE
──────────────────────────
Removing "thruster 0" measures the layout's numbering, not its redundancy.
Every single-unit fault is therefore applied to each unit in turn and reported
at its WORST, which is the number a redundancy argument actually needs: what
the unluckiest single failure costs.

WHAT IS MEASURED
────────────────
Volume of the attainable force and moment sets, the worst-direction support
(positive means the origin is interior and the vehicle has authority about
every axis with margin), and whether zero net wrench survives at all.  All are
reported as fractions of the same vehicle healthy, so vehicles four orders of
magnitude apart in thrust can be compared at all.

Run:  python run_fleet_capability.py
"""

import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))

RESULTS = os.path.join(HERE, 'results')

import vehicles as vh                    # noqa: E402
import campaign as cp                    # noqa: E402
import capability_lib as cl              # noqa: E402

N_DIRS = 700                 # fleet sweep: 21 vehicles x ~9 faults x n units
N_SUP = 300                  # directions for the worst-direction support
STUCK_FRAC = 0.30            # a stuck-open valve's floor, as a fraction of rated

# The catalogue, restated at actuator level.  `tier` says which units the fault
# can strike, and every fault is swept over all of them.
FAULTS = [
    dict(key='engine_out',    label='Engine out',                tier='engine'),
    dict(key='thrust_loss_85', label=r'Thrust reduction, $\eta$=0.15',
         tier='engine', eta=0.15),
    dict(key='thrust_loss_50', label=r'Thrust reduction, $\eta$=0.50',
         tier='engine', eta=0.50),
    dict(key='thrust_excess', label=r'Thrust excess, $\eta$=1.30',
         tier='engine', eta=1.30),
    dict(key='tvc_bias',      label='TVC misalignment (3°, 2°)', tier='engine'),
    dict(key='gimbal_seized', label='Gimbal seizure',            tier='engine'),
    dict(key='valve_stuck_open', label='Valve stuck open (30 % floor)',
         tier='engine'),
    dict(key='rcs_out',       label='RCS thruster dead',         tier='rcs'),
    dict(key='rcs_stuck_open', label='RCS thruster stuck open',  tier='rcs'),
]
# Faults that provably do not touch a static capability set, listed so the
# report can say so rather than leave them out silently.
TEMPORAL = ['dead_time', 'slow_thrust', 'erosion_drift (at onset)']


def to_model(veh, name=None):
    """A capability model of a fleet vehicle, healthy."""
    engines = [cl.Engine(e.pos, e.axis, 0.0, e.T_max, e.gimbal_max)
               for e in veh.engines if e.T_max > 0]
    pos = np.array([t.pos for t in veh.rcs]) if veh.rcs else np.zeros((0, 3))
    dirs = np.array([t.dir for t in veh.rcs]) if veh.rcs else np.zeros((0, 3))
    F = np.array([t.F for t in veh.rcs]) if veh.rcs else np.zeros(0)
    return cl.Model(name or veh.name, engines, pos, dirs, F,
                    veh.mass, veh.inertia)


def damaged(base, fault, unit):
    """`base` with `fault` applied to unit index `unit`. None if not applicable."""
    m = cl.Model(base.name, [cl.Engine(e.pos, e.axis, e.T_min, e.T_max,
                                       e.gimbal_max) for e in base.engines],
                 base.rcs_pos.copy(), base.rcs_dir.copy(), base.rcs_F.copy(),
                 base.mass, base.inertia, base.bias.copy())
    k = fault['key']
    if fault['tier'] == 'engine':
        if unit >= len(m.engines):
            return None
        e = m.engines[unit]
        if k == 'engine_out':
            m.engines.pop(unit)
        elif k in ('thrust_loss_85', 'thrust_loss_50', 'thrust_excess'):
            e.T_max *= fault['eta']
        elif k == 'tvc_bias':
            e.axis = cl.rot_pitch_yaw(e.axis, np.deg2rad(3.0), np.deg2rad(2.0))
        elif k == 'gimbal_seized':
            if e.gimbal_max <= 0.0:
                return None                 # nothing to seize
            e.gimbal_max = 0.0
        elif k == 'valve_stuck_open':
            e.T_min = STUCK_FRAC * e.T_max
    else:
        if unit >= m.n_rcs:
            return None
        keep = [j for j in range(m.n_rcs) if j != unit]
        if k == 'rcs_stuck_open':
            d, r, F = m.rcs_dir[unit], m.rcs_pos[unit], m.rcs_F[unit]
            m.bias = m.bias + np.concatenate([F * d, F * np.cross(r, d)])
        m.rcs_pos, m.rcs_dir = m.rcs_pos[keep], m.rcs_dir[keep]
        m.rcs_F = m.rcs_F[keep]
    return m


def measure(m, ref=None):
    """Size, reach and origin containment of both sets.

    Three measures, because no single one survives the fleet.  `volume` is the
    natural size but is identically zero for a planar set - a vehicle whose
    only actuator is one centreline gimballed engine has no roll authority, so
    its moment set is a disc.  `size` falls through to that set's own
    dimension.  `mean_support` is defined for every set and is what the fleet
    map is drawn from.
    """
    out = {}
    for key, mom in (('F', False), ('M', True)):
        P, hull = cl.attainable_set(m, moment=mom, n_dirs=N_DIRS)
        size, dim = cl.set_measure(P)
        out[f'{key}_volume'] = float(hull.volume) if hull is not None else 0.0
        out[f'{key}_size'] = size
        out[f'{key}_dim'] = dim
        out[f'{key}_authority'] = cl.mean_support(m, mom, N_SUP)
        out[f'{key}_min_support'] = cl.min_support(m, mom, N_SUP)
        out[f'{key}_origin'] = out[f'{key}_min_support'] >= -1e-9
    if ref:
        for key in ('F', 'M'):
            v, a = ref[f'{key}_volume'], ref[f'{key}_authority']
            sz, s = ref[f'{key}_size'], ref[f'{key}_min_support']
            out[f'{key}_vol_frac'] = (out[f'{key}_volume'] / v) if v > 0 else np.nan
            # same-dimension comparison only: a damaged set that has LOST a
            # dimension is reported as 0, which is the truth, not as a ratio
            # between sizes measured in different units
            out[f'{key}_size_frac'] = (
                (out[f'{key}_size'] / sz) if sz > 0 and
                out[f'{key}_dim'] >= ref[f'{key}_dim'] else
                (0.0 if sz > 0 else np.nan))
            out[f'{key}_auth_frac'] = (out[f'{key}_authority'] / a) if a > 1e-12 else np.nan
            out[f'{key}_sup_frac'] = (out[f'{key}_min_support'] / s
                                      if s > 1e-9 else np.nan)
    return out


def main():
    fleet = [v for v in vh.build_all()]
    rows, healthy = [], {}

    print(f'{"vehicle":36s} {"class":19s} units    healthy AMS support')
    for veh in fleet:
        m = to_model(veh)
        if not m.engines and m.n_rcs == 0:
            print(f'  {veh.name[:34]:36s} {veh.category[:18]:19s} '
                  f'no actuator geometry — skipped')
            continue
        h = measure(m)
        healthy[veh.name] = h
        rows.append(dict(vehicle=veh.name, category=veh.category,
                         fault='healthy', label='Healthy', tier='—',
                         n_eng=len(m.engines), n_rcs=m.n_rcs, worst_unit='—',
                         F_vol_frac=1.0, M_vol_frac=1.0, F_sup_frac=1.0,
                         M_sup_frac=1.0, applicable=True, **h))
        print(f'  {veh.name[:34]:36s} {veh.category[:18]:19s} '
              f'{len(m.engines)}e/{m.n_rcs}r   dim {h["M_dim"]}  '
              f'reach {h["M_authority"]:.3e}')

    for veh in fleet:
        if veh.name not in healthy:
            continue
        base, h = to_model(veh), healthy[veh.name]
        n_unit = {'engine': len(base.engines), 'rcs': base.n_rcs}
        for f in FAULTS:
            worst, worst_u = None, None
            for u in range(n_unit[f['tier']]):
                m = damaged(base, f, u)
                if m is None:
                    continue
                r = measure(m, h)
                # worst case = the unit whose loss costs the most moment
                # authority; ties broken on volume
                key = (r['M_auth_frac'] if np.isfinite(r['M_auth_frac'])
                       else 9.0, r['M_sup_frac'] if
                       np.isfinite(r['M_sup_frac']) else 9.0)
                if worst is None or key < worst[0]:
                    worst, worst_u = (key, r), u
            if worst is None:
                rows.append(dict(vehicle=veh.name, category=veh.category,
                                 fault=f['key'], label=f['label'],
                                 tier=f['tier'], n_eng=len(base.engines),
                                 n_rcs=base.n_rcs, worst_unit='n/a',
                                 applicable=False))
                continue
            rows.append(dict(vehicle=veh.name, category=veh.category,
                             fault=f['key'], label=f['label'], tier=f['tier'],
                             n_eng=len(base.engines), n_rcs=base.n_rcs,
                             worst_unit=worst_u, applicable=True, **worst[1]))
        print(f'  {veh.name[:34]:36s} done')

    cp.write_csv(os.path.join(RESULTS, 'IF_fleet.csv'), rows)

    # ── fingerprints: how similar are two vehicles' responses? ───────────
    keys = [f['key'] for f in FAULTS]
    by = {}
    for r in rows:
        if r['fault'] != 'healthy':
            by.setdefault(r['vehicle'], {})[r['fault']] = r
    # A vehicle with zero healthy moment authority cannot be compared to
    # anything: every retention ratio is 0/0.  In this fleet that is Juno,
    # whose single engine is centreline and rigidly mounted and whose RCS
    # layout is not modelled - a data gap, not a spacecraft without attitude
    # control.  Excluding it explicitly is the only honest option; leaving it
    # in produces a blank row that reads as a result.
    no_moment = sorted(v for v in healthy if healthy[v]['M_authority'] <= 0)
    names = [v for v in by if all(k in by[v] for k in keys)
             and v not in no_moment]
    fp, cats = {}, {}
    for v in names:
        vec = []
        for k in keys:
            r = by[v][k]
            vec.append(r['M_auth_frac'] if r.get('applicable') and
                       np.isfinite(r.get('M_auth_frac', np.nan)) else np.nan)
        fp[v] = vec
        cats[v] = next(x['category'] for x in rows if x['vehicle'] == v)

    def dist(a, b):
        """Mean absolute difference over the faults both vehicles can suffer."""
        d = [abs(x - y) for x, y in zip(fp[a], fp[b])
             if np.isfinite(x) and np.isfinite(y)]
        return float(np.mean(d)) if d else np.nan

    D = {a: {b: dist(a, b) for b in names} for a in names}
    within, between = [], []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            d = D[a][b]
            if np.isfinite(d):
                (within if cats[a] == cats[b] else between).append(d)

    head = dict(
        n_vehicles=len(healthy), n_faults=len(FAULTS), faults=FAULTS,
        temporal=TEMPORAL, stuck_frac=STUCK_FRAC, n_dirs=N_DIRS,
        rows=rows, excluded_no_moment=no_moment,
        fingerprint={v: fp[v] for v in names},
        fingerprint_faults=keys, categories=cats, distance=D,
        within_mean=float(np.mean(within)) if within else None,
        between_mean=float(np.mean(between)) if between else None,
        within_n=len(within), between_n=len(between))
    with open(os.path.join(RESULTS, 'headline_IF.json'), 'w') as fh:
        json.dump(head, fh, indent=1, default=float)

    print(f"\n[saved] results/IF_fleet.csv  ({len(rows)} rows)")
    print(f"[saved] results/headline_IF.json")
    if within:
        print(f"\nfault-response similarity (mean |difference| in AMS retention)")
        print(f"  same spacecraft class : {np.mean(within):.3f}  "
              f"({len(within)} pairs)")
        print(f"  different classes     : {np.mean(between):.3f}  "
              f"({len(between)} pairs)")


if __name__ == '__main__':
    main()
