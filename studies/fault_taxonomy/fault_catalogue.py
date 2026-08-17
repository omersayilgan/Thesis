"""
STUDY G — Fault taxonomy x initial-condition regime
═══════════════════════════════════════════════════
Catalogue side of the study: the sixteen plant configurations under test and
the five initial-condition regimes they are tested from.

Where this sits relative to the earlier studies
───────────────────────────────────────────────
Studies A-C each took *one* fault and flew it well.  Study F took three fault
families and asked whether a fault is expressible as an initial condition (it is
not: the plant change persists).  Study G takes the fault catalogue of
`docs/spacecraft_engine_fault_framework.md` seriously and instantiates **one
plant per dynamic-effect category** — eleven of them, plus severity variants —
then measures the landing probability of each from five *different* regions of
the state space.

The two axes are therefore
    FAULT   — which of the framework's dynamic effects the vehicle has, and
              (per framework section 3) whether it is additive, multiplicative
              or structural;
    REGIME  — where the vehicle is when it has to fly with it.

and the deliverable is the landing probability over their product, because
neither axis answers the question alone: a fault that is survivable on a high,
calm approach is not the same fault at 300 m with the vehicle already rolling.

Pairing
───────
Initial conditions are drawn once per regime and reused for every plant, so any
difference in landing rate within a regime column is attributable to the plant
alone (common random numbers).  That also makes the fault-vs-healthy comparison
a within-sample McNemar test rather than two independent proportions.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))   # fault_lib, campaign
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))        # shared engine

import apollo_full as af
import fault_lib as fl


D2R = np.deg2rad
_REF = af.LMParams()          # reference vehicle, for expressing faults in its own units


# ══════════════════════════════════════════════════════════════════════
#  1. THE FAULT CATALOGUE
# ══════════════════════════════════════════════════════════════════════
#  Every entry names the framework section it instantiates and the FTC fault
#  structure that section assigns it (framework sections 4-5).  All faults are
#  on engine 2 (index 1); engine 1 stays healthy, so each case is an asymmetry
#  the vehicle has to trim as well as a loss of performance.
#
#  Severity is chosen so the catalogue spans the interesting range rather than
#  the survivable one: several of these are meant to be lost most of the time.
#  A taxonomy in which everything lands measures nothing.
# ══════════════════════════════════════════════════════════════════════

ENG = 1                                   # the faulted engine (0-based)
T_HOV_ENG = _REF.T_hover / _REF.n_eng     # 6262 N — one engine's hover share


class FaultCase:
    """One plant configuration: what the vehicle *is* after the fault."""

    def __init__(self, key, label, short, section, structure, temporal,
                 detail, failed=(), **plant):
        self.key, self.label, self.short = key, label, short
        self.section = section          # framework section it instantiates
        self.structure = structure      # additive / multiplicative / structural
        self.temporal = temporal        # abrupt / incipient / intermittent
        self.detail = detail            # the actual parameter change, in prose
        self.failed = tuple(failed)
        self.plant = plant              # LMParams kwargs

    def lm(self):
        return af.LMParams(**self.plant)

    def __repr__(self):
        return f'FaultCase({self.key})'


CATALOGUE = [
    FaultCase(
        'healthy', 'Healthy (control)', 'healthy',
        '—', 'none', '—',
        'nominal plant; measures what the state dispersion alone costs'),

    # ── section 2.1  thrust reduction — multiplicative ΔB ────────────────
    FaultCase(
        'thrust_loss_50', r'Thrust reduction, $\eta$=0.50', r'$\eta$=0.50',
        '2.1', 'multiplicative', 'abrupt / incipient',
        'engine 2 delivers half of its internal thrust '
        '(turbopump degradation, injector blockage, throat erosion)',
        thrust_eff_eng={ENG: 0.50}),
    FaultCase(
        'thrust_loss_85', r'Thrust reduction, $\eta$=0.15', r'$\eta$=0.15',
        '2.1', 'multiplicative', 'abrupt',
        'engine 2 delivers 15 % — near-total gain loss with the gimbal alive',
        thrust_eff_eng={ENG: 0.15}),

    # ── section 2.2  thrust excess / overpressure ────────────────────────
    FaultCase(
        'thrust_excess', r'Thrust excess, $\eta$=1.30', r'$\eta$=1.30',
        '2.2', 'multiplicative', 'abrupt',
        'pressurant regulator runaway: engine 2 delivers 130 % of its '
        'commanded thrust',
        thrust_eff_eng={ENG: 1.30}),
    FaultCase(
        'valve_stuck_open', 'Valve stuck open (thrust floor)', 'stuck open',
        '2.2 / 1.4', 'structural', 'abrupt',
        f'engine 2 cannot be throttled below {1.35 * T_HOV_ENG:.0f} N '
        '(1.35x its hover share) — the input set itself is cut',
        T_min_eng_ovr={ENG: 1.35 * T_HOV_ENG}),

    # ── total loss of an engine — structural ─────────────────────────────
    FaultCase(
        'engine_out', 'Engine out', 'engine out',
        '2.1 / 3.1', 'structural', 'abrupt',
        'engine 2 dead: thrust and both gimbals pinned to zero for the rest '
        'of the flight',
        failed=(ENG,)),

    # ── section 2.5  slower dynamics — multiplicative ΔA ─────────────────
    FaultCase(
        'slow_thrust', r'Slow thrust response, $\tau_T$=2.5 s', r'$\tau_T$=2.5 s',
        '2.5', 'multiplicative', 'incipient',
        'engine 2 thrust lag grows from 0.4 s to 2.5 s (valve friction, '
        'coking, actuator supply loss) with the gain untouched',
        tau_T_eng={ENG: 2.5}),
    FaultCase(
        'gimbal_slow', r'Gimbal bandwidth loss, $\omega_n$=0.6', r'$\omega_n$=0.6',
        '2.5', 'multiplicative', 'incipient',
        'engine 2 gimbal actuator slowed from 4.0 to 0.6 rad/s',
        gimbal_wn_eng={ENG: 0.6}, gimbal_zeta_eng={ENG: 0.70}),
    FaultCase(
        'gimbal_underdamped', r'Gimbal underdamped, $\zeta$=0.25', r'$\zeta$=0.25',
        '2.3 / 2.8', 'multiplicative', 'incipient',
        'engine 2 gimbal at $\\omega_n$=1.0 rad/s with damping down to '
        '0.25 — a lightly damped TVC mode',
        gimbal_wn_eng={ENG: 1.0}, gimbal_zeta_eng={ENG: 0.25}),

    # ── section 1.7 / 2.7  gimbal hardware ───────────────────────────────
    FaultCase(
        'gimbal_seized', 'Gimbal seizure', 'seized gimbal',
        '1.7', 'structural', 'abrupt',
        'engine 2 gimbal bearing seizes: the deflection freezes at whatever '
        'it held at the fault and no longer answers the command',
        gimbal_lock_eng={ENG: True}),
    FaultCase(
        'tvc_gain_loss', 'TVC effectiveness loss (35 %)', 'TVC gain 0.35',
        '2.7', 'multiplicative', 'incipient',
        'engine 2 gimbal reaches only 35 % of the commanded deflection',
        gimbal_eff_eng={ENG: 0.35}),
    FaultCase(
        'tvc_bias', 'Thrust-vector misalignment (3°, 2°)', 'TVC bias',
        '2.7', 'additive', 'incipient',
        'asymmetric nozzle erosion leaves engine 2 pointing 3° in pitch and '
        '2° in yaw off its commanded axis, independent of command',
        gimbal_bias_eng={ENG: (D2R(3.0), D2R(2.0))}),

    # ── section 2.3  thrust oscillation — additive, forced ───────────────
    FaultCase(
        'chugging', 'Thrust oscillation (chugging)', 'chugging',
        '2.3', 'additive', 'intermittent / forced',
        'feed-coupled instability: engine 2 thrust rings at 0.25 Hz with an '
        'amplitude of 20 % of its hover share, regardless of throttle',
        thrust_osc_eng={ENG: (0.20, 1.6)}),

    # ── section 2.6  transport delay ─────────────────────────────────────
    FaultCase(
        'dead_time', 'Transport delay (1 interval)', 'dead time',
        '2.6', 'structural', 'abrupt / intermittent',
        'a vapour pocket in engine 2\'s feed line delays every command by one '
        'full control interval (1 s) — exact on a zero-order-hold grid, so no '
        'Pade approximation is involved',
        u_delay_eng={ENG: 1}),

    # ── section 2.4  mixture-ratio shift — coupled ΔB + ΔA ───────────────
    FaultCase(
        'mixture_ratio', 'Mixture-ratio shift (coupled)', 'mixture ratio',
        '2.4', 'multiplicative (coupled)', 'incipient',
        'oxidiser-side erosion on engine 2: gain falls to 0.75 *and* the '
        'combustion time constant grows to 1.2 s — the framework\'s coupled '
        'ΔB + ΔA case, where the gain change drags the dynamics with it',
        thrust_eff_eng={ENG: 0.75}, tau_T_eng={ENG: 1.2}),

    # ── section 2.10  parametric drift — time-varying multiplicative ─────
    FaultCase(
        'erosion_drift', 'Throat-erosion drift', 'erosion drift',
        '2.10', 'time-varying multiplicative', 'incipient',
        'engine 2 efficiency decays at 1.2 %/s from the moment the planner '
        'starts: healthy at t=0, eta=0.52 forty seconds later. The vehicle it '
        'plans with is not the vehicle it lands with',
        eta_rate_eng={ENG: -0.012}),
]

CASES = {c.key: c for c in CATALOGUE}
KEYS = [c.key for c in CATALOGUE]

# Grouping used by every figure and table: the FTC fault structure of framework
# section 3, which is the classification that decides what an FTC architecture
# has to *do* about the fault.
STRUCTURES = ['none', 'additive', 'multiplicative',
              'multiplicative (coupled)', 'time-varying multiplicative',
              'structural']


# ══════════════════════════════════════════════════════════════════════
#  2. THE INITIAL-CONDITION REGIMES
# ══════════════════════════════════════════════════════════════════════
#  Each regime is a box over the same 22 coordinates Study F sampled (12 rigid
#  + 10 actuator), plus an optional acceptance predicate that carves a corner
#  out of the box.  The boxes are deliberately *not* nested: they name
#  qualitatively different situations a lander can be in, not severity levels of
#  one situation.
# ══════════════════════════════════════════════════════════════════════

RIGID_NAMES = ['x_E', 'y_E', 'alt', 'u', 'v', 'w',
               'phi', 'theta', 'psi', 'p', 'q', 'r']
RIGID_UNITS = ['m', 'm', 'm', 'm/s', 'm/s', 'm/s',
               'deg', 'deg', 'deg', 'deg/s', 'deg/s', 'deg/s']
ACT_NAMES = ['T1', 'dp1', 'dy1', 'dp1_dot', 'dy1_dot',
             'T2', 'dp2', 'dy2', 'dp2_dot', 'dy2_dot']
ACT_UNITS = ['N', 'deg', 'deg', 'deg/s', 'deg/s',
             'N', 'deg', 'deg', 'deg/s', 'deg/s']
ALL_NAMES = RIGID_NAMES + ACT_NAMES
ALL_UNITS = RIGID_UNITS + ACT_UNITS

GD = np.rad2deg(_REF.gimbal_max)                              # 6 deg
GRATE = 0.6 * np.rad2deg(_REF.gimbal_wn * _REF.gimbal_max)    # 14.4 deg/s


def _act_box(t_lo, t_hi, g, gd_rate):
    """Actuator sub-box, the same for both engines."""
    lo, hi = [], []
    for _ in range(af.N_ENG):
        lo += [t_lo, -g, -g, -gd_rate, -gd_rate]
        hi += [t_hi,  g,  g,  gd_rate,  gd_rate]
    return np.array(lo), np.array(hi)


class Regime:
    def __init__(self, key, label, blurb, rigid_lo, rigid_hi, act, accept=None):
        self.key, self.label, self.blurb = key, label, blurb
        a_lo, a_hi = act
        self.lo = np.concatenate([np.array(rigid_lo, float), a_lo])
        self.hi = np.concatenate([np.array(rigid_hi, float), a_hi])
        self.accept = accept

    def __repr__(self):
        return f'Regime({self.key})'


def _upset(row):
    """An upset state is one that is already *doing* something bad: a real
    body rate, or a real tilt.  Without this the box's interior is dominated by
    near-benign draws and the regime would not differ from the dispersed one."""
    tilt = np.hypot(row[6], row[7])
    rate = np.abs(row[9:12]).max()
    return rate >= 10.0 or tilt >= 15.0


REGIMES = [
    Regime('approach', 'On approach',
           'high, descending, small dispersions — the vehicle is where a '
           'healthy descent would have put it, and the fault is the only thing '
           'wrong',
           [-350., -350.,  800., -20., -5.,  0., -8., -8., -15., -3., -3., -3.],
           [ 350.,  350., 1300.,   0.,  5., 25.,  8.,  8.,  15.,  3.,  3.,  3.],
           _act_box(0.85 * T_HOV_ENG, 1.15 * T_HOV_ENG, 1.5, 3.0)),

    Regime('dispersed', 'Dispersed',
           'Study F\'s wide box: position, velocity, attitude, rates and both '
           'sets of actuator states drawn over their full admissible ranges',
           [-900., -900.,  300., -25., -12., -5., -25., -25., -40., -25., -25., -25.],
           [ 900.,  900., 1400.,  10.,  12., 28.,  25.,  25.,  40.,  25.,  25.,  25.],
           _act_box(_REF.T_min_eng, _REF.T_max_eng, GD, GRATE)),

    Regime('upset', 'Upset',
           'the corner of the box where the vehicle is already rotating or '
           'tilted (>= 10 deg/s on some axis, or >= 15 deg of tilt) with the '
           'gimbals deflected — the states a fault transient actually produces',
           [-600., -600.,  500., -30., -15.,  0., -40., -40., -60., -30., -30., -30.],
           [ 600.,  600., 1100.,  15.,  15., 30.,  40.,  40.,  60.,  30.,  30.,  30.],
           _act_box(_REF.T_min_eng, _REF.T_max_eng, GD, GRATE),
           accept=_upset),

    Regime('low_late', 'Low and late',
           'between 60 m and 200 m and still descending: the fault arrives '
           'when there is very little altitude left to trade for time',
           [-200., -200.,  60., -25., -14.,  5., -28., -28., -40., -16., -16., -16.],
           [ 200.,  200., 200.,  10.,  14., 32.,  28.,  28.,  40.,  16.,  16.,  16.],
           _act_box(0.6 * T_HOV_ENG, 1.5 * T_HOV_ENG, 4.0, 8.0)),

    Regime('critical', 'Critical',
           'below 140 m, descending hard, tilted and rotating — the regime '
           'where even the healthy vehicle frequently has no trajectory left, '
           'so the fault has to be paid for out of a margin that is already '
           'spent',
           [-140., -140.,  50., -30., -18.,  8., -35., -35., -50., -22., -22., -22.],
           [ 140.,  140., 140.,  15.,  18., 34.,  35.,  35.,  50.,  22.,  22.,  22.],
           _act_box(0.5 * T_HOV_ENG, 1.6 * T_HOV_ENG, 6.0, 12.0)),
]

REG = {r.key: r for r in REGIMES}
REG_KEYS = [r.key for r in REGIMES]


# ══════════════════════════════════════════════════════════════════════
#  3. SAMPLING
# ══════════════════════════════════════════════════════════════════════

def to_state(row):
    """Sampled row (deg, m, altitude-up) -> the 22-state the dynamics use."""
    x = np.zeros(af.N_RIGID + af.N_ACT)
    x[0], x[1] = row[0], row[1]
    x[2] = -row[2]                                  # altitude -> z_E (down)
    x[3:6] = row[3:6]
    x[6:9] = np.deg2rad(row[6:9])
    x[9:12] = np.deg2rad(row[9:12])
    for i in range(af.N_ENG):
        b = 12 + 5 * i
        x[af.IDX_T[i]] = row[b]
        x[af.IDX_DP[i]] = np.deg2rad(row[b + 1])
        x[af.IDX_DY[i]] = np.deg2rad(row[b + 2])
        x[af.IDX_DPD[i]] = np.deg2rad(row[b + 3])
        x[af.IDX_DYD[i]] = np.deg2rad(row[b + 4])
    return x


def admissible(row, cfg):
    """A legal *starting* state.  Same test as Study F: only already-lost
    states and states outside the mission's approach cone are rejected.  A
    state being uncomfortable is not a reason to drop it — those are the ones
    the study exists to price."""
    r = np.hypot(row[0], row[1])
    if np.tan(cfg.glide_slope) * r > row[2]:
        return False, 'outside_glide_cone'
    if fl.hard_loss(to_state(row), cfg) is not None:
        return False, 'already_lost'
    return True, ''


def sample_regime(reg, n, seed=20260816):
    """Sobol points in the regime's box, filtered by admissibility and by the
    regime's own acceptance predicate.  The draw is doubled until n survive, so
    a regime defined by a narrow corner still gets its full sample."""
    from scipy.stats import qmc
    cfg = af.OCPConfig()
    m = int(2 ** np.ceil(np.log2(max(n * 8, 32))))
    for _ in range(8):
        pts = qmc.Sobol(d=22, scramble=True, seed=seed).random(m)
        rows = qmc.scale(pts, reg.lo, reg.hi)
        out, n_adm, why = [], 0, {}
        for i in range(m):
            if reg.accept is not None and not reg.accept(rows[i]):
                why['off_regime'] = why.get('off_regime', 0) + 1
                continue
            ok, w = admissible(rows[i], cfg)
            if not ok:
                why[w] = why.get(w, 0) + 1
                continue
            n_adm += 1
            if len(out) < n:
                out.append(rows[i])
        if len(out) >= n:
            break
        m *= 2
    frac = n_adm / m
    print(f'  [{reg.key}] admissible {frac:.3f} ({n_adm}/{m}); rejects: {why}')
    return np.array(out), frac, why
