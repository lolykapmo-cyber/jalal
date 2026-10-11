"""A small software 3D renderer: lathed meshes, z-buffer, Blinn-Phong, supersampling.

Everything is plain numpy so the deck's 3D objects can be rendered here and shipped
as looping animations.
"""
import numpy as np

# ---------------------------------------------------------------- geometry ---

def lathe(profile, nu=28):
    """Surface of revolution around +Y.

    profile: iterable of (radius, y, normal_r, normal_y) rings, top to bottom.
    """
    prof = np.asarray(profile, dtype=np.float64)
    u = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    cu, su = np.cos(u), np.sin(u)
    V, N = [], []
    for r, y, nr, ny in prof:
        V.append(np.stack([r * cu, np.full(nu, y), r * su], 1))
        n = np.stack([nr * cu, np.full(nu, ny), nr * su], 1)
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        N.append(n / np.where(ln == 0, 1, ln))
    V = np.concatenate(V)
    N = np.concatenate(N)
    F = []
    for j in range(len(prof) - 1):
        r0, r1 = prof[j, 0], prof[j + 1, 0]
        if r0 == 0 and r1 == 0:
            continue
        for i in range(nu):
            a, b = j * nu + i, j * nu + (i + 1) % nu
            c, d = (j + 1) * nu + (i + 1) % nu, (j + 1) * nu + i
            if r0 != 0:
                F.append([a, b, c])
            if r1 != 0:
                F.append([a, c, d])
    return V, N, np.asarray(F, dtype=np.int32)


def sphere(r=1.0, nu=26, nv=16):
    v = np.linspace(0, np.pi, nv + 1)
    prof = [(np.sin(t) * r, np.cos(t) * r, np.sin(t), np.cos(t)) for t in v]
    return lathe(prof, nu)


def capsule(r=1.0, h=1.0, nu=26, nv=16):
    """Capsule along Y: cylinder of length h capped by two hemispheres."""
    nv = nv + nv % 2
    v = np.linspace(0, np.pi, nv + 1)
    prof = []
    for t in v[: nv // 2 + 1]:
        prof.append((np.sin(t) * r, np.cos(t) * r + h / 2, np.sin(t), np.cos(t)))
    for t in v[nv // 2:]:
        prof.append((np.sin(t) * r, np.cos(t) * r - h / 2, np.sin(t), np.cos(t)))
    return lathe(prof, nu)


def cylinder(r=1.0, h=1.0, nu=24, caps=True):
    prof = []
    if caps:
        prof += [(0.0, h / 2, 0, 1), (r, h / 2, 0, 1)]
    prof += [(r, h / 2, 1, 0), (r, -h / 2, 1, 0)]
    if caps:
        prof += [(r, -h / 2, 0, -1), (0.0, -h / 2, 0, -1)]
    return lathe(prof, nu)


def disc(r=1.0, y=0.0, nu=36, up=True):
    s = 1 if up else -1
    return lathe([(0.0, y, 0, s), (r, y, 0, s)], nu)


# -------------------------------------------------------------- transforms ---

def rot_x(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


class Obj:
    """A mesh placed in the world with a material."""

    def __init__(self, geo, color, pos=(0, 0, 0), rot=None, scale=1.0,
                 spec=0.55, shin=48.0, emis=0.0):
        V, N, F = geo
        R = np.eye(3) if rot is None else rot
        self.V = (V * scale) @ R.T + np.asarray(pos, dtype=np.float64)
        self.N = N @ R.T
        self.F = F
        self.color = np.asarray(color, dtype=np.float64)
        self.spec, self.shin, self.emis = spec, shin, emis


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


# ------------------------------------------------------------------ camera ---

def look_at(eye, target, up=(0, 1, 0)):
    eye = np.asarray(eye, float); target = np.asarray(target, float)
    f = target - eye; f /= np.linalg.norm(f)
    s = np.cross(f, np.asarray(up, float)); s /= np.linalg.norm(s)
    u = np.cross(s, f)
    M = np.eye(4)
    M[0, :3], M[1, :3], M[2, :3] = s, u, -f
    M[:3, 3] = -M[:3, :3] @ eye
    return M


def perspective(fovy, aspect, near=0.1, far=100.0):
    t = 1.0 / np.tan(fovy / 2)
    M = np.zeros((4, 4))
    M[0, 0] = t / aspect; M[1, 1] = t
    M[2, 2] = (far + near) / (near - far); M[2, 3] = 2 * far * near / (near - far)
    M[3, 2] = -1.0
    return M


# --------------------------------------------------------------- rendering ---

def radial_bg(W, H, inner, outer, cx=0.5, cy=0.45, radius=0.75):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx / W - cx) * (W / H)) ** 2 + (yy / H - cy) ** 2) / radius
    t = np.clip(d, 0, 1)[..., None] ** 1.35
    return inner * (1 - t) + outer * t


def render(objs, eye, target, W, H, lights, bg, fov=np.deg2rad(32), ss=2, fog=None):
    """Rasterise objs into an (H, W, 3) float image over background bg."""
    w, h = W * ss, H * ss
    img = np.repeat(np.repeat(bg, ss, 0), ss, 1).astype(np.float64)
    zbuf = np.full((h, w), -np.inf)
    view = look_at(eye, target)
    proj = perspective(fov, w / h)
    eye = np.asarray(eye, float)

    for o in objs:
        n = len(o.V)
        vh = np.concatenate([o.V, np.ones((n, 1))], 1)
        cam = vh @ view.T
        clip = cam @ proj.T
        wclip = clip[:, 3]
        bad = wclip <= 1e-6
        wclip = np.where(bad, 1e-6, wclip)
        ndc = clip[:, :3] / wclip[:, None]
        sx = (ndc[:, 0] * 0.5 + 0.5) * w
        sy = (0.5 - ndc[:, 1] * 0.5) * h
        depth = -cam[:, 2]                      # positive distance in front of camera

        for tri in o.F:
            i0, i1, i2 = tri
            if bad[i0] or bad[i1] or bad[i2]:
                continue
            x0, y0 = sx[i0], sy[i0]; x1, y1 = sx[i1], sy[i1]; x2, y2 = sx[i2], sy[i2]
            area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
            if abs(area) < 1e-9:
                continue
            xlo = max(int(np.floor(min(x0, x1, x2))), 0)
            xhi = min(int(np.ceil(max(x0, x1, x2))) + 1, w)
            ylo = max(int(np.floor(min(y0, y1, y2))), 0)
            yhi = min(int(np.ceil(max(y0, y1, y2))) + 1, h)
            if xlo >= xhi or ylo >= yhi:
                continue
            X, Y = np.meshgrid(np.arange(xlo, xhi) + 0.5, np.arange(ylo, yhi) + 0.5)
            l0 = ((x1 - x0) * (Y - y0) - (X - x0) * (y1 - y0)) / area
            l1 = ((x2 - x1) * (Y - y1) - (X - x1) * (y2 - y1)) / area
            b2, b0, b1 = l0, l1, 1.0 - l0 - l1
            m = (b0 >= 0) & (b1 >= 0) & (b2 >= 0)
            if not m.any():
                continue
            iw = b0 / depth[i0] + b1 / depth[i1] + b2 / depth[i2]
            z = 1.0 / np.where(iw == 0, 1e-9, iw)
            sub = zbuf[ylo:yhi, xlo:xhi]
            m &= (-z) > sub
            if not m.any():
                continue
            bb = np.stack([b0, b1, b2], -1)[m]
            idx = np.array([i0, i1, i2])
            P = bb @ o.V[idx]
            Nn = bb @ o.N[idx]
            Nn /= np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-12
            Vd = eye - P
            Vd /= np.linalg.norm(Vd, axis=1, keepdims=True) + 1e-12
            Nn = np.where((Nn * Vd).sum(1, keepdims=True) < 0, -Nn, Nn)
            col = o.color * (0.17 + o.emis)
            for ldir, lcol, lint in lights:
                L = np.asarray(ldir, float); L = L / np.linalg.norm(L)
                nd = np.clip(Nn @ L, 0, 1)[:, None]
                col = col + o.color * np.asarray(lcol) * (lint * nd)
                Hh = L + Vd
                Hh /= np.linalg.norm(Hh, axis=1, keepdims=True) + 1e-12
                sp = np.clip((Nn * Hh).sum(1), 0, 1)[:, None] ** o.shin
                col = col + np.asarray(lcol) * (o.spec * lint * sp) * (nd > 0)
            if fog is not None:
                fcol, fnear, ffar = fog
                t = np.clip((z[m] - fnear) / (ffar - fnear), 0, 1)[:, None]
                col = col * (1 - t) + np.asarray(fcol) * t
            tgt = img[ylo:yhi, xlo:xhi]
            tgt[m] = np.clip(col, 0, 1)
            sub[m] = -z[m]

    img = img.reshape(H, ss, W, ss, 3).mean((1, 3))
    return np.clip(img * 255, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------- output ---

def save_gif(frames, path, duration=70, bg=None):
    """Write frames (list of HxWx3 uint8) as a looping GIF on one shared palette.

    bg, an (r, g, b) tuple, is the exact background colour to preserve. Median-cut
    shifts a flat background by a few levels, which shows up as a visible rectangle
    against a slide filled with the same colour, so the palette entry the corner
    pixel lands on is rewritten with the exact value afterwards.
    """
    from PIL import Image
    pil = [Image.fromarray(f) for f in frames]
    montage = Image.fromarray(np.concatenate(frames[::max(1, len(frames) // 8)], 0))
    pal = montage.quantize(colors=255, method=Image.MEDIANCUT)
    # No dithering: a flat background then stays byte-identical between frames,
    # which lets the GIF encoder collapse them and keeps the file small.
    q = [p.quantize(palette=pal, dither=Image.NONE) for p in pil]
    if bg is not None:
        idx = q[0].getpixel((1, 1))
        palette = q[0].getpalette()
        palette[idx * 3:idx * 3 + 3] = list(bg)
        for f in q:
            f.putpalette(palette)
    q[0].save(path, save_all=True, append_images=q[1:], duration=duration,
              loop=0, optimize=True)
    return path
