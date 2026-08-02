"""
Per-vehicle actuator layouts for the 21 spacecraft in spacecraft_values.xlsx
════════════════════════════════════════════════════════════════════════════
Thrust magnitudes, actuator counts and masses are read live from the workbook
(SOURCED). Geometry and inertia are defined here (ESTIMATED unless noted),
each with the basis of the assumption recorded in the `flags` dict.

Dimensions below are approximate published envelope sizes used only to place
actuators and to drive the inertia shape model. They are deliberately kept in
one table so a reader can audit or replace them in a single place.
"""

import numpy as np
import pandas as pd
from pathlib import Path

from geometry_db import (Vehicle, Thruster, GimbalEngine,
                         inertia_cylinder, inertia_box,
                         quad_ring, face_pairs, canted_ring, branch_clusters)

WORKBOOK = Path(__file__).resolve().parents[2] / 'ExcelSheets' / 'spacecraft_values.xlsx'

# ── characteristic envelope dimensions ───────────────────────────────────
# (shape, primary dim [m], secondary dim [m]) — cylinder: (radius, height);
# box: stored as (a, b, c) triples. Approximate published bus/stage envelopes.
DIMS = {
    'Delta IV Heavy':                       ('cyl', 2.5,  70.0),
    'Ariane 5 ECA':                         ('cyl', 2.7,  50.0),
    'Vega-C':                               ('cyl', 1.7,  35.0),
    'Vega':                                 ('cyl', 1.5,  30.0),
    'GRACE-FO (per satellite)':             ('box', (3.1, 1.9, 0.8)),
    'Sentinel-3A':                          ('box', (3.9, 2.2, 2.2)),
    'SMAP':                                 ('box', (1.5, 1.5, 1.8)),
    'Sentinel-1A':                          ('box', (2.8, 2.5, 4.0)),
    'Solar Dynamics Observatory (SDO)':     ('box', (2.2, 2.2, 4.5)),
    'Meteosat Second Generation (MSG)':     ('cyl', 1.6,  2.4),
    'GOES-16 (GOES-R)':                     ('box', (3.0, 2.5, 6.1)),
    'GOES-19 (GOES-U)':                     ('box', (3.0, 2.5, 6.1)),
    'Orion (CM + European Service Module)': ('cyl', 2.5,  8.0),
    'Apollo Command & Service Module':      ('cyl', 1.96, 11.0),
    'Apollo Lunar Module':                  ('cyl', 2.1,  7.0),
    'Crew Dragon (Dragon 2)':               ('cyl', 2.0,  8.1),
    'Juno':                                 ('cyl', 1.8,  3.5),
    'Cassini (Cassini-Huygens)':            ('cyl', 2.0,  6.8),
    'New Horizons':                         ('box', (2.1, 2.1, 0.7)),
    'Europa Clipper':                       ('box', (3.0, 2.8, 5.0)),
    'Voyager 1':                            ('cyl', 0.9,  0.5),
}

# Gimbal cone half-angles [deg]. 0.0 = rigidly mounted (no TVC).
GIMBAL = {
    'Delta IV Heavy':                       (6.0,  'ESTIMATED (typical large LOX/LH2 gimballed engine throw)'),
    'Ariane 5 ECA':                         (6.0,  'ESTIMATED (typical cryogenic core-stage gimbal throw)'),
    'Vega-C':                               (6.5,  'ESTIMATED (P120C flex-bearing nozzle TVC)'),
    'Vega':                                 (6.5,  'ESTIMATED (P80 flex-bearing nozzle TVC)'),
    'Orion (CM + European Service Module)': (6.0,  'ESTIMATED (OMS-E derived gimbal authority)'),
    'Apollo Command & Service Module':      (4.5,  'ESTIMATED (SPS gimbal throw, pitch/yaw)'),
    'Apollo Lunar Module':                  (6.0,  'SOURCED (apollo_full.py LMParams.gimbal_max)'),
    'Cassini (Cassini-Huygens)':            (2.0,  'ESTIMATED (main-engine gimbal actuator, small throw)'),
}

# Which vehicles have a genuinely gimballed main engine at all. Everything
# else is treated as rigidly mounted, which is the conservative assumption:
# a fixed engine contributes force but almost no controllable moment.
FIXED_ENGINE_NOTE = 'ESTIMATED (treated as rigidly mounted — no published TVC)'

# Masses the workbook records as "n/d". Supplying them here keeps two major
# vehicles in the study rather than dropping them; both are flagged ESTIMATED
# and the value used is printed in the summary sheet.
MASS_FALLBACK = {
    'SMAP':                   (944.0,   'ESTIMATED (workbook n/d; approx. published launch mass)'),
    'Crew Dragon (Dragon 2)': (12519.0, 'ESTIMATED (workbook n/d; approx. published launch mass)'),
}

# Firing restrictions stated in the workbook's own engine designation text.
MAX_ENGINES_ON = {
    'Europa Clipper': (8, 'SOURCED (workbook: "24 installed; max 8 fired simultaneously")'),
}

# Engine axial offset below the CG [m], overriding the generic "aft plane"
# placement. The moment arm is the single most influential geometric quantity
# for the moment set, so where a validated value exists it must be used.
ENGINE_Z = {
    'Apollo Lunar Module': (2.5, 'SOURCED (apollo_full.py LMParams.dz_eng)'),
}


def _read_workbook():
    d = pd.read_excel(WORKBOOK, 'Data')
    num = lambda v: (np.nan if (pd.isna(v) or str(v).strip() in ('n/d', 'None', ''))
                     else float(v))
    rows = {}
    for _, r in d.iterrows():
        rows[str(r['Spacecraft'])] = dict(
            category=str(r['Category']),
            F_main=num(r['Main engine thrust, each [N]']),
            n_main=num(r['No. of main engines']),
            F_rcs=num(r['RCS thrust, each [N]']),
            n_rcs=num(r['No. of RCS thrusters']),
            mass=num(r['Reference mass, as published [kg]']),
            eng_desig=str(r['Main / TVC engine designation']),
            rcs_desig=str(r['RCS thruster designation']))
    return rows


def _inertia(name, mass):
    spec = DIMS[name]
    if spec[0] == 'cyl':
        _, R, H = spec
        return inertia_cylinder(mass, R, H), f'uniform cylinder R={R} m, H={H} m'
    _, (a, b, c) = spec
    return inertia_box(mass, a, b, c), f'uniform box {a}x{b}x{c} m'


def _extent(name):
    """(ring radius, half-height) used to place actuators."""
    spec = DIMS[name]
    if spec[0] == 'cyl':
        return spec[1], spec[2] / 2.0
    a, b, c = spec[1]
    return max(a, b) / 2.0, c / 2.0


def build_all():
    """Construct every Vehicle. Returns a list in workbook order."""
    wb = _read_workbook()
    out = []

    for name, w in wb.items():
        mass, mass_flag = w['mass'], 'SOURCED (workbook: Reference mass, as published)'
        if not np.isfinite(mass) and name in MASS_FALLBACK:
            mass, mass_flag = MASS_FALLBACK[name]
        if not np.isfinite(mass):
            # no published mass anywhere -> cannot form accelerations at all
            out.append(Vehicle(name=name, category=w['category'], mass=np.nan,
                               inertia=np.full(3, np.nan),
                               flags={'mass': 'MISSING (workbook: n/d)'},
                               notes='No published mass; excluded from accelerations.'))
            continue

        R, hz = _extent(name)
        I, shape_txt = _inertia(name, mass)
        flags = {
            'mass':            mass_flag,
            'thrust_main':     'SOURCED (workbook: Main engine thrust, each)',
            'thrust_rcs':      'SOURCED (workbook: RCS thrust, each)',
            'counts':          'SOURCED (workbook: No. of main engines / RCS thrusters)',
            'dimensions':      f'ESTIMATED (approx. published envelope: {shape_txt})',
            'inertia':         f'ESTIMATED (shape model: {shape_txt}, uniform density)',
        }

        # ── main / TVC engines ───────────────────────────────────────────
        engines = []
        n_main = int(w['n_main']) if np.isfinite(w['n_main']) else 0
        F_main = w['F_main'] if np.isfinite(w['F_main']) else 0.0
        if n_main > 0 and F_main > 0:
            gim_deg, gim_flag = GIMBAL.get(name, (0.0, FIXED_ENGINE_NOTE))
            flags['gimbal'] = gim_flag
            z_eng, z_flag = ENGINE_Z.get(name, (hz, None))
            if n_main == 1:
                pos = [np.array([0.0, 0.0, z_eng])]
                flags['engine_position'] = z_flag or (
                    f'ESTIMATED (single engine on the centreline, {z_eng:.2f} m aft of the CG)')
            else:
                # multiple engines spread on an aft ring
                r_eng = 0.55 * R
                pos = [np.array([r_eng * np.cos(a), r_eng * np.sin(a), z_eng])
                       for a in 2 * np.pi * np.arange(n_main) / n_main]
                flags['engine_position'] = z_flag or (
                    f'ESTIMATED ({n_main} engines on an aft ring of radius {r_eng:.2f} m, '
                    f'{z_eng:.2f} m aft of the CG)')
            for p in pos:
                engines.append(GimbalEngine(p, np.array([0., 0., -1.]),
                                            F_main, np.deg2rad(gim_deg)))

        # ── RCS ──────────────────────────────────────────────────────────
        rcs = []
        n_r = int(w['n_rcs']) if np.isfinite(w['n_rcs']) else 0
        F_r = w['F_rcs'] if np.isfinite(w['F_rcs']) else 0.0
        if n_r > 0 and not np.isfinite(w['F_rcs']):
            flags['rcs_layout'] = ('MISSING (workbook lists thrusters but records per-unit '
                                   'thrust as n/d — RCS tier omitted from the envelope)')
        elif n_r == 0 and np.isfinite(w['F_rcs']) and w['F_rcs'] == 0:
            flags['rcs_layout'] = 'N/A (no RCS tier at vehicle level per workbook)'
        if n_r > 0 and F_r > 0:
            if name == 'Apollo Lunar Module':
                # the one layout this repository already models and validates
                rcs = quad_ring(4, 1.7, 0.0, F_r)
                flags['rcs_layout'] = ('SOURCED (apollo_full.py rcs_geometry(): 4 quads at '
                                       '45/135/225/315 deg, arm 1.7 m, 4 jets per quad)')
            elif name == 'Apollo Command & Service Module':
                rcs = quad_ring(4, R, 0.0, F_r)
                flags['rcs_layout'] = ('ESTIMATED (4 quads x 4 engines per workbook, placed '
                                       f'on the {R:.2f} m service-module radius)')
            elif name == 'Orion (CM + European Service Module)':
                rcs = quad_ring(6, R, 0.0, F_r)
                flags['rcs_layout'] = ('ESTIMATED (6 clusters of 4 per workbook, placed on '
                                       f'the {R:.2f} m service-module radius)')
            elif name == 'Crew Dragon (Dragon 2)':
                # 4 Draco pods rather than a purely radial canted ring: a ring
                # canted only outward has zero tangential component, so every
                # r x d is yaw-free and the vehicle models as having no yaw
                # authority at all — which a 16-thruster RCS plainly does have.
                rcs = branch_clusters(n_r, R, 0.3 * hz, F_r, n_clusters=4)
                flags['rcs_layout'] = ('ESTIMATED (16 Draco thrusters in 4 pods around the '
                                       f'bus at radius {R:.2f} m)')
            elif name in ('GRACE-FO (per satellite)', 'New Horizons'):
                per = max(1, -(-n_r // 6))
                a, b, c = DIMS[name][1]
                rcs = face_pairs((a / 2, b / 2, c / 2), F_r, n_per_face=per)
                flags['rcs_layout'] = (f'ESTIMATED ({per} thruster(s) per face on all six '
                                       'faces of the bus envelope)')
            else:
                rcs = branch_clusters(n_r, R, 0.0, F_r, n_clusters=4)
                flags['rcs_layout'] = (f'ESTIMATED ({n_r} thrusters spread over 4 clusters at '
                                       f'45/135/225/315 deg on a ring of radius {R:.2f} m)')

            # keep the actuator count faithful to the workbook
            rcs = rcs[:n_r] if len(rcs) > n_r else rcs

        # the LM's inertia is published in this repo's own validated model
        if name == 'Apollo Lunar Module':
            I = np.array([5368.0, 5368.0, 5040.0])
            flags['inertia'] = 'SOURCED (apollo_full.py LMParams Ixx/Iyy/Izz)'
            flags['mass'] = ('SOURCED (workbook reference mass; note apollo_full.py '
                             'models the 7711 kg landing configuration)')
            shape_txt = 'published rigid-body inertia'

        max_on = None
        if name in MAX_ENGINES_ON:
            max_on, flags['engine_firing_limit'] = MAX_ENGINES_ON[name]

        out.append(Vehicle(name=name, category=w['category'], mass=mass,
                           inertia=I, rcs=rcs, engines=engines, flags=flags,
                           shape=shape_txt, max_engines_on=max_on,
                           notes=f"{w['eng_desig']} | {w['rcs_desig']}"))
    return out


if __name__ == '__main__':
    for v in build_all():
        est = sum(v.is_estimated(k) for k in v.flags)
        print(f'{v.name:40s} m={v.mass!s:>8} rcs={v.n_rcs:3d} eng={v.n_engines:2d} '
              f'flags={len(v.flags)} estimated={est}')
