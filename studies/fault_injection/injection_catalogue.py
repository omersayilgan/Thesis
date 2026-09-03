"""
STUDY H — the fault set
═══════════════════════
The Study G catalogue minus the gimbal-actuator faults, rebuilt on the
y_eng = 0.25 m vehicle.

Why gimbal faults are out
─────────────────────────
This study is about what a *thrust-side* engine fault does to a descent, so the
four faults whose subject is the gimbal actuator's own response — bandwidth
loss, light damping, seizure and effectiveness loss — are excluded.

Thrust-vector misalignment is kept, and the distinction is worth stating
because it looks like a borderline call.  It is not a property of the gimbal
*response* at all: it is a fixed angular offset of the nozzle, from asymmetric
throat erosion, that no command can null and that would be present if the
gimbal were welded solid.  It is also the catalogue's only other additive
fault, so dropping it would leave the additive class represented by chugging
alone.  If it should go too, delete the one entry.

Twelve plants, all faults on engine 2 (index 1, body station y = +0.25 m).
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

import apollo_full as af          # noqa: E402
import apollo_nominal as an       # noqa: E402

D2R = np.deg2rad
_REF = an.make_lm()
ENG = 1
T_HOV_ENG = _REF.T_hover / _REF.n_eng


class FaultCase:
    def __init__(self, key, label, short, section, structure, temporal,
                 detail, failed=(), **plant):
        self.key, self.label, self.short = key, label, short
        self.section, self.structure = section, structure
        self.temporal, self.detail = temporal, detail
        self.failed = tuple(failed)
        self.plant = plant

    def lm(self):
        """The vehicle this fault leaves behind — always at y_eng = 0.25 m."""
        return an.make_lm(**self.plant)

    @property
    def klass(self):
        if self.structure == 'none':
            return 'none'
        return ('multiplicative' if 'multiplicative' in self.structure
                else self.structure)

    def __repr__(self):
        return f'FaultCase({self.key})'


CATALOGUE = [
    FaultCase(
        'healthy', 'Healthy (control)', 'healthy', '—', 'none', '—',
        'nominal plant; measures what the injection point alone costs'),

    FaultCase(
        'thrust_loss_50', r'Thrust reduction, $\eta$=0.50', r'$\eta$=0.50',
        '2.1', 'multiplicative', 'abrupt / incipient',
        'engine 2 delivers half of its internal thrust (turbopump '
        'degradation, injector blockage, throat erosion)',
        thrust_eff_eng={ENG: 0.50}),
    FaultCase(
        'thrust_loss_85', r'Thrust reduction, $\eta$=0.15', r'$\eta$=0.15',
        '2.1', 'multiplicative', 'abrupt',
        'engine 2 delivers 15 % — near-total gain loss with the gimbal alive',
        thrust_eff_eng={ENG: 0.15}),
    FaultCase(
        'thrust_excess', r'Thrust excess, $\eta$=1.30', r'$\eta$=1.30',
        '2.2', 'multiplicative', 'abrupt',
        'pressurant regulator runaway: engine 2 delivers 130 % of commanded',
        thrust_eff_eng={ENG: 1.30}),
    FaultCase(
        'valve_stuck_open', 'Valve stuck open (thrust floor)', 'stuck open',
        '2.2 / 1.4', 'structural', 'abrupt',
        f'engine 2 cannot be throttled below {1.35 * T_HOV_ENG:.0f} N '
        '(1.35x its hover share) — the input set itself is cut',
        T_min_eng_ovr={ENG: 1.35 * T_HOV_ENG}),
    FaultCase(
        'engine_out', 'Engine out', 'engine out',
        '2.1 / 3.1', 'structural', 'abrupt',
        'engine 2 dead: thrust and both gimbals pinned to zero for the rest '
        'of the flight',
        failed=(ENG,)),
    FaultCase(
        'slow_thrust', r'Slow thrust response, $\tau_T$=2.5 s',
        r'$\tau_T$=2.5 s', '2.5', 'multiplicative', 'incipient',
        'engine 2 thrust lag grows from 0.4 s to 2.5 s (valve friction, '
        'coking, actuator supply loss) with the gain untouched',
        tau_T_eng={ENG: 2.5}),
    FaultCase(
        'tvc_bias', 'Thrust-vector misalignment (3°, 2°)', 'TVC bias',
        '2.7', 'additive', 'incipient',
        'asymmetric nozzle erosion leaves engine 2 pointing 3° in pitch and '
        '2° in yaw off its commanded axis, independent of command',
        gimbal_bias_eng={ENG: (D2R(3.0), D2R(2.0))}),
    FaultCase(
        'chugging', 'Thrust oscillation (chugging)', 'chugging',
        '2.3', 'additive', 'intermittent / forced',
        'feed-coupled instability: engine 2 thrust rings at 0.25 Hz with an '
        'amplitude of 20 % of its hover share, regardless of throttle',
        thrust_osc_eng={ENG: (0.20, 1.6)}),
    FaultCase(
        'dead_time', 'Transport delay (1 interval)', 'dead time',
        '2.6', 'structural', 'abrupt / intermittent',
        "a vapour pocket in engine 2's feed line delays every command by one "
        'full control interval (1 s)',
        u_delay_eng={ENG: 1}),
    FaultCase(
        'mixture_ratio', 'Mixture-ratio shift (coupled)', 'mixture ratio',
        '2.4', 'multiplicative (coupled)', 'incipient',
        'oxidiser-side erosion on engine 2: gain falls to 0.75 *and* the '
        'combustion time constant grows to 1.2 s',
        thrust_eff_eng={ENG: 0.75}, tau_T_eng={ENG: 1.2}),
    FaultCase(
        'erosion_drift', 'Throat-erosion drift', 'erosion drift',
        '2.10', 'time-varying multiplicative', 'incipient',
        'engine 2 efficiency decays at 1.2 %/s from the moment of injection: '
        'healthy at onset, 0.52 forty seconds later',
        eta_rate_eng={ENG: -0.012}),
]

CASES = {c.key: c for c in CATALOGUE}
KEYS = [c.key for c in CATALOGUE]
CLASS_ORDER = ['none', 'additive', 'multiplicative', 'structural']


def ordered_keys():
    """Catalogue order regrouped by FTC fault class, for figures and tables."""
    return [k for cl in CLASS_ORDER for k in KEYS if CASES[k].klass == cl]
