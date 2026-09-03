"""
STUDY F — the outcome grid
══════════════════════════
The overview figure Study H uses, drawn for this campaign's shape.

Study F crosses six plants with two engine half-spacings, 48 Sobol samples per
combination, so a cell is 48 solves and its honest value is the share that
landed.  The spacing axis is the point of the study: y_eng = 1.5 m puts a
one-engine-out asymmetry beyond what a single gimbal can trim, y_eng = 0.25 m
keeps it inside, and the grid shows that difference as a column-to-column jump
rather than as a sentence.

Run:  python plot_outcome_grid.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')

import campaign as cp                 # noqa: E402
import outcome_grid as og             # noqa: E402

FAMILY_COLOR = {'healthy': '#9a9994', 'engine_out': '#1baf7a',
                'thrust_eff': '#eb6834', 'gimbal': '#2a78d6'}
PLANT_LABEL = {
    'healthy': 'Healthy (control)', 'engout': 'Engine out',
    'eta15': r'Thrust reduction, $\eta$=0.15',
    'eta50': r'Thrust reduction, $\eta$=0.50',
    'gimbal_slow': 'Gimbal bandwidth loss',
    'gimbal_undamped': 'Gimbal underdamped',
}


def split(plant):
    """'eta50_y0.25' -> ('eta50', '0.25')"""
    base, _, y = plant.rpartition('_y')
    return base, y


def main():
    rows = cp.read_csv(os.path.join(RESULTS, 'F_samples.csv'))
    for r in rows:
        r['base'], r['y'] = split(r['plant'])

    bases, ys = [], sorted({r['y'] for r in rows}, key=float)
    for r in rows:                       # keep the catalogue's own order
        if r['base'] not in bases:
            bases.append(r['base'])

    cells = [[[r['outcome'] for r in rows if r['base'] == b and r['y'] == y]
              for y in ys] for b in bases]
    n_per = len(cells[0][0])

    shares = og.outcome_grid(
        cells,
        row_labels=[PLANT_LABEL.get(b, b.replace('_', ' ')) for b in bases],
        col_labels=[f'$y_{{eng}}$ = {y} m' for y in ys],
        row_colors=[FAMILY_COLOR.get(
            next((r['family'] for r in rows if r['base'] == b), 'healthy'),
            '#52514e') for b in bases],
        path=os.path.join(FIGURES, 'F0_outcome_grid.png'),
        title='Outcome by plant and engine half-spacing',
        subtitle=f'{len(rows)} solves — {n_per} Sobol samples per cell, '
                 f'shaded and labelled by how many of them landed',
        mode='aggregated', xlabel='engine half-spacing',
        cell_w=2.6, cell_h=0.46,
        note='The roll-trim limit is $y_{eng} \\leq d z_{eng}\\tan\\delta_{max}$'
             ' = 0.263 m: at 0.25 m a single gimbal can trim a one-engine-out\n'
             'asymmetry, at 1.5 m it cannot. Every row is the same plant and '
             'the same 48 initial conditions on either side of that threshold.')

    print(f'\n{"plant":34s} landing share')
    for b, s in zip(bases, shares):
        print(f'  {PLANT_LABEL.get(b, b)[:32]:34s} {s:6.1%}')


if __name__ == '__main__':
    main()
