"""
Build the actuation-envelope study
════════════════════════════════════════════════════════════════════════
    python build_report.py

Produces, in this directory:
    figures/<Spacecraft>.png     one 3-panel figure per spacecraft
    figures/_fleet_comparison.png
    actuation_envelope_summary.xlsx

The workbook has four sheets:
    Max acceleration  — per-axis max linear & angular acceleration (the ask)
    Max force-moment  — the underlying forces [N] and moments [N m]
    Provenance        — per-value SOURCED / ESTIMATED flags for every input
    Method            — what was computed and the standing caveats
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src' / 'apollo_gnc'))

from vehicles import build_all
from envelopes import axis_maxima, AXES, set_metrics
from plots import figure_for, figure_fleet

FIG_DIR = HERE / 'figures'
XLSX    = HERE / 'actuation_envelope_summary.xlsx'


def _clean(x, floor=1e-12):
    """Support-function values that should be exactly zero come back as ~1e-19
    from the hull sweep; report them as zero rather than as false precision."""
    return 0.0 if (np.isfinite(x) and abs(x) < floor) else x


def accel_table(vehicles):
    rows = []
    for v in vehicles:
        if not (v.engines or v.rcs):
            continue
        mx = axis_maxima(v)
        r = {'Category': v.category, 'Spacecraft': v.name,
             'Mass [kg]': v.mass,
             'Ixx [kg m^2]': v.inertia[0], 'Iyy [kg m^2]': v.inertia[1],
             'Izz [kg m^2]': v.inertia[2]}
        for a, _ in AXES:
            r[f'a {a} [m/s^2]'] = _clean(mx[a]['accel_ms2'])
        for a, _ in AXES:
            r[f'alpha {a} [deg/s^2]'] = _clean(np.rad2deg(mx[a]['ang_accel_rads2']))
        best = max(_clean(mx[a]['accel_ms2']) for a, _ in AXES)
        wrst = min(_clean(mx[a]['accel_ms2']) for a, _ in AXES)
        r['a best axis [m/s^2]'] = best
        r['a worst axis [m/s^2]'] = wrst
        r['a anisotropy best/worst'] = (best / wrst) if wrst > 0 else np.inf
        ba = max(_clean(np.rad2deg(mx[a]['ang_accel_rads2'])) for a, _ in AXES)
        wa = min(_clean(np.rad2deg(mx[a]['ang_accel_rads2'])) for a, _ in AXES)
        r['alpha best axis [deg/s^2]'] = ba
        r['alpha worst axis [deg/s^2]'] = wa
        r['alpha anisotropy best/worst'] = (ba / wa) if wa > 0 else np.inf
        n_est = sum(v.is_estimated(k) for k in v.flags)
        r['Inputs ESTIMATED'] = f'{n_est} of {len(v.flags)}'
        rows.append(r)
    return pd.DataFrame(rows)


def force_table(vehicles):
    rows = []
    for v in vehicles:
        if not (v.engines or v.rcs):
            continue
        mx = axis_maxima(v)
        m = set_metrics(v, n_dirs=800)
        r = {'Category': v.category, 'Spacecraft': v.name,
             'RCS thrusters': v.n_rcs, 'Main/TVC engines': v.n_engines}
        for a, _ in AXES:
            r[f'F {a} [N]'] = _clean(mx[a]['force_N'])
        for a, _ in AXES:
            r[f'M {a} [N m]'] = _clean(mx[a]['moment_Nm'])
        r['Force-set volume [N^3]']  = m['force']['volume']
        r['Moment-set volume [N^3 m^3]'] = m['moment']['volume']
        r['Force isotropy [-]']  = m['force']['isotropy']
        r['Moment isotropy [-]'] = m['moment']['isotropy']
        rows.append(r)
    return pd.DataFrame(rows)


def provenance_table(vehicles):
    rows = []
    for v in vehicles:
        for k in sorted(v.flags):
            flag = v.flags[k]
            rows.append({'Spacecraft': v.name, 'Quantity': k,
                         'Status': flag.split('(')[0].strip(),
                         'Basis': flag})
    return pd.DataFrame(rows)


METHOD = [
    ('What this workbook contains',
     'Per-axis maximum linear and angular acceleration for each spacecraft in '
     'spacecraft_values.xlsx, derived from the achievable force set and '
     'achievable moment set of its actuators.'),
    ('Achievable set definition',
     'Each RCS thruster is throttleable in [0, F] along a fixed direction, so it '
     'contributes a line segment to the set; summing them gives a zonotope. Each '
     'gimballed engine contributes T*d with T in [0, T_max] and d ranging over a '
     'spherical cap of half-angle equal to the gimbal limit. The reported set is '
     'the convex hull of the total, recovered exactly by a support-function sweep '
     'over a Fibonacci sphere of directions.'),
    ('Per-axis maxima',
     'Max force along an axis is the support function of the force set evaluated '
     'on that axis; +x and -x are reported separately because layouts are often '
     'asymmetric. Linear acceleration = F/m. Angular acceleration = M/I_jj.'),
    ('CAVEAT — geometry is not in the source workbook',
     'spacecraft_values.xlsx contains thrust magnitudes, actuator counts and '
     'masses only. It has NO thruster positions, NO thrust direction vectors, NO '
     'gimbal limits and NO inertia tensors. All four were supplied in '
     'vehicles.py / geometry_db.py and are flagged per value on the Provenance '
     'sheet. Any row whose geometry is ESTIMATED yields a moment and an angular '
     'acceleration that are indicative, not authoritative.'),
    ('CAVEAT — inertia is a shape model',
     'Inertia is derived from mass plus an approximate published envelope using a '
     'uniform-density cylinder or box, except the Apollo Lunar Module, which uses '
     'the published rigid-body inertia already validated in apollo_full.py. '
     'Uniform density understates inertia for a vehicle with heavy peripheral '
     'items and therefore OVERSTATES angular acceleration.'),
    ('CAVEAT — angular acceleration neglects coupling',
     'alpha_j = M_j / I_jj ignores products of inertia and the gyroscopic term '
     'omega x (I omega). It is an instantaneous small-rate figure, valid at rest.'),
    ('CAVEAT — moment arms are taken about the geometric CG',
     'The true CG moves with propellant load; a shifted CG changes every moment '
     'arm and hence the whole moment set. Values are for the nominal CG only.'),
    ('Most reliable rows',
     'Apollo Lunar Module — geometry, gimbal limit and inertia all come from this '
     "repository's validated model and reproduce its allocation matrix exactly."),
]


def main():
    FIG_DIR.mkdir(exist_ok=True)
    vehicles = build_all()

    print('Rendering figures ...')
    made = 0
    for v in vehicles:
        if not (v.engines or v.rcs):
            print(f'  [skip] {v.name:40s} no usable actuator data')
            continue
        p = figure_for(v, FIG_DIR)
        made += 1
        print(f'  [ok]   {v.name:40s} -> {p.name}')
    print(f'  [ok]   fleet comparison -> {figure_fleet(vehicles, FIG_DIR).name}')

    print('Writing workbook ...')
    acc, frc, prov = accel_table(vehicles), force_table(vehicles), provenance_table(vehicles)
    meth = pd.DataFrame(METHOD, columns=['Topic', 'Detail'])

    with pd.ExcelWriter(XLSX, engine='openpyxl') as xw:
        acc.to_excel(xw, 'Max acceleration', index=False)
        frc.to_excel(xw, 'Max force-moment', index=False)
        prov.to_excel(xw, 'Provenance', index=False)
        meth.to_excel(xw, 'Method', index=False)
        for sheet, df in (('Max acceleration', acc), ('Max force-moment', frc),
                          ('Provenance', prov), ('Method', meth)):
            ws = xw.sheets[sheet]
            for i, col in enumerate(df.columns, start=1):
                w = max(len(str(col)), *(len(str(x)) for x in df[col].head(60)))
                ws.column_dimensions[ws.cell(1, i).column_letter].width = min(w + 2, 60)
            ws.freeze_panes = 'C2' if sheet.startswith('Max') else 'A2'

    print(f'\n{made} spacecraft figures in {FIG_DIR}')
    print(f'workbook: {XLSX}')
    return acc


if __name__ == '__main__':
    df = main()
    pd.set_option('display.width', 250)
    print('\n', df[['Spacecraft', 'a best axis [m/s^2]', 'a worst axis [m/s^2]',
                    'alpha best axis [deg/s^2]', 'Inputs ESTIMATED']].to_string(index=False))
