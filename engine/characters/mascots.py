# mascots.py — mascotas de IA de plastilina. Todas tienen boca que se abre con su voz, parpadeo y expresiones.
#   Clawd (Claude), ChatGPT (nudo negro + recibo), Gemini (destello) y Mascota genérica (forma/color por parámetros).
# Convención: la raíz está en el punto de apoyo (abajo); el frente mira a -Y.
import bpy, json, math, os
from mathutils import Vector, Matrix, Quaternion
from clay import (D, hexc, mat4, blob, sphere, superbox, tube, clay, simple, marble)
from rig import Joint, child_joint, qe
from characters.parts import TINY, M_world, shade, build_eye, pose_eye, rec_eye
from characters.props import contour_mesh, receipt_material, receipt_strip, ASSETS

# expresiones comunes de las mascotas (las mismas palabras que usa blocking.json)
EXPR = ('normal', 'calm', 'happy', 'wide', 'sad', 'determined', 'suspicious')


class Mascot:
    kind = 'mascota'
    half_h = 0.05

    def socket(self, name):
        if name in ('ojos', 'cara', 'cabeza', 'boca'):
            return self.body, self.eyes_local
        if name == 'ojo_izq':
            return self.body, self.eyes_local + Vector((self.eye_dx, 0, 0))
        if name == 'ojo_der':
            return self.body, self.eyes_local - Vector((self.eye_dx, 0, 0))
        if name in ('raiz', 'pies'):
            return self.root, Vector((0, 0, 0))
        if name == 'centro':
            return self.root, Vector((0, 0, self.half_h))
        raise KeyError(f'{self.name}: anclaje desconocido «{name}»')

    def world_point(self, name):
        j, p = self.socket(name)
        return j.world() @ p

    def facing(self):
        v = self.root.world().to_3x3() @ Vector((0, -1, 0))
        v.z = 0
        return v.normalized()


# ================================================================ CLAWD
class Clawd(Mascot):
    """silueta del ref: cuerpo 12x4 u (22.5 % más alto: 12x4.9 u), brazos 2x1 u, 4 patas 1x1 u, ojos 1x1 u, boca voxel"""
    kind = 'clawd'

    def __init__(self, name, spec):
        u = float(spec.get('u', 0.026))
        self.u = u
        self.name = name
        hb = self.TALL = float(spec.get('alto', 1.225))
        self.root = Joint(name, M_world((0, 0, 0)))
        body = clay(f'clawd_{name}', spec.get('color', '#D6572D'), rough=0.62, sss=0.0, sheen=0.0, prints=1.2, spec=0.3)
        self.mat = body
        ink = clay('clawd_ojo', '#1C1A17', rough=0.32, prints=0)
        dep = 1.6 * u
        self.half_h = (1.0 + 2.0 * hb) * u
        self.legs = []
        for x in (-4.5, -2.5, 2.5, 4.5):
            j = child_joint(f'{name}_pata{x}', self.root, (x * u, 0, 1.0 * u))
            j.attach(superbox(f'{name}_leg{x}', body, (0, 0, -0.45 * u), (0.5 * u, 0.62 * u, 0.62 * u), None, e=0.24,
                              disp=0.0012, dscale=0.05), 'local')
            self.legs.append((x, j))
        self.body = child_joint(f'{name}_cuerpo', self.root, (0, 0, 1.0 * u))
        self.body.attach(superbox(f'{name}_body', body, (0, 0, 2.0 * hb * u), (6 * u, dep, 2 * hb * u), None, e=0.2, disp=0.0025,
                                  dscale=0.06), 'local')
        self.arms = {}
        for s in (+1, -1):
            j = child_joint(f'{name}_hombro{s}', self.body, (s * 6.0 * u, 0, 1.5 * hb * u))
            j.attach(superbox(f'{name}_arm{s}', body, (s * 0.95 * u, 0, 0), (1.05 * u, 0.62 * u, 0.5 * u), None, e=0.26,
                              disp=0.0012, dscale=0.05), 'local')
            self.arms[s] = j
        self.eyes = {}
        for s in (+1, -1):
            j = child_joint(f'{name}_ojo{s}', self.body, (s * 3.5 * u, -dep - 0.02 * u, 2.5 * hb * u))
            sq = superbox(f'{name}_eyeSq{s}', ink, (0, 0, 0), (0.5 * u, 0.16 * u, 0.5 * u), None, e=0.22, disp=0)
            car = [superbox(f'{name}_eyeCar{s}{k}', ink, (k * 0.27 * u, 0, 0.0), (0.36 * u, 0.15 * u, 0.12 * u), None,
                            rot=(0, D(42) * k, 0), e=0.3, disp=0) for k in (-1, 1)]
            sqj = child_joint(f'{name}_ojoSq{s}', j, (0, 0, 0))
            caj = child_joint(f'{name}_ojoCar{s}', j, (0, 0, 0))
            sqj.attach(sq, 'local')
            caj.attach(car, 'local')
            self.eyes[s] = (j, sqj, caj)
        self.eyes_local = Vector((0, -dep, 2.5 * hb * u))
        self.eye_dx = 3.5 * u
        mz = 1.72 * hb * u
        self.mouth = child_joint(f'{name}_bocaJ', self.body, (0, -dep - 0.02 * u, mz))
        slot = []
        for k, (x0, x1, z0, z1) in enumerate(((-1.25, -0.45, 0.32, 0.0), (-0.45, 0.45, 0.0, 0.0), (0.45, 1.25, 0.0, 0.32))):
            cx, cz = (x0 + x1) / 2 * u, (z0 + z1) / 2 * u
            ang = math.atan2((z1 - z0), (x1 - x0))
            slot.append(superbox(f'{name}_mouthSlot{k}', ink, (cx, 0, cz), ((x1 - x0) / 2 * u + 0.12 * u, 0.15 * u, 0.17 * u),
                                 None, rot=(0, -ang, 0), e=0.3, disp=0))
        self.mouth_slot = child_joint(f'{name}_bocaRanura', self.mouth, (0, 0, 0))
        self.mouth_slot.attach(slot, 'local')
        self.mouth_open = child_joint(f'{name}_bocaAbierta', self.mouth, (0, 0, 0.1 * u))
        inner = clay('clawd_boca', '#140605', rough=0.85, prints=0, spec=0.05, sheen=0.0)
        tongue = clay('clawd_lengua', '#B8402E', rough=0.5, prints=0.3)
        self.mouth_open.attach([superbox(f'{name}_mouthHole', inner, (0, 0, -0.42 * u), (0.85 * u, 0.16 * u, 0.42 * u), None,
                                         e=0.25, disp=0),
                                superbox(f'{name}_mouthTongue', tongue, (0, -0.02 * u, -0.7 * u), (0.5 * u, 0.12 * u, 0.15 * u),
                                         None, e=0.35, disp=0)], 'local')

    def apply(self, p, t):
        u = self.u
        R = self.root
        R.loc = Vector(p.get('pos', (0, 0, 0)))
        R.rot = qe(D(p.get('pitch', 0)), D(p.get('roll', 0)), D(p.get('yaw', 0)), 'XYZ')
        R.scl = Vector((1, 1, 1)) * (TINY if p.get('hide', False) else p.get('scale', 1.0))
        sq = p.get('squash', 0.0)
        self.body.scl = Vector((1 - 0.45 * sq, 1 - 0.3 * sq, 1 + sq))
        self.body.rot = qe(D(p.get('tilt', 0)), D(p.get('lean_side', 0)), D(p.get('twist', 0)))
        self.body.loc = Vector((0, 0, p.get('bob', 0.0)))
        for s, j in self.arms.items():
            up, fw = p.get('armL' if s > 0 else 'armR', (0, 0))
            j.rot = qe(0, D(-up * s), D(-fw * s))
        ph, amp, tuck = p.get('legphase', 0.0), p.get('legamp', 0.0), p.get('tuck', 0.0)
        for i, (x, j) in enumerate(self.legs):
            a = amp * math.sin(ph + (0 if i in (0, 3) else math.pi))
            j.rot = qe(D(a), 0, 0)
            j.loc = Vector((0, 0, 0.35 * u * tuck))
            j.scl = Vector((1, 1, 1 - 0.35 * tuck))
        ex = p.get('eyes', 'normal')
        blink = p.get('blink', 0.0)
        gx, gz = p.get('gaze', (0.0, 0.0))
        for s, (j, sqj, caj) in self.eyes.items():
            j.loc = Vector((gx * 0.35 * u, 0, gz * 0.3 * u))
            j.rot = Quaternion()
            sqs, cas, sql = Vector((1, 1, 1)), Vector((1, 1, 1)) * TINY, Vector((0, 0, 0))
            if ex == 'happy':
                sqs, cas = Vector((1, 1, 1)) * TINY, Vector((1, 1, 1))
            elif ex == 'calm':
                sqs, sql = Vector((1.05, 1, 0.42)), Vector((0, 0, -0.22 * u))
            elif ex == 'wide':
                sqs = Vector((1.3, 1, 1.3))
            elif ex == 'sad':
                sqs = Vector((1, 1, 0.75))
                j.rot = qe(0, D(18 * s), 0)
            elif ex == 'determined':
                sqs = Vector((1.05, 1, 0.8))
                j.rot = qe(0, D(-16 * s), 0)
            elif ex == 'suspicious':
                sqs = Vector((1.1, 1, 0.35))
            if ex != 'happy' and blink > 0:
                sqs = Vector((sqs.x, sqs.y, max(0.12, sqs.z * (1 - blink))))
            sqj.scl, sqj.loc, caj.scl = sqs, sql, cas
        o = max(0.0, min(1.0, p.get('mouth', 0.0)))
        talk = o > 0.06
        sx, curve = {'happy': (1.15, 1.6), 'calm': (0.75, 0.6), 'wide': (0.5, 0.0), 'sad': (0.85, -1.0),
                     'determined': (0.9, 0.2), 'suspicious': (0.8, -0.3)}.get(ex, (1.0, 1.0))
        self.mouth_slot.rot = qe(0, D(180), 0) if curve < 0 else Quaternion()
        self.mouth_slot.scl = (Vector((sx, 1, max(0.15, abs(curve)))) if not talk else Vector((1, 1, 1)) * TINY)
        if ex == 'wide' and not talk:
            o = 0.35
        if talk or ex == 'wide':
            w = 1.0 - 0.25 * (ex == 'wide')
            self.mouth_open.scl = Vector((w * 1.12 + 0.08 * o, 1, 0.18 + 0.72 * o))
        else:
            self.mouth_open.scl = Vector((1, 1, 1)) * TINY

    def record(self, f):
        self.root.record(f)
        self.body.record(f)
        for j in (self.mouth, self.mouth_slot, self.mouth_open):
            j.record(f)
        for j in self.arms.values():
            j.record(f, scale=False)
        for x, j in self.legs:
            j.record(f)
        for j, sqj, caj in self.eyes.values():
            j.record(f, scale=False)
            sqj.record(f)
            caj.record(f)


# ================================================================ ChatGPT
class GPT(Mascot):
    """nudo negro de ChatGPT con ojos de canica, sonrisa presumida y recibo térmico que se desenrolla"""
    kind = 'chatgpt'

    def __init__(self, name, spec, receipt_tex=None):
        size = float(spec.get('tamano', 0.11))
        self.name = name
        self.size = size
        self.half_h = 0.75 * size
        self.root = Joint(name, M_world((0, 0, 0)))
        self.body = child_joint(f'{name}_centro', self.root, (0, 0, self.half_h))
        ink = clay('tinta_gpt', spec.get('color', '#0C0C0E'), rough=0.38, sheen=0.0, prints=1.3, spec=0.45)
        data = json.load(open(os.path.join(ASSETS, 'chatgpt-knot.json')))
        self.knot = child_joint(f'{name}_nudoJ', self.body, (0, 0, 0))
        k = contour_mesh(f'{name}_nudo', [c['pts'] for c in data], size, 0.30 * size, ink, bevel=0.022 * size)
        k.data.transform(Matrix.Translation((0, 0.15 * size, 0)))
        self.knot.attach(k, 'local')
        self.face = child_joint(f'{name}_caraJ', self.body, (0, -0.2 * size, 0.02 * size))
        r = 0.16 * size
        self.eyes = {}
        for sd in (+1, -1):
            c = Vector((0.24 * size * sd, -0.02, 0.02 * size))
            self.face.attach(sphere(f'{name}_socket{sd}', ink, c + Vector((0, 0.01, 0)), r * 1.3, None, disp=0.001), 'local')
            self.eyes[sd] = build_eye(f'{name}_eye{sd}', self.face, c, r, clay('gpt_parpado', '#26262B', rough=0.4, prints=0),
                                      iris='#0A0A0B', lash='#E8E3D8', lash_r=0.17, lower_rim=False, iris_k=0.36,
                                      sclera=simple('gpt_esclera', '#FFFFFF', rough=0.15, emit='#FFFFFF', estr=0.35),
                                      glint=(6.0, 0.16))
        self.eyes_local = Vector((0, -0.2 * size - 0.02, 0.04 * size))
        self.eye_dx = 0.24 * size
        self.receipt = None
        if spec.get('recibo', False) or receipt_tex:
            tex = receipt_tex or os.path.join(ASSETS, 'recibo-ejemplo.png')
            self.receipt = child_joint(f'{name}_reciboJ', self.body, (0.0, -0.085 * size / 0.11, -0.045 * size / 0.11))
            self.receipt_mat = receipt_material(tex)
            self.receipt.attach(receipt_strip(f'{name}_recibo', self.receipt_mat, length=float(spec.get('recibo_largo', 1.05))),
                                'local')
        cream = clay('gpt_labio', '#E9E1D2', rough=0.45, prints=0.4)
        self.mouth = child_joint(f'{name}_bocaJ', self.face, (0.02 * size, -0.03, -0.24 * size))
        sm = [Vector((-0.17, 0, 0.035)), Vector((-0.06, 0, -0.01)), Vector((0.06, 0, -0.005)), Vector((0.17, 0, 0.06))]
        self.mouth_slot = child_joint(f'{name}_bocaRanura', self.mouth, (0, 0, 0))
        self.mouth_slot.attach(tube(f'{name}_smirk', cream, [v * size for v in sm], [0.018 * size, 0.024 * size, 0.024 * size,
                                    0.016 * size], None, ring=10, per=5, disp=0), 'local')
        self.mouth_open = child_joint(f'{name}_bocaAbierta', self.mouth, (0, 0, -0.01 * size))
        self.mouth_open.attach([sphere(f'{name}_mouthRim', cream, (0, 0.004, 0), (0.12 * size, 0.03 * size, 0.07 * size), None, disp=0),
                                sphere(f'{name}_mouthIn', clay('gpt_boca', '#3A0E10', rough=0.5, prints=0),
                                       (0, -0.004, -0.004 * size), (0.095 * size, 0.03 * size, 0.052 * size), None, disp=0)],
                               'local')
        self.receipt_len = 0.0

    def apply(self, p, t):
        R = self.root
        R.loc = Vector(p.get('pos', (0, 0, 0)))
        R.rot = qe(D(p.get('pitch', 0)), D(p.get('roll', 0)), D(p.get('yaw', 0)), 'XYZ')
        R.scl = Vector((1, 1, 1)) * (TINY if p.get('hide') else p.get('scale', 1.0))
        o = max(0.0, min(1.0, p.get('mouth', 0.0)))
        self.knot.rot = qe(0, D(p.get('spin', 0) + 8 * math.sin(t * 6.0) * o + p.get('idle', 1.0) * 6 * math.sin(t * 1.3)), 0)
        self.knot.scl = Vector((1, 1, 1)) * (1 + 0.16 * o)
        self.body.loc = Vector((0, 0, p.get('bob', 0.0)))
        self.body.rot = qe(D(p.get('tilt', 0)), D(p.get('lean_side', 0)), 0)
        self.face.loc = Vector((0, -0.01 * o, 0))
        gy, gp = p.get('gaze', (0, 0))
        ex = p.get('eyes', 'normal')
        lid = {'normal': 14, 'calm': 8, 'happy': 6, 'wide': 30, 'sad': 10, 'determined': 8, 'suspicious': 3}.get(ex, 14)
        for sd, E in self.eyes.items():
            pose_eye(E, gy * 30, gp * 30, p.get('lidU', lid), p.get('lidL', 40), p.get('blink', 0))
        self.receipt_len = p.get('receipt', 0.0)
        if o > 0.06:
            self.mouth_slot.scl = Vector((1, 1, 1)) * TINY
            self.mouth_open.scl = Vector((0.75 + 0.3 * o, 1, 0.35 + 1.0 * o))
        else:
            self.mouth_slot.scl = Vector((1, 1, 1))
            self.mouth_open.scl = Vector((1, 1, 1)) * TINY

    def record(self, f):
        self.root.record(f)
        self.body.record(f)
        self.knot.record(f)
        self.face.record(f)
        for j in (self.mouth, self.mouth_slot, self.mouth_open):
            j.record(f)
        if self.receipt is not None:
            nd = self.receipt_mat.node_tree.nodes['largo']
            nd.outputs[0].default_value = self.receipt_len
            nd.outputs[0].keyframe_insert('default_value', frame=f)
        for E in self.eyes.values():
            rec_eye(E, f)


# ================================================================ mascota genérica (y Gemini)
def gradient_material(name, c0, c1, zr=0.06, emit=0.6):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = clay(name, c1, rough=0.4, prints=0.6)
    nt = m.node_tree
    bs = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = -zr
    mr.inputs['From Max'].default_value = zr
    nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = hexc(c0)
    cr.color_ramp.elements[1].color = hexc(c1)
    nt.links.new(mr.outputs[0], cr.inputs['Fac'])
    nt.links.new(cr.outputs['Color'], bs.inputs['Base Color'])
    nt.links.new(cr.outputs['Color'], bs.inputs['Emission Color'])
    bs.inputs['Emission Strength'].default_value = emit
    return m


class Critter(Mascot):
    """mascota de plastilina con ojos de canica (o pixel), boca que habla y brazos/patas opcionales.
    forma: pan | blob | fantasma | bot | ballena | caja | gota | estrella | gemini"""
    kind = 'mascota'

    def __init__(self, name, spec):
        self.name = name
        shape = spec.get('forma', 'blob')
        sz = float(spec.get('tamano', 0.12))
        self.sz = sz
        col = spec.get('color', '#9A6FD0')
        col2 = spec.get('color2', shade(col, 1.25))
        self.root = Joint(name, M_world((0, 0, 0)))
        parts = []
        brillo = float(spec.get('brillo', 0.0))
        if shape == 'gemini':
            m = gradient_material('gemini_degradado', '#9B6BE8', '#3F8CF5', 0.06 * sz / 0.11)
        else:
            m = clay(f'mascota_{name}', col, rough=0.55, prints=0.9)
            if brillo:
                bs = [n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
                bs.inputs['Emission Color'].default_value = hexc(col)
                bs.inputs['Emission Strength'].default_value = brillo
        self.mat = m
        m2 = clay(f'mascota2_{name}', col2, rough=0.6, prints=0.6)
        # cuerpo centrado en c (altura del centro) con semiejes r; los rasgos van sobre su frente
        if shape == 'pan':
            r = (0.75 * sz, 0.55 * sz, 0.42 * sz)

            def roll(v):
                return Vector((v.x, v.y, v.z * (0.8 if v.z < 0 else 1.0)))
            parts.append(blob(f'{name}_body', m, mat4((0, 0, 0), (0, 0, 0), r), None, deform=roll, disp=0.003, dscale=0.05))
            for i, x in enumerate((-0.35, 0.0, 0.35)):      # cortes del pan pegados a la corteza
                pts = []
                for k in range(5):
                    yy = -0.3 + 0.6 * k / 4
                    xx = x + 0.1 * (k / 4 - 0.5)
                    zz = 0.42 * math.sqrt(max(0.0, 1 - (xx / 0.75) ** 2 - (yy / 0.55) ** 2)) - 0.012
                    pts.append((xx * sz, yy * sz, zz * sz))
                parts.append(tube(f'{name}_corte{i}', m2, pts, 0.04 * sz, None, ring=10, per=4, flat=0.45, disp=0.001))
            c = 0.34 * sz
        elif shape in ('blob', 'fantasma'):
            r = (0.5 * sz, 0.45 * sz, 0.6 * sz)
            parts.append(blob(f'{name}_body', m, mat4((0, 0, 0), (0, 0, 0), r), None,
                              deform=lambda v: Vector((v.x * (1 + 0.18 * max(0, -v.z)), v.y * (1 + 0.12 * max(0, -v.z)), v.z)),
                              disp=0.003))
            c = 0.6 * sz
        elif shape == 'gota':
            r = (0.48 * sz, 0.44 * sz, 0.6 * sz)
            parts.append(blob(f'{name}_body', m, mat4((0, 0, 0), (0, 0, 0), r), None,
                              deform=lambda v: Vector((v.x * (1 - 0.65 * max(0, v.z) ** 1.5), v.y * (1 - 0.65 * max(0, v.z) ** 1.5),
                                                       v.z * (1.25 if v.z > 0 else 1.0))), disp=0.002))
            c = 0.6 * sz
        elif shape in ('bot', 'caja'):
            r = (0.55 * sz, 0.45 * sz, 0.5 * sz) if shape == 'bot' else (0.62 * sz, 0.38 * sz, 0.5 * sz)
            parts.append(superbox(f'{name}_body', m, (0, 0, 0), r, None, e=0.4 if shape == 'bot' else 0.24, disp=0.002))
            if shape == 'bot':
                parts.append(tube(f'{name}_ant', clay('ia_gris', '#5B5752'), [(0, 0, 0.45 * sz), (0.05 * sz, 0, 0.85 * sz)], 0.04 * sz, None))
                parts.append(sphere(f'{name}_antb', m2, (0.06 * sz, 0, 0.9 * sz), 0.1 * sz, None))
            c = 0.5 * sz
        elif shape == 'ballena':
            r = (0.75 * sz, 0.5 * sz, 0.45 * sz)
            parts.append(sphere(f'{name}_body', m, (0, 0, 0), r, None, disp=0.002))
            parts.append(tube(f'{name}_tail', m, [(0.6 * sz, 0.1 * sz, 0), (0.95 * sz, 0.15 * sz, 0.25 * sz), (1.05 * sz, 0.15 * sz, 0.45 * sz)],
                              [0.18 * sz, 0.12 * sz, 0.16 * sz], None, flat=0.5))
            parts.append(sphere(f'{name}_belly', m2, (0, -0.2 * sz, -0.15 * sz), (0.55 * sz, 0.32 * sz, 0.26 * sz), None, disp=0.001))
            c = 0.45 * sz
        elif shape in ('estrella', 'gemini'):
            pts = []
            for i in range(64):
                a = 2 * math.pi * i / 64
                cc, ss = math.cos(a), math.sin(a)
                pw = 2.7 if shape == 'gemini' else 3.0
                pts.append((math.copysign(abs(cc) ** pw, cc) * 0.95, math.copysign(abs(ss) ** pw, ss) * 1.08))
            o = contour_mesh(f'{name}_star', [pts], sz, 0.32 * sz, m, bevel=0.012 * sz)
            o.data.transform(Matrix.Translation((0, 0.16 * sz, 0)))
            parts.append(o)
            r = (0.3 * sz, 0.16 * sz, 1.08 * sz)
            c = 1.08 * sz
        else:
            raise KeyError(f'forma de mascota desconocida: {shape}')
        self.half_h = c
        self.body = child_joint(f'{name}_cuerpo', self.root, (0, 0, c))
        self.body.attach(parts, 'local')

        def front(x, z):
            """y del frente del cuerpo (elipsoide aprox.) en (x, z) relativos al centro"""
            if shape in ('estrella', 'gemini'):
                return -0.16 * sz - 0.02 * sz
            if shape in ('bot', 'caja'):
                return -r[1] * 0.98
            q = 1 - (x / r[0]) ** 2 - (z / r[2]) ** 2
            return -r[1] * math.sqrt(max(0.05, q))
        # ojos
        eye_z = {'pan': 0.12, 'gemini': 0.08, 'estrella': 0.05, 'ballena': 0.1}.get(shape, 0.16) * sz
        dx = float(spec.get('ojos_sep', 0.17 if shape not in ('pan',) else 0.22)) * sz
        er = float(spec.get('ojos_tam', 0.11)) * sz
        self.eye_dx = dx
        self.eye_style = spec.get('ojos', 'canica')
        self.eyes = {}
        ink = clay('mascota_tinta', '#141210', rough=0.35, prints=0)
        for s in (+1, -1):
            y = front(s * dx, eye_z)
            j = child_joint(f'{name}_ojo{s}', self.body, (s * dx, y, eye_z))
            if self.eye_style == 'pixel':
                j.attach(superbox(f'{name}_eyeSq{s}', ink, (0, -0.1 * er, 0), (er * 0.8, er * 0.25, er * 0.8), None, e=0.22, disp=0),
                         'local')
            else:
                j.attach([sphere(f'{name}_eye{s}', marble('canica_blanca', '#F5F0E8'), (0, 0.25 * er, 0), er, None, disp=0),
                          sphere(f'{name}_pup{s}', marble('canica_negra', '#0B0A0A'), (0, -0.55 * er, 0.05 * er), er * 0.52, None,
                                 disp=0)], 'local')
            self.eyes[s] = j
        self.eyes_local = Vector((0, front(0, eye_z), eye_z))
        # boca: sonrisa (cerrada) + óvalo oscuro que se abre al hablar
        mz = eye_z - float(spec.get('boca_z', 0.2)) * sz
        my = front(0, mz)
        self.mouth = child_joint(f'{name}_bocaJ', self.body, (0, my - 0.004 * sz, mz))
        mink = clay(f'mascota_boca_{name}', spec.get('boca_color', '#2A0E0C'), rough=0.5, prints=0)
        self.mouth_slot = child_joint(f'{name}_bocaRanura', self.mouth, (0, 0, 0))
        sm = [Vector((-0.1, 0, 0.02)), Vector((0, 0, -0.02)), Vector((0.1, 0, 0.02))]
        self.mouth_slot.attach(tube(f'{name}_smile', mink, [v * sz for v in sm], 0.016 * sz, None, ring=8, per=4, disp=0), 'local')
        self.mouth_open = child_joint(f'{name}_bocaAbierta', self.mouth, (0, 0, -0.01 * sz))
        self.mouth_open.attach([sphere(f'{name}_mouthIn', mink, (0, 0, 0), (0.075 * sz, 0.025 * sz, 0.05 * sz), None, disp=0),
                                sphere(f'{name}_tongue', clay('lengua', '#C24A3C', rough=0.5), (0, -0.004 * sz, -0.028 * sz),
                                       (0.045 * sz, 0.02 * sz, 0.018 * sz), None, disp=0)], 'local')
        # brazos opcionales (salchichas cortas a los lados)
        self.arms = {}
        if spec.get('brazos', shape not in ('estrella', 'gemini', 'ballena')):
            for s in (+1, -1):
                ax = r[0] * 0.92
                j = child_joint(f'{name}_hombro{s}', self.body, (s * ax, 0, -0.05 * sz))
                j.attach(tube(f'{name}_arm{s}', m, [(0, 0, 0), (s * 0.12 * sz, 0, -0.03 * sz), (s * 0.2 * sz, 0, -0.1 * sz)],
                              [0.06 * sz, 0.055 * sz, 0.05 * sz], None, ring=10, per=4, disp=0.001), 'local')
                self.arms[s] = j
        self.legs = []
        for x in ((-0.28, 0.28) if spec.get('patas', shape in ('pan', 'blob', 'caja', 'bot')) else ()):
            j = child_joint(f'{name}_pata{x}', self.root, (x * sz, 0, 0.06 * sz))
            j.attach(sphere(f'{name}_leg{x}', m, (0, -0.02 * sz, -0.02 * sz), (0.09 * sz, 0.11 * sz, 0.07 * sz), None, disp=0.001),
                     'local')
            self.legs.append((x, j))

    def apply(self, p, t):
        sz = self.sz
        R = self.root
        R.loc = Vector(p.get('pos', (0, 0, 0)))
        R.rot = qe(D(p.get('pitch', 0)), D(p.get('roll', 0)), D(p.get('yaw', 0)), 'XYZ')
        R.scl = Vector((1, 1, 1)) * (TINY if p.get('hide') else p.get('scale', 1.0))
        sq = p.get('squash', 0.0)
        self.body.scl = Vector((1 - 0.35 * sq, 1 - 0.25 * sq, 1 + sq))
        self.body.rot = qe(D(p.get('tilt', 0)), D(p.get('lean_side', 0)), D(p.get('twist', 0)))
        self.body.loc = Vector((0, 0, p.get('bob', 0.0)))
        ex = p.get('eyes', 'normal')
        blink = p.get('blink', 0.0)
        gx, gz = p.get('gaze', (0.0, 0.0))
        es = {'normal': (1, 1, 1), 'calm': (1.05, 1, 0.55), 'happy': (1.1, 1, 0.3), 'wide': (1.25, 1.1, 1.25),
              'sad': (1, 1, 0.75), 'determined': (1.05, 1, 0.7), 'suspicious': (1.1, 1, 0.4)}.get(ex, (1, 1, 1))
        for s, j in self.eyes.items():
            j.scl = Vector((es[0], es[1], max(0.1, es[2] * (1 - 0.9 * blink))))
            j.rot = qe(0, D({'sad': 16, 'determined': -14}.get(ex, 0) * s), D(gx * 12))
            j.loc = Vector((0, 0, gz * 0.01 * sz))
        o = max(0.0, min(1.0, p.get('mouth', 0.0)))
        if o > 0.06:
            self.mouth_slot.scl = Vector((1, 1, 1)) * TINY
            self.mouth_open.scl = Vector((0.8 + 0.3 * o, 1, 0.4 + 1.1 * o))
        else:
            curve = {'sad': -1.0, 'suspicious': -0.4, 'wide': 0.2, 'happy': 1.5}.get(ex, 1.0)
            self.mouth_slot.rot = qe(0, D(180), 0) if curve < 0 else Quaternion()
            self.mouth_slot.scl = Vector((1, 1, max(0.2, abs(curve))))
            self.mouth_open.scl = Vector((0.6, 1, 0.5)) if ex == 'wide' else Vector((1, 1, 1)) * TINY
        for s, j in self.arms.items():
            up, fw = p.get('armL' if s > 0 else 'armR', (0, 0))
            j.rot = qe(0, D(-up * s), D(-fw * s))
        ph, amp = p.get('legphase', 0.0), p.get('legamp', 0.0)
        for i, (x, j) in enumerate(self.legs):
            j.rot = qe(D(amp * math.sin(ph + i * math.pi)), 0, 0)

    def record(self, f):
        self.root.record(f)
        self.body.record(f)
        for j in (self.mouth, self.mouth_slot, self.mouth_open):
            j.record(f)
        for j in self.eyes.values():
            j.record(f)
        for j in self.arms.values():
            j.record(f, scale=False)
        for x, j in self.legs:
            j.record(f, scale=False)


def build(name, spec, receipt_tex=None):
    t = spec.get('tipo', 'mascota')
    if t == 'clawd':
        return Clawd(name, spec)
    if t == 'chatgpt':
        return GPT(name, spec, receipt_tex)
    if t == 'gemini':
        s = dict(spec)
        s.setdefault('forma', 'gemini')
        s.setdefault('tamano', 0.11)
        s.setdefault('ojos_sep', 0.13)
        s.setdefault('ojos_tam', 0.1)
        s.setdefault('boca_z', 0.2)
        c = Critter(name, s)
        c.kind = 'gemini'
        return c
    return Critter(name, spec)
