"""
Build fault_onset_study.pdf from results/headline.json + figures/.
═════════════════════════════════════════════════════════════════
Every number in the PDF is read from headline.json, which analyse.py writes
from the campaign CSVs.  Nothing is typed in by hand, so the document cannot
drift from the data it describes.

    python build_report.py          # -> fault_onset_study.md and .pdf
"""

import os
import json
import subprocess
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
MD = os.path.join(HERE, 'fault_onset_study.md')
PDF = os.path.join(HERE, 'fault_onset_study.pdf')


def load_head():
    with open(os.path.join(RESULTS, 'headline.json')) as fh:
        return json.load(fh)


def fmt_ms(x):
    return f'{1e3 * x:.0f} ms' if x < 1 else f'{x:.2f} s'


def pct(x):
    return f'{100 * x:.1f} %'


def ci(p, lo, hi):
    return f'{p:.3f} [{lo:.3f}, {hi:.3f}]'


def table(rows, header, align=None):
    align = align or ['---'] * len(header)
    out = ['| ' + ' | '.join(header) + ' |',
           '|' + '|'.join(align) + '|']
    for r in rows:
        out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    return '\n'.join(out)


def fig(name, caption, width='\\linewidth'):
    return (f'![{caption}]({os.path.join("figures", name)})'
            f'{{width={width}}}\n')


def build(head, body_fn):
    md = body_fn(head)
    with open(MD, 'w') as fh:
        fh.write(md)
    print('[saved]', MD)
    cmd = ['pandoc', MD, '-o', PDF, '--pdf-engine=xelatex',
           '--resource-path', HERE]
    try:
        subprocess.run(cmd, check=True, cwd=HERE)
        print('[saved]', PDF)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print('pandoc failed:', e)


if __name__ == '__main__':
    from report_body import body
    build(load_head(), body)
