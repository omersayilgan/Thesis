"""
The outcome grid — one overview figure, shared by every campaign study
═════════════════════════════════════════════════════════════════════
Study H's "outcome by fault and injection point" reads well because it answers
the only question a campaign really has, *what happened where*, without
averaging anything away: one cell per solve, coloured by what that solve did.
This module generalises it so the other campaigns can draw the same figure from
their own results.

Two modes, because the campaigns are not shaped alike:

    CATEGORICAL   one solve per cell.  The cell is the outcome's colour and
                  nothing is aggregated - Study H's original figure.

    AGGREGATED    n solves per cell (Study G runs 10 samples per fault-regime
                  pair, Study F 48 per plant).  The cell is shaded by the share
                  that landed and annotated with the count, so a cell is still
                  one honest number rather than a colour standing in for a
                  distribution.

Both keep the same reading direction and the same palette, so the three
studies' overviews can sit side by side in a thesis chapter and be compared
without a legend lookup each time.
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.colors import LinearSegmentedColormap

SURFACE = '#fcfcfb'
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#8a8985'

# the palette every study shares
STATUS = {'land': '#0ca30c', 'gate_miss': '#fab219',
          'subsurface': '#2b2b6b', 'no_recovery': '#d03b3b',
          'no_replan': '#d03b3b', 'lost_in_delay': '#8b2f8b',
          'already_lost': '#8a8985'}
OUT_LABEL = {'land': 'landed', 'gate_miss': 'flew, missed the gate',
             'subsurface': 'path goes below the surface',
             'no_recovery': 'no trajectory found',
             'no_replan': 'no re-plan found',
             'lost_in_delay': 'lost during the reaction delay',
             'already_lost': 'lost before the planner ran'}

# white -> green for landing share; deliberately not a rainbow, so the eye
# reads "more green = more landings" without decoding anything
SHARE_CMAP = LinearSegmentedColormap.from_list(
    'share', ['#f6d7d7', '#fbeccd', '#e4f2d9', '#0ca30c'])

RC = {
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE, 'axes.edgecolor': '#d8d7d2',
    'axes.labelcolor': INK2, 'text.color': INK,
    'xtick.color': INK2, 'ytick.color': INK2, 'font.size': 9,
}


def _blank(ax, n_col, n_row):
    ax.set_xlim(0, n_col)
    ax.set_ylim(n_row, 0)
    ax.grid(False)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)


def outcome_grid(cells, row_labels, col_labels, path, title, subtitle='',
                 mode='categorical', row_colors=None, xlabel='', ylabel='',
                 cell_w=0.52, cell_h=0.40, note='', share_key='land',
                 col_fontsize=7.5, row_fontsize=8.5, legend_pad=None):
    """Draw and save the grid.

    `cells[i][j]` is an outcome string in categorical mode, or a sequence of
    outcome strings in aggregated mode (empty/None for a cell with no data).

    Returns the landing share per row, which is what the reports quote.
    """
    plt.rcParams.update(RC)
    n_row, n_col = len(row_labels), len(col_labels)
    fig, ax = plt.subplots(figsize=(2.2 + cell_w * n_col,
                                    1.9 + cell_h * n_row))
    _blank(ax, n_col, n_row)

    seen, shares = set(), []
    for i in range(n_row):
        row_land = row_n = 0
        for j in range(n_col):
            c = cells[i][j]
            if c is None or (mode == 'aggregated' and not len(c)):
                continue
            if mode == 'categorical':
                fc = STATUS.get(c, MUTED)
                seen.add(c)
                row_land += (c == share_key)
                row_n += 1
                txt = ''
            else:
                k = sum(o == share_key for o in c)
                fc = SHARE_CMAP(k / len(c))
                seen.update(c)
                row_land += k
                row_n += len(c)
                txt = f'{k}/{len(c)}'
            ax.add_patch(plt.Rectangle((j + 0.03, i + 0.06), 0.94, 0.88,
                                       facecolor=fc, edgecolor=SURFACE,
                                       linewidth=1.4))
            if txt:
                # white only on the deepest green; mid-greens are too light
                # to carry white text
                k_frac = k / len(c)
                ax.text(j + 0.5, i + 0.5, txt, ha='center', va='center',
                        fontsize=7.6, weight='bold',
                        color='white' if k_frac > 0.9 else INK2)
        shares.append(row_land / row_n if row_n else float('nan'))

    ax.set_xticks(np.arange(n_col) + 0.5)
    ax.set_xticklabels(col_labels, fontsize=col_fontsize)
    ax.set_yticks(np.arange(n_row) + 0.5)
    ax.set_yticklabels(row_labels, fontsize=row_fontsize)
    if row_colors:
        for tl, c in zip(ax.get_yticklabels(), row_colors):
            tl.set_color(c)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)

    # the title is padded off the axes to leave the subtitle a clear line of
    # its own; drawing both through set_title() overlaps them
    ax.set_title(title, fontsize=11, weight='bold', color=INK, loc='left',
                 pad=26 if subtitle else 10)
    if subtitle:
        ax.text(0.0, 1.012, subtitle, transform=ax.transAxes, fontsize=8.6,
                color=INK2, va='bottom')

    if mode == 'categorical':
        order = ['land', 'gate_miss', 'subsurface', 'no_recovery',
                 'no_replan', 'lost_in_delay', 'already_lost']
        handles = [Patch(facecolor=STATUS[o], label=OUT_LABEL[o])
                   for o in order if o in seen]
    else:
        handles = [Patch(facecolor=SHARE_CMAP(v),
                         label=f'{v:.0%} of the cell landed')
                   for v in (0.0, 0.34, 0.67, 1.0)]
    # a short grid needs the legend pushed further down: the offset is a
    # fraction of the axes height, so few rows means a small absolute gap and
    # the legend lands on the x-label
    pad = legend_pad if legend_pad is not None else max(0.10, 1.2 / n_row)
    ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -pad),
              ncol=min(4, len(handles)), frameon=False, fontsize=8.5)
    if note:
        ax.text(0.0, -pad - 0.10, note, transform=ax.transAxes, fontsize=8,
                color=MUTED, va='top')

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'[saved] {path}')
    return shares
