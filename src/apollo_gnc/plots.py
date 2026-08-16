"""
3-D actuation-envelope figures
════════════════════════════════════════════════════════════════════════
One figure per spacecraft, three panels:

  1  Actuator layout      — where every RCS thruster and TVC engine sits, which
                            way it pushes, and the gimbal cone it can sweep.
                            This is the geometry the other two panels follow
                            from, so it is shown rather than assumed.
  2  Achievable force set — convex hull of every net force the actuators can
                            produce, with the six axis maxima marked.
  3  Achievable moment set— same for net moment about the CG.

Colours are the validated categorical palette (checked with the dataviz
validator: lightness band, chroma floor, CVD separation and normal-vision
floor all pass on the light chart surface). Aqua sits below 3:1 contrast, so
it is always accompanied by a visible label — never used as the sole encoding.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from envelopes import achievable_set, axis_maxima, AXES, best_dir_in_cone

C_FORCE  = '#2a78d6'      # categorical slot 1 — blue
C_MOMENT = '#eb6834'      # slot 2 — orange
C_RCS    = '#1baf7a'      # slot 3 — aqua   (always directly labelled)
C_ENGINE = '#4a3aa7'      # slot 7 — violet
C_INK    = '#0b0b0b'
C_MUTED  = '#52514e'


def _unit(vals, base):
    """Pick a readable unit prefix — this fleet spans 10 mN to 3.1 MN."""
    m = np.nanmax(np.abs(vals)) if len(vals) else 0.0
    if not np.isfinite(m) or m == 0:
        return 1.0, base
    for scale, pre in ((1e6, 'M'), (1e3, 'k'), (1.0, ''), (1e-3, 'm')):
        if m >= scale:
            return scale, pre + base
    return 1e-3, 'm' + base


def _style3d(ax):
    ax.grid(True, alpha=0.15)
    for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane.pane.set_alpha(0.03)
        pane.pane.set_edgecolor('#cccccc')
    ax.tick_params(colors=C_MUTED, labelsize=8)


def _draw_hull(ax, P, hull, color, scale):
    """Filled hull with recessive edges. Falls back to a scatter when the set
    is degenerate (a flat or lower-dimensional set — e.g. a single fixed
    engine, whose force set is a line segment)."""
    Q = P / scale
    if hull is None:
        ax.scatter(Q[:, 0], Q[:, 1], Q[:, 2], c=color, s=6, alpha=0.6)
        return
    tri = [Q[s] for s in hull.simplices]
    ax.add_collection3d(Poly3DCollection(
        tri, facecolor=color, alpha=0.22, edgecolor=color,
        linewidths=0.25, zsort='average'))


def _equal_box(ax, Q, pad=1.15):
    r = np.abs(Q).max() * pad if len(Q) else 1.0
    r = max(r, 1e-9)
    ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(-r, r)
    ax.set_box_aspect((1, 1, 1))


def panel_layout(ax, veh):
    """Actuator geometry: positions, thrust directions, gimbal cones."""
    pts = ([t.pos for t in veh.rcs] + [e.pos for e in veh.engines]) or [np.zeros(3)]
    L = max(np.abs(np.array(pts)).max(), 1e-3)
    q = 0.30 * L                                  # quiver length

    for t in veh.rcs:
        ax.quiver(*t.pos, *(q * t.dir), color=C_RCS, linewidth=1.1,
                  arrow_length_ratio=0.25, alpha=0.9)
    if veh.rcs:
        Pr = np.array([t.pos for t in veh.rcs])
        ax.scatter(Pr[:, 0], Pr[:, 1], Pr[:, 2], c=C_RCS, s=14, depthshade=False)

    for e in veh.engines:
        ax.quiver(*e.pos, *(1.5 * q * e.axis), color=C_ENGINE, linewidth=2.0,
                  arrow_length_ratio=0.22)
        ax.scatter(*e.pos, c=C_ENGINE, s=45, marker='s', depthshade=False)
        if e.gimbal_max > 0:                      # sweep the deflection cone
            ring = []
            for a in np.linspace(0, 2*np.pi, 40):
                u = np.array([np.cos(a), np.sin(a), 0.0])
                perp = u - (u @ e.axis) * e.axis
                n = np.linalg.norm(perp)
                d = (np.cos(e.gimbal_max) * e.axis +
                     np.sin(e.gimbal_max) * perp / n) if n > 1e-9 else e.axis
                ring.append(e.pos + 1.5 * q * d)
            ring = np.array(ring)
            ax.plot(ring[:, 0], ring[:, 1], ring[:, 2],
                    color=C_ENGINE, lw=0.9, alpha=0.55)
            for k in range(0, 40, 5):
                ax.plot(*zip(e.pos, ring[k]), color=C_ENGINE, lw=0.5, alpha=0.35)

    _style3d(ax)
    # x/y share a scale so actuator rings stay circular, but z gets its own
    # range: a 70 m booster under a single equal-aspect box shrinks the engine
    # cluster to a dot and the layout becomes unreadable.
    P = np.array(pts)
    rxy = max(np.abs(P[:, :2]).max(), 1e-3) * 1.35
    z0, z1 = P[:, 2].min(), P[:, 2].max()
    zpad = max((z1 - z0) * 0.25, rxy * 0.35)
    ax.set_xlim(-rxy, rxy); ax.set_ylim(-rxy, rxy)
    ax.set_zlim(z0 - zpad, z1 + zpad)
    ax.set_box_aspect((1, 1, 0.85))
    ax.invert_zaxis()          # body +z is DOWN; draw it downward
    ax.set_xlabel('$x_B$ [m]', fontsize=8); ax.set_ylabel('$y_B$ [m]', fontsize=8)
    ax.set_zlabel('$z_B$ [m]  (down)', fontsize=8)
    gim = [np.rad2deg(e.gimbal_max) for e in veh.engines]
    gtxt = (f'gimbal ±{max(gim):.1f}°' if gim and max(gim) > 0 else 'no TVC')
    ax.set_title(f'Actuator layout\n{veh.n_rcs} RCS · {veh.n_engines} engine(s) · {gtxt}',
                 fontsize=10, color=C_INK)


def panel_set(ax, veh, moment, n_dirs):
    P, hull = achievable_set(veh, moment=moment, n_dirs=n_dirs)
    color = C_MOMENT if moment else C_FORCE
    base = 'N·m' if moment else 'N'
    scale, unit = _unit(np.linalg.norm(P, axis=1), base)

    _draw_hull(ax, P, hull, color, scale)

    mx = axis_maxima(veh)
    key = 'moment_Nm' if moment else 'force_N'
    lines = []
    for label, e in AXES:
        v = mx[label][key] / scale
        if abs(v) > 1e-12:
            ax.scatter(*(e * v), color=C_INK, s=11, depthshade=False, zorder=5)
        lines.append(f'{label}  {v:>9.3g}')
    # the six maxima are listed in a corner block rather than annotated in the
    # 3-D scene: four of them cluster near the origin on a set as elongated as
    # a booster's and the text collides into an unreadable knot
    ax.text2D(0.015, 0.985, f'max [{unit}]\n' + '\n'.join(lines),
              transform=ax.transAxes, fontsize=7, family='monospace',
              color=C_MUTED, va='top', ha='left',
              bbox=dict(boxstyle='round,pad=0.35', fc='#fcfcfb',
                        ec='#dddddd', lw=0.6, alpha=0.9))

    _style3d(ax)
    _equal_box(ax, P / scale)
    ax.set_xlabel(f'{"L" if moment else "$F_x$"} [{unit}]', fontsize=8)
    ax.set_ylabel(f'{"M" if moment else "$F_y$"} [{unit}]', fontsize=8)
    ax.set_zlabel(f'{"N" if moment else "$F_z$"} [{unit}]', fontsize=8)
    vol = hull.volume if hull is not None else 0.0
    ax.set_title(f'Achievable {"moment" if moment else "force"} set\n'
                 f'hull volume {vol/scale**3:.3g} {unit}³',
                 fontsize=10, color=C_INK)


def figure_for(veh, out_dir, n_dirs=1200):
    fig = plt.figure(figsize=(16.5, 5.8))
    est = sum(veh.is_estimated(k) for k in veh.flags)
    fig.suptitle(f'{veh.name}   —   {veh.category}',
                 fontsize=14, weight='bold', color=C_INK, y=0.99)

    for i, fn in enumerate([lambda a: panel_layout(a, veh),
                            lambda a: panel_set(a, veh, False, n_dirs),
                            lambda a: panel_set(a, veh, True, n_dirs)]):
        fn(fig.add_subplot(1, 3, i + 1, projection='3d'))

    handles = []
    if veh.n_rcs:
        handles.append(Line2D([0], [0], color=C_RCS, lw=2,
                              label=f'RCS thruster ({veh.n_rcs})'))
    if veh.n_engines:
        handles.append(Line2D([0], [0], color=C_ENGINE, lw=2,
                              label=f'Main / TVC engine ({veh.n_engines})'))
    handles += [Line2D([0], [0], color=C_FORCE, lw=6, alpha=0.5, label='Achievable force set'),
                Line2D([0], [0], color=C_MOMENT, lw=6, alpha=0.5, label='Achievable moment set'),
                Line2D([0], [0], color=C_INK, marker='o', ls='', ms=4, label='Per-axis maximum')]
    fig.legend(handles=handles, loc='lower center', ncol=len(handles), frameon=False,
               fontsize=9, bbox_to_anchor=(0.5, 0.005))

    fig.text(0.5, 0.055,
             f'mass {veh.mass:,.0f} kg   ·   I = ({veh.inertia[0]:,.0f}, '
             f'{veh.inertia[1]:,.0f}, {veh.inertia[2]:,.0f}) kg·m²   ·   '
             f'{est} of {len(veh.flags)} inputs ESTIMATED — see Provenance sheet',
             ha='center', fontsize=8, color=C_MUTED)

    fig.tight_layout(rect=[0, 0.10, 1, 0.96])
    safe = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in veh.name)
    path = out_dir / f'{safe.strip().replace(" ", "_")}.png'
    fig.savefig(path, dpi=145, facecolor='#fcfcfb')
    plt.close(fig)
    return path


def figure_fleet(vehicles, out_dir):
    """Cross-fleet comparison: per-axis linear and angular acceleration.

    Log scale on both — this fleet spans seven decades of acceleration, so a
    linear axis would collapse every satellite onto zero. One axis per panel
    (never a second y-scale): force and moment authority are different
    measures and get their own panel.
    """
    vs = [v for v in vehicles if v.engines or v.rcs]
    vs = sorted(vs, key=lambda v: -max(axis_maxima(v)[a]['accel_ms2']
                                       for a, _ in AXES))
    names = [v.name for v in vs]
    y = np.arange(len(vs))

    fig, axes = plt.subplots(1, 2, figsize=(15.5, 0.42 * len(vs) + 3.2))
    for ax, (key, lab, color) in zip(axes, [
            ('accel_ms2', 'Peak linear acceleration [m/s²]', C_FORCE),
            ('ang_accel_rads2', 'Peak angular acceleration [°/s²]', C_MOMENT)]):
        best, worst = [], []
        for v in vs:
            mx = axis_maxima(v)
            vals = [mx[a][key] for a, _ in AXES]
            if key == 'ang_accel_rads2':
                vals = list(np.rad2deg(vals))
            vals = [0.0 if abs(x) < 1e-12 else x for x in vals]
            best.append(np.nanmax(vals)); worst.append(np.nanmin(vals))
        best, worst = np.array(best), np.array(worst)

        # A worst axis of exactly zero means the vehicle has NO authority in
        # that direction. On a log axis that cannot be plotted as a position,
        # and clamping it to a tiny number would read as "very small but able".
        # Zeros are drawn as a cross on the floor line and called out in the
        # legend, so "none" never masquerades as "little".
        pos = np.concatenate([best[best > 0], worst[worst > 0]])
        floor = (pos.min() / 8.0) if len(pos) else 1e-6
        iz = worst <= 0
        lo = np.where(iz, floor, worst)

        ax.hlines(y[~iz], lo[~iz], best[~iz], color=color, lw=3, alpha=0.35)
        ax.hlines(y[iz], floor, best[iz], color=color, lw=3, alpha=0.15,
                  linestyles=':')
        ax.plot(best, y, 'o', color=color, ms=6, label='best axis')
        ax.plot(worst[~iz], y[~iz], 'o', mfc='white', mec=color, mew=1.4, ms=6,
                label='worst axis')
        if iz.any():
            ax.plot(np.full(iz.sum(), floor), y[iz], 'x', color=color, ms=7,
                    mew=1.8, label='worst axis = 0 (no authority)')
        ax.set_xlim(floor / 1.8, best.max() * 3)
        ax.set_xscale('log')
        ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel(lab, fontsize=9, color=C_INK)
        ax.grid(True, axis='x', alpha=0.18)
        ax.legend(frameon=False, fontsize=8, loc='lower right')
        for sp in ('top', 'right', 'left'):
            ax.spines[sp].set_visible(False)

    fig.suptitle('Fleet comparison — control authority spread between the best '
                 'and worst body axis', fontsize=13, weight='bold', color=C_INK)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = out_dir / '_fleet_comparison.png'
    fig.savefig(path, dpi=145, facecolor='#fcfcfb')
    plt.close(fig)
    return path
