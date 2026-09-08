---
title: "Recovering the Unrecoverable"
subtitle: "Study H-R — the 12 Study H injections that found no trajectory, re-solved with the state corridor relaxed"
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

# The question

Study H injected 12-odd faults along an
Apollo descent and found that **11** of its injections had no
recovery trajectory at all: IPOPT declared local infeasibility from seven
independent seeds at up to 1,200 iterations. The natural reading of that result
is "the vehicle is lost". It is not the only reading.

The optimal-control problem those solves failed carries a corridor of path
constraints, and **not all of them are physics**:


| Constraint | Study H value | What it actually is |
|:--------------|:--------------------------|:------------------------------------------------------------|
| Glide cone | 12° above horizontal | A scenario choice. It exists to rule out the dive-and-crawl-back trajectory family, not because a vehicle cannot fly below it. |
| Attitude | 45° per axis | Planner comfort. `fault_lib`'s own `hard_loss()` puts genuine loss of control at 90°, twice this. |
| Body rate | 10°/s | Comfort again; `hard_loss()` uses 120°/s. |
| Speed | 60 m/s per axis and as a norm | The vehicle model has no aerodynamic or structural speed limit at all; this is a modelling convenience. |


So "no trajectory exists" may mean "no trajectory exists **that stays inside
the corridor**". Those are very different engineering statements. The first is a
lost vehicle. The second is a vehicle that could be saved by a guidance law
willing to leave the nominal envelope — and knowing which one you have is worth
more than the failure count itself.

This study separates them. It re-solves every case Study H could not land,
at progressively weaker corridors, and records **the weakest relaxation that
admits a trajectory** together with **how far outside the baseline limits that
trajectory actually goes**.

# Method

## The ladder

Each case is re-attacked at 4 levels, stopping at the first that yields a
trajectory:


| Level | Corridor | Constraints removed outright |
|:--------|:----------------------------------------------|:------------------------------|
| L1 | glide cone 12 to 6 deg | none dropped |
| L2 | + attitude 45 to 60 deg, rate 10 to 20 deg/s | none dropped |
| L3 | + speed 60 to 90 m/s (axis and norm) | none dropped |
| L4 | all state constraints dropped except z > 0 | cone, vel, att, rate |


## What is never relaxed

The ladder changes what the vehicle is allowed to do **en route**. It never
changes what counts as success, and it never invents hardware:

* **Thrust and gimbal bounds stand at every level.** They are actuator
  hardware; relaxing them would answer a question about a vehicle that does not
  exist.
* **The Apollo landing gate stands at every level.** A relaxed solve still has
  to touch down inside the same gate to be counted as a landing, which is why
  the results below distinguish *found a trajectory* from *landed*.
* **The altitude floor stands at every level.** The vehicle may not fly through
  the surface, and there is no version of this question in which dropping that
  is informative: a path through the ground is not a path the vehicle can fly,
  yet its touchdown state would score against the landing gate exactly as if it
  were — the gate inspects only the final state. Dropping it would manufacture
  "recoveries" that are arithmetic, not flight.

That makes **L4 the weakest problem in this study**: every state constraint is
gone except $z > 0$. A case that fails there fails with nothing asked of it but
to stay above the surface, which is as close to "the vehicle cannot do it" as
this machinery can get.

## Effort parity

A relaxed solve that fails must fail for the same reason the baseline did, not
because it was tried less hard. Study H spent 7 seeds at up to 1,200 iterations
on each of these cases (2 in the campaign, 6 in the hardening pass). Each rung
here gets 3 horizon seeds at 1,200 iterations, and the
terminal rung L4 — where a failure is the study's
strongest claim — gets 6. A case still infeasible there has now
resisted **22 seeds** in total.

# Results

Of the 12 cases carried forward — 11 that found no
trajectory and 1 that flew but missed the gate —
**3 found a trajectory** once the corridor was relaxed, and
**2** of those still land inside the unchanged Apollo gate.
**9** remained infeasible at every level.



![The weakest relaxation that admits a trajectory](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/HR1_ladder.png)


| Fault | Injected | Altitude | Study H | Solved at | Outcome | Gate margin | Binding baseline limit | Exceeded by |
|:----------------------|:----------|:----------|:--------------|:----------|:------------|:------------|:----------------------|:------------|
| dead time | 17 s | 419 m | no recovery | — | no recovery | — | n/a | nan× |
| dead time | 25 s | 282 m | no recovery | — | no recovery | — | n/a | nan× |
| dead time | 30 s | 212 m | no recovery | — | no recovery | — | n/a | nan× |
| dead time | 38 s | 109 m | no recovery | — | no recovery | — | n/a | nan× |
| dead time | 55 s | 8 m | no recovery | — | no recovery | — | n/a | nan× |
| engine out | 38 s | 109 m | gate miss | L1 | gate miss | 6.88 | glide cone | 2.02× |
| engine out | 42 s | 56 m | no recovery | — | no recovery | — | n/a | nan× |
| engine out | 46 s | 19 m | no recovery | — | no recovery | — | n/a | nan× |
| engine out | 51 s | 4 m | no recovery | L1 | land | 0.60 | glide cone | 1.77× |
| $\eta$=0.50 | 46 s | 19 m | no recovery | L1 | land | 0.60 | glide cone | 2.02× |
| $\eta$=0.15 | 42 s | 56 m | no recovery | — | no recovery | — | n/a | nan× |
| $\eta$=0.15 | 46 s | 19 m | no recovery | — | no recovery | — | n/a | nan× |


Read the last two columns first. "Binding baseline limit" is the Study H
constraint the relaxed trajectory leans on hardest, and "exceeded by" is the
peak excursion as a multiple of that limit. A value of 1.00× would mean the
relaxation was never used — the trajectory stayed inside the original corridor
and only the *solver* needed help. Anything above 1.00× is a constraint the
recovery genuinely could not have respected.

## Which constraint was actually binding


| Binding limit | Cases | Which |
|:--------------------|:--------|:----------------------------------------------------|
| glide cone | 3 | engine_out@38, engine_out@51, thrust_loss_50@46 |


![Peak excursion beyond each baseline limit, per recovered case](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/HR2_excursions.png)


**These excursions are measured after the post-fault transient**, from node
6 onward. `solve_ocp` opens a corridor over the first
6 nodes — up to 3x the rate limit, 1.35x the attitude limit,
1.2x the speed limit — which shrinks to the nominal envelope by node
6 and which **the baseline problem opens too**. An excursion
inside that window is something Study H already permitted, not something the
relaxation bought, so counting it would credit the recovery to the wrong
constraint. Measured over the whole trajectory, two of the recoveries here look
like they were bought by the body-rate limit at ~2x; measured after the ramp,
their rate and attitude peaks sit at exactly 1.00x and the glide cone is the
only limit genuinely broken — which is the answer that agrees with all three
having solved at L1, where the cone is the only thing that
moved.


## The trajectories themselves


![The relaxed recoveries against the nominal and the original cone](/home/omersayilgan/Desktop/ThesisGit/studies/fault_injection/figures/HR3_trajectories.png)


# What this means

**A failed solve is a statement about the problem, not only about the vehicle.**
3 of 12 cases that Study H recorded as unrecoverable
have a trajectory once the corridor is widened. Reporting them as lost vehicles
would have overstated the fault's severity by exactly that much.

**The relaxation is not free, and the excursion column prices it.** Every
recovered case names a specific limit it had to break and the factor by which it
broke it. That is the number a guidance designer needs: not "relax the
constraints" but "this fault is survivable if the vehicle is permitted
glide cone
beyond the nominal envelope".

**The gate is the honest discriminator.** 2 of the
3 recovered cases land inside
the Apollo gate; the rest fly a trajectory to the surface but arrive outside it.
A trajectory that exists is not the same as a landing, and the ladder deliberately
keeps those separate.


**9 cases did not yield to any
relaxation** (dead time @17 s, dead time @25 s, dead time @30 s, dead time @38 s, dead time @55 s, engine out @42 s, engine out @46 s, $\eta$=0.15 @42 s, $\eta$=0.15 @46 s).
With the entire corridor removed, the only constraints left are the actuator
bounds, the surface, and the dynamics — so these are the cases where the
*vehicle* genuinely cannot get to the pad, not the cases where the planner was
being asked to fly politely. They are the ones a fault-tolerance budget should
carry as real losses.


# Limitations

* **Local infeasibility is still not global.** 22 seeds is strong
  evidence, not a proof. A case that resists the whole ladder has resisted a lot
  of search; it has not been shown impossible.
* **The relaxed corridors are chosen, not derived.** 6°, 60°, 20°/s and 90 m/s
  are round numbers picked to bracket the baseline, not limits computed from
  vehicle structure or sensor range. The ladder measures *which* constraint
  binds and *roughly how much* is needed, not the exact threshold.
* **Relaxing a planner constraint does not make the vehicle able to fly it.**
  A trajectory that pitches past 45° is admissible here because the model has no
  structural or plume-impingement limit at that attitude. A real vehicle may.
* **Everything inherited from Study H still applies**: instantaneous perfect
  detection, open loop, one nominal, constant mass.

# Reproducing

```bash
python studies/fault_injection/run_relaxed_study.py    # the ladder campaign
python studies/fault_injection/analyse_relaxed.py      # figures + headline JSON
python studies/fault_injection/build_relaxed_report.py # this document
```
