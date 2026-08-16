"""
Animate the Apollo LM landing
═════════════════════════════
Reads the trajectory saved by `save_trajectory.py` and renders a 3-D animation
of a procedural Apollo Lunar Module (descent + ascent stage, four landing legs,
engine plume) flying the descent and settling on the pad. The engine plume
switches off at cut-off.

    python animate_landing.py                         # -> landing.mp4 (or .gif)
    python animate_landing.py --data apollo_trajectory.npz --out landing.gif

Body frame: x fwd, y right, z down. Plot axes: (x_E, y_E, altitude = -z_E),
matching apollo_full's trajectory_with_axes figure.
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')                      # headless render
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
from matplotlib.animation import FuncAnimation, writers


# ── attitude: body-to-surface DCM (3-2-1 Euler), same convention as apollo_full
def dcm_eb(phi, th, psi):
    cp, sp = np.cos(phi), np.sin(phi)
    ct, st = np.cos(th),  np.sin(th)
    cs, ss = np.cos(psi), np.sin(psi)
    return np.array([
        [ct*cs,  sp*st*cs - cp*ss,  cp*st*cs + sp*ss],
        [ct*ss,  sp*st*ss + cp*cs,  cp*st*ss - sp*cs],
        [-st,    sp*ct,             cp*ct]])


# ══════════════════════════════════════════════════════════════════════
#  Procedural Apollo LM model  (body frame, z down; sizes exaggerated so the
#  vehicle is visible against a ~1 km descent, like the 30 m axis triads)
# ══════════════════════════════════════════════════════════════════════

def _prism(radius, z_top, z_bot, n=8, phase=np.pi/8):
    """Octagonal prism -> list of quad side faces + top & bottom caps."""
    a = phase + np.linspace(0, 2*np.pi, n, endpoint=False)
    top = np.c_[radius*np.cos(a), radius*np.sin(a), np.full(n, z_top)]
    bot = np.c_[radius*np.cos(a), radius*np.sin(a), np.full(n, z_bot)]
    faces = [np.array([top[i], top[(i+1) % n], bot[(i+1) % n], bot[i]])
             for i in range(n)]
    faces.append(top)              # top cap
    faces.append(bot[::-1])        # bottom cap
    return faces, top, bot


def lm_model(S=16.0):
    """Return (body_faces, foot_faces, leg_segments) in the body frame.
    S sets the overall half-size in metres (full span ~2.3*S)."""
    # descent stage (main box) — z down, so 'up' is -z
    d_r, d_hi, d_lo = 0.62*S, -0.28*S, 0.28*S
    desc, d_top, d_bot = _prism(d_r, d_hi, d_lo)
    # ascent stage — smaller, sitting on top of the descent stage
    a_r = 0.40*S
    asc, _, _ = _prism(a_r, d_hi - 0.55*S, d_hi)
    body_faces = desc + asc

    # four landing legs: from upper attach on the descent stage out to footpads
    foot_r, foot_z = 1.15*S, d_lo + 0.42*S           # footpad radius & depth
    att_r,  att_z  = 0.60*S, d_hi + 0.10*S           # leg attach point
    leg_segments, foot_faces = [], []
    for az in np.deg2rad([45, 135, 225, 315]):
        c, s = np.cos(az), np.sin(az)
        attach = np.array([att_r*c,  att_r*s,  att_z])
        foot   = np.array([foot_r*c, foot_r*s, foot_z])
        leg_segments.append(np.array([attach, foot]))
        # a small square footpad in the x-y plane at the foot
        t = np.array([-s, c, 0.0]) * 0.12*S          # tangent
        rad = np.array([c, s, 0.0]) * 0.12*S         # radial
        foot_faces.append(np.array([foot+rad+t, foot+rad-t,
                                    foot-rad-t, foot-rad+t]))
    return body_faces, foot_faces, leg_segments


def make_cone(base, axis, radius, length, n=12):
    """Triangle-fan cone in the body frame: base ring of `radius` centred at
    `base`, apex at `base + length*axis`. `axis` need not be unit or aligned to
    an axis (used for the gimballed DPS plume and the 16 RCS jets)."""
    axis = np.asarray(axis, float)
    L = np.linalg.norm(axis)
    if L < 1e-9 or length <= 0:
        return []
    axis = axis / L
    ref = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(axis, ref); u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    a = np.linspace(0, 2*np.pi, n, endpoint=False)
    ring = base + radius*(np.cos(a)[:, None]*u + np.sin(a)[:, None]*v)
    tip = base + length*axis
    return [np.array([ring[i], ring[(i+1) % n], tip]) for i in range(n)]


def dps_plume(S, gp, gy, frac, flick=1.0):
    """DPS exhaust cones (bright inner core + translucent outer flame). The
    plume exits opposite the gimballed thrust, so it tilts with the gimbal."""
    e = np.array([-np.sin(gp), np.cos(gp)*np.sin(gy), np.cos(gp)*np.cos(gy)])
    nozzle = np.array([0.0, 0.0, 0.28*S])
    length = (0.45 + 1.25*frac) * S * flick        # grows with thrust
    outer = make_cone(nozzle, e, 0.24*S, length,        14)
    inner = make_cone(nozzle, e, 0.12*S, 0.68*length,   14)
    return outer, inner


def rcs_plumes(S, rcs_pos_m, rcs_dir, fire, F_rcs, thresh=0.04):
    """One small cone per firing RCS thruster, exiting opposite its fire
    direction, length scaled by the commanded force."""
    faces = []
    for i in range(len(fire)):
        f = fire[i] / F_rcs
        if f > thresh:
            length = (0.28 + 0.75*min(f, 1.0)) * S
            faces += make_cone(rcs_pos_m[i], -rcs_dir[i], 0.07*S, length, 8)
    return faces


# ── transform body-frame vertices to plot coords (x_E, y_E, alt=-z_E)
def to_plot(V, r_plot, C):
    W = V @ C.T                       # surface-frame offset (n,3)
    return np.column_stack([r_plot[0] + W[:, 0],
                            r_plot[1] + W[:, 1],
                            r_plot[2] - W[:, 2]])


def load(path):
    d = np.load(path)
    return {k: d[k] for k in d.files}


def resample(D, nframes):
    """Interpolate everything to a uniform time grid so playback is smooth
    (the free-fall phase is finely sampled; the descent coarsely)."""
    t = D['t']
    tt = np.linspace(t[0], t[-1], nframes)
    rows = lambda A: np.vstack([np.interp(tt, t, A[i]) for i in range(A.shape[0])])
    return {
        'pos':    rows(D['pos']),
        'att':    rows(D['att']),
        'gimbal': rows(D['gimbal']),
        'rcs':    rows(D['rcs']),
        'thrust': np.interp(tt, t, D['thrust']),
        'eng':    np.interp(tt, t, D['engine_on'].astype(float)) > 0.5,
        'tt':     tt,
    }


def animate(data='apollo_trajectory.npz', out='landing.mp4',
            nframes=220, fps=10, model_size=16.0, trail=True,
            follow=True, zoom=3.2):
    D = load(data)
    x0 = D['x0']
    T_max, F_rcs = float(D['T_max']), float(D['F_rcs'])
    # place the (small, real) RCS quads at the exaggerated model's outer radius
    rcs_dir = D['rcs_dir']
    rmag = np.linalg.norm(D['rcs_pos'][:, :2], axis=1).max()
    rcs_pos_m = D['rcs_pos'] * (0.62 * model_size / max(rmag, 1e-6))

    R = resample(D, nframes)
    pos, att, gim, rcs = R['pos'], R['att'], R['gimbal'], R['rcs']
    thrust, eng, tt = R['thrust'], R['eng'], R['tt']

    alt = -pos[2]                                   # plot vertical axis
    px, py = pos[0], pos[1]
    body_faces, foot_faces, legs = lm_model(model_size)

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')

    # ground plane, pad and start marker (mirrors trajectory_with_axes.png)
    pad_xy = 40
    xl = [min(px.min(), 0) - pad_xy, max(px.max(), 0) + pad_xy]
    yl = [min(py.min(), 0) - pad_xy, max(py.max(), 0) + pad_xy]
    gx, gy = np.meshgrid(np.linspace(*xl, 4), np.linspace(*yl, 4))
    ax.plot_surface(gx, gy, np.zeros_like(gx), alpha=0.10, color='gray')
    ps = 15
    ax.plot([-ps, ps], [0, 0], [0, 0], 'r-', lw=2)
    ax.plot([0, 0], [-ps, ps], [0, 0], 'r-', lw=2)
    ax.scatter(0, 0, 0, c='red', s=150, marker='*', zorder=2)
    ax.scatter(x0[0], x0[1], -x0[2], c='green', s=90, marker='^', zorder=5)

    # full planned path (faint) + growing trail
    ax.plot(px, py, alt, color='0.6', lw=1.0, alpha=0.5)
    (trail_ln,) = ax.plot([], [], [], 'b-', lw=1.8, alpha=0.9)

    # LM artists
    body = Poly3DCollection([], facecolor='#C9A24B', edgecolor='k',
                            linewidths=0.4, alpha=0.97)
    foot = Poly3DCollection([], facecolor='#7A7A7A', edgecolor='k',
                            linewidths=0.3, alpha=0.97)
    legc = Line3DCollection([np.zeros((2, 3))], colors='0.15', linewidths=2.0)
    # DPS plume: translucent orange flame with a bright yellow core
    dps_out = Poly3DCollection([], facecolor='#FF7A1A', edgecolor='none', alpha=0.35)
    dps_in  = Poly3DCollection([], facecolor='#FFE24A', edgecolor='none', alpha=0.75)
    # RCS jets: cold-gas, light blue
    rcs_c   = Poly3DCollection([], facecolor='#5FC8FF', edgecolor='none', alpha=0.6)
    for art in (dps_out, dps_in, rcs_c, body, foot, legc):
        ax.add_collection3d(art)

    ax.set_xlabel('North  $x_E$  [m]'); ax.set_ylabel('East  $y_E$  [m]')
    ax.set_zlabel('Altitude  [m]')
    if follow:
        ax.set_box_aspect((1, 1, 1))                 # cubic so jets aren't skewed
    else:
        ax.set_xlim(xl); ax.set_ylim(yl); ax.set_zlim(0, max(alt.max(), 1)*1.05)
    ax.view_init(elev=24, azim=-58)
    W = zoom * model_size                            # follow-window half-width
    title = ax.set_title('')

    legend = [Line2D([0], [0], color='#C9A24B', lw=6, label='Descent/ascent'),
              Line2D([0], [0], color='0.15', lw=2, label='Landing legs'),
              Line2D([0], [0], color='#FF7A1A', lw=6, label='DPS plume'),
              Line2D([0], [0], color='#5FC8FF', lw=6, label='RCS jets'),
              Line2D([0], [0], color='b', lw=2, label='Flown path'),
              Line2D([0], [0], color='green', marker='^', ls='', label='Start'),
              Line2D([0], [0], color='red', marker='*', ls='', label='Pad')]
    ax.legend(handles=legend, loc='upper right', fontsize=8)

    def update(k):
        C = dcm_eb(att[0, k], att[1, k], att[2, k])
        r = np.array([px[k], py[k], alt[k]])
        body.set_verts([to_plot(f, r, C) for f in body_faces])
        foot.set_verts([to_plot(f, r, C) for f in foot_faces])
        legc.set_segments([to_plot(seg, r, C) for seg in legs])

        # DPS plume — scaled by thrust, tilted by the gimbal, off after cut-off
        frac = thrust[k] / T_max
        if eng[k] and frac > 0.02:
            flick = 0.85 + 0.15*np.sin(k*1.7)
            outer, inner = dps_plume(model_size, gim[0, k], gim[1, k], frac, flick)
            dps_out.set_verts([to_plot(f, r, C) for f in outer])
            dps_in.set_verts([to_plot(f, r, C) for f in inner])
        else:
            dps_out.set_verts([]); dps_in.set_verts([])

        # RCS jets — one small cone per firing thruster
        rfaces = rcs_plumes(model_size, rcs_pos_m, rcs_dir, rcs[:, k], F_rcs)
        rcs_c.set_verts([to_plot(f, r, C) for f in rfaces])

        if trail:
            trail_ln.set_data(px[:k+1], py[:k+1]); trail_ln.set_3d_properties(alt[:k+1])
        if follow:                                   # keep the vehicle centred & zoomed
            ax.set_xlim(px[k]-W, px[k]+W)
            ax.set_ylim(py[k]-W, py[k]+W)
            ax.set_zlim(max(0.0, alt[k]-W), alt[k]+W)
        n_jets = int(np.sum(rcs[:, k] > 0.04*F_rcs))
        state = f'ENGINE ON  ({frac*100:3.0f}% T)' if eng[k] else 'ENGINE CUT'
        title.set_text(f'Apollo LM Descent   t = {tt[k]:5.1f} s   '
                       f'alt = {alt[k]:6.1f} m   [{state}]   RCS jets: {n_jets}')
        return body, foot, legc, dps_out, dps_in, rcs_c, trail_ln, title

    anim = FuncAnimation(fig, update, frames=nframes, interval=1000/fps, blit=False)

    if out.lower().endswith('.mp4') and writers.is_available('ffmpeg'):
        anim.save(out, writer='ffmpeg', fps=fps, dpi=120)
    else:
        out = out.rsplit('.', 1)[0] + '.gif'
        anim.save(out, writer='pillow', fps=fps, dpi=90)
    plt.close(fig)
    print(f'[saved] {out}  ({nframes} frames @ {fps} fps)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='apollo_trajectory.npz')
    ap.add_argument('--out',  default='landing.mp4')
    ap.add_argument('--frames', type=int, default=220)
    ap.add_argument('--fps', type=int, default=10)
    ap.add_argument('--size', type=float, default=16.0, help='LM model half-size [m]')
    ap.add_argument('--no-follow', dest='follow', action='store_false',
                    help='fixed wide view instead of a zoomed follow camera')
    ap.add_argument('--zoom', type=float, default=3.2,
                    help='follow-window half-width in model-size units')
    a = ap.parse_args()
    animate(a.data, a.out, a.frames, a.fps, a.size, follow=a.follow, zoom=a.zoom)
