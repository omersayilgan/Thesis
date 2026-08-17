# Spacecraft Propulsion Engine Fault Framework
## A Unified Dynamical Systems & Fault-Tolerant Control Perspective

---

## 1. Physical Fault Catalogue

### 1.1 Combustion Chamber & Nozzle Failures

- Burn-through of the chamber wall due to hot-gas erosion or cooling system degradation
- Thermal cracking from cyclic heating and cooling stresses
- Nozzle throat erosion, particularly in solid rocket motors where particulate-laden exhaust wears away the throat insert material
- Nozzle delamination in ablatively cooled designs, where composite layers separate under thermal load
- Coking or carbon deposits in regeneratively cooled channels, restricting coolant flow and creating local hot spots
- Acoustic instabilities (combustion instabilities) — longitudinal, tangential, or radial oscillation modes producing destructive pressure waves inside the chamber
- Chamber pressure excursions (overpressure leading to structural failure, or underpressure causing inefficient/unstable combustion)

### 1.2 Turbopump Failures

- Bearing seizure from contamination, lubrication starvation, or thermal distortion
- Inducer cavitation, where vapor bubbles form at the pump inlet, degrading flow and causing mechanical damage
- Turbine blade fatigue cracking from high-cycle vibration or thermal cycling
- Seal failures (static and dynamic) leading to propellant leakage into the turbine gas path or externally
- Rotor imbalance causing destructive vibration (material loss on blades, manufacturing tolerance issues)
- Gear failures in geared turbopump designs
- Overspeed events where a control valve fails open and the turbine accelerates beyond design limits
- Secondary flow path blockages in interpropellant seals, allowing fuel and oxidizer to mix in unintended cavities

### 1.3 Injector Failures

- Injector element erosion from oxidizer-rich hot gas recirculation near the face
- Coking or blockage of individual injector orifices, creating mixture ratio maldistribution
- Injector face plate cracking from thermal stress or acoustic loading
- Poor atomization due to manufacturing defects in orifice geometry
- Manifold pressure drop anomalies creating feed coupling between injector elements

### 1.4 Propellant Feed System Failures

- Valve failures (stuck open, stuck closed, partial stroke) — main valves, isolation valves, bleed/vent valves
- Water hammer (hydraulic transients) during rapid valve openings or closings
- Propellant line leaks at fittings, welds, or flex joints
- Pressurant system failures — regulator malfunction, helium tank structural failure, check valve leakage allowing propellant migration into pressurant lines (geysering / COPI)
- Filter or screen blockage from particulate contamination or propellant reaction byproducts
- Ullage collapse in pressure-fed systems, where thermal stratification causes pressurant gas ingestion into the feed line

### 1.5 Ignition System Failures

- Igniter no-light from electrical faults, depleted pyrotechnic charges, or propellant starvation
- Hard start — delayed ignition followed by rapid energy release producing a destructive pressure spike
- Torch igniter blowout
- Hypergolic slug ignition failures where TEA/TEB charge is exhausted or fails to distribute

### 1.6 Cooling System Failures

- Regenerative cooling channel blockage from debris, weld spatter, or propellant decomposition products
- Channel wall breach allowing coolant to leak into the combustion chamber (or hot gas into the coolant jacket)
- Film cooling disruption from acoustic oscillations or injector pattern changes causing local overheating
- Heat exchanger fouling in expander-cycle or gas-generator-cycle engines
- Thermal runaway in ablatively cooled engines when char rate exceeds design margins

### 1.7 Structural & Mechanical Failures

- Gimbal bearing seizure or actuator failure preventing thrust vector control
- Thrust mount fatigue cracking from vibration or repeated load cycling
- Bolt or fastener failure from thermal cycling or hydrogen embrittlement
- Weld defects — porosity, lack of fusion, or stress corrosion cracking
- Bellows or flex line fatigue failure from vibration or pressure cycling

### 1.8 Solid Rocket Motor-Specific Failures

- Grain cracking or debonding from the case wall, creating unplanned burn surface area
- Case breach from manufacturing defects, joint failures, or thermal protection erosion
- Propellant aging effects — oxidizer migration, binder degradation, plasticizer evaporation
- Slag accumulation and ejection causing thrust perturbations
- Bore choking from excessive erosion debris

### 1.9 Electric Propulsion-Specific Failures

- Grid erosion in ion thrusters causing structural failure of accelerator or screen grids
- Electron source (cathode/neutralizer) depletion or poisoning
- Hall thruster channel wall erosion changing the magnetic field topology
- Power processing unit failures from thermal cycling or component degradation
- Propellant feed system contamination causing sputtering anomalies
- Spacecraft charging from incomplete beam neutralization

### 1.10 Start/Restart & Transient Failures

- Chill-down failures leading to cavitation or thermal shock
- Pop and drop — initial ignition followed by immediate extinction from inadequate flow during ramp-up
- Failed restart after coast phase due to propellant settling issues in microgravity (vapor lock)
- Shutdown-induced water hammer from rapid valve closure

---

## 2. Dynamic Effect Categories (System-Level Perspective)

These categories describe how physical faults manifest as observable changes in the engine's dynamic behavior. Multiple physical faults can produce the same dynamic signature (many-to-one mapping), and a single fault can produce multiple dynamic effects simultaneously (one-to-many).

### 2.1 Thrust Reduction (Gain Loss)

The engine delivers less thrust than it should for a given operating point. The plant's static gain drops.

**Physical causes:** turbopump bearing degradation reducing delivered flow rate, injector orifice blockage reducing total propellant mass flow, nozzle throat erosion increasing throat area and lowering chamber pressure, propellant depletion or boil-off reducing available feed pressure, pressurant leak reducing tank pressure in pressure-fed systems, chamber wall burn-through creating a parasitic mass flow path bypassing the nozzle, valve partial stroke failure limiting propellant flow, pump cavitation reducing volumetric efficiency, film cooling excess lowering effective combustion temperature, propellant contamination reducing specific impulse, feed line restriction from filter blockage or frozen propellant slugs, grid erosion in ion engines reducing beam current, cathode depletion in electric thrusters reducing ionization efficiency.

**Dynamic character:** erosion processes produce a slow ramp, valve failure or sudden blockage produces a step, cavitation onset can be abrupt with hysteresis.

### 2.2 Thrust Excess / Overpressure (Gain Increase)

The engine produces more thrust or chamber pressure than commanded.

**Physical causes:** solid motor grain crack or debond exposing additional burn surface area, propellant accumulation followed by delayed ignition (hard start), pressurant regulator failure driving feed pressure above nominal, valve mechanically stuck fully open, thermal runaway in monopropellant catalytic beds.

**Dynamic character:** step increase, ramp (propagating grain crack), or sharp transient spike (hard start). Hard start pressure spikes can exceed structural margins within milliseconds.

### 2.3 Thrust Oscillations

Periodic or quasi-periodic fluctuation in thrust output.

**Physical causes and frequency signatures:**

- **Combustion instability — longitudinal modes (chugging):** typically 50–500 Hz, driven by coupling between combustion process delay and chamber acoustic response
- **Tangential/radial acoustic modes (screaming):** typically kHz range, driven by energy feedback from combustion into chamber acoustic eigenmodes
- **Feed-coupled instability:** below ~100 Hz, hydraulic compliance and inertia of propellant lines resonate with chamber pressure (insufficient injector-to-chamber pressure drop ratio allows this coupling)
- **Turbopump rotor imbalance:** forced oscillation at shaft frequency
- **Cavitation-induced flow oscillations:** broadband or narrowly periodic
- **Solid motor slag accumulation and periodic ejection:** discrete thrust impulses
- **Regenerative cooling channel thermal-acoustic interaction:** coolant boiling or flow instability modulates heat absorption

### 2.4 Mixture Ratio Shift

Oxidizer-to-fuel mass flow ratio deviates from nominal, changing combustion temperature, exhaust molecular weight, specific impulse, and thermal loading simultaneously.

**Physical causes:** injector orifice erosion preferentially on one propellant side, valve wear/degradation on a single propellant leg, turbopump efficiency degradation on one side in dual-pump architectures, feed line restriction on one propellant path, propellant density change from thermal stratification, differential pressurant leak rates between fuel and oxidizer tanks, regulator creep on one propellant side.

**Dynamic character:** slow mixture ratio drift means combustion gain, time constants, and thermal boundary conditions are slowly time-varying. Sudden shift (valve failure) produces abrupt change in the entire combustion operating point.

### 2.5 Increased Engine Response Time (Slower Dynamics)

The engine's bandwidth decreases — it responds more sluggishly. Effective time constants grow.

**Physical causes:** valve actuator mechanical degradation (friction buildup, seal swelling, loss of actuator supply pressure), increased propellant viscosity from temperature drop (particularly RP-1), turbopump bearing drag increasing spool-up/down time, partial blockage in propellant passages increasing hydraulic time constant, coking deposits in regenerative cooling channels increasing thermal time constant (in expander-cycle engines this directly slows the power-generation feedback loop), preburner/gas generator degradation in staged-combustion or gas-generator cycles (lag in preburner propagates and amplifies through the drive chain).

**Modeling perspective:** increase in dominant pole time constant. DC gain may be unchanged but corner frequency of frequency response shifts lower.

### 2.6 Increased Dead Time (Transport Delay)

Pure delay between an operating-point change and onset of engine response.

**Physical causes:** vapor bubble or gas pocket formation in propellant feed lines, increased effective line length from bellows extension or feed geometry changes under thermal loading, ignition delay variability in restartable engines, valve mechanical deadband from wear, partial cooling jacket blockage increasing coolant transit time in expander-cycle engines.

**Criticality:** dead time directly erodes phase margin. A system stable with 10 ms of transport delay can become unstable at 30 ms with no other change.

### 2.7 Thrust Vector Disturbance

Direction of thrust vector deviates from commanded/expected direction.

**Static misalignment:** asymmetric nozzle throat erosion creating side-force, structural deformation of thrust mount from thermal loading, asymmetric ablation in solid motor nozzles, injector face damage creating asymmetric combustion pattern shifting pressure centroid off-axis.

**Dynamic disturbances:** nozzle side-loads during start/shutdown transients (flow separation creates asymmetric pressure loading), gimbal bearing friction causing stick-slip behavior, gimbal actuator mechanical degradation reducing positioning accuracy.

### 2.8 Internal Feedback Loop Degradation (Cycle-Specific)

Degradation of physics-intrinsic feedback loops within the engine, changing its inherent dynamic character.

- **Expander cycle:** chamber wall heats coolant → coolant drives turbine → turbine drives pump → pump delivers propellant to chamber. Cooling channel blockage, turbine blade erosion, pump wear all change loop gain and can shift the engine toward instability or inability to bootstrap
- **Staged combustion cycle:** preburner injector erosion, turbine efficiency loss, or preburner mixture ratio changes alter internal power loop gain. Very high operating pressures mean small perturbations produce large absolute pressure changes
- **Gas generator cycle:** less susceptible to internal feedback instability, but gas generator injector degradation or turbine fouling shifts pump operating point, indirectly changing main chamber conditions

### 2.9 Nonlinear Regime Transitions (Bifurcations)

Engine crosses a boundary where governing dynamics change qualitatively.

**Physical causes:** pump stall (operating below minimum stable flow — pump curve peaks and operating point jumps discontinuously), combustion blowout (conditions cross flammability boundary), two-phase flow transition in feed lines (pressure-flow relationship changes discontinuously), cavitation onset/collapse in pump inducers (exhibits hysteresis — onset and recovery at different NPSH), thermal choking in regenerative cooling channels.

**Modeling implication:** linear perturbation analysis around nominal gives no warning these transitions are approaching. Nonlinear analysis (bifurcation theory, continuation methods) or high-fidelity simulation is required.

### 2.10 Parametric Drift (Time-Varying Plant)

Engine characteristic parameters change continuously over burn duration or operational life.

**Physical causes:** nozzle throat erosion gradually increasing throat area, turbopump wear changing pump curves, catalyst bed degradation, coking buildup progressively increasing thermal resistance and pressure drop, grid erosion in ion engines changing perveance, propellant tank draining changing feed system hydraulic impedance (gas spring gets softer), thermal soak shifting clearances and material properties.

**Modeling implication:** linearized plant model is only locally valid in time. The engine at ignition is not the same engine 300 seconds into the burn.

---

## 3. Fault-Tolerant Control Classification

### 3.1 FTC Fault Taxonomy

Consider the nominal engine plant in state-space form:

```
ẋ = A·x + B·u
y = C·x
```

where `x` is the engine state vector (chamber pressure, turbopump speed, propellant flow rates, temperatures, etc.), `u` is the input vector (valve commands, gimbal commands).

Faults modify this system in three fundamental ways:

#### Additive Faults

Extra terms independent of current state and input, shifting equilibria and biasing outputs:

```
ẋ = A·x + B·u + E·f_a(t)
y = C·x + F·f_a(t)
```

The fault signal `f_a(t)` acts like an unknown disturbance input (constant bias, ramp drift, or time-varying signal). **Key property:** it does not depend on `x` or `u`.

#### Multiplicative Faults

Alterations to the system matrices themselves:

```
ẋ = (A + ΔA)·x + (B + ΔB)·u
y = (C + ΔC)·x
```

The fault is state-dependent or input-dependent. Gain changes, efficiency losses, shifted time constants all modify A or B. **Key property:** the effect of the fault scales with the operating point.

#### Structural Faults

Changes to the order or topology of the system — an actuator is completely lost, a feedback path breaks, a new dynamic mode appears. These go beyond parameter changes and alter the model structure itself.

### 3.2 Temporal Profiles

- **Abrupt:** step-like onset (valve seizure, sudden bearing failure, hard start)
- **Incipient:** slow progressive drift, modeled as ramp or exponential (erosion, wear, coking, catalyst degradation)
- **Intermittent:** fault appears and disappears (cavitation at flow boundaries, intermittent valve stiction, thermal cycling effects)

---

## 4. Unified Framework: Dynamic Effects × Fault Structure

The general faulty engine plant:

```
ẋ = A(θ)·x + B(θ)·u + E·f_a(t)
```

where `θ` is a parameter vector capturing physical characteristics (efficiencies, flow coefficients, time constants, areas). Nominally `θ = θ₀` and `f_a = 0`.

### 4.1 Thrust Reduction / Thrust Excess → Multiplicative (ΔB) + Additive transients

**Primary FTC structure: multiplicative, acting on B(θ).**

The parameter θ contains nozzle throat area `A_t`, pump efficiency `η_p`, injector discharge coefficients `C_d`, catalyst/grid efficiencies. A change `θ → θ + Δθ` modifies B such that for the same input `u`, steady-state thrust `F = f(B(θ), u)` changes. Thrust scales as `F ∝ η_p · C_d · g(A_t)`, so degradation in any of these is a multiplicative modification of input effectiveness.

**Exception:** thrust disturbances independent of operating point (hard start spike, slag ejection) are **additive** `E·f_a(t)`. The distinction is testable: if doubling the throttle command also doubles the fault effect, it is multiplicative; if the fault effect stays the same, it is additive.

**Typical profile:** incipient multiplicative (erosion, wear) with occasional abrupt multiplicative (valve failure) and rare abrupt additive transients (hard start).

**FTC approach:** online estimation of effective B matrix gain via model reference adaptive control or multiplicative fault observer tracking actual-to-expected output ratio.

### 4.2 Thrust Oscillations → Structural (ΔA → instability) or Additive (forced)

**Self-excited combustion instability is structural.** A pair of eigenvalues of A crosses into the right half-plane. ΔA modifies the diagonal damping entry for the acoustic mode from negative to positive:

```
ẋ = (A + ΔA)·x
```

Algebraically multiplicative, but qualitatively structural because stability properties change. A robust controller sized for parametric ΔA uncertainty can tolerate damping reduction but cannot stabilize once the mode goes fully unstable unless it has authority at that frequency.

**Feed-coupled oscillations (chugging):** multiplicative change in off-diagonal coupling gain between feed system hydraulic states and chamber pressure, pushing a coupled mode past its stability boundary.

**Turbopump rotor imbalance:** additive periodic disturbance:

```
ẋ = A·x + B·u + E·f_a(t),   f_a(t) = a·sin(ω_shaft · t)
```

Additive because forcing exists regardless of operating point. Typically incipient as imbalance grows from wear.

**Cavitation-induced oscillations:** intermittent, either additive (collapsing cavities inject pressure pulses) or multiplicative (time-varying cavity volume modulates pump compliance, changing A).

**FTC approach:** additive oscillations → disturbance observer or notch filtering. Multiplicative/structural → active damping requiring gain and phase authority at oscillation frequency, or operating point shift away from instability boundary.

### 4.3 Mixture Ratio Shift → Multiplicative (asymmetric ΔB + coupled ΔA)

**FTC structure: multiplicative, acting asymmetrically on B matrix columns.**

For input `u = [u_ox, u_fuel]ᵀ`, mixture ratio shift is `B → B + ΔB` where ΔB modifies one column differently from the other. Oxidizer-side injector erosion increases discharge coefficient for oxidizer orifices while leaving fuel unchanged — ΔB is non-zero only in the `u_ox` column.

**Deeper consequence:** mixture ratio also modifies combustion process parameters (flame temperature, reaction rate, exhaust properties), simultaneously modifying A matrix terms. This creates a **coupled multiplicative fault** where ΔB causes an operating point shift that induces ΔA. The two are linked through combustion physics.

**Typical profile:** almost always incipient (erosion, wear, thermal drift), occasionally abrupt (valve failure).

**FTC approach:** parametric estimation with the complexity that mixture ratio is typically not directly measured — must be inferred from chamber pressure, temperature, or exhaust spectral measurements. Unknown input observer estimating differential flow perturbation.

### 4.4 Slower Engine Response → Multiplicative (ΔA)

**FTC structure: purely multiplicative, acting on A(θ).**

Engine time constants are eigenvalues of A. Physical degradation modifies specific A entries:

- Valve friction: `τ_v · ẋ_v = -x_v + u` becomes `(τ_v + Δτ) · ẋ_v = -x_v + u`, modifying `A_vv → A_vv · τ_v/(τ_v + Δτ)`
- Feed system hydraulic resistance: modifies A entries coupling pressure states to flow states (increasing R in the hydraulic R-C circuit)
- Coking in expander-cycle cooling: modifies A entries governing thermal coupling between chamber wall and coolant

**Typical profile:** almost universally incipient.

**FTC approach:** robust control (H∞, μ-synthesis) for bounded structured uncertainty. Online time constant estimation for gain-scheduled compensation maintaining closed-loop bandwidth.

### 4.5 Increased Dead Time → Structural / Multiplicative phase uncertainty

**FTC structure: does not fit cleanly into finite-dimensional additive/multiplicative framework.** Dead time is infinite-dimensional — the transfer function acquires `e^(-sΔτ)` which cannot be represented by finite ΔA or ΔB.

**Approximations for FTC:**
- Padé approximation converts delay into additional poles/zeros → **structural fault** (state dimension increases)
- For small delay perturbations, bound the phase margin effect and treat as **multiplicative uncertainty** at plant output: `e^(-jωΔτ)` is a multiplicative gain-and-phase change at each frequency

**Typical profiles:** vapor pocket formation can be abrupt or intermittent. Valve deadband growth is incipient. Ignition delay variability across restarts is intermittent.

**FTC approach:** dead time most aggressively destabilizes feedback loops. Smith predictors compensate known delay but are fragile to delay estimation errors. Robust H∞ design with delay-dependent Lyapunov-Krasovskii functionals for uncertain/varying delay.

### 4.6 Thrust Vector Disturbance → Additive (bias) + Multiplicative (gain)

**Steady side-force from asymmetric erosion is additive:**
```
F_lateral = F_nominal_lateral + f_a
```
where `f_a` is roughly constant, independent of gimbal command. Incipient as erosion progresses.

**Gimbal actuator gain loss is multiplicative on B:**
```
δ_actual = (1 - Δ) · δ_commanded
```
Direct ΔB on TVC input channel. Incipient.

**Gimbal friction (stick-slip) is a nonlinear multiplicative fault:** B matrix modified in a state-dependent way (effective gain depends on whether gimbal is moving or stuck). Modeled as sector-bounded nonlinearity within multiplicative uncertainty framework (circle criterion, Popov criterion).

**Nozzle side-loads during transients:** additive and intermittent, large broadband force disturbances independent of gimbal command.

**FTC approach:** additive → disturbance observers or integral action. Multiplicative → robust margins or online gimbal gain estimation.

### 4.7 Internal Loop Degradation → Multiplicative (ΔA loop gain)

**FTC structure: multiplicative, acting on A matrix loop gain.**

Expander-cycle internal loop transfer function: `L(s) = G_thermal(s) · G_turbine(s) · G_pump(s) · G_chamber(s)`. Degradation in any block reduces loop gain, modifying eigenvalues of closed-loop A matrix.

**Critical threshold:** if loop gain drops below unity, engine cannot self-sustain (cannot bootstrap). This is a **structural consequence** of a multiplicative fault — parametric change is smooth but a critical threshold exists below which dynamics change qualitatively.

**Typical profile:** incipient.

**FTC approach:** adaptive control with online system identification that captures internal closed-loop dynamics, not just external input-output response.

### 4.8 Bifurcation Transitions → Structural

**FTC structure: structural faults.** Model structure itself changes — not parameter variations within a fixed structure.

- **Pump stall:** fold bifurcation, operating point jumps discontinuously. Stable equilibrium disappears. No finite ΔA/ΔB captures this.
- **Combustion blowout:** reacting equilibrium disappears, states transition to trivial no-flame fixed point.
- **Cavitation onset:** new state variable (cavity volume) appears, system order changes from n to n+1.
- **Two-phase flow transition:** constitutive relations change, replacing single-phase with two-phase models.

**Typical profiles:** abrupt at transition, though approach to bifurcation boundary may be incipient.

**FTC approach:** switching-based architectures. Detection of proximity to bifurcation boundary for preventive action, or detection of transition occurrence triggering switch to post-bifurcation controller. Hybrid system theory, switched system stability analysis (common Lyapunov functions, dwell-time conditions).

### 4.9 Parametric Drift → Incipient Multiplicative

**FTC structure: time-varying multiplicative, by definition.**

```
ẋ = A(θ(t))·x + B(θ(t))·u
```

where `θ(t)` evolves according to slow dynamics (erosion rates, wear models, thermal soak).

**Two time scales:**
- **Burn-time drift** (seconds to minutes): throat erosion, thermal soak, ullage growth
- **Life-cycle drift** (hours of accumulated operation): pump wear, catalyst aging, thermal fatigue

**FTC approach:** key design parameter is **ratio of parameter drift rate to adaptation rate**. If adaptation converges faster than parameters drift, tracking is feasible. Otherwise, robust design with worst-case margins over expected parameter trajectory. For burn-time drift, gain scheduling indexed to burn time using known nominal θ(t) trajectory, with adaptive correction for deviations.

---

## 5. Summary Classification Table

| Dynamic Effect | Primary FTC Fault Type | Typical Temporal Profile | Key Parameter Affected |
|---|---|---|---|
| Thrust reduction/excess | Multiplicative (ΔB) | Incipient / Abrupt | Plant gain |
| Thrust oscillations (self-excited) | Structural (ΔA → instability) | Abrupt onset | Modal damping |
| Thrust oscillations (forced) | Additive (E·f_a) | Incipient / Intermittent | Disturbance spectrum |
| Mixture ratio shift | Multiplicative (asymmetric ΔB + coupled ΔA) | Incipient | Multi-channel gain balance |
| Slower engine response | Multiplicative (ΔA) | Incipient | Dominant pole location |
| Increased dead time | Structural / multiplicative phase uncertainty | Abrupt / Intermittent | Phase margin |
| Thrust vector bias | Additive (E·f_a) | Incipient | Force/moment offset |
| Thrust vector gain loss | Multiplicative (ΔB) | Incipient | TVC effectiveness |
| Internal loop degradation | Multiplicative (ΔA loop gain) | Incipient | Self-sustaining capability |
| Bifurcation transitions | Structural | Abrupt (approach may be incipient) | Model topology |
| Parametric drift | Multiplicative (time-varying Δθ) | Incipient | All plant parameters |

---

## 6. Cross-Classification: Temporal Profile × Fault Type

| | Multiplicative | Additive | Structural |
|---|---|---|---|
| **Abrupt** | Valve seizure at partial stroke, sudden pump impeller damage, sudden bearing failure | Hard start pressure spike, nozzle side-load onset, slag ejection, valve spring failure causing position bias | Complete valve seizure (input loss), combustion extinction, combustion instability onset, pump stall, cavitation onset |
| **Incipient** | Throat erosion, pump wear, coking, catalyst degradation, valve wear, bearing drag increase, grid erosion — **largest and most common category** | Growing pressurant leak (increasing gas entrainment), progressive asymmetric erosion (growing side-force bias), thermal creep in valve (growing position offset) | Damping margin slowly decreasing toward instability (structural change is abrupt, but approach is incipient and potentially detectable) |
| **Intermittent** | Valve stiction appearing/disappearing with thermal cycling, cavitation near boundary (pump efficiency fluctuates) | Periodic slag ejection in solid motors, intermittent gas entrainment from slosh | Cavitation intermittently appearing/disappearing (system order changes each time), two-phase flow transitions during throttle transients |

---

## 7. Implications for FTC Architecture Design

### Multiplicative Fault Handling

The controller must handle parametric uncertainty. Robust control (H∞, μ-synthesis) can handle bounded multiplicative uncertainty without explicit fault detection if bounds are known. For larger or time-varying multiplicative faults, adaptive control or gain-scheduled control with online parameter estimation is needed. Detectability depends on excitation — a gain change is invisible if the input is zero, motivating active fault detection (injecting test signals).

### Additive Fault Handling

Disturbance rejection and unknown input estimation are the primary tools. Unknown input observers, disturbance observers, or integral action can reject constant or slowly varying additive faults. Impulsive additive faults require transient disturbance robustness. Additive faults are generally easier to detect than multiplicative because they produce a residual even at equilibrium.

### Structural Fault Handling

The controller architecture must reconfigure. This is the domain of active FTC — fault detection and isolation triggers a switch to a different control law designed for the degraded plant. Loss of control input requires control allocation or redistribution. New unstable modes (combustion instability) may require frequency-targeted control or engine shutdown if the mode is not controllable.

### Detection Architecture

The temporal profile drives detection design:
- **Incipient faults:** detectable by parameter estimation or trend monitoring, require long observation windows
- **Abrupt faults:** detectable quickly by residual-based methods (observers, parity relations), require fast detection to limit damage
- **Intermittent faults:** hardest category — can reset detection logic during healthy intervals, requiring stateful algorithms that accumulate evidence across multiple fault appearances

### Layered Architecture Requirement

No single FTC methodology covers all three fault types. The architecture must be layered:
1. **Base layer:** robust/adaptive control handling incipient multiplicative faults (dominant for liquid engines during mainstage)
2. **Detection and switching layer:** handling structural faults (combustion instability, pump stall)
3. **Disturbance estimation layer:** handling significant additive disturbances (solid motor applications, liquid engine transient phases)
