"""
STUDY G — the outcome grid
══════════════════════════
The overview figure Study H uses, drawn for this campaign's shape.

Study H runs one solve per fault-and-injection-point, so its grid can colour
each cell by that solve's outcome.  Study G runs 10 Sobol samples per fault and
regime, so a cell here is 10 solves and the honest cell value is the SHARE that
landed, printed as k/10 and shaded with it.  Averaging is stated rather than
hidden: 4/10 is a fault that half-works in that regime, which a single colour
would have to round one way or the other.

Run:  python plot_outcome_grid.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')

import campaign as cp                       # noqa: E402
import outcome_grid as og                   # noqa: E402

try:
    import fault_catalogue as fc            # noqa: E402
except Exception:                            # the figure must not need it
    fc = None

# rows are tinted by how the fault enters the model, the same three classes
# the taxonomy uses everywhere else
CLASS_COLOR = {'none': '#9a9994', 'additive': '#2a78d6',
               'multiplicative': '#eb6834', 'structural': '#1baf7a'}
REGIME_LABEL = {'approach': 'approach', 'critical': 'critical',
                'dispersed': 'dispersed', 'low_late': 'low & late',
                'upset': 'upset'}


def label_of(fault):
    if fc is not None:
        case = getattr(fc, 'CASES', {}).get(fault)
        for attr in ('label', 'short'):
            if case is not None and getattr(case, attr, None):
                return getattr(case, attr)
    return fault.replace('_', ' ')


def klass_of(rows, fault):
    """The fault's structural class, as the samples themselves record it."""
    s = next((r.get('structure') or 'none'
              for r in rows if r['fault'] == fault), 'none')
    # the samples carry variants - "time-varying multiplicative",
    # "multiplicative (coupled)" - that belong to the same class for colouring
    for base in ('multiplicative', 'additive', 'structural'):
        if base in s:
            return base
    return 'none' 


def main():
    rows = cp.read_csv(os.path.join(RESULTS, 'G_samples.csv'))
    faults = sorted({r['fault'] for r in rows})
    regimes = sorted({r['regime'] for r in rows})

    cells = [[[r['outcome'] for r in rows
               if r['fault'] == f and r['regime'] == g] for g in regimes]
             for f in faults]
    n_per = len(cells[0][0]) if cells and cells[0] and cells[0][0] else 0

    shares = og.outcome_grid(
        cells,
        row_labels=[label_of(f) for f in faults],
        col_labels=[REGIME_LABEL.get(g, g) for g in regimes],
        row_colors=[CLASS_COLOR.get(klass_of(rows, f), '#52514e')
                    for f in faults],
        path=os.path.join(FIGURES, 'G0_outcome_grid.png'),
        title='Outcome by fault and initial-condition regime',
        subtitle=f'{len(rows)} solves — {n_per} Sobol samples per cell, '
                 f'shaded and labelled by how many of them landed',
        mode='aggregated', xlabel='initial-condition regime',
        cell_w=1.15, cell_h=0.42,
        note='Study G samples initial conditions from boxes, so a cell is a '
             'region of the state space rather than a moment on a trajectory;\n'
             'the comparable figure in Study H (H2) colours one solve per '
             'cell because there is exactly one per injection point.')

    print(f'\n{"fault":34s} landing share')
    for f, s in zip(faults, shares):
        print(f'  {label_of(f)[:32]:34s} {s:6.1%}')


if __name__ == '__main__':
    main()
