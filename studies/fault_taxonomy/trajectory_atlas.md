---
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


\newpage

# `approach` — On approach

High, descending, small dispersions — the vehicle is where a healthy descent would have put it, and the fault is the only thing wrong. Across all 16 plants this regime landed
140 of 160 cases.


![Descent profiles — On approach regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T1_approach_profile.png)


![Ground tracks — On approach regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T2_approach_ground.png)


![One initial condition, every plant — On approach regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T3_approach_one_ic.png)


\newpage

# `dispersed` — Dispersed

Study f's wide box: position, velocity, attitude, rates and both sets of actuator states drawn over their full admissible ranges. Across all 16 plants this regime landed
124 of 160 cases.


![Descent profiles — Dispersed regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T1_dispersed_profile.png)


![Ground tracks — Dispersed regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T2_dispersed_ground.png)


![One initial condition, every plant — Dispersed regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T3_dispersed_one_ic.png)


\newpage

# `upset` — Upset

The corner of the box where the vehicle is already rotating or tilted (>= 10 deg/s on some axis, or >= 15 deg of tilt) with the gimbals deflected — the states a fault transient actually produces. Across all 16 plants this regime landed
120 of 160 cases.


![Descent profiles — Upset regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T1_upset_profile.png)


![Ground tracks — Upset regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T2_upset_ground.png)


![One initial condition, every plant — Upset regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T3_upset_one_ic.png)


\newpage

# `low_late` — Low and late

Between 60 m and 200 m and still descending: the fault arrives when there is very little altitude left to trade for time. Across all 16 plants this regime landed
105 of 160 cases.


![Descent profiles — Low and late regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T1_low_late_profile.png)


![Ground tracks — Low and late regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T2_low_late_ground.png)


![One initial condition, every plant — Low and late regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T3_low_late_one_ic.png)


\newpage

# `critical` — Critical

Below 140 m, descending hard, tilted and rotating — the regime where even the healthy vehicle frequently has no trajectory left, so the fault has to be paid for out of a margin that is already spent. Across all 16 plants this regime landed
66 of 160 cases.


![Descent profiles — Critical regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T1_critical_profile.png)


![Ground tracks — Critical regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T2_critical_ground.png)


![One initial condition, every plant — Critical regime](/home/omersayilgan/Desktop/ThesisGit/studies/fault_taxonomy/figures/T3_critical_one_ic.png)
