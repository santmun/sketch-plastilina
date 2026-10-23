# parts.py — piezas compartidas por todos los personajes: boca con shape keys (open/O/smile/frown/wide),
# ojos articulados (globo + iris en articulación de mirada + párpados) y utilidades. Extraído de «A escondidas».
import bpy, bmesh, math
from mathutils import Vector, Matrix, Euler, Quaternion
from clay import (D, hexc, mat4, frame_from, bm_obj, blob, sphere, tube, clay, simple, marble)
from rig import Joint, child_joint, REC, qe

TINY = 1e-4


def M_world(loc=(0, 0, 0), yaw=0.0):
    return Matrix.Translation(Vector(loc)) @ Matrix.Rotation(yaw, 4, 'Z')


def shade(hex_, k):
    """aclara (k>1) u oscurece (k<1) un color hex"""
    h = hex_.lstrip('#')
    c = [min(255, max(0, int(int(h[i:i + 2], 16) * k))) for i in (0, 2, 4)]
    return '#%02X%02X%02X' % tuple(c)


def luminance(hex_):
    h = hex_.lstrip('#')
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ================================================================ boca con shape keys
def _surf_pt(H, sz0, x, z, out):
    sz = sz0 + z / H.rz
    k = H.f(sz)
    sx = x / (H.rx * k)
    return H.surf(sx, sz, out)


def _surf_n(H, sz0, x, z):
    a = _surf_pt(H, sz0, x, z, 0.0)
    b = _surf_pt(H, sz0, x, z, 0.01)
    return (b - a).normalized()


def mouth_outline(P, w0, n=16):
    w = w0 * (1 - 0.40 * P['round']) * (1 + 0.18 * P['wide'] + 0.06 * P['smile'])
    up = 0.0016 + P['open'] * 0.0065 + P['round'] * 0.007 + P['wide'] * 0.005
    lo = 0.0016 + P['open'] * 0.019 + P['round'] * 0.011 + P['wide'] * 0.007
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = w * math.cos(t)
        s = math.sin(t)
        z = up * s if s > 0 else lo * s
        c = (x / max(w, 1e-6)) ** 2
        z += (P['smile'] - P['frown']) * 0.011 * c - (P['smile'] - P['frown']) * 0.002
        pts.append((x, z))
    return pts


def build_mouth(tag, H, sz0, w0, joint, scale=1.0, lip_mat=None, lip_r=(0.0062, 0.0082), teeth=True):
    """boca de plastilina: labios (aro), interior oscuro, dientes. Shape keys: open, O, smile, frown, wide"""
    dark = clay('boca_oscura', '#3A1714', rough=0.4, prints=0)
    white = clay('dientes', '#F3EEE4', rough=0.35, prints=0.2)
    keys = {'Basis': {}, 'open': {'open': 1.0}, 'O': {'round': 1.0}, 'smile': {'smile': 1.0},
            'frown': {'frown': 1.0}, 'wide': {'wide': 1.0}}

    def params(d):
        P = dict(open=0.0, round=0.0, smile=0.0, frown=0.0, wide=0.0)
        P.update(d)
        return P

    def gen_lips(P):
        ol = mouth_outline(P, w0)
        pts = [_surf_pt(H, sz0, x, z, 0.003) for x, z in ol]
        n = len(ol)
        rad = []
        for i in range(n):
            s = math.sin(2 * math.pi * i / n)
            c = abs(math.cos(2 * math.pi * i / n))
            r = lip_r[0] if s > 0 else lip_r[1]
            rad.append(r * (1 - 0.35 * c ** 4))
        rad.append(rad[0])
        return pts, rad

    def gen_inner(P):
        ol = mouth_outline(P, w0)
        ring = [_surf_pt(H, sz0, x * 0.97, z * 0.97, 0.0022) for x, z in ol]
        c = _surf_pt(H, sz0, 0, sum(z for _, z in ol) / len(ol), 0.0008)
        return ring, c

    def gen_teeth(P):
        ol = mouth_outline(P, w0)
        w = max(x for x, _ in ol)
        up = max(z for _, z in ol)
        pts = []
        for i in range(7):
            x = -0.62 * w + 1.24 * w * i / 6
            z = up * math.sqrt(max(0.0, 1 - (x / w) ** 2)) - 0.0045
            pts.append(_surf_pt(H, sz0, x, z, 0.0026))
        return pts

    objs = []
    # labios
    lip_objs = {}
    for kname, kd in keys.items():
        pts, rad = gen_lips(params(kd))
        o = tube(f'{tag}_tmp_{kname}', lip_mat, pts, rad, None, ring=12, per=3, closed=True, sub=1, disp=0.0008,
                 dscale=0.05)
        lip_objs[kname] = o
    lips = lip_objs['Basis']
    lips.name = f'{tag}_labios'
    _shape_keys_from(lips, lip_objs)
    objs.append(lips)
    # interior
    inner_objs = {}
    for kname, kd in keys.items():
        ring, c = gen_inner(params(kd))
        bm = bmesh.new()
        vc = bm.verts.new(c)
        vr = [bm.verts.new(p) for p in ring]
        for i in range(len(vr)):
            bm.faces.new((vc, vr[i], vr[(i + 1) % len(vr)]))
        inner_objs[kname] = bm_obj(f'{tag}_tmpi_{kname}', bm, dark, None, sub=1, disp=0, smooth=True)
    inner = inner_objs['Basis']
    inner.name = f'{tag}_interior'
    _shape_keys_from(inner, inner_objs)
    objs.append(inner)
    if teeth:
        t_objs = {}
        for kname, kd in keys.items():
            t_objs[kname] = tube(f'{tag}_tmpt_{kname}', white, gen_teeth(params(kd)), 0.0042, None, ring=10, per=3,
                                 flat=0.7, sub=1, disp=0)
        tt = t_objs['Basis']
        tt.name = f'{tag}_dientes'
        _shape_keys_from(tt, t_objs)
        objs.append(tt)
    joint.attach(objs, 'local')
    return objs


def _shape_keys_from(base, variants):
    base.shape_key_add(name='Basis', from_mix=False)
    for kname, o in variants.items():
        if kname == 'Basis':
            continue
        kb = base.shape_key_add(name=kname, from_mix=False)
        co = [0.0] * (len(o.data.vertices) * 3)
        o.data.vertices.foreach_get('co', co)
        kb.data.foreach_set('co', co)
        kb.slider_min = -0.5
        kb.slider_max = 1.5
        kb.value = 0.0
        me = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(me)


def key_mouth(objs, frame, P):
    for o in objs:
        key = o.data.shape_keys
        for kname, v in (('open', P.get('open', 0)), ('O', P.get('round', 0)), ('smile', P.get('smile', 0)),
                         ('frown', P.get('frown', 0)), ('wide', P.get('wide', 0))):
            REC.key(key, f'key_blocks["{kname}"].value', 0, frame, v)


# ================================================================ ojos articulados
def build_eye(tag, parent_joint, c, r, lid_mat, iris='#5A3420', lash='#2A1A12', lash_r=0.12, lower_rim=True,
              lid_scale=1.07, iris_k=0.52, sclera=None, glint=(1.5, 0.09)):
    """globo fijo + iris/pupila en articulación de mirada + párpados semiesfera en articulaciones (rotan en X)."""
    c = Vector(c)
    ball = sphere(f'{tag}_globo', sclera or marble('canica_blanca', '#F5F0E8'), (0, 0, 0), r, None, disp=0, sub=1)
    gz = child_joint(f'{tag}_mirada', parent_joint, c)
    gz.attach(ball, 'local')
    g = Vector((0, -1, 0))
    R = frame_from(g, (0, 0, 1)).to_4x4()
    ir = blob(f'{tag}_iris', marble(f'iris_{iris}', iris), Matrix.Translation(g * r * 0.9) @ R @
              Matrix.Diagonal((r * iris_k, r * iris_k, r * 0.16, 1)), None, disp=0)
    pu = blob(f'{tag}_pupila', marble('canica_negra', '#0B0A0A'), Matrix.Translation(g * r * 0.985) @ R @
              Matrix.Diagonal((r * 0.25, r * 0.25, r * 0.08, 1)), None, disp=0)
    hl = sphere(f'{tag}_brillo', simple(f'brillo_ojo_{glint[0]}', '#FFFFFF', emit='#FFFFFF', estr=glint[0]),
                (r * 0.28, -r * 0.93 - r * 0.05 * (glint[1] > 0.1), r * 0.3), r * glint[1], None, disp=0, sub=1)
    gz.attach([ir, pu], 'local')
    # el brillo no gira con la mirada: va con la cabeza
    hj = child_joint(f'{tag}_brilloJ', parent_joint, c)
    hj.attach(hl, 'local')
    lr = r * lid_scale
    lu = child_joint(f'{tag}_parpU', parent_joint, c)
    ll = child_joint(f'{tag}_parpL', parent_joint, c)
    up = blob(f'{tag}_lidU', lid_mat, Matrix.Diagonal((lr, lr, lr, 1)), None, cut=((0, 0, 0), (0, 0, 1)), disp=0.0012,
              dscale=0.05)
    lo = blob(f'{tag}_lidL', lid_mat, Matrix.Diagonal((lr * 0.99, lr * 0.99, lr * 0.99, 1)), None,
              cut=((0, 0, 0), (0, 0, -1)), disp=0.0012, dscale=0.05)
    rimU = tube(f'{tag}_pestana', clay(f'pestana_{lash}', lash, rough=0.45, prints=0, sheen=0.0, spec=0.2),
                [(lr * math.cos(th), -lr * math.sin(th), 0.0) for th in [D(-10) + D(200) * i / 10 for i in range(11)]],
                r * lash_r, None, ring=10, per=3, disp=0)
    lu.attach([up, rimU], 'local')
    parts = [lo]
    if lower_rim:
        parts.append(tube(f'{tag}_rimL', lid_mat, [(lr * 0.99 * math.cos(th), -lr * 0.99 * math.sin(th), 0.0)
                                                   for th in [D(10) + D(160) * i / 8 for i in range(9)]],
                          r * 0.09, None, ring=10, per=3, disp=0.0005))
    ll.attach(parts, 'local')
    return dict(gaze=gz, up=lu, low=ll, r=r)


def pose_eye(E, gaze_yaw, gaze_pitch, beta, gamma, blink=0.0):
    """beta: borde del párpado superior (grados de elevación). gamma: inferior. blink 0..1 cierra."""
    E['gaze'].rot = qe(D(-gaze_pitch), 0, D(gaze_yaw))
    b = beta + (-8 - beta) * blink
    g = gamma + (2 - gamma) * blink * 0.6
    E['up'].rot = qe(D(-b))
    E['low'].rot = qe(D(g))


def rec_eye(E, f):
    for k in ('gaze', 'up', 'low'):
        E[k].record(f, scale=False)


