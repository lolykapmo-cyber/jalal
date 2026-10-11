"""The deck's five animated 3D scenes, rendered to looping GIFs."""
import os, sys, time
import numpy as np
import three as T
from three import Obj, hexc, rot_x, rot_y, rot_z, render, radial_bg, save_gif

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img')
C = {k: hexc(v) for k, v in dict(
    deep='0B2B32', dk2='0E4A54', tint='EFF7F5', white='FFFFFF',
    teal='0E7C86', mint='17B3A3', mintL='8FDCD2', pale='DCEFEC',
    amber='E8A33D', terra='C8553D', slate='3D6E8C', gray='9FB6B8').items()}

KEY = ((-0.55, 0.95, 0.75), (1.0, 0.99, 0.96), 0.78)
FILL = ((0.85, 0.15, 0.55), (0.68, 0.86, 1.0), 0.30)
RIM = ((0.2, -0.5, -0.9), (0.75, 0.95, 1.0), 0.22)
LIGHTS = [KEY, FILL, RIM]


def flat(w, h, hexcol):
    return np.tile(hexc(hexcol), (h, w, 1))


def align_y(d):
    """Rotation taking +Y to direction d."""
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    a = np.array([0.0, 1.0, 0.0])
    v = np.cross(a, d); s = np.linalg.norm(v); c = float(a @ d)
    if s < 1e-9:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)


def half_capsule(r, h, top=True, nu=28, nv=18):
    v = np.linspace(0, np.pi / 2, nv // 2 + 1)
    if top:
        prof = [(np.sin(t) * r, np.cos(t) * r + h / 2, np.sin(t), np.cos(t)) for t in v]
        prof += [(r, 0.0, 1, 0), (0.0, 0.0, 0, -1)]
    else:
        prof = [(0.0, 0.0, 0, 1), (r, 0.0, 1, 0)]
        prof += [(np.sin(t) * r, -np.cos(t) * r - h / 2, np.sin(t), -np.cos(t))
                 for t in v[::-1]]
    return T.lathe(prof, nu)


def pill(color_a, color_b, r, h, R, pos, nu=28):
    """A two-tone capsule as two objects."""
    return [Obj(half_capsule(r, h, True, nu), color_a, pos=pos, rot=R, spec=0.6, shin=60),
            Obj(half_capsule(r, h, False, nu), color_b, pos=pos, rot=R, spec=0.5, shin=50)]


def run(name, frames, W, H, build, eye, target, bg, fov=32, ss=2, dur=70, fog=None,
        bgcol=None):
    t0 = time.time()
    imgs = []
    for i in range(frames):
        imgs.append(render(build(i / frames), eye, target, W, H, LIGHTS, bg,
                           fov=np.deg2rad(fov), ss=ss, fog=fog))
        sys.stdout.write('\r  %s %d/%d' % (name, i + 1, frames)); sys.stdout.flush()
    p = save_gif(imgs, os.path.join(OUT, name + '.gif'), duration=dur, bg=bgcol)
    print('\r  %-18s %d frames  %5.1fs  %6.0f KB' %
          (name, frames, time.time() - t0, os.path.getsize(p) / 1024))


# ------------------------------------------------- 1. cover hero: the capsule
def hero(t):
    a = 2 * np.pi * t
    R = rot_y(a) @ rot_z(0.42)
    objs = pill(C['mint'], C['pale'], 0.62, 1.25, R, (0, 0, 0))
    for k in range(7):                       # drug particles orbiting the capsule
        b = a * -1.4 + k * 2 * np.pi / 7
        objs.append(Obj(T.sphere(1, 14, 9), C['mintL'],
                        pos=(1.58 * np.cos(b), 0.66 * np.sin(b * 2 + 0.6), 1.58 * np.sin(b)),
                        scale=0.13, spec=0.7, shin=70, emis=0.08))
    return objs


# ------------------------------- 2. a molecule crossing the lipid bilayer (s8)
HEAD = T.sphere(1, 14, 9)
TAIL = T.cylinder(1, 1, 8)
BALL = T.sphere(1, 18, 11)
STICK = T.cylinder(1, 1, 10)


def molecule(pos, col, scale=1.0, charge=False):
    o = []
    offs = [(-0.34, 0.1, 0.0), (0.34, 0.12, 0.05), (0.0, -0.28, -0.1)]
    cols = [col, col, C['white'] if not charge else C['pale']]
    p = np.asarray(pos, float)
    for d, c in zip(offs, cols):
        o.append(Obj(BALL, c, pos=p + np.array(d) * scale, scale=0.26 * scale,
                     spec=0.65, shin=64))
    for a, b in [(0, 2), (1, 2)]:
        pa = p + np.array(offs[a]) * scale; pb = p + np.array(offs[b]) * scale
        mid = (pa + pb) / 2; d = pb - pa; L = np.linalg.norm(d)
        o.append(Obj(STICK, C['gray'], pos=mid, rot=align_y(d) @ np.diag([0.07, L, 0.07]),
                     spec=0.3, shin=24))
    if charge:
        o.append(Obj(BALL, C['terra'], pos=p + np.array([0.34, 0.46, 0.05]) * scale,
                     scale=0.17 * scale, spec=0.8, shin=90, emis=0.12))
    return o


def bilayer():
    o = []
    for zi, z in enumerate((-0.75, 0.0, 0.75)):
        for i in range(15):
            x = -4.2 + i * 0.6
            for sgn in (1, -1):
                o.append(Obj(HEAD, C['amber'], pos=(x, sgn * 0.62, z), scale=0.24,
                             spec=0.55, shin=40))
                o.append(Obj(TAIL, C['amber'] * 0.82 + 0.18, pos=(x, sgn * 0.22, z),
                             rot=np.diag([0.055, 0.62, 0.055]), spec=0.2, shin=16))
    return o


BILAYER = None


def membrane(t):
    global BILAYER
    if BILAYER is None:
        BILAYER = bilayer()
    o = list(BILAYER)
    y = 1.6 - 3.6 * t                                    # unionized: passes through
    o += molecule((-1.95, y, 0.25), C['teal'], 1.35)
    yi = 1.6 - 0.55 * np.sin(np.pi * t)                  # ionized: repelled
    o += molecule((1.95, yi, 0.25), C['mintL'] * 0.45 + C['pale'] * 0.55, 1.35, charge=True)
    return o


# ------------------------------------------- 3. a bile-salt micelle spinning (s13)
def micelle(t):
    a = 2 * np.pi * t
    R = rot_y(a) @ rot_x(0.26)
    o = pill(C['mint'], C['white'], 0.4, 0.66, R @ rot_z(0.5), (0, 0, 0), nu=24)
    n = 18
    gold = np.pi * (3 - np.sqrt(5))
    for k in range(n):
        yy = 1 - 2 * (k + 0.5) / n
        rr = np.sqrt(max(0.0, 1 - yy * yy))
        d = R @ np.array([np.cos(gold * k) * rr, yy, np.sin(gold * k) * rr])
        o.append(Obj(STICK, C['amber'] * 0.8 + 0.2, pos=d * 0.92,
                     rot=align_y(d) @ np.diag([0.06, 0.62, 0.06]), spec=0.25, shin=20))
        o.append(Obj(HEAD, C['amber'], pos=d * 1.3, scale=0.165, spec=0.6, shin=52))
    return o


# --------------------------------- 4. acid bouncing off an enteric coat (s15)
def enteric(t):
    a = 2 * np.pi * t
    R = rot_y(a) @ rot_z(np.pi / 2)
    o = pill(C['slate'], C['slate'] * 0.75 + 0.25, 0.66, 1.5, R, (0, -0.05, 0))
    for k in range(8):
        p = (t + k / 8.0) % 1.0
        x0 = -2.1 + k * 0.6
        y = 2.5 - 4.3 * p
        x = x0
        if p > 0.47:                       # deflected off the coat
            s = (p - 0.47) / 0.53
            x = x0 + np.sign(x0 if x0 else 1) * 1.5 * s * s
            y = 0.62 - 2.6 * s * s
        o.append(Obj(BALL, C['terra'], pos=(x, y, 0.55 - 0.3 * (k % 3)),
                     scale=0.17, spec=0.8, shin=80))
    return o


# ------------------------------------ 5. metal ions chelating the drug (s16)
def chelation(t):
    a = 2 * np.pi * t
    R = rot_y(a * 1.0)
    o = pill(C['teal'], C['pale'], 0.52, 0.95, R @ rot_z(0.35), (0, 0, 0))
    d = 1.08 + 0.92 * (0.5 + 0.5 * np.cos(2 * np.pi * t))
    ions = [(C['amber'], 0.0), (C['terra'], 2 * np.pi / 3), (C['slate'], 4 * np.pi / 3)]
    for col, ph in ions:
        v = R @ np.array([np.cos(ph), 0.42 * np.sin(ph * 1.5), np.sin(ph)])
        v = v / np.linalg.norm(v)
        o.append(Obj(BALL, col, pos=v * d, scale=0.34, spec=0.75, shin=78))
    return o


# --------------------------------------------------------------------- build
if __name__ == '__main__':
    only = sys.argv[1:] or None
    jobs = [
        ('hero_capsule', 36, 760, 640, hero, (2.4, 1.5, 4.2), (0, 0, 0),
         lambda w, h: flat(w, h, '0B2B32'), 34),
        ('membrane_3d', 36, 1040, 540, membrane, (0.0, 1.8, 7.8), (0, -0.1, 0),
         lambda w, h: flat(w, h, 'FFFFFF'), 38),
        ('micelle_3d', 36, 600, 600, micelle, (1.1, 1.5, 4.8), (0, 0, 0),
         lambda w, h: flat(w, h, 'EFF7F5'), 36),
        ('enteric_3d', 36, 900, 470, enteric, (0.2, 1.2, 5.7), (0, -0.15, 0),
         lambda w, h: flat(w, h, 'EFF7F5'), 36),
        ('chelation_3d', 36, 820, 500, chelation, (0.6, 1.5, 5.2), (0, 0, 0),
         lambda w, h: flat(w, h, 'FFFFFF'), 36),
    ]
    BGCOL = {'hero_capsule': (11, 43, 50), 'membrane_3d': (255, 255, 255),
             'micelle_3d': (239, 247, 245), 'enteric_3d': (239, 247, 245),
             'chelation_3d': (255, 255, 255)}
    for name, n, W, H, fn, eye, tgt, bgf, fov in jobs:
        if only and name not in only:
            continue
        run(name, n, W, H, fn, eye, tgt, bgf(W, H), fov=fov, bgcol=BGCOL[name])
