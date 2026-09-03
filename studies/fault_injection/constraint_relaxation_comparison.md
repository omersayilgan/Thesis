---
title: "Corridor or Vehicle?"
subtitle: "Comparing Study H with Study H-R — what the relaxed constraints reveal about the faults that had no recovery"
date: "1 September 2026"
geometry: margin=2.2cm
fontsize: 10.5pt
numbersections: true
toc: true
colorlinks: true
header-includes:
  - \usepackage{booktabs}
  - \usepackage{amsmath}
  - \usepackage{float}
  - \let\origfigure\figure
  - \let\endorigfigure\endfigure
  - \renewenvironment{figure}[1][2]{\expandafter\origfigure\expandafter[H]}{\endorigfigure}
---

# The two studies in one paragraph

**Study H** injected 12 engine plants at 15 points
along one Apollo-anchored nominal descent — 180 optimal-control solves —
and asked *where on the descent is this fault survivable*. It found
168 landings and **11 injections with no recovery
trajectory at all**.

**Study H-R** took those failures and asked a different question: *is the
vehicle lost, or is the corridor too tight?* It re-solved each one at four
progressively weaker sets of path constraints, keeping the altitude floor, the
actuator bounds and the landing gate fixed throughout.

This document sets the two against each other.

# The headline comparison


| Measure | Study H (baseline corridor) | Study H-R (relaxed) | Change |
|:----------------------------------|:--------------------------|:------------------------|:----------|
| Injections with a trajectory | 169 of 180 | 172 of 180 | +4 |
| ...of which fly above the surface | 169 of 180 | 171 of 180 | +3 |
| Injections that land in the gate | 168 of 180 | 170 of 180 | +2 |
| Cases with no trajectory at all | 11 | 8 | −3 |


4 of the 12 carried-forward cases found a trajectory
once the corridor was widened, and 2 of those still touch down
inside the **unchanged** Apollo gate. The gate was never relaxed — only what the
vehicle was permitted to do on the way there.

# What the difference actually is

## Reading 1 — the failures were mostly about the corridor



4 cases that Study H reported as
unrecoverable are recoverable by a vehicle allowed outside the nominal envelope.
Those results were never statements about the vehicle's capability; they were
statements about the *problem as posed*. Reported as lost vehicles, they would
have overstated the severity of
$\eta$=0.50, engine out by exactly that margin.

The binding constraint names what each one needed:

| Baseline limit the recovery had to break | Cases | Which |
|:----------------------------------------|:--------|:--------------------------------------------|
| glide cone | 3 | engine_out@38, engine_out@51, thrust_loss_50@46 |
| altitude floor | 1 | engine_out@46 |


## Reading 2 — what the relaxation could not fix


8 cases resisted the entire ladder:


| Fault | Injected at | Altitude | Range to pad |
|:------------------------|:------------|:------------|:--------------|
| dead time | 17 s | 419 m | 1746 m |
| dead time | 25 s | 282 m | 1276 m |
| dead time | 30 s | 212 m | 978 m |
| dead time | 38 s | 109 m | 499 m |
| dead time | 55 s | 8 m | 17 m |
| engine out | 42 s | 56 m | 264 m |
| $\eta$=0.15 | 42 s | 56 m | 264 m |
| $\eta$=0.15 | 46 s | 19 m | 87 m |


The last level removes **every state constraint in the problem** — the cone,
the speed box, the attitude and rate limits, and finally the altitude floor
itself — leaving only the dynamics and the actuator bounds. A failure there is
as close to "the vehicle cannot do it" as this machinery can get: there is no
longer any restriction on the state to blame. **These are the cases a fault-tolerance budget should carry
as real losses** — and there are 8 of
them, not 11.


## Reading 3 — the faults sort into three groups


| Group | Faults | What it means |
|:------------------------------|:--------------------------|:--------------------------------------------------------|
| Recoverable with a wider corridor | $\eta$=0.50 | Every failed injection of this fault yields to relaxation. Its Study H boundary is a corridor artefact. |
| Mixed | engine out | Some injections are corridor-limited, some are not. The boundary is real but sits later than Study H put it. |
| Genuinely unrecoverable | dead time, $\eta$=0.15 | No relaxation helps. The vehicle cannot reach the pad from these states with this plant. |


# Figures, side by side

Study H's outcome grid, with the red cells being the ones this study
re-examined:


![Study H — outcome by fault and injection point](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/H2_grid.png)


And the ladder result for exactly those cells:


![Study H-R — the weakest relaxation that admits a trajectory](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/HR1_ladder.png)


The excursion chart is the bridge between them: it shows, for each recovered
case, which Study H limit the new trajectory had to break and by how much.


![Peak excursion beyond each baseline limit](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/HR2_excursions.png)


# What we can understand from this

**A solver's "infeasible" is a property of the constraint set, and it must be
reported as one.** The single most transferable result here is methodological:
11 failures became 8 once the same states and the
same plants were given a wider corridor. Any study that reports fault
survivability from a constrained planner is reporting the constraints as much as
the vehicle, and the only way to know the split is to vary them deliberately.

**Severity should be quoted with the corridor attached.** "This fault is
unrecoverable after t = X" is incomplete. The defensible statement is "this
fault is unrecoverable after t = X *inside a 12° cone with
45° attitude and 60 m/s limits*, and after
t = Y with the corridor open" — two numbers, and the gap between them is the
value of an envelope-expanding guidance mode.

**Removing the state constraints entirely is a diagnosis, not a rescue.**
1 case found a trajectory only with every
state constraint gone, the altitude floor included — meaning the path they take
passes through the lunar surface. They are not recoveries. What they establish
is that the plant still has the authority to make the geometry, and that the
binding difficulty is doing it above the ground. The
8 cases that fail even there
are short of authority outright.

**Relaxation buys a trajectory, not necessarily a landing.** Of the
4 recovered cases, 2
still land in the gate. The rest reach the
surface outside it. Feasibility and success are different questions and the
distinction survives the relaxation intact — which is what makes the recovered
landings credible rather than an artefact of loosened scoring.

**The cases that remain are worth more than the ones that moved.** After the
ladder, 8 cases
are left. Those have now survived
22 independent seeds across two studies and
four corridors. That is a far stronger claim than the original
11 could support, and it is the number worth defending.

# Caveats that apply to the comparison itself

* **The two campaigns are not equal-effort by design.** The relaxed run spends
  more search on fewer cases, deliberately: extra search can only convert a
  false "no" into a true "yes", never the reverse. It cannot manufacture a
  landing that does not exist, but it does mean "H-R found more" is partly a
  statement about effort as well as about constraints.
* **Only the failures were re-run.** The 168 baseline landings were
  not re-solved under the relaxed corridor, so this document compares the
  *failures* of one study with the *failures* of another, not two complete
  campaigns. A relaxed re-run of the landings would be expected to change
  margins, not outcomes.
* **The relaxed limits are round numbers**, chosen to bracket the baseline
  rather than derived from vehicle structure. The ladder localises which
  constraint binds; it does not find the exact threshold.
* **Everything Study H assumed still holds**: instantaneous perfect detection,
  open loop, one nominal trajectory, constant mass.

# Reproducing

```bash
python studies/fault_injection/run_injection_study.py     # Study H campaign
python studies/fault_injection/harden.py                  # H hardening pass
python studies/fault_injection/analyse_injection.py       # H figures + JSON
python studies/fault_injection/run_relaxed_study.py       # H-R ladder
python studies/fault_injection/analyse_relaxed.py         # H-R figures + JSON
python studies/fault_injection/build_comparison_report.py # this document
```
