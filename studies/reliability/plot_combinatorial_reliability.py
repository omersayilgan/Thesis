#!/usr/bin/env python3
"""
Combinatorial failure probability against thrust-to-weight ratio.

    x = T/W          thrust used for T/W / vehicle weight (payload excluded)
    y = P(failure)   share of the failure sample space that breaks the vehicle

THE DIFFERENCE FROM plot_reliability.py
---------------------------------------
That script asks "how likely is a unit to fail?" and needs a per-unit failure
probability p that nobody publishes. This one asks nothing of the hardware's
reliability at all. It counts.

Every subset of the units is one point of the sample space - all 2^N of them,
each weighted equally - and the question is what FRACTION of that space the
vehicle cannot absorb. No p, no exponentials, just combinations.

RCS
    The required control DOF m comes first: a gimballed main engine does the
    translating, so where one exists the RCS is only responsible for the three
    moments (m = 3); where there is none, whatever the vehicle needs falls to
    the thrusters (6 for something that has to translate itself, 3 or 2 for
    the pointers and spinners).

    Then WHICH thruster losses cost that DOF. Thrusters push only, so this is
    geometry, not counting: by Farkas' Lemma the survivors keep full authority
    only if their wrench columns POSITIVELY span R^m, and a loss set F is
    fatal exactly when F contains every column on the positive side of some
    direction y. Those sets P_y = {i : y . w_i > 0} are enumerated exactly
    (minimal ones sit where y is orthogonal to m-1 independent columns), and
    a subset is fatal iff it contains one of them.

        P_fail(RCS) = #{F : F is fatal} / 2^N
                    = sum_k fatal_k / sum_k C(N,k)

    fatal_k is counted exactly for every k, not truncated at a depth.

ENGINES
    Interchangeable, so only how many fail matters - the question is how many
    are NEEDED.

    A BOOSTER needs enough thrust to leave the pad: n is the fewest main
    engines that hold T/W >= the threshold once the strap-ons are counted, and
    a stack that cannot clear it even intact has no redundancy (n = N). Losing
    N-n or more of them is then a failure:

        P_fail(booster) = sum_{k >= max(1, N-n)} C(N,k) / 2^N

    Everything else has no threshold to clear and steers on one engine, so
    n = 1 and --engine-mode decides what gets counted: 'losable' (default)
    every combination it could shed, sum_{k=1}^{N-1} C(N,k) / 2^N; 'fatal'
    only the losses that leave too few, sum_{k>N-1} C(N,k) / 2^N.

THE VEHICLE
    Either system going is enough, so the two combine as an OR:

        P_fail = P_rcs + P_eng - P_rcs * P_eng

    and a vehicle with only one system is judged on that one alone.

Usage
    python3 plot_combinatorial_reliability.py
    python3 plot_combinatorial_reliability.py --engine-mode fatal
    python3 plot_combinatorial_reliability.py --yscale linear
"""

import argparse
import csv
import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
G0 = 9.80665
DEFAULT_XLSX = HERE.parents[1] / "data" / "spacecraft_values.xlsx"

import rcs_dof                                                   # noqa: E402
from rcs_dof import DOF_ROWS, wrench_matrix                      # noqa: E402

CATEGORY_STYLE = {
    "Boosters":          ("#2a78d6", "o"),
    "LEO Satellites":    ("#1baf7a", "s"),
    "GEO Satellites":    ("#eda100", "^"),
    "Crewed Vehicles":   ("#e87ba4", "D"),
    "Deep Space Probes": ("#4a3aa7", "v"),
}
SURFACE, INK, INK2, INK3 = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8981"

SHORT = {
    "Solar Dynamics Observatory (SDO)": "SDO",
    "Meteosat Second Generation (MSG)": "MSG",
    "Orion (CM + European Service Module)": "Orion",
    "Apollo Command & Service Module": "Apollo CSM",
    "Apollo Lunar Module": "Apollo LM",
    "Crew Dragon (Dragon 2)": "Crew Dragon",
    "Cassini (Cassini-Huygens)": "Cassini",
    "GRACE-FO (per satellite)": "GRACE-FO",
    "GOES-16 (GOES-R)": "GOES-16",
    "GOES-19 (GOES-U)": "GOES-19",
}


# --- reading the workbook ---------------------------------------------------

def val(x):
    """Float for a numeric cell, else None ('n/d', 'n/a', blank, text)."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def read_rows(xlsx):
    df = pd.read_excel(xlsx, "Data")
    rows = []
    for _, r in df.iterrows():
        if not isinstance(r["Spacecraft"], str):
            continue
        rows.append(dict(
            category=r["Category"], name=r["Spacecraft"],
            main_f=val(r["Main engine thrust, each [N]"]),
            main_n=val(r["No. of main engines"]),
            rcs_f=val(r["RCS thrust, each [N]"]),
            rcs_n=val(r["No. of RCS thrusters"]),
            aux_f=val(r["Aux thrust, each [N]"]),
            aux_n=val(r["No. of aux units"]),
            mass=val(r["Reference mass, as published [kg]"]),
            payload=val(r["Payload mass excluded [kg]"]),
            prop_units=val(r["Propulsive units counted (main-thrust capable)"]),
            units=val(r["Units installed, N"]),
            groups=val(r["Actuator groups/clusters, k"]),
            dof=val(r["Control DOF required, m"])))
    return rows


def thrust_and_tw(r):
    """Total thrust used for T/W, and T/W itself (payload excluded)."""
    def tier(f, n):
        return None if f is None or n is None else f * n

    tiers = [tier(r["main_f"], r["main_n"]), tier(r["aux_f"], r["aux_n"])]
    if r["category"] != "Boosters":            # boosters neglect the RCS tier
        tiers.append(tier(r["rcs_f"], r["rcs_n"]))
    thrust = sum(t for t in tiers if t is not None)
    mass = None if r["mass"] is None else r["mass"] - (r["payload"] or 0.0)
    tw = thrust / (mass * G0) if mass and mass > 0 and thrust > 0 else None
    return thrust, mass, tw


# --- the RCS side: which loss sets cost a control DOF ------------------------

def minimal_fatal_masks(W, tol=1e-9):
    """Bitmasks of the MINIMAL thruster losses that cost a control DOF.

    A loss set F is fatal when the survivors no longer positively span R^m,
    which by Farkas' Lemma means some direction y != 0 has y . w_i <= 0 for
    every survivor - i.e. F contains all of

        P_y = { i : y . w_i > 0 }

    So the fatal sets are exactly the supersets of the P_y, and every subset
    of the sample space can be classified by testing against the minimal ones.

    The count #P_y is piecewise constant in y and changes only as y crosses a
    plane w_i^perp; sliding y onto such a plane moves columns off the strictly
    positive side and never onto it, so every MINIMAL P_y is attained with y
    orthogonal to m-1 linearly independent columns. Enumerating those C(N,m-1)
    subsets is therefore exact, not a sample.
    """
    m, N = W.shape
    norms = np.linalg.norm(W, axis=0)
    Wh = W / np.where(norms > tol, norms, 1.0)      # compare directions fairly
    bit = 1 << np.arange(N)

    found = set()
    for idx in (combinations(range(N), m - 1) if m > 1 else [()]):
        A = Wh[:, list(idx)] if idx else np.zeros((m, 0))
        if A.shape[1]:
            s = np.linalg.svd(A, compute_uv=False)
            if np.sum(s > tol) < m - 1:
                continue                            # degenerate subset
            _, s2, vt = np.linalg.svd(A.T)
            rank = int(np.sum(s2 > tol))
        else:
            vt, rank = np.eye(m), 0
        for y in vt[rank:]:
            for sgn in (1.0, -1.0):
                pos = (sgn * y) @ Wh > tol
                found.add(int(bit[pos].sum()))

    # keep only the minimal ones: a superset of a fatal set is fatal anyway
    masks = sorted(found, key=lambda v: bin(v).count("1"))
    minimal = []
    for mk in masks:
        if not any(mn & mk == mn for mn in minimal):
            minimal.append(mk)
    return minimal


_POP16 = np.array([bin(i).count("1") for i in range(1 << 16)], dtype=np.uint8)


def count_fatal(N, minimal, chunk=1 << 21):
    """How many of the 2^N loss sets are fatal, split by how many failed.

    Brute force over the whole sample space, which is what makes it exact:
    a set is fatal iff it contains one of the minimal fatal sets, and that is
    one bitwise AND per minimal set. N <= 24 here, so this is 16M masks at
    worst - seconds, and no truncation depth to apologise for.
    """
    counts = np.zeros(N + 1, dtype=np.int64)
    if not minimal:
        return counts
    if 0 in minimal:                                # already broken intact
        return np.array([math.comb(N, k) for k in range(N + 1)], dtype=np.int64)
    mins = np.array(minimal, dtype=np.uint32)
    for start in range(0, 1 << N, chunk):
        f = np.arange(start, min(start + chunk, 1 << N), dtype=np.uint32)
        fatal = np.zeros(f.shape, dtype=bool)
        for mk in mins:
            np.logical_or(fatal, (f & mk) == mk, out=fatal)
        f = f[fatal]
        k = (_POP16[f & 0xFFFF].astype(np.int64) + _POP16[f >> 16])
        counts += np.bincount(k, minlength=N + 1)
    return counts


def cluster_fallback(r):
    """Fatal-set counts for a vehicle whose thruster GEOMETRY is unknown.

    Without the wrench columns there is nothing to test for positive spanning,
    so the only honest answer is the worst case the workbook's own redundancy
    columns describe: losing one whole cluster of floor(N/k) thrusters costs
    the DOF, and any larger loss does too. Every subset that big is counted
    fatal, which OVERSTATES the failure share - a real geometry always absorbs
    some of those. It is flagged as 'cluster' in the CSV for exactly that
    reason, and never mixed silently with the exact counts.
    """
    if not r["units"] or not r["groups"]:
        return None, None
    N, per = int(r["units"]), max(1, int(r["units"]) // int(r["groups"]))
    counts = np.array([math.comb(N, k) if k >= per else 0
                       for k in range(N + 1)], dtype=np.int64)
    return N, counts


def rcs_dof_required(r, has_tvc):
    """How many DOF the RCS alone is responsible for.

    With a gimballed main engine to translate, the thrusters only have to hold
    attitude - the three moment rows. Without one, whatever the vehicle needs
    falls to them: 6 for a vehicle that translates itself, 3 for the pointers,
    and the workbook's lower figure for the spin-stabilised ones, whose design
    deliberately avoids controlling the third axis.
    """
    if r["dof"] is None:
        return None
    return min(int(r["dof"]), 3) if has_tvc else int(r["dof"])


# --- the engine side: pure counting -----------------------------------------

def engine_system(r, eo_threshold):
    """(N engines installed, n of them needed) or None.

    For a BOOSTER "needed" is a thrust question, not a control question: it
    must hold T/W >= the liftoff threshold, so n is the fewest main engines
    that still clear it once the strap-ons are counted. A stack that cannot
    clear the threshold even with every engine lit has no redundancy at all -
    n = N, nothing is sheddable.

    Everything else keeps attitude control on a single engine, so n = 1.
    """
    if r["category"] == "Boosters":
        if not (r["main_f"] and r["main_n"] and r["mass"]):
            return None
        N = int(r["main_n"])
        aux = (r["aux_f"] or 0.0) * (r["aux_n"] or 0.0)
        W = (r["mass"] - (r["payload"] or 0.0)) * G0
        need = next((n for n in range(N + 1)
                     if (aux + n * r["main_f"]) / W >= eo_threshold), None)
        return N, (N if need is None else need)
    # no propulsive unit count means no separable engine system: either no main
    # engine at all, or the thrusters ARE the attitude tier
    if not r["prop_units"]:
        return None
    return int(r["prop_units"]), 1


def engine_fail_probability(N, need, mode, booster):
    """Share of the 2^N engine loss sets counted as failures.

    A booster is counted the way the thrust budget reads it: if n of N engines
    are enough, then losing N-n OR MORE is a failure,

        P_fail = sum_{k >= max(1, N-n)} C(N,k) / 2^N

    The lower limit of 1 is the one liberty taken - k = 0 is the intact
    vehicle, which cannot be a failure however tight the margin is. Note the
    boundary term is deliberately pessimistic: losing exactly N-n leaves n
    engines, which still clears the threshold, and it is counted as a failure
    anyway.

    Everything else is counted the same way with n = 1: it steers on any one
    engine, so losing N-1 or more is a failure. A SINGLE-engine vehicle then
    has no redundancy to enumerate and comes out at 1/2 - the one loss set out
    of two that is not the intact vehicle - which is the point. Counting the
    combinations it could SHED instead (--engine-mode losable) hands exactly
    those vehicles a failure share of zero, because there is nothing to shed:
    no redundancy reads as perfect. That is why it is not the default.
    """
    total = float(1 << N)
    if mode == "losable" and not booster:
        return sum(math.comb(N, k)
                   for k in range(1, N - need + 1)) / total
    return sum(math.comb(N, k)
               for k in range(max(1, N - need), N + 1)) / total


# --- putting the vehicle together -------------------------------------------

def evaluate(rows, args):
    vehicles = {v.name: v for v in rcs_dof.build_all()}
    for r in rows:
        thrust, mass, tw = thrust_and_tw(r)
        eng = engine_system(r, args.engine_out_threshold)
        r.update(thrust=thrust, vehicle_mass=mass, tw=tw, eng=eng)
        r["P_eng"] = (None if eng is None else engine_fail_probability(
            *eng, args.engine_mode, r["category"] == "Boosters"))

        m = rcs_dof_required(r, eng is not None)
        veh = vehicles.get(r["name"])
        W = wrench_matrix(veh) if veh else None
        r.update(rcs_dof=m, rcs_N=None, rcs_minimal=None, rcs_counts=None,
                 P_rcs=None, rcs_basis="none")
        if W is None or W.shape[1] == 0 or m is None or m not in DOF_ROWS:
            # The vehicle may still HAVE an RCS - the geometry is just not
            # modelled. Scoring it engine-only would read as "no RCS", so it
            # either gets the cluster fallback or is left out and reported.
            if r["units"] and args.rcs_fallback == "cluster":
                N, counts = cluster_fallback(r)
                if N:
                    r.update(rcs_N=N, rcs_counts=counts, rcs_basis="cluster",
                             P_rcs=float(counts.sum()) / float(1 << N))
            continue
        Wm, N = W[DOF_ROWS[m], :], W.shape[1]
        minimal = minimal_fatal_masks(Wm)
        counts = count_fatal(N, minimal)
        r.update(rcs_N=N, rcs_minimal=minimal, rcs_counts=counts,
                 rcs_basis="geometry",
                 P_rcs=float(counts.sum()) / float(1 << N))

    gap = [r["name"] for r in rows
           if r["units"] and r["P_rcs"] is None]
    if gap:
        print("warning: RCS installed but no thruster geometry, so no RCS "
              "term, so LEFT OUT: " + ", ".join(gap) +
              "\n         (--rcs-fallback cluster scores them on the "
              "workbook's cluster count instead)",
              file=sys.stderr)

    for r in rows:
        a, b = r["P_rcs"], r["P_eng"]
        # A vehicle whose RCS could not be evaluated is NOT a vehicle without
        # an RCS. Scoring it on its engines alone would put it on the plot
        # with a term missing, which reads as redundancy it was never given.
        if a is None and r["units"]:
            r["P_fail"] = r["P_success"] = None
            continue
        r["P_fail"] = (a if b is None else b if a is None
                       else a + b - a * b) if (a is not None or b is not None) else None
        r["P_success"] = None if r["P_fail"] is None else 1.0 - r["P_fail"]
    return rows


# --- output -----------------------------------------------------------------

def write_csv(path, rows):
    depth = max((len(r["rcs_counts"]) - 1 for r in rows
                 if r["rcs_counts"] is not None),
                default=0)
    fatal_cols = [f"Fatal {k}-thruster losses" for k in range(1, depth + 1)]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Category", "Spacecraft", "T/W",
                    "RCS units N", "RCS DOF required", "RCS basis",
                    "Minimal fatal sets",
                    "Fewest fatal failures", "Fatal loss sets", "Sample space",
                    *fatal_cols, "P(fail) RCS",
                    "Engines N", "Engines needed n", "Engines losable",
                    "Engine loss sets counted",
                    "Engine sample space", "P(fail) engines",
                    "P(fail) vehicle", "P(success) vehicle", "Plotted"])
        for r in rows:
            c = r["rcs_counts"]
            f = lambda v, s="{:.9f}": "n/a" if v is None else s.format(v)
            N, e = r["rcs_N"], r["eng"]
            w.writerow([
                r["category"], r["name"], f(r["tw"], "{:.6g}"),
                N or "n/a", r["rcs_dof"] if N else "n/a",
                r["rcs_basis"] if N else "n/a",
                len(r["rcs_minimal"]) if r["rcs_minimal"] else "n/a",
                (min((k for k in range(1, N + 1) if c[k]), default="none")
                 if N else "n/a"),
                int(c.sum()) if N else "n/a", 1 << N if N else "n/a",
                *[(int(c[k]) if N and k < len(c) else "n/a")
                  for k in range(1, depth + 1)],
                f(r["P_rcs"]),
                e[0] if e else "n/a", e[1] if e else "n/a",
                (e[0] - e[1]) if e else "n/a",
                (round(r["P_eng"] * (1 << e[0])) if e else "n/a"),
                (1 << e[0]) if e else "n/a", f(r["P_eng"]),
                f(r["P_fail"]), f(r["P_success"]),
                "yes" if r["tw"] and r["P_fail"] is not None else "no"])


def place_labels(fig, ax, anns, pts, key, pad=2.0):
    """Nudge the point labels off each other and off the markers. Cosmetic
    only: it moves text, never a point."""
    offsets = [(dx, dy, ha) for dy in (4, -12, 15, -23, 26, -34, 38, -46)
               for dx, ha in ((9, "left"), (-9, "right"))]
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    axbox = ax.get_window_extent(renderer=rend)
    taken = []
    for p in pts:
        x, y = ax.transData.transform((p["tw"], p[key]))
        taken.append(matplotlib.transforms.Bbox.from_bounds(x - 9, y - 9, 18, 18))

    def cost(box):
        c = 0.0
        for t in taken:
            dx = min(box.x1, t.x1) - max(box.x0, t.x0)
            dy = min(box.y1, t.y1) - max(box.y0, t.y0)
            if dx > 0 and dy > 0:
                c += dx * dy
        outside = (max(0, axbox.y0 - box.y0) + max(0, box.y1 - axbox.y1) +
                   max(0, axbox.x0 - box.x0) + max(0, box.x1 - axbox.x1))
        return c + outside * 1000.0
    for i in sorted(range(len(anns)), key=lambda i: -len(anns[i].get_text())):
        ann, best = anns[i], None
        for dx, dy, ha in offsets:
            ann.xyann = (dx, dy)
            ann.set_horizontalalignment(ha)
            b = ann.get_window_extent(renderer=rend)
            box = matplotlib.transforms.Bbox.from_bounds(
                b.x0 - pad, b.y0 - pad, b.width + 2 * pad, b.height + 2 * pad)
            c = cost(box)
            if best is None or c < best[0]:
                best = (c, dx, dy, ha, box)
            if c == 0.0:
                break
        _, dx, dy, ha, box = best
        ann.xyann, _ = (dx, dy), ann.set_horizontalalignment(ha)
        taken.append(box)
        if ann.arrow_patch is not None:
            ann.arrow_patch.set_visible(abs(dy) > 16)


def draw(rows, args):
    # Plotted as SUCCESS, 1 - P_fail: the interesting vehicles are the ones
    # that absorb the most, and they belong at the top.
    key = "P_fail" if args.plot == "failure" else "P_success"
    plotted = [r for r in rows if r["tw"] and r[key] is not None]
    fig, ax = plt.subplots(figsize=(13, 8.5))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    for cat, (colour, marker) in CATEGORY_STYLE.items():
        pts = [r for r in plotted if r["category"] == cat]
        if pts:
            ax.scatter([p["tw"] for p in pts], [p[key] for p in pts],
                       s=125, c=colour, marker=marker, edgecolors=SURFACE,
                       linewidths=1.6, zorder=3, label=cat)

    anns = [ax.annotate(SHORT.get(r["name"], r["name"]),
                        (r["tw"], r[key]), textcoords="offset points",
                        xytext=(9, 4), fontsize=7.6, color=INK2, zorder=4,
                        arrowprops=dict(arrowstyle="-", lw=0.6, color="#b8b7b0",
                                        shrinkA=1, shrinkB=4))
            for r in plotted]

    ax.set_xscale("log")
    xs = [r["tw"] for r in plotted]
    ax.set_xlim(min(xs) / 4.0, max(xs) * 4.0)
    ys = [r[key] for r in plotted]
    if args.yscale == "log":
        ax.set_yscale("log")
    else:
        span = max(ys) - min(ys) or 1.0
        ax.set_ylim(max(0.0, min(ys) - 0.12 * span), min(1.0, max(ys) + 0.12 * span))

    ax.set_xlabel("Thrust-to-weight ratio  T/W  [-]   (payload excluded)",
                  fontsize=10.5, color=INK, labelpad=9)
    fail = key == "P_fail"
    ax.set_ylabel(("Probability of a failure combination\n"
                   "(share of the 2^N loss sets the vehicle cannot absorb)")
                  if fail else
                  ("Probability the vehicle survives\n"
                   "(share of the 2^N loss sets it can absorb)"),
                  fontsize=10.5, color=INK, labelpad=9)
    ax.set_title("Combinatorial "
                 + ("failure" if fail else "success")
                 + " probability against thrust-to-weight ratio",
                 fontsize=13.5, color=INK, pad=46, loc="left", fontweight="bold")

    ax.text(0.0, 1.045,
            ("" if fail else r"$P_{success} = 1 - P_{fail}$,   ")
            + r"$P_{fail} = P_{RCS} + P_{eng} - P_{RCS}P_{eng}$,   "
            r"$P_{RCS} = \sum_k \mathrm{fatal}_k / 2^{N}$,   "
            r"$P_{eng} = \sum_k \binom{N}{k} / 2^{N}$"
            "   ·   no per-unit failure rate assumed",
            transform=ax.transAxes, fontsize=8.6, color=INK3)
    est = [r for r in plotted if r["rcs_basis"] == "cluster"]
    ax.text(0.0, 1.012,
            "RCS fatal sets: exact over the actuator geometry (Farkas, every k)"
            + (f", floor(N/k) worst case for {', '.join(SHORT.get(r['name'], r['name']) for r in est)}"
               " (no geometry)" if est else "")
            + f"   ·   engines: booster needs n of N for T/W ≥ "
            f"{args.engine_out_threshold:g}, N-n or more lost is a failure; "
            f"others {args.engine_mode} combinations on one engine"
            + f"   ·   {len(plotted)} of {len(rows)} spacecraft",
            transform=ax.transAxes, fontsize=8.6, color=INK3)

    ax.grid(True, which="both", linewidth=0.6, color="#e3e3df", zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d5d5d0")
    ax.tick_params(colors=INK2, labelsize=9)

    # No fixed corner survives both orientations - the crowd moves when the
    # axis flips, and a legend pinned to a corner lands on top of whoever is
    # there (GRACE-FO on one flip, three boosters on the other). "best" picks
    # the emptiest region from the data itself.
    legend = ax.legend(loc="best", frameon=True, fontsize=9.2,
                       facecolor=SURFACE, edgecolor="#d5d5d0", framealpha=1.0,
                       borderpad=0.8, labelspacing=0.7, title="Spacecraft class")
    legend.get_title().set_fontsize(9.2)
    legend.get_title().set_color(INK)
    for t in legend.get_texts():
        t.set_color(INK2)

    fig.tight_layout()
    place_labels(fig, ax, anns, plotted, key)
    fig.savefig(args.out, dpi=args.dpi, facecolor=SURFACE, bbox_inches="tight")
    return plotted


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path,
                    default=HERE / "combinatorial_success_vs_tw.png")
    ap.add_argument("--csv", type=Path,
                    default=HERE / "combinatorial_success_vs_tw.csv")
    ap.add_argument("--engine-mode", choices=["fatal", "losable"],
                    default="fatal",
                    help="'fatal' (default) counts the losses that leave too "
                         "few engines, N-n or more, the same rule the boosters "
                         "use; 'losable' counts every combination a non-booster "
                         "could shed, which scores a single-engine vehicle at 0")
    ap.add_argument("--rcs-fallback", choices=["none", "cluster"],
                    default="none",
                    help="what to do with a vehicle that has an RCS but no "
                         "modelled thruster geometry: 'none' (default) leaves "
                         "its RCS term out and says so; 'cluster' counts every "
                         "loss of floor(N/k) or more as fatal")
    ap.add_argument("--engine-out-threshold", type=float, default=1.2,
                    help="booster liftoff T/W threshold for engine-out (1.2)")
    ap.add_argument("--plot", choices=["success", "failure"], default="success",
                    help="plot 1 - P (default) or P itself")
    ap.add_argument("--yscale", choices=["linear", "log"], default="linear")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    if not args.xlsx.exists():
        sys.exit(f"error: workbook not found: {args.xlsx}")
    rcs_dof.WORKBOOK = args.xlsx

    rows = evaluate(read_rows(args.xlsx), args)
    write_csv(args.csv, rows)
    plotted = draw(rows, args)

    print(f"wrote {args.out}\nwrote {args.csv}\n")
    print(f"{'Spacecraft':38s} {'T/W':>8s} {'m':>3s} {'N':>3s} "
          f"{'eng':>7s} {'P(fail) RCS':>12s} {'P(fail) eng':>12s} {'P(success)':>12s}")
    for r in sorted(rows, key=lambda r: (r["category"], r["name"])):
        f = lambda v: "         n/a" if v is None else f"{v:12.9f}"
        tw = f"{r['tw']:8.3f}" if r["tw"] else "     n/d"
        e = f"{r['eng'][1]}/{r['eng'][0]}" if r["eng"] else "-"
        print(f"{r['name'][:38]:38s} {tw} {r['rcs_dof'] or '  -':>3} "
              f"{r['rcs_N'] or '  -':>3} {e:>7s} {f(r['P_rcs'])} "
              f"{f(r['P_eng'])} {f(r['P_success'])}")
    skipped = [r for r in rows if r not in plotted]
    if skipped:
        print(f"\n{len(skipped)} not plotted (no T/W or no actuation data): "
              + ", ".join(r["name"] for r in skipped))


if __name__ == "__main__":
    main()
