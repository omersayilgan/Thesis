"""
STUDY G — Appendix B: the trajectory atlas
══════════════════════════════════════════
Bundles the fifteen trajectory figures into one document, so the
paths can be leafed through regime by regime rather than opened file by file.
Captions carry the per-regime landing counts, computed from the campaign CSV.

Run:  python build_trajectory_atlas.py     (after plot_trajectories.py)
"""

import os
import sys
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'studies', 'fault_onset'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'apollo_gnc'))

RESULTS = os.path.join(HERE, 'results')
FIGURES = os.path.join(HERE, 'figures')
MD = os.path.join(HERE, 'trajectory_atlas.md')
PDF = os.path.join(HERE, 'trajectory_atlas.pdf')

import fault_catalogue as fc   # noqa: E402
import campaign as cp          # noqa: E402


def build():
    rows = cp.read_csv(os.path.join(RESULTS, 'G_samples.csv'))
    st = np.load(os.path.join(RESULTS, 'G_states.npz'), allow_pickle=True)
    regs = [str(g) for g in st['regimes']]

    P = []
    A = P.append
    A(r"""---
title: "Study G — Appendix B: Trajectory Atlas"
subtitle: "Every recovery the campaign found, fault by fault and state by state"
date: "17 August 2026"
geometry: "margin=1.3cm"
fontsize: 10pt
numbersections: true
toc: true
colorlinks: true
header-includes:
  - \usepackage{float}
  - \usepackage{graphicx}
  - \let\origfigure\figure
  - \let\endorigfigure\endfigure
  - \renewenvironment{figure}[1][2]{\expandafter\origfigure\expandafter[H]}{\endorigfigure}
---

# How to read these

Three views per regime, all drawn from the same set of solves:

* **Descent profile** — altitude against horizontal distance to the pad, one
  panel per fault, with all ten of that regime's initial conditions overlaid.
  The dashed line is the 30° glide-slope cone the descent has to stay above;
  trajectories that ride it are ones for which the approach geometry, not the
  fault, is the binding constraint.
* **Ground track** — the same paths seen from above, with the pad and the 15 m
  landing-gate circle.
* **One initial condition, sixteen vehicles** — a single shared state flown by
  every plant in the catalogue. This is the study's premise in one picture:
  same state, different vehicle, different future. The state drawn is the one
  the faults disagree about most.

Line colour is the outcome: **green** landed, **amber** flew but missed the
touchdown gate, **red ×** no trajectory found at all — drawn at the initial
condition it started from, because a missing line and an unsampled state would
otherwise look identical. Panel-title colour is the FTC fault structure
(grey healthy, blue additive, orange multiplicative, green structural).

Trajectories include the engine-off ballistic settle from the contact altitude
down to the surface, so each line ends where the vehicle actually touched down.

A note on what these are **not**: each line is a single open-loop optimal
control solution computed with exact knowledge of the damaged plant. They show
what trajectory *exists*, not what a controller flying with an estimated plant
would achieve.
""")

    for g in regs:
        n = len(st[f'rows_{g}'])
        sub = [r for r in rows if r['regime'] == g]
        landed = sum(r['lands'] in ('True', 'true', '1') for r in sub)
        A(f"""
\\newpage

# `{g}` — {fc.REG[g].label}

{fc.REG[g].blurb.capitalize()}. Across all 16 plants this regime landed
{landed} of {len(sub)} cases.
""")
        for tag, name, cap in (
                ('T1', f'T1_{g}_profile.png', 'Descent profiles'),
                ('T2', f'T2_{g}_ground.png', 'Ground tracks'),
                ('T3', f'T3_{g}_one_ic.png',
                 'One initial condition, every plant')):
            p = os.path.join(FIGURES, name)
            if os.path.exists(p):
                A(f'\n![{cap} — {fc.REG[g].label} regime]({p})\n')

    open(MD, 'w').write('\n'.join(P))
    print('[saved]', MD)
    cmd = ['pandoc', MD, '-o', PDF, '--pdf-engine=xelatex',
           '--resource-path', HERE]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print('[saved]', PDF)
    except subprocess.CalledProcessError as e:
        print('pandoc failed:\n', e.stderr[-2500:])


if __name__ == '__main__':
    build()
