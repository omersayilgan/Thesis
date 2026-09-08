"""
STUDY I — the capability-space campaign
═══════════════════════════════════════
For every fault in the Study H catalogue, compute what the damaged vehicle can
still push and twist with, and check whether the one wrench it actually needs -
its own weight held with no net moment - is still inside that set.

Three questions, in order:

  1. WHAT DOES THE FAULT DO TO THE SETS?  Volume, per-axis authority, isotropy
     and origin containment of the attainable force and moment sets, against
     the healthy vehicle.

  2. IS THE OPERATING POINT STILL INSIDE?  The hover wrench is one point in
     R^6.  A set can lose most of its volume and keep it (survivable) or keep
     most of its volume and lose it (not).  The LP in capability_lib measures
     how far short the vehicle falls.

  3. WHAT DOES REDUNDANCY BUY?  The same two questions asked of a vehicle
     missing one actuator at a time - each of the 16 RCS thrusters, then each
     engine - and asked at both engine spacings, because engine-out authority
     is entirely a question of the moment arm the layout leaves behind.

Run:  python run_capability_study.py
"""

import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_injection'))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))

RESULTS = os.path.join(HERE, 'results')

import apollo_nominal as an              # noqa: E402
import apollo_full as af                 # noqa: E402
import injection_catalogue as ic         # noqa: E402
import campaign as cp                    # noqa: E402
import capability_lib as cl              # noqa: E402

N_DIRS = 1200
EROSION_TIMES = [0.0, 10.0, 20.0, 40.0]   # seconds after onset, for the drift


def classify(healthy, m, slack_h, slack_f, tol=0.02):
    """Which of the four capability effects the fault has.

    The categories are the study's own vocabulary and they are decided from
    the numbers, not asserted: a fault that leaves volume, axes and origin
    containment untouched is `unchanged` however lethal Study H found it.
    """
    vf = m['force']['volume'] / (healthy['force']['volume'] or 1.0)
    vm = m['moment']['volume'] / (healthy['moment']['volume'] or 1.0)
    if not (m['force']['contains_origin'] and m['moment']['contains_origin']):
        return 'punctured'
    if vf > 1.0 + tol or vm > 1.0 + tol:
        return 'enlarged'
    if vf < 1.0 - tol or vm < 1.0 - tol:
        return 'shrunk'
    # same volume: has the set moved? compare per-axis support directly
    for key in ('force', 'moment'):
        for lab in healthy[key]['axes']:
            a, b = healthy[key]['axes'][lab], m[key]['axes'][lab]
            if abs(a - b) > tol * max(abs(a), 1.0):
                return 'deformed'
    return 'unchanged'


def summarise(m, healthy=None, extra=None, F_z=None, cond_ref=None):
    met = cl.metrics(m, N_DIRS)
    row = dict(
        n_eng=m.n_eng, n_rcs=m.n_rcs,
        F_volume=met['force']['volume'], M_volume=met['moment']['volume'],
        F_max=met['force']['max_norm'], M_max=met['moment']['max_norm'],
        F_isotropy=met['force']['isotropy'], M_isotropy=met['moment']['isotropy'],
        F_origin=met['force']['contains_origin'],
        M_origin=met['moment']['contains_origin'])
    for key, tag in (('force', 'F'), ('moment', 'M')):
        for lab, v in met[key]['axes'].items():
            row[f'{tag}{lab}'] = v
    if healthy is not None:
        row['F_vol_frac'] = met['force']['volume'] / (healthy['force']['volume'] or 1)
        row['M_vol_frac'] = met['moment']['volume'] / (healthy['moment']['volume'] or 1)
    if F_z is not None:
        # the moment authority left while the vehicle is holding itself up -
        # the set an allocator actually draws from, and the one that separates
        # faults the unconstrained AMS reports as identical
        _, hull = cl.conditional_moment_set(m, F_z)
        row['C_volume'] = float(hull.volume) if hull is not None else 0.0
        row['hover_holdable'] = hull is not None
        if cond_ref:
            row['C_vol_frac'] = row['C_volume'] / (cond_ref or 1.0)
    row.update(extra or {})
    return row, met


def main():
    lm0 = an.make_lm()                      # y_eng = 0.25 m, the Study H plant
    w_hover = cl.hover_wrench(lm0)

    F_z_hover = -lm0.T_hover               # body -z holds the vehicle up
    m_h = cl.model_from_lm(lm0, None, 'healthy')
    row_h, met_h = summarise(m_h, F_z=F_z_hover)
    cond_h = row_h['C_volume']
    slack_h = cl.wrench_slack(m_h, w_hover)
    print(f'healthy: AFS volume {row_h["F_volume"]:.3e} N^3, '
          f'AMS volume {row_h["M_volume"]:.3e} (N m)^3, '
          f'hover wrench slack {slack_h:.1f}')

    # ── 1. every fault in the catalogue ──────────────────────────────────
    rows = []
    for key in ic.ordered_keys():
        case = ic.CASES[key]
        lm = case.lm()
        m = cl.model_from_lm(lm, case, key)
        band = cl.chugging_band(lm, case)
        if band is not None:               # keep only the guaranteed authority
            i, amp = band
            for e in m.engines:
                e.T_max = max(e.T_min, e.T_max - amp)
        row, met = summarise(m, met_h, F_z=F_z_hover, cond_ref=cond_h)
        slack = cl.wrench_slack(m, w_hover)
        trim = cl.wrench_slack(m, w_hover, free=(0, 1))
        row.update(fault=key, label=case.label, short=case.short,
                   klass=case.klass, structure=case.structure,
                   section=case.section, temporal=case.temporal,
                   hover_slack=slack, hover_ok=slack <= 1e-6,
                   trim_slack=trim, trim_ok=trim <= 1e-6,
                   effect=classify(met_h, met, slack_h, slack),
                   chugging_derated=band is not None)
        rows.append(row)
        print(f'  {case.short[:26]:28s} {row["effect"]:10s} '
              f'AFS {row["F_vol_frac"]:5.2f}x  AMS {row["M_vol_frac"]:5.2f}x  '
              f'AMS|hover {row["C_vol_frac"]:5.2f}x  hover slack {slack:6.1f}')

    cp.write_csv(os.path.join(RESULTS, 'I_faults.csv'), rows)

    # ── 2. the erosion drift, as a function of time ──────────────────────
    drift = []
    case = ic.CASES['erosion_drift']
    for t in EROSION_TIMES:
        m = cl.model_from_lm(case.lm(), case, 'erosion_drift', t=t)
        row, _ = summarise(m, met_h, dict(t=t), F_z=F_z_hover,
                           cond_ref=cond_h)
        row['hover_slack'] = cl.wrench_slack(m, w_hover)
        drift.append(row)
    cp.write_csv(os.path.join(RESULTS, 'I_erosion.csv'), drift)
    print(f'\nerosion drift: AMS {drift[0]["M_vol_frac"]:.2f}x at t=0 -> '
          f'{drift[-1]["M_vol_frac"]:.2f}x at t={EROSION_TIMES[-1]:.0f} s')

    # ── 3. redundancy: lose one actuator at a time ───────────────────────
    red = []
    for j in range(m_h.n_rcs):
        m = cl.model_from_lm(lm0, None, f'rcs{j}')
        keep = [k for k in range(m.n_rcs) if k != j]
        m.rcs_pos, m.rcs_dir = m.rcs_pos[keep], m.rcs_dir[keep]
        m.rcs_F = m.rcs_F[keep]
        row, _ = summarise(m, met_h, dict(unit=f'RCS {j}', kind='rcs'),
                           F_z=F_z_hover, cond_ref=cond_h)
        row['hover_slack'] = cl.wrench_slack(m, w_hover)
        red.append(row)
    for i in range(lm0.n_eng):
        lm = an.make_lm()
        m = cl.model_from_lm(lm, type('C', (), {'failed': (i,)})(), f'eng{i}')
        row, _ = summarise(m, met_h, dict(unit=f'Engine {i}', kind='engine'),
                           F_z=F_z_hover, cond_ref=cond_h)
        row['hover_slack'] = cl.wrench_slack(m, w_hover)
        red.append(row)
    cp.write_csv(os.path.join(RESULTS, 'I_redundancy.csv'), red)
    worst = min(red, key=lambda r: r['M_vol_frac'])
    print(f'redundancy: worst single loss is {worst["unit"]} '
          f'(AMS {worst["M_vol_frac"]:.2f}x)')

    # ── 4. engine-out against engine spacing: the trim threshold ─────────
    spacing = []
    y_lim = lm0.dz_eng * np.tan(lm0.gimbal_max)
    # dense around the analytic threshold, coarse elsewhere: the interesting
    # behaviour is entirely within a few centimetres of dz*tan(delta)
    ys = np.unique(np.round(np.concatenate([
        np.linspace(0.05, 2.0, 40),
        np.linspace(max(0.05, y_lim - 0.06), y_lim + 0.06, 25)]), 4))
    for y in ys:
        # LMParams directly: make_lm() pins y_eng to the study's value
        lm = af.LMParams(y_eng=float(y))
        m = cl.model_from_lm(lm, type('C', (), {'failed': (1,)})(), 'engine_out')
        w = cl.hover_wrench(lm)
        s = cl.wrench_slack(m, w, free=(0, 1))          # trim the MOMENT
        # the same question with the RCS tier removed, to separate what the
        # gimbal can trim from what the thrusters are quietly covering
        m2 = cl.model_from_lm(lm, type('C', (), {'failed': (1,)})(), 'no_rcs')
        m2.rcs_pos, m2.rcs_dir = m2.rcs_pos[:0], m2.rcs_dir[:0]
        m2.rcs_F = m2.rcs_F[:0]
        s2 = cl.wrench_slack(m2, w, free=(0, 1))
        spacing.append(dict(y_eng=float(y), trim_slack=s, trim_ok=s <= 1e-6,
                            trim_slack_no_rcs=s2, trim_ok_no_rcs=s2 <= 1e-6))
    cp.write_csv(os.path.join(RESULTS, 'I_spacing.csv'), spacing)
    ok = [r['y_eng'] for r in spacing if r['trim_ok_no_rcs']]
    print(f'engine-out on the gimbal alone: trimmable up to y_eng = '
          f'{max(ok) if ok else float("nan"):.3f} m '
          f'(analytic limit dz*tan(delta) = {y_lim:.3f} m)')

    head = dict(
        healthy=row_h, healthy_slack=slack_h, cond_healthy=cond_h,
        hover_wrench=list(w_hover), y_eng=lm0.y_eng,
        y_trim_limit=float(y_lim),
        y_trim_measured=float(max(ok)) if ok else None,
        gimbal_deg=float(np.rad2deg(lm0.gimbal_max)), dz_eng=lm0.dz_eng,
        T_max_eng=lm0.T_max_eng, T_hover=lm0.T_hover,
        F_rcs_per=lm0.F_rcs_per, n_rcs=m_h.n_rcs, n_eng=lm0.n_eng,
        mass=lm0.mass, inertia=[lm0.Ixx, lm0.Iyy, lm0.Izz],
        erosion_times=EROSION_TIMES, n_dirs=N_DIRS,
        faults=rows, erosion=drift, redundancy=red, spacing=spacing)
    with open(os.path.join(RESULTS, 'headline_I.json'), 'w') as fh:
        json.dump(head, fh, indent=1, default=float)
    print(f"\n[saved] {os.path.join(RESULTS, 'headline_I.json')}")


if __name__ == '__main__':
    main()
