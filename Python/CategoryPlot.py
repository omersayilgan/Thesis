"""
Spacecraft Propulsion System Redundancy Classification
=======================================================

Dimensionless parameter space for classifying spacecraft by their
propulsion architecture and redundancy characteristics.

Two composite indices reduce a 6-parameter space to 2D:

  MEI  = log10( Γ · μ / (1 − μ) )
         Mission Energy Index — propulsive demand
         Γ = thrust-to-weight ratio,  μ = propellant mass fraction

  SRI  = HRI_Δv × SRD_Δv  +  α × HRI_att × SRD_att
         System Resilience Index (propulsion-specific)
         HRI = n_installed / n_minimum   (component-level redundancy)
         SRD = min independent failures to lose function (system-level)
         α   = weighting of attitude-control redundancy (default 0.25)

A parallel-coordinates subplot decomposes SRI into its five constituents:
  HRI_Δv, SRD_Δv, HRI_att, SRD_att, DCF

DCF (Degraded Capability Fraction) captures cross-functionality:
  what fraction of mission Δv can attitude thrusters deliver alone
  if the main engine(s) fail.

Usage
-----
  python spacecraft_propulsion_classification.py          # default α = 0.25
  python spacecraft_propulsion_classification.py --alpha 0.5
  python spacecraft_propulsion_classification.py --dark   # dark theme
  python spacecraft_propulsion_classification.py --save   # save to PNG

Author: Generated with Claude
"""

import argparse
import os
import sys
import numpy as np

# ── Matplotlib backend selection ──────────────────────────────────────
# Must happen BEFORE any other matplotlib import.
# Priority: 1) --save flag → Agg (no GUI needed)
#           2) $DISPLAY / $WAYLAND_DISPLAY set → default backend (TkAgg etc.)
#           3) macOS → macosx backend (always available)
#           4) fallback → Agg with auto-save
import matplotlib
_save_mode = "--save" in sys.argv
_has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
_is_mac = sys.platform == "darwin"

if _save_mode or (not _has_display and not _is_mac):
    matplotlib.use("Agg")
# ──────────────────────────────────────────────────────────────────────

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from matplotlib.collections import LineCollection
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
# Data Model
# ─────────────────────────────────────────────

@dataclass
class Spacecraft:
    name: str
    category: str

    # Vehicle-level parameters
    gamma: float          # Thrust-to-weight ratio (Earth g reference)
    mu: float             # Propellant mass fraction

    # Δv delivery redundancy
    hri_dv: float         # HRI for main engine(s)
    srd_dv: int           # SRD for Δv delivery function

    # Attitude control redundancy
    hri_att: float        # HRI for RCS / attitude thrusters
    srd_att: int          # SRD for attitude control function

    # Cross-functionality
    dcf: float = 0.0      # Degraded Capability Fraction

    # Optional notes
    notes: str = ""

    @property
    def mei(self) -> float:
        """Mission Energy Index."""
        return np.log10(self.gamma * self.mu / (1 - self.mu))

    def sri(self, alpha: float = 0.25) -> float:
        """System Resilience Index (propulsion-specific)."""
        return self.hri_dv * self.srd_dv + alpha * self.hri_att * self.srd_att


# ─────────────────────────────────────────────
# Spacecraft Database
# ─────────────────────────────────────────────

SPACECRAFT = [
    # ── Launch Vehicle 1st Stages ──────────────────────────────────────
    Spacecraft("Saturn V S-IC", "Launch vehicle 1st stages",
               gamma=1.2, mu=0.91, hri_dv=1.25, srd_dv=2,
               hri_att=1.25, srd_att=2, dcf=0.0,
               notes="5× F-1; engine-out for 1 of 5"),
    Spacecraft("Falcon 9 S1", "Launch vehicle 1st stages",
               gamma=1.3, mu=0.88, hri_dv=1.29, srd_dv=3,
               hri_att=1.5, srd_att=2, dcf=0.0,
               notes="9× Merlin; can lose 2 engines"),
    Spacecraft("SLS Core Stage", "Launch vehicle 1st stages",
               gamma=1.15, mu=0.89, hri_dv=1.0, srd_dv=1,
               hri_att=1.0, srd_att=1, dcf=0.0,
               notes="4× RS-25; no engine-out capability"),
    Spacecraft("Super Heavy", "Launch vehicle 1st stages",
               gamma=1.5, mu=0.90, hri_dv=1.22, srd_dv=7,
               hri_att=1.5, srd_att=3, dcf=0.0,
               notes="33× Raptor; can lose ~6 engines"),
    Spacecraft("Ariane 5 ECA", "Launch vehicle 1st stages",
               gamma=1.2, mu=0.90, hri_dv=1.0, srd_dv=1,
               hri_att=1.0, srd_att=1, dcf=0.0,
               notes="1× Vulcain 2; single engine"),
    Spacecraft("Proton-M S1", "Launch vehicle 1st stages",
               gamma=1.3, mu=0.87, hri_dv=1.0, srd_dv=1,
               hri_att=1.0, srd_att=1, dcf=0.0,
               notes="6× RD-275M; needs all 6"),

    # ── Crewed Orbital Vehicles ────────────────────────────────────────
    Spacecraft("Apollo CSM", "Crewed orbital vehicles",
               gamma=0.25, mu=0.15, hri_dv=1.0, srd_dv=1,
               hri_att=2.0, srd_att=3, dcf=0.05,
               notes="Single SPS engine; 12 RCS in 4 quads"),
    Spacecraft("Crew Dragon", "Crewed orbital vehicles",
               gamma=0.30, mu=0.18, hri_dv=2.0, srd_dv=2,
               hri_att=2.67, srd_att=5, dcf=0.80,
               notes="16 Dracos serve both Δv and attitude"),
    Spacecraft("Soyuz MS", "Crewed orbital vehicles",
               gamma=0.20, mu=0.10, hri_dv=2.0, srd_dv=2,
               hri_att=2.0, srd_att=3, dcf=0.30,
               notes="SKD main + DPO backup set; 14 DPO RCS"),
    Spacecraft("Shuttle Orbiter", "Crewed orbital vehicles",
               gamma=0.35, mu=0.16, hri_dv=2.0, srd_dv=2,
               hri_att=3.0, srd_att=6, dcf=0.20,
               notes="2× OMS; 44 RCS (38 primary + 6 vernier)"),
    Spacecraft("Orion MPCV", "Crewed orbital vehicles",
               gamma=0.25, mu=0.14, hri_dv=1.5, srd_dv=2,
               hri_att=2.0, srd_att=3, dcf=0.15,
               notes="1× OMS-E + 8 aux thrusters; 24 RCS"),
    Spacecraft("Starliner", "Crewed orbital vehicles",
               gamma=0.28, mu=0.14, hri_dv=2.0, srd_dv=2,
               hri_att=2.5, srd_att=5, dcf=0.30,
               notes="4× OMAC engines; 28 RCS thrusters"),

    # ── Earth-Orbiting Satellites ──────────────────────────────────────
    Spacecraft("GPS III", "Earth-orbiting satellites",
               gamma=0.002, mu=0.04, hri_dv=1.0, srd_dv=1,
               hri_att=2.0, srd_att=2, dcf=0.0,
               notes="Single apogee motor; hydrazine RCS"),
    Spacecraft("TDRS", "Earth-orbiting satellites",
               gamma=0.002, mu=0.05, hri_dv=1.0, srd_dv=1,
               hri_att=2.0, srd_att=2, dcf=0.0,
               notes="GEO relay; single LAE + 12 RCS"),
    Spacecraft("ISS (Zvezda)", "Earth-orbiting satellites",
               gamma=0.0001, mu=0.01, hri_dv=1.0, srd_dv=1,
               hri_att=2.5, srd_att=4, dcf=0.0,
               notes="Reboost via Progress; 32 attitude thrusters"),
    Spacecraft("Tiangong", "Earth-orbiting satellites",
               gamma=0.0005, mu=0.02, hri_dv=1.0, srd_dv=1,
               hri_att=2.0, srd_att=3, dcf=0.0,
               notes="Station propulsion module"),
    Spacecraft("GOES-R", "Earth-orbiting satellites",
               gamma=0.001, mu=0.03, hri_dv=1.0, srd_dv=1,
               hri_att=1.5, srd_att=2, dcf=0.0,
               notes="GEO weather; stationkeeping thrusters"),

    # ── Deep Space Probes ──────────────────────────────────────────────
    Spacecraft("Cassini", "Deep space probes",
               gamma=0.008, mu=0.55, hri_dv=2.0, srd_dv=2,
               hri_att=2.67, srd_att=4, dcf=0.10,
               notes="Dual-redundant main engines; 16 RCS thrusters"),
    Spacecraft("Mars Recon Orbiter", "Deep space probes",
               gamma=0.01, mu=0.25, hri_dv=1.5, srd_dv=2,
               hri_att=2.0, srd_att=2, dcf=0.0,
               notes="6 main thrusters + 8 small RCS"),
    Spacecraft("Juno", "Deep space probes",
               gamma=0.005, mu=0.30, hri_dv=1.0, srd_dv=1,
               hri_att=2.0, srd_att=2, dcf=0.0,
               notes="Single LEROS-1b; 12 RCS thrusters"),
    Spacecraft("MESSENGER", "Deep space probes",
               gamma=0.01, mu=0.35, hri_dv=1.0, srd_dv=1,
               hri_att=2.0, srd_att=2, dcf=0.05,
               notes="Single biprop engine; 12 monoprop RCS"),
    Spacecraft("Voyager", "Deep space probes",
               gamma=0.0005, mu=0.06, hri_dv=1.0, srd_dv=1,
               hri_att=2.67, srd_att=2, dcf=0.0,
               notes="No main engine post-launch; 16 RCS dual-branch"),

    # ── Crewed Landers ─────────────────────────────────────────────────
    Spacecraft("Apollo LM", "Crewed landers",
               gamma=0.5, mu=0.60, hri_dv=1.0, srd_dv=1,
               hri_att=2.67, srd_att=4, dcf=0.15,
               notes="Single LMDE; 16 RCS; abort via ascent engine"),
    Spacecraft("Starship HLS", "Crewed landers",
               gamma=0.6, mu=0.82, hri_dv=1.5, srd_dv=3,
               hri_att=2.5, srd_att=4, dcf=0.10,
               notes="~6 Raptors for landing; hot-gas RCS"),
    Spacecraft("Blue Moon Mk 2", "Crewed landers",
               gamma=0.5, mu=0.65, hri_dv=1.0, srd_dv=1,
               hri_att=2.0, srd_att=3, dcf=0.10,
               notes="Single BE-7; RCS clusters"),
    Spacecraft("Altair (Constellation)", "Crewed landers",
               gamma=0.5, mu=0.65, hri_dv=1.33, srd_dv=2,
               hri_att=2.67, srd_att=4, dcf=0.10,
               notes="4× RL-10 derived; 16 RCS; engine-out for 1"),
    Spacecraft("LK (Soviet)", "Crewed landers",
               gamma=0.5, mu=0.58, hri_dv=1.0, srd_dv=1,
               hri_att=2.0, srd_att=2, dcf=0.10,
               notes="Single Block E engine; limited RCS"),
]


# ─────────────────────────────────────────────
# Category styling
# ─────────────────────────────────────────────

CATEGORIES = {
    "Launch vehicle 1st stages": {"color": "#2a78d6", "marker": "o", "order": 0},
    "Crewed orbital vehicles":   {"color": "#e34948", "marker": "s", "order": 1},
    "Earth-orbiting satellites":  {"color": "#daa520", "marker": "D", "order": 2},
    "Deep space probes":          {"color": "#1baf7a", "marker": "^", "order": 3},
    "Crewed landers":             {"color": "#7c5cbf", "marker": "p", "order": 4},
}


# ─────────────────────────────────────────────
# Plotting
# ─────────────────────────────────────────────

def setup_style(dark: bool = False):
    """Configure matplotlib for a clean, modern look."""
    if dark:
        plt.style.use("dark_background")
        return {
            "bg": "#1a1a19",
            "card": "#242423",
            "text": "#ffffff",
            "text2": "#b0afa8",
            "muted": "#6e6d69",
            "grid": "#2c2c2a",
            "spine": "#3a3a38",
        }
    else:
        plt.rcParams.update({"figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
        return {
            "bg": "#fcfcfb",
            "card": "#f5f4f0",
            "text": "#0b0b0b",
            "text2": "#52514e",
            "muted": "#898781",
            "grid": "#e8e7e2",
            "spine": "#c3c2b7",
        }


def plot_bubble(ax, spacecraft: list, alpha: float, theme: dict):
    """
    Main bubble chart: MEI vs SRI_prop.
    Bubble size ∝ DCF, marker shape ∝ category.
    """
    for cat_name, style in sorted(CATEGORIES.items(), key=lambda x: x[1]["order"]):
        vehicles = [s for s in spacecraft if s.category == cat_name]
        if not vehicles:
            continue

        xs = [v.mei for v in vehicles]
        ys = [v.sri(alpha) for v in vehicles]
        sizes = [max(50, v.dcf * 500 + 50) for v in vehicles]

        ax.scatter(
            xs, ys, s=sizes,
            c=style["color"], marker=style["marker"],
            alpha=0.7, edgecolors=style["color"],
            linewidths=1.5, label=cat_name, zorder=3,
        )

        # Label each point
        for v, x, y in zip(vehicles, xs, ys):
            # Shorten long names
            label = v.name
            if len(label) > 18:
                label = label[:16] + "…"
            ax.annotate(
                label, (x, y),
                textcoords="offset points", xytext=(8, 6),
                fontsize=7, color=theme["text2"],
                fontstyle="italic", zorder=4,
            )

    ax.set_xlabel("Mission Energy Index  (MEI)", fontsize=11,
                  fontweight="medium", color=theme["text"], labelpad=8)
    ax.set_ylabel(f"SRI$_{{prop}}$  (α = {alpha:.2f})", fontsize=11,
                  fontweight="medium", color=theme["text"], labelpad=8)

    ax.set_xlim(-5.8, 1.8)
    y_max = max(v.sri(alpha) for v in spacecraft) * 1.2 + 1
    ax.set_ylim(-0.5, max(16, y_max))

    ax.tick_params(colors=theme["muted"], labelsize=9)
    ax.grid(True, alpha=0.5, color=theme["grid"], linewidth=0.5)
    for spine in ax.spines.values():
        spine.set_color(theme["spine"])
        spine.set_linewidth(0.5)

    legend = ax.legend(
        loc="upper left", fontsize=8, framealpha=0.9,
        edgecolor=theme["spine"], fancybox=False,
        borderpad=0.8, labelspacing=0.7,
    )
    legend.get_frame().set_linewidth(0.5)
    for text in legend.get_texts():
        text.set_color(theme["text2"])

    # Formula annotation
    formula = (
        r"$\mathrm{SRI_{prop}} = "
        r"\mathrm{HRI}_{\Delta v} \times \mathrm{SRD}_{\Delta v}"
        r" + \alpha \cdot \mathrm{HRI}_{att} \times \mathrm{SRD}_{att}$"
    )
    ax.text(
        0.98, 0.02, formula, transform=ax.transAxes,
        fontsize=8, color=theme["muted"],
        ha="right", va="bottom",
        bbox=dict(boxstyle="round,pad=0.4", fc=theme["card"], ec=theme["spine"],
                  linewidth=0.5, alpha=0.9),
    )


def plot_parallel(ax, spacecraft: list, theme: dict):
    """
    Parallel coordinates decomposing SRI into five constituent axes.
    """
    axes_def = [
        ("hri_dv",  r"HRI$_{\Delta v}$",  0.8, 4.5),
        ("srd_dv",  r"SRD$_{\Delta v}$",  0,   8),
        ("hri_att", r"HRI$_{att}$",        0.8, 3.5),
        ("srd_att", r"SRD$_{att}$",        0,   7),
        ("dcf",     "DCF",                 0,   1.0),
    ]
    n_axes = len(axes_def)
    x_positions = np.linspace(0, 1, n_axes)

    # Draw vertical axis lines
    for i, (key, label, lo, hi) in enumerate(axes_def):
        x = x_positions[i]
        ax.plot([x, x], [0, 1], color=theme["spine"], linewidth=0.8, zorder=1)
        ax.text(x, 1.08, label, ha="center", va="bottom",
                fontsize=9, fontweight="medium", color=theme["text"])

        # Tick marks
        if key == "dcf":
            ticks = [0, 0.25, 0.5, 0.75, 1.0]
        elif hi <= 4.5:
            ticks = [1, 2, 3, 4]
        else:
            ticks = [t for t in range(0, int(hi) + 1, 2) if lo <= t <= hi]

        for t in ticks:
            y_norm = (t - lo) / (hi - lo)
            ax.plot([x - 0.01, x + 0.01], [y_norm, y_norm],
                    color=theme["muted"], linewidth=0.5)
            ax.text(x - 0.025, y_norm, f"{t:g}", ha="right", va="center",
                    fontsize=7, color=theme["muted"])

    # Draw polylines for each spacecraft
    for v in spacecraft:
        style = CATEGORIES[v.category]
        values = [v.hri_dv, v.srd_dv, v.hri_att, v.srd_att, v.dcf]
        y_norms = []
        for val, (_, _, lo, hi) in zip(values, axes_def):
            y_norms.append(np.clip((val - lo) / (hi - lo), 0, 1))

        points = list(zip(x_positions, y_norms))
        segments = [[points[i], points[i + 1]] for i in range(len(points) - 1)]
        lc = LineCollection(
            segments, colors=style["color"],
            linewidths=1.5, alpha=0.35, zorder=2,
        )
        ax.add_collection(lc)

    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-0.05, 1.18)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def create_figure(
    spacecraft: list,
    alpha: float = 0.25,
    dark: bool = False,
    save: bool = False,
    filename: str = "spacecraft_propulsion_classification.png",
):
    """Build the two-panel figure."""
    theme = setup_style(dark)

    fig = plt.figure(figsize=(14, 10), dpi=150)
    fig.patch.set_facecolor(theme["bg"])

    gs = gridspec.GridSpec(
        2, 1, height_ratios=[1.3, 1],
        hspace=0.35, left=0.08, right=0.95, top=0.92, bottom=0.06,
    )

    # ── Title ──
    fig.text(
        0.08, 0.96,
        "Spacecraft propulsion system classification",
        fontsize=16, fontweight="medium", color=theme["text"],
    )
    fig.text(
        0.08, 0.935,
        "Dimensionless redundancy parameters for chemical propulsion architectures",
        fontsize=10, color=theme["muted"],
    )

    # ── Bubble chart ──
    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor(theme["bg"])
    plot_bubble(ax1, spacecraft, alpha, theme)

    # ── Parallel coordinates ──
    ax2 = fig.add_subplot(gs[1])
    ax2.set_facecolor(theme["bg"])
    plot_parallel(ax2, spacecraft, theme)
    ax2.set_title(
        "Per-function propulsion redundancy decomposition",
        fontsize=11, fontweight="medium", color=theme["text"],
        loc="left", pad=20,
    )

    if save:
        fig.savefig(filename, dpi=200, bbox_inches="tight", facecolor=theme["bg"])
        print(f"Saved to {filename}")

    backend = matplotlib.get_backend().lower()
    if backend == "agg" and not save:
        # No GUI backend available and user didn't ask to save —
        # auto-save so the work isn't lost.
        fig.savefig(filename, dpi=200, bbox_inches="tight", facecolor=theme["bg"])
        print(f"No display available — auto-saved to {filename}")
        print("Tip: use --save to suppress this message, or install a GUI backend.")
    elif backend != "agg":
        plt.show()


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Spacecraft propulsion system redundancy classification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--alpha", type=float, default=0.25,
        help="Attitude-control weighting factor (0–1, default 0.25)",
    )
    parser.add_argument(
        "--dark", action="store_true",
        help="Use dark theme",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save figure to PNG",
    )
    parser.add_argument(
        "--filename", type=str, default="spacecraft_propulsion_classification.png",
        help="Output filename (default: spacecraft_propulsion_classification.png)",
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_vehicles",
        help="Print vehicle database as a table and exit",
    )
    args = parser.parse_args()

    if args.list_vehicles:
        print(f"\n{'Name':<26} {'Category':<28} {'Γ':>5} {'μ':>5} "
              f"{'HRI_Δv':>7} {'SRD_Δv':>7} {'HRI_att':>8} {'SRD_att':>8} "
              f"{'DCF':>5}  {'MEI':>6}  {'SRI':>6}")
        print("─" * 130)
        for v in sorted(SPACECRAFT, key=lambda s: (CATEGORIES[s.category]["order"], s.name)):
            print(f"{v.name:<26} {v.category:<28} {v.gamma:5.3f} {v.mu:5.2f} "
                  f"{v.hri_dv:7.2f} {v.srd_dv:7d} {v.hri_att:8.2f} {v.srd_att:8d} "
                  f"{v.dcf:5.2f}  {v.mei:6.2f}  {v.sri(args.alpha):6.2f}")
        return

    create_figure(
        SPACECRAFT,
        alpha=args.alpha,
        dark=args.dark,
        save=args.save,
        filename=args.filename,
    )


if __name__ == "__main__":
    main()