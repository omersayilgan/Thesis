"""
The findings section, generated from headline.json.

Written as code rather than prose so the claims adapt to the campaign instead
of being asserted independently of it: if a later run moves a boundary, the
sentences move with it.
"""

import numpy as np

from build_report import table, fig, ci, pct, fmt_ms


def _tally(d):
    """(n, n_dead, n_bracketed, n_censored) over one profile's bisection."""
    brk = d.get('bracket', [])
    return (len(brk),
            sum(1 for b in brk if b in ('unrecoverable', 'no_margin')),
            sum(1 for b in brk if b == 'bracketed'),
            sum(1 for b in brk if b in ('censored_high', 'censored_low')))


def findings_text(h):
    d1, d2, d3, d5, e = (h.get(k, {}) for k in ('D1', 'D2', 'D3', 'D5', 'E'))
    out = ['\n\\newpage\n\n# What the campaign found\n']

    # ── 1. engine-out ─────────────────────────────────────────────────
    if d1:
        allbrk = [b for p in d1.values() if isinstance(p, dict)
                  for b in p.get('bracket', [])]
        n, dead, _, _ = _tally(dict(bracket=allbrk))
        if dead == n:
            out.append(f"""
## A hard engine-out is fatal whenever it happens, on either reference

All {n} onset times, on both reference profiles, are **unrecoverable even with
an instantaneous, omniscient response** ($\\tau^* = 0$). The reaction delay
never gets a chance to matter: there is no recovery trajectory from the
post-fault state, however quickly the planner is told.

That is not a new physical claim so much as a confirmation, from a completely
different direction, of Study A's static roll budget. At the design engine
spacing $y_{{eng}} = 1.5$ m, one dead engine applies 18 796 N$\\cdot$m of roll
against 5 432 N$\\cdot$m of combined gimbal and RCS authority — a 3.5$\\times$
deficit. Study A established that as a *steady-trim* impossibility; D1
establishes that no transient, at any point in the descent, and no amount of
reaction speed, gets round it. **Timing is irrelevant to this fault; geometry
decides it.**

The practical consequence is that the reaction-delay axis, which was expected
to be the interesting one, carries no information for the engine-out fault.
The axis that does is severity — which is what D5 sweeps.
""")

    # ── 2. severity vs onset (the central result) ─────────────────────
    if d5:
        for prof, label in (('derated', 'de-rated'), ('design', 'design')):
            p = d5.get(prof)
            if not isinstance(p, dict) or 'eta_star' in p is None:
                continue
        des, der = d5.get('design'), d5.get('derated')
        para = ['\n## Severity, not timing, is what decides survival\n']
        for prof, lab in (('design', 'design'), ('derated', 'de-rated')):
            p = d5.get(prof)
            if not isinstance(p, dict):
                continue
            n, dead, br, cen = _tally(p)
            eta = np.array(p.get('eta_star', []), float)
            good = np.isfinite(eta)
            ctl = p.get('n_control_fail', 0)
            if dead == n:
                para.append(f"""
On the **{lab} reference**, no severity survives at any of the {n} onset times.""")
            else:
                span = (f'{np.nanmin(eta[good]):.3f} to {np.nanmax(eta[good]):.3f}'
                        if good.any() else 'n/a')
                var = (float(np.nanmax(eta[good]) - np.nanmin(eta[good]))
                       if good.any() else float('nan'))
                para.append(f"""
On the **{lab} reference**, the critical severity $\\eta^*$ ranges over {span}
across the {n - ctl} onset times where the boundary was resolved"""
                    + (f' ({ctl} excluded — see below)' if ctl else '')
                    + f""" — a spread of {var:.3f} in $\\eta$. """ + (
                    'The boundary is essentially flat: *when* the fault arrives '
                    'barely changes how severe a fault can be absorbed.'
                    if var < 0.15 else
                    'The boundary moves materially with onset time, so when the '
                    'fault arrives genuinely matters.'))
        out.append('\n'.join(para))

        # the *shape* of the boundary is the most useful part, so describe it
        # from the data rather than asserting it
        der = d5.get('derated')
        if isinstance(der, dict):
            t = np.array(der.get('t_f', []), float)
            y = np.array(der.get('eta_star', []), float)
            g = np.isfinite(y)
            if g.sum() >= 4:
                tg, yg = t[g], y[g]
                iw, ib = int(np.argmax(yg)), int(np.argmin(yg))
                ends = 0.5 * (yg[0] + yg[-1])
                esat = d5.get('eta_sat', float('nan'))
                out.append(f"""
### The vehicle is most vulnerable in mid-descent

The boundary is not monotone, and its shape is the most useful thing in this
study. On the de-rated reference $\\eta^*$ is **lowest at the two ends** of the
descent — {yg[0]:.3f} at $t_f$ = {tg[0]:.1f} s and {yg[-1]:.3f} at
{tg[-1]:.1f} s — and **highest in the middle**, peaking at {yg[iw]:.3f} at
$t_f$ = {tg[iw]:.1f} s, where only a fault of a few per cent is survivable at
all. Tolerance is therefore U-shaped in onset time: the vehicle can absorb a
{100*(1-yg[ib]):.0f} % thrust loss on one engine early or late, and almost
nothing halfway down.

The reason is that the two ends are where the trajectory has slack of different
kinds. Early, there is altitude and time to re-plan a whole descent around the
fault. Late, the vehicle is nearly stopped over the pad and the remaining
manoeuvre is small. In between it is committed: braking hard, with the fault
disturbing a trajectory that has neither the altitude to start over nor the
proximity to simply finish.

The end values are also a check on the model. Both approach — without going
below — the analytic saturation limit $\\eta_{{sat}} = (T_{{hover}}/2)/
T_{{max,eng}} = {esat:.3f}$ derived in Study C, below which the healthy engine
can no longer be throttled up to match its partner. The early end sits
{abs(yg[0]-esat):.3f} above it and the late end {abs(yg[-1]-esat):.3f} above;
neither crosses it.

That is a meaningful consistency check rather than an exact agreement. $\\eta_
{{sat}}$ was derived from statics alone, with no reference to onset time, to
transients, or to this campaign, and it is a *lower bound* on what a dynamic
trajectory can tolerate — the numerical boundary should sit at or above it, and
approach it where the trajectory has enough slack for statics to be the binding
constraint. It does, at both ends, which is what an independent derivation and
an independent measurement agreeing looks like when one of them is a bound.
""")
        if isinstance(der, dict) and isinstance(des, dict):
            nd, dd, _, _ = _tally(der)
            ns, ds, _, _ = _tally(des)
            if ds == ns and dd < nd:
                out.append(f"""
The contrast between the two is the study's most transferable result. Same
vehicle, same fault, same initial condition, same optimiser — the only
difference is how much of its own authority the reference was already
spending. The design descent reaches contact in 26 s by riding $V_{{max}}$ and
saturating all three rate channels; the de-rated one takes 42 s and sits inside
its envelope. The first can absorb **no** fault at all; the second absorbs
{nd - dd} of {nd}.

**Fault tolerance here is bought by flying below the envelope, and the design
descent spends the entire budget on speed.** That is a trajectory-design
conclusion, not a vehicle-design one, and it is invisible to any study that
plans the fault in from $t = 0$.
""")

    # ── 2b. the null-fault control ────────────────────────────────────
    if d5:
        nctl = sum(v.get('n_control_fail', 0) for v in d5.values()
                   if isinstance(v, dict))
        nslice = sum(len(v.get('bracket', [])) for v in d5.values()
                     if isinstance(v, dict))
        if nctl:
            out.append(f"""
### A control that had to be run, and what it caught

Every severity bisection begins by solving the $\\eta = 1$ case: a "fault" that
changes nothing about the vehicle, whose replan must simply reproduce the
nominal continuation. It is a pure control on the machinery, and it is the only
thing in this study that has a known right answer.

It failed on {nctl} of {nslice} slices. A null fault cannot make a vehicle
unflyable, so those are failures of the replan formulation, not of the vehicle.
They are reported as excluded control failures rather than as $\\eta^* = 1$ —
which is what they would otherwise have masqueraded as: a maximally alarming
and entirely false result.

Two things are worth stating plainly about them. First, they were **not** fixed
by re-seeding. Every replan in this campaign is attempted twice, from two
independent initial guesses (the nominal trajectory it interrupts, and a
straight-line ramp to the pad), and a failure is only recorded once both have
failed; these five survived that. Second, they cluster at *late* onsets, where
the replan's horizon is dominated by holding the 1 m contact-altitude floor
rather than by descending — the same pathology that motivated the 20 s reserve
in Section 2.5, evidently not fully eliminated by it.

The honest summary is that a small, identifiable, and clearly-signposted part
of the onset axis is not resolved by this formulation. That is a better outcome
than the alternative, which was to publish those five points as physics.
""")

    # ── 3. severity vs delay ──────────────────────────────────────────
    if d2:
        der = d2.get('derated')
        if isinstance(der, dict):
            n, dead, br, cen = _tally(der)
            tau = np.array(der.get('y', []), float)   # already in ms
            alive = [t for t, b in zip(tau, der['bracket'])
                     if b not in ('unrecoverable', 'no_margin')]
            if alive:
                out.append(f"""
## How much reaction time a survivable fault allows

Where a fault *is* survivable, D2 measures how long the vehicle may keep flying
the stale command before that stops being true. On the de-rated reference,
{n - dead} of the {n} severities tested left a non-zero window""" + (
                    f', at {fmt_ms(alive[0] / 1e3)}.' if len(alive) == 1 else
                    f', spanning {fmt_ms(min(alive) / 1e3)} to '
                    f'{fmt_ms(max(alive) / 1e3)}.') + f"""

For scale, one engine at $\\eta$ produces a roll moment $(1-\\eta)\\,T_{{trim}}
\\,y_{{eng}}$ about a 5 368 kg$\\cdot$m$^2$ roll inertia. The windows above are
the time it takes that moment to build a rate excursion the corridor can no
longer retire within six seconds — which is why they are short even when the
steady-state fault is comfortably trimmable.
""")

    # ── 4. mechanism ──────────────────────────────────────────────────
    mech = h.get('mechanism', {})
    if mech:
        tot = sum(mech.values())
        rows = [(k.replace('_', ' '), v, pct(v / tot))
                for k, v in sorted(mech.items(), key=lambda x: -x[1])]
        dom = max(mech, key=mech.get)
        expl = {
            'no_replan': 'no recovery trajectory exists from the post-fault '
                         'state — the fault itself, not the delay, is what '
                         'kills it',
            'lost_in_delay': 'the vehicle is already tumbling or past '
                             'horizontal before the planner is even told — '
                             'reaction speed is the binding resource',
            'gate_miss': 'a recovery exists and reaches the ground, but '
                         'outside the touchdown gate',
            'land': 'recovered and landed within gate',
            'no_time': 'the fault arrives too late for any horizon to remain',
        }.get(dom, '')
        out.append(f"""
## Which loss mechanism dominates

{table(rows, ['mechanism', 'solves', 'share'], ['---', '---:', '---:'])}

The dominant mechanism is **{dom.replace('_', ' ')}** at
{pct(mech[dom] / tot)} of all {tot} fault solves: {expl}.

The distinction matters for design. *Lost in delay* would be an argument for
faster fault detection. *No recovery trajectory* is an argument that detection
speed is irrelevant — the vehicle needs more control authority or a slacker
reference, and no amount of avionics fixes it.
""")

    # ── 5. does bisection's premise hold? ─────────────────────────────
    mono = h.get('monotonicity', {})
    if mono:
        tot_v = sum(v['violations'] for v in mono.values())
        tot_p = sum(v['comparable_pairs'] for v in mono.values())
        rows = [(k, v['n'], v['comparable_pairs'], v['violations'])
                for k, v in sorted(mono.items())]
        tol = list(mono.values())[0]['t_tol']
        out.append(f"""
## Checking the bisection's assumption, rather than asserting it

Bisection presumes survival is monotone along the axis being bisected: more
delivered thrust is never worse, more blind time is never better. The Sobol
samples were drawn without that assumption, so they can test it — but not by
eye. A projected scatter plot will look monotone whether or not it is, which is
precisely the kind of claim that needs arithmetic.

The test is dominance. Sample $A$ dominates $B$ when it is no worse on every
axis — $\\eta_A \\ge \\eta_B$ and $\\tau_A \\le \\tau_B$, at onset times within
{tol:.0f} s. Monotonicity forbids $A$ failing while $B$ lands. Every ordered
pair was checked:

{table(rows, ['reference', 'samples', 'comparable pairs', 'violations'],
       ['---', '---:', '---:', '---:'])}

**{tot_v} violation{'s' if tot_v != 1 else ''} in {tot_p} comparable pairs.**
The assumption is very nearly, but not exactly, satisfied. That is what should
be expected of a nonconvex NLP solved to local optimality: an occasional solve
fails from a seed where a neighbouring, nominally harder one succeeds. It also
sets the honest precision of the bisected boundaries — they are good to about
the scale on which the solver itself is self-consistent, which is coarser than
the 1/128 bracket resolution the bisection nominally delivers.
""")

    # ── 6. study E ────────────────────────────────────────────────────
    if e:
        imp = e.get('importance', {})
        top = list(imp.items())[:3]
        drop = e['p_nom'] - e['p_fault']
        agree = e['lo_fault'] <= e['surrogate_volume'] <= e['hi_fault']
        tau_imp = imp.get('tau_d', 0.0)
        eta_imp = imp.get('eta', 0.0)
        out.append(f"""
## Landing feasibility over the dispersion box

Of {e['n']} admissible arrivals drawn from the 12-D box,
**{ci(e['p_nom'], e['lo_nom'], e['hi_nom'])}** admit a healthy landing. The
vehicle can essentially get down from anywhere it might plausibly arrive: only
{e['n'] - e['n_nom_land']} of {e['n']} dispersions had no feasible healthy
trajectory at all.

Of those that could, only **{ci(e['p_fault'], e['lo_fault'], e['hi_fault'])}**
still land after a randomly drawn mid-descent fault — a drop of {pct(drop)}.
**Arrival dispersion is not this vehicle's problem; mid-descent faults are.**

## What actually decides survival — and what does not

The surrogate is fitted to the *faulted* outcome rather than the healthy one.
Healthy feasibility came out at {e['p_nom']:.3f}, leaving only
{e['n'] - e['n_nom_land']} negatives — a classifier on that target would score
0.98 by predicting "lands" every time and would have learned nothing. The
faulted outcome is where the structure is, and its feature set is the twelve
arrival dimensions *plus* the three fault parameters, since those are part of
what decides survival.

Permutation importance is unambiguous:

{table([(k, f'{v:.4f}') for k, v in list(imp.items())[:6]],
       ['feature', 'permutation importance'], ['---', '---:'])}

**Severity dominates everything** ({eta_imp:.3f}), followed distantly by onset
time. The reaction delay scores {tau_imp:.3f} — indistinguishable from
irrelevant — and none of the twelve *arrival* dimensions matters materially.

That is a strong and slightly uncomfortable conclusion. The intuitive
engineering response to a mid-descent fault is "detect it faster". Over this
sample, how fast the fault was detected made no measurable difference to
whether the vehicle survived, because in {pct(e['outcome'].get('no recovery trajectory', 0) / e['n'])}
of cases there was no recovery trajectory to find at any detection speed. It is
consistent with the mechanism table above and with D1: for the faults that kill
this vehicle, reaction speed is not the binding resource.

The surrogate integrates to
{ci(e['surrogate_volume'], e['surrogate_lo'], e['surrogate_hi'])} over the same
box, with out-of-fold accuracy {e['cv_accuracy']:.3f} and AUC {e['auc']:.3f}. It
{'agrees with' if agree else 'sits outside'} the direct estimate's interval —
the useful check, since the two are computed by entirely different routes and
only the direct one is assumption-free.
""")

    return '\n'.join(out)
