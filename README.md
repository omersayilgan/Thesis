# Thesis — Apollo LM Landing GNC

Trajectory optimisation and actuator-fault analysis for an Apollo-class lunar
lander, plus a fleet-wide actuation-envelope survey.

## Layout

```
src/apollo_gnc/     Shared engine — imported by every study
  apollo_full.py      Vehicle model + landing OCP (the core module)
  geometry_db.py      Thruster/engine geometry dataclasses
  vehicles.py         Fleet definitions, reads data/spacecraft_values.xlsx
  envelopes.py        Achievable-set / attainable-moment geometry
  plots.py            Envelope plotting helpers

studies/            One directory per investigation, each self-contained
  actuation_envelopes/    Fleet envelope survey      -> figures/
  engine_failure/         Engine-out authority       -> 01_*, 02_*, 03_*
  gimbal_degradation/     Gimbal bandwidth sweep     -> G1_*..G4_*
  thrust_efficiency/      Thrust efficiency sweep    -> E1_*..E6_*
  fault_onset/            Fault-onset campaigns D/E/F -> results/, figures/
  fault_taxonomy/         16 framework faults x 4 IC regimes -> results/, figures/
  reliability/            Reliability vs T/W, RCS DOF analysis

docs/               Thesis-level write-ups (.tex/.md sources + built .pdf)
data/               spacecraft_values.xlsx (fleet parameter workbook)
tools/              Standalone utilities (trajectory dump, animation, plots)
results/baseline/   Output of a plain `apollo_full.py` run
```

## Running

Study scripts add `src/apollo_gnc` to `sys.path` themselves, so run them
directly from anywhere — no install or `PYTHONPATH` needed:

```bash
python studies/engine_failure/run_case_study.py
python studies/thrust_efficiency/run_efficiency_study.py
python studies/gimbal_degradation/run_gimbal_study.py
python studies/fault_onset/run_study_D.py       # then run_study_E.py, run_study_F.py
python studies/fault_taxonomy/run_taxonomy_study.py   # then analyse.py, build_report.py
python studies/actuation_envelopes/build_report.py
```

Each study writes its figures and data **inside its own directory**, next to
the README that describes it. The per-study reports in
`studies/*/[name].pdf` are generated in place by their build scripts; only
thesis-level documents live in `docs/`.

Animation pipeline (the solve is slow, so it is cached):

```bash
python tools/save_trajectory.py     # -> apollo_trajectory.npz
python tools/animate_landing.py     # -> landing.mp4
```

## Dependencies

numpy, scipy, matplotlib, pandas, casadi, openpyxl (and ffmpeg for the
animation).
