# Thesis

`thesis.pdf` is assembled from the studies already in this repository by
`build_thesis.py`. No study is re-run and no number is typed in by hand: every
quantitative claim is read at build time from the headline JSON or CSV written
by the study that produced it, so the document cannot drift from its campaigns.

    python thesis/build_thesis.py     # -> thesis/thesis.md -> thesis/thesis.pdf

Requires pandoc with xelatex, and the TeX Gyre Termes OTF fonts (texlive
`tex-gyre` and `tex-gyre-math`).

## Layout

Academic-paper format: title block, abstract with keywords, nomenclature,
Roman-numbered sections, numbered figures and tables with cross-references.
Results are reported in Section VII and interpreted in Section VIII; the two are
kept separate.

| Section | Content | Source studies |
|:--|:--|:--|
| I–II | Introduction, background | — |
| III | Vehicle and actuator models | `actuation_envelopes`, `reliability`, `engine_placement` |
| IV | Fault model | `fault_onset/fault_lib.py` |
| V | Simulation and motion-planning environment | `src/apollo_gnc/apollo_full.py` |
| VI | Design of the evaluation campaigns | all four campaigns |
| VII | Results | `capability_space`, `fault_taxonomy`, `fault_onset`, `fault_injection` |
| VIII–IX | Discussion, conclusions | — |

Appendix A maps every result to the script that produced it.
