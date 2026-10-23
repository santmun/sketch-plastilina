# rig.py — articulaciones (empties), cinemática directa en Python, IK de dos huesos y grabado masivo de keyframes
import bpy, math
from mathutils import Vector, Matrix, Quaternion, Euler
from clay import empty

D = math.radians


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def vlerp(a, b, t):
    return Vector(a).lerp(Vector(b), t)


class Rec:
    """acumula (frame, valor) por canal y los escribe en bloque al final"""

    def __init__(self):
        self.ch = {}   # (id, path, index) -> {frame: value}
        self.interp = {}

    def key(self, idb, path, index, frame, value, interp='CONSTANT'):
        k = (idb.name, type(idb).__name__, path, index)
        d = self.ch.get(k)
        if d is None:
            d = self.ch[k] = {}
            self.interp[k] = (idb, interp)
        d[frame] = float(value)

    def write(self):
        n_k = 0
        modes = {'CONSTANT': 0, 'LINEAR': 1, 'BEZIER': 2}
        for k, d in self.ch.items():
            idb, interp = self.interp[k]
            path, index = k[2], k[3]
            ad = idb.animation_data or idb.animation_data_create()
            if ad.action is None:
                ad.action = bpy.data.actions.new(f'act_{idb.name}')
            fc = ad.action.fcurve_ensure_for_datablock(idb, path, index=index)
            frames = sorted(d)
            fc.keyframe_points.add(len(frames))
            co = []
            for f in frames:
                co += [f, d[f]]
            fc.keyframe_points.foreach_set('co', co)
            fc.keyframe_points.foreach_set('interpolation', [modes[interp]] * len(frames))
            fc.update()
            n_k += len(frames)
        self.ch.clear()       # se puede escribir por etapas (personajes, luego cámaras) sin duplicar claves
        self.interp.clear()
        return n_k


REC = Rec()


class Joint:
    """empty articulado. rest_local = matriz local en reposo (sin escala). La pose es un delta en el marco local."""

    def __init__(self, name, rest_world, parent=None):
        self.name = name
        self.parent = parent
        self.rest_world = Matrix(rest_world)
        self.obj = empty(name)
        self.obj.empty_display_size = 0.03
        self.obj.rotation_mode = 'QUATERNION'
        if parent is not None:
            self.obj.parent = parent.obj
            self.rest_local = parent.rest_world.inverted() @ self.rest_world
        else:
            self.rest_local = self.rest_world.copy()
        self.obj.matrix_basis = self.rest_local
        self.reset()

    def reset(self):
        self.loc = Vector((0, 0, 0))
        self.rot = Quaternion()
        self.scl = Vector((1, 1, 1))

    def local(self):
        return (self.rest_local @ Matrix.Translation(self.loc) @ self.rot.to_matrix().to_4x4()
                @ Matrix.Diagonal((*self.scl, 1)))

    def world(self):
        m = self.local()
        return (self.parent.world() @ m) if self.parent is not None else m

    def attach(self, objs, space='world'):
        """space='world': geometría construida en coordenadas de mundo (pose de reposo);
        'local': geometría construida en el marco de la articulación"""
        if not isinstance(objs, (list, tuple)):
            objs = [objs]
        inv = self.rest_world.inverted() if space == 'world' else Matrix.Identity(4)
        for o in objs:
            o.parent = self.obj
            o.matrix_parent_inverse = inv
        return objs

    def record(self, frame, interp='CONSTANT', scale=True):
        r0 = self.rest_local.to_quaternion()
        t0 = self.rest_local.to_translation()
        loc = t0 + r0 @ self.loc
        q = r0 @ self.rot
        o = self.obj
        for i in range(3):
            REC.key(o, 'location', i, frame, loc[i], interp)
        for i in range(4):
            REC.key(o, 'rotation_quaternion', i, frame, q[i], interp)
        if scale:
            for i in range(3):
                REC.key(o, 'scale', i, frame, self.scl[i], interp)


def child_joint(name, parent, local_loc, local_rot=None):
    """articulación con reposo relativo al reposo del padre"""
    m = Matrix.Translation(Vector(local_loc))
    if local_rot is not None:
        m = m @ Euler(local_rot).to_matrix().to_4x4()
    return Joint(name, parent.rest_world @ m, parent)


def qe(x=0.0, y=0.0, z=0.0, order='XYZ'):
    return Euler((x, y, z), order).to_quaternion()


class Arm:
    """brazo de 2 huesos colgando en reposo (-Z del marco del padre). La bisagra en reposo es -X (el antebrazo se dobla hacia -Y)."""

    def __init__(self, tag, parent, shoulder_local, l1, l2):
        self.S = Vector(shoulder_local)
        self.l1, self.l2 = l1, l2
        self.sh = child_joint(f'{tag}_hombro', parent, shoulder_local)
        self.el = child_joint(f'{tag}_codo', self.sh, (0, 0, -l1))
        self.wr = child_joint(f'{tag}_muneca', self.el, (0, 0, -l2))
        self.parent = parent

    def solve(self, target_parent, pole_parent, wrist_rot=None):
        """target/pole en el marco ACTUAL del padre (ya con su pose)"""
        S = self.sh.rest_local.to_translation()
        P = Vector(target_parent)
        d = P - S
        dist = max(abs(self.l1 - self.l2) + 1e-3, min(self.l1 + self.l2 - 1e-3, d.length))
        dn = d.normalized()
        P = S + dn * dist
        a = (self.l1 ** 2 + dist ** 2 - self.l2 ** 2) / (2 * dist)
        h = math.sqrt(max(0.0, self.l1 ** 2 - a * a))
        pl = Vector(pole_parent)
        pp = pl - dn * pl.dot(dn)
        if pp.length < 1e-6:
            pp = dn.orthogonal()
        pp.normalize()
        E = S + dn * a + pp * h
        u = (E - S).normalized()
        w = (P - E).normalized()
        n1 = u.cross(w)
        if n1.length < 1e-6:
            n1 = u.cross(-pp)
        n1.normalize()
        u0 = Vector((0, 0, -1))
        n0 = Vector((-1, 0, 0))
        F0 = Matrix((u0, n0, u0.cross(n0))).transposed()
        F1 = Matrix((u, n1, u.cross(n1))).transposed()
        self.sh.rot = (F1 @ F0.transposed()).to_quaternion()
        ang = math.acos(max(-1.0, min(1.0, u.dot(w))))
        self.el.rot = Quaternion(n0, ang)
        self.wr.rot = wrist_rot if wrist_rot is not None else Quaternion()
        return E, P


class Track:
    """pista de parámetro: lista de (t, valor[, 'ease'|'lin'|'step'|(blend s)]). valor puede ser float, tupla o Vector."""

    def __init__(self, keys, default=0.0):
        self.keys = sorted(keys, key=lambda k: k[0])
        self.default = default

    def __call__(self, t):
        ks = self.keys
        if not ks:
            return self.default
        if t <= ks[0][0]:
            return ks[0][1]
        if t >= ks[-1][0]:
            return ks[-1][1]
        for i in range(len(ks) - 1):
            t0, v0 = ks[i][0], ks[i][1]
            t1, v1 = ks[i + 1][0], ks[i + 1][1]
            if t0 <= t <= t1:
                mode = ks[i + 1][2] if len(ks[i + 1]) > 2 else 'ease'
                x = (t - t0) / max(1e-6, t1 - t0)
                if mode == 'step':
                    x = 0.0
                elif mode == 'lin':
                    pass
                elif mode == 'out':
                    x = 1 - (1 - x) ** 3
                elif mode == 'in':
                    x = x ** 3
                elif mode == 'back':   # sobrepaso tipo caricatura
                    s = 1.9
                    x = x - 1
                    x = 1 + x * x * ((s + 1) * x + s)
                else:
                    x = ease(x)
                if isinstance(v0, (tuple, list, Vector)):
                    return tuple(Vector(v0).lerp(Vector(v1), x))
                return v0 + (v1 - v0) * x
        return ks[-1][1]
