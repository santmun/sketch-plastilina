# mascots.py — mascotas de IA de plastilina. Todas tienen boca que se abre con su voz, parpadeo y expresiones.
#   Clawd (Claude), ChatGPT (nudo negro + recibo), Gemini (destello) y Mascota genérica (forma/color por parámetros).
# Convención: la raíz está en el punto de apoyo (abajo); el frente mira a -Y.
import bpy, json, math, os
from mathutils import Vector, Matrix, Quaternion
from clay import (D, hexc, mat4, blob, sphere, superbox, tube, clay, simple, marble, text, FONT_BOLD)
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


# ================================================================ Meta AI (anillo con degradado)
def angle_gradient_material(name, stops, emit=0.7):
    """degradado por ángulo alrededor del eje Y local (anillo de pie en el plano XZ, mirando a -Y)"""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = clay(name, stops[0][1], rough=0.32, prints=0.5, spec=0.5, coat=0.3)
    nt = m.node_tree
    bs = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    at = nt.nodes.new('ShaderNodeMath')
    at.operation = 'ARCTAN2'
    nt.links.new(sep.outputs['Z'], at.inputs[0])
    nt.links.new(sep.outputs['X'], at.inputs[1])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = -math.pi
    mr.inputs['From Max'].default_value = math.pi
    nt.links.new(at.outputs[0], mr.inputs['Value'])
    cr = nt.nodes.new('ShaderNodeValToRGB')
    el = cr.color_ramp.elements
    el[0].position, el[0].color = stops[0][0], hexc(stops[0][1])
    el[1].position, el[1].color = stops[-1][0], hexc(stops[-1][1])
    for pos, col in stops[1:-1]:
        e = el.new(pos)
        e.color = hexc(col)
    nt.links.new(mr.outputs[0], cr.inputs['Fac'])
    nt.links.new(cr.outputs['Color'], bs.inputs['Base Color'])
    nt.links.new(cr.outputs['Color'], bs.inputs['Emission Color'])
    bs.inputs['Emission Strength'].default_value = emit
    return m


class MetaAI(Mascot):
    """anillo de Meta AI (degradado azul → violeta → rosa, ligeramente elíptico e inclinado) que flota;
    ojos de canica y boca dentro del hueco del anillo"""
    kind = 'metaai'

    def __init__(self, name, spec):
        sz = float(spec.get('tamano', 0.1))
        self.name, self.sz = name, sz
        self.root = Joint(name, M_world((0, 0, 0)))
        R, th = 0.42 * sz, 0.12 * sz
        c = R + th + 0.08 * sz
        self.half_h = c
        self.body = child_joint(f'{name}_cuerpo', self.root, (0, 0, c))
        m = angle_gradient_material('metaai_degradado', [(0.0, '#0A57FF'), (0.3, '#5A22F5'), (0.55, '#B21FDC'),
                                                         (0.78, '#FF2F86'), (1.0, '#0A57FF')], emit=float(spec.get('brillo', 0.35)))
        tilt = D(-14)
        pts = []
        for i in range(24):
            a = 2 * math.pi * i / 24
            x, z = R * 1.04 * math.cos(a), R * 0.94 * math.sin(a)
            pts.append((x * math.cos(tilt) - z * math.sin(tilt), 0, x * math.sin(tilt) + z * math.cos(tilt)))
        self.ring = child_joint(f'{name}_anilloJ', self.body, (0, 0, 0))
        self.ring.attach(tube(f'{name}_anillo', m, pts, th, None, closed=True, ring=20, per=4, flat=0.8, disp=0.0008), 'local')
        er = 0.085 * sz
        self.eye_dx = 0.13 * sz
        self.eyes = {}
        for s in (+1, -1):
            j = child_joint(f'{name}_ojo{s}', self.body, (s * self.eye_dx, -0.02 * sz, 0.07 * sz))
            j.attach([sphere(f'{name}_eye{s}', marble('canica_blanca', '#F5F0E8'), (0, 0, 0), er, None, disp=0),
                      sphere(f'{name}_pup{s}', marble('canica_negra', '#0B0A0A'), (0, -0.8 * er, 0.05 * er), er * 0.5, None,
                             disp=0)], 'local')
            self.eyes[s] = j
        self.eyes_local = Vector((0, -0.02 * sz, 0.07 * sz))
        mink = clay('metaai_boca', '#2A0E1E', rough=0.5, prints=0)
        lip = clay('metaai_labio', '#F4EEF8', rough=0.4, prints=0)
        self.mouth = child_joint(f'{name}_bocaJ', self.body, (0, -0.03 * sz, -0.12 * sz))
        self.mouth_slot = child_joint(f'{name}_bocaRanura', self.mouth, (0, 0, 0))
        sm = [Vector((-0.09, 0, 0.02)), Vector((0, 0, -0.025)), Vector((0.09, 0, 0.02))]
        self.mouth_slot.attach(tube(f'{name}_smile', lip, [v * sz for v in sm], 0.016 * sz, None, ring=8, per=4, disp=0), 'local')
        self.mouth_open = child_joint(f'{name}_bocaAbierta', self.mouth, (0, 0, -0.01 * sz))
        self.mouth_open.attach([sphere(f'{name}_mouthRim', lip, (0, 0.004 * sz, 0), (0.07 * sz, 0.02 * sz, 0.05 * sz), None, disp=0),
                                sphere(f'{name}_mouthIn', mink, (0, -0.004 * sz, 0), (0.055 * sz, 0.02 * sz, 0.038 * sz), None,
                                       disp=0)], 'local')

    def apply(self, p, t):
        R = self.root
        R.loc = Vector(p.get('pos', (0, 0, 0)))
        R.rot = qe(D(p.get('pitch', 0)), D(p.get('roll', 0)), D(p.get('yaw', 0)), 'XYZ')
        R.scl = Vector((1, 1, 1)) * (TINY if p.get('hide') else p.get('scale', 1.0))
        o = max(0.0, min(1.0, p.get('mouth', 0.0)))
        sq = p.get('squash', 0.0)
        self.body.scl = Vector((1 - 0.3 * sq, 1, 1 + sq)) * (1 + 0.06 * o)
        # flota: vaivén suave y el anillo gira un poco como si respirara
        self.body.loc = Vector((0, 0, p.get('bob', 0.0) + 0.06 * self.sz * math.sin(t * 2.1)))
        self.body.rot = qe(D(p.get('tilt', 0)), D(p.get('lean_side', 0)), D(p.get('twist', 0)))
        self.ring.rot = qe(0, D(10 * math.sin(t * 1.4) + 12 * o * math.sin(t * 9.0)), 0)
        ex = p.get('eyes', 'normal')
        blink = p.get('blink', 0.0)
        gx, gz = p.get('gaze', (0.0, 0.0))
        es = {'normal': (1, 1, 1), 'calm': (1.05, 1, 0.6), 'happy': (1.1, 1, 0.45), 'wide': (1.25, 1.1, 1.25),
              'sad': (1, 1, 0.75), 'determined': (1.05, 1, 0.7), 'suspicious': (1.1, 1, 0.45)}.get(ex, (1, 1, 1))
        for s, j in self.eyes.items():
            j.scl = Vector((es[0], es[1], max(0.1, es[2] * (1 - 0.9 * blink))))
            j.rot = qe(0, 0, D(gx * 14))
            j.loc = Vector((0, 0, gz * 0.012 * self.sz))
        if o > 0.06:
            self.mouth_slot.scl = Vector((1, 1, 1)) * TINY
            self.mouth_open.scl = Vector((0.8 + 0.3 * o, 1, 0.4 + 1.1 * o))
        else:
            self.mouth_slot.scl = Vector((1, 1, 1.4 if ex == 'happy' else 1.0))
            self.mouth_open.scl = Vector((1, 1, 1)) * TINY

    def record(self, f):
        for j in (self.root, self.body, self.ring, self.mouth, self.mouth_slot, self.mouth_open):
            j.record(f)
        for j in self.eyes.values():
            j.record(f)


# ================================================================ Muse (agente de IA de Meta, sept. 2026)
def linear_gradient_material(name, c0, c1, axis=(0.6, 0.0, -0.4), span=0.08, emit=0.25):
    """degradado lineal en coordenadas de objeto a lo largo de 'axis' (de c0 a c1)"""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = clay(name, c0, rough=0.34, prints=0.6, spec=0.5, coat=0.35)
    nt = m.node_tree
    bs = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    tc = nt.nodes.new('ShaderNodeTexCoord')
    dot = nt.nodes.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = axis
    nt.links.new(tc.outputs['Object'], dot.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = -span
    mr.inputs['From Max'].default_value = span
    nt.links.new(dot.outputs['Value'], mr.inputs['Value'])
    cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = hexc(c0)
    cr.color_ramp.elements[1].color = hexc(c1)
    nt.links.new(mr.outputs[0], cr.inputs['Fac'])
    nt.links.new(cr.outputs['Color'], bs.inputs['Base Color'])
    nt.links.new(cr.outputs['Color'], bs.inputs['Emission Color'])
    bs.inputs['Emission Strength'].default_value = emit
    return m


class Muse(Mascot):
    """el logo de Muse (Meta): una «M» azul de trazo fluido con tres picos y colitas en los extremos, en plastilina;
    ojos de canica con cuencas azules y boca, al estilo del nudo de ChatGPT"""
    kind = 'muse'
    # trazo del logo en unidades de media anchura (x a la derecha del espectador, z arriba)
    STROKE = ((-0.99, 0.06), (-0.83, 0.33), (-0.6, 0.62), (-0.5, 0.52), (-0.55, 0.0), (-0.63, -0.52), (-0.58, -0.66),
              (-0.47, -0.58), (-0.2, 0.08), (0.06, 0.55), (0.15, 0.42), (0.09, -0.12), (-0.01, -0.6), (0.07, -0.67),
              (0.17, -0.58), (0.4, -0.05), (0.57, 0.32), (0.65, 0.2), (0.59, -0.3), (0.55, -0.62), (0.63, -0.68),
              (0.74, -0.6), (0.9, -0.3), (0.97, -0.08))

    def __init__(self, name, spec):
        sz = float(spec.get('tamano', 0.1))
        self.name, self.sz = name, sz
        hw = 0.9 * sz
        self.root = Joint(name, M_world((0, 0, 0)))
        c = 0.75 * hw + 0.1 * sz
        self.half_h = c
        self.body = child_joint(f'{name}_cuerpo', self.root, (0, 0, c))
        m = linear_gradient_material('muse_degradado', '#0A46DC', '#1594FF', span=0.7 * hw)
        self.mark = child_joint(f'{name}_trazoJ', self.body, (0, 0, 0))
        self.mark.attach(tube(f'{name}_trazo', m, [(x * hw, 0, z * hw) for x, z in self.STROKE], 0.13 * hw, None, ring=16,
                              per=6, flat=0.7, disp=0.0008), 'local')
        er = 0.16 * hw
        self.eye_dx = 0.27 * hw
        self.eyes = {}
        for s in (+1, -1):
            cx = 0.05 * hw + s * self.eye_dx
            self.mark.attach(sphere(f'{name}_socket{s}', m, (cx, -0.03 * hw, 0.12 * hw), er * 1.32, None, disp=0.0006), 'local')
            j = child_joint(f'{name}_ojo{s}', self.body, (cx, -0.03 * hw - er * 0.5, 0.12 * hw))
            j.attach([sphere(f'{name}_eye{s}', marble('canica_blanca', '#F5F0E8'), (0, 0, 0), er, None, disp=0),
                      sphere(f'{name}_pup{s}', marble('canica_negra', '#0B0A0A'), (0, -0.8 * er, 0.05 * er), er * 0.52, None,
                             disp=0)], 'local')
            self.eyes[s] = j
        self.eyes_local = Vector((0.05 * hw, -0.03 * hw - er, 0.12 * hw))
        lip = clay('muse_labio', '#EAF2FF', rough=0.4, prints=0.2)
        self.mouth = child_joint(f'{name}_bocaJ', self.body, (0.05 * hw, -0.2 * hw, -0.2 * hw))
        self.mark.attach(sphere(f'{name}_mouthpad', m, (0.05 * hw, -0.05 * hw, -0.2 * hw), (0.22 * hw, 0.12 * hw, 0.13 * hw), None,
                                disp=0.0006), 'local')
        self.mouth_slot = child_joint(f'{name}_bocaRanura', self.mouth, (0, 0, 0))
        sm = [Vector((-0.14, 0, 0.03)), Vector((0, 0, -0.035)), Vector((0.14, 0, 0.03))]
        self.mouth_slot.attach(tube(f'{name}_smile', lip, [v * hw for v in sm], 0.025 * hw, None, ring=8, per=4, disp=0), 'local')
        self.mouth_open = child_joint(f'{name}_bocaAbierta', self.mouth, (0, 0, -0.01 * hw))
        self.mouth_open.attach([sphere(f'{name}_mouthRim', lip, (0, 0.004 * hw, 0), (0.11 * hw, 0.03 * hw, 0.08 * hw), None, disp=0),
                                sphere(f'{name}_mouthIn', clay('muse_boca', '#0B1A40', rough=0.5, prints=0),
                                       (0, -0.004 * hw, 0), (0.085 * hw, 0.03 * hw, 0.06 * hw), None, disp=0)], 'local')

    def apply(self, p, t):
        R = self.root
        R.loc = Vector(p.get('pos', (0, 0, 0)))
        R.rot = qe(D(p.get('pitch', 0)), D(p.get('roll', 0)), D(p.get('yaw', 0)), 'XYZ')
        R.scl = Vector((1, 1, 1)) * (TINY if p.get('hide') else p.get('scale', 1.0))
        o = max(0.0, min(1.0, p.get('mouth', 0.0)))
        sq = p.get('squash', 0.0)
        self.body.scl = Vector((1 - 0.3 * sq, 1, 1 + sq))
        # flota con un vaivén suave; el trazo «baila» un poco al hablar
        self.body.loc = Vector((0, 0, p.get('bob', 0.0) + 0.05 * self.sz * math.sin(t * 2.1)))
        self.body.rot = qe(D(p.get('tilt', 0)), D(p.get('lean_side', 0)), D(p.get('twist', 0)))
        self.mark.rot = qe(0, D(4 * math.sin(t * 1.4) + 6 * o * math.sin(t * 9.0)), 0)
        self.mark.scl = Vector((1, 1, 1)) * (1 + 0.08 * o)
        ex = p.get('eyes', 'normal')
        blink = p.get('blink', 0.0)
        gx, gz = p.get('gaze', (0.0, 0.0))
        es = {'normal': (1, 1, 1), 'calm': (1.05, 1, 0.6), 'happy': (1.1, 1, 0.45), 'wide': (1.25, 1.1, 1.25),
              'sad': (1, 1, 0.75), 'determined': (1.05, 1, 0.7), 'suspicious': (1.1, 1, 0.45)}.get(ex, (1, 1, 1))
        for s, j in self.eyes.items():
            j.scl = Vector((es[0], es[1], max(0.1, es[2] * (1 - 0.9 * blink))))
            j.rot = qe(0, 0, D(gx * 14))
            j.loc = Vector((0, 0, gz * 0.012 * self.sz))
        if o > 0.06:
            self.mouth_slot.scl = Vector((1, 1, 1)) * TINY
            self.mouth_open.scl = Vector((0.8 + 0.3 * o, 1, 0.4 + 1.1 * o))
        else:
            self.mouth_slot.scl = Vector((1, 1, 1.4 if ex == 'happy' else 1.0))
            self.mouth_open.scl = Vector((1, 1, 1)) * TINY

    def record(self, f):
        for j in (self.root, self.body, self.mark, self.mouth, self.mouth_slot, self.mouth_open):
            j.record(f)
        for j in self.eyes.values():
            j.record(f)


# ================================================================ Grok Bot (esfera negra, ojos de píldora inclinados)
class GrokBot(Mascot):
    """el logo de Grok Bot: esfera negra brillante con dos píldoras blancas inclinadas arriba a la derecha, sin boca.
    Al hablar aparece una ranura blanca pequeña; en silencio solo quedan los ojos (como el logo)"""
    kind = 'grok'
    # centros de las píldoras en coordenadas del logo (radio 1, x a la derecha del espectador, z arriba) y largo
    PILLS = (((0.02, 0.25), 0.5), ((0.56, 0.47), 0.5))

    def __init__(self, name, spec):
        sz = float(spec.get('tamano', 0.1))
        self.name, self.sz = name, sz
        r = 0.5 * sz
        self.r = r
        self.root = Joint(name, M_world((0, 0, 0)))
        self.half_h = r
        self.body = child_joint(f'{name}_cuerpo', self.root, (0, 0, r))
        black = clay('grok_negro', spec.get('color', '#111113'), rough=0.42, prints=0.6, spec=0.45, coat=0.15, sheen=0.0)
        self.body.attach(sphere(f'{name}_body', black, (0, 0, 0), r, None, disp=0.0012, dscale=0.05), 'local')
        white = simple('grok_blanco', '#F4F1EA', rough=0.35, emit='#FFFFFF', estr=0.35)
        # los ojos giran juntos sobre la esfera (mirada) desde el centro
        self.gazeJ = child_joint(f'{name}_mirada', self.body, (0, 0, 0))
        self.eyes = {}
        tilt = D(32)
        for k, ((lx, lz), ln) in enumerate(self.PILLS):
            s = -1 if k == 0 else +1
            # píldora en el plano de la cara; luego se proyecta a la superficie
            ax = Vector((-math.sin(tilt), 0, math.cos(tilt)))       # eje largo: la punta de arriba se va a la izquierda
            c = Vector((lx * r, 0, lz * r))
            j = child_joint(f'{name}_ojo{s}', self.gazeJ, (0, 0, 0))
            pts = []
            for i in range(5):
                q = c + ax * (ln * r * (i / 4 - 0.5))
                yy = -math.sqrt(max(1e-6, r * r - q.x * q.x - q.z * q.z)) - 0.035 * r
                pts.append((q.x, yy, q.z))
            j.attach(tube(f'{name}_pill{s}', white, pts, 0.12 * r, None, ring=12, per=4, flat=0.8, disp=0), 'local')
            self.eyes[s] = (j, c)
        self.eye_dx = 0.27 * r
        self.eyes_local = Vector((0.29 * r, -r, 0.36 * r))
        self.mouth = child_joint(f'{name}_bocaJ', self.body, (0.28 * r, -math.sqrt(r * r - 0.28 ** 2 * r * r - 0.12 ** 2 * r * r) - 0.01 * r,
                                                             -0.12 * r))
        self.mouth_open = child_joint(f'{name}_bocaAbierta', self.mouth, (0, 0, 0))
        self.mouth_open.attach(superbox(f'{name}_mouth', white, (0, 0, 0), (0.17 * r, 0.03 * r, 0.06 * r), None, e=0.4, disp=0),
                               'local')
        self.mouth_slot = self.mouth_open

    def apply(self, p, t):
        r = self.r
        R = self.root
        R.loc = Vector(p.get('pos', (0, 0, 0)))
        R.rot = qe(D(p.get('pitch', 0)), D(p.get('roll', 0)), D(p.get('yaw', 0)), 'XYZ')
        R.scl = Vector((1, 1, 1)) * (TINY if p.get('hide') else p.get('scale', 1.0))
        sq = p.get('squash', 0.0)
        o = max(0.0, min(1.0, p.get('mouth', 0.0)))
        self.body.scl = Vector((1 - 0.3 * sq, 1 - 0.2 * sq, 1 + sq))
        self.body.loc = Vector((0, 0, p.get('bob', 0.0)))
        self.body.rot = qe(D(p.get('tilt', 0)), D(p.get('lean_side', 0)), D(p.get('twist', 0)))
        gx, gz = p.get('gaze', (0.0, 0.0))
        self.gazeJ.rot = qe(D(-gz * 8), 0, D(gx * 8))
        ex = p.get('eyes', 'normal')
        blink = p.get('blink', 0.0)
        k = {'normal': 1.0, 'calm': 0.62, 'happy': 0.5, 'wide': 1.2, 'sad': 0.8, 'determined': 0.75, 'suspicious': 0.42}.get(ex, 1.0)
        k = max(0.12, k * (1 - 0.88 * blink))
        for s, (j, c) in self.eyes.items():
            # se acorta hacia su centro (párpado): escala alrededor de c
            j.scl = Vector((1, 1, k))
            j.loc = Vector((0, 0, c.z * (1 - k)))
        self.mouth_open.scl = Vector((0.7 + 0.4 * o, 1, 0.5 + 1.3 * o)) if o > 0.06 else Vector((1, 1, 1)) * TINY

    def record(self, f):
        for j in (self.root, self.body, self.gazeJ, self.mouth, self.mouth_open):
            j.record(f)
        for j, c in self.eyes.values():
            j.record(f)


# ================================================================ Modelo nuevo («AGI»): juguete de caja, genérico (sin marca real)
class NuevoModelo(Mascot):
    """robotito de juguete recién salido de la caja: cuerpo blanco perla, visor negro brillante con ojos de luz,
    placa ámbar en el pecho con letras, antena con foco, bracitos y patitas. Solemne (tipo guardián espacial)"""
    kind = 'nuevo'

    def __init__(self, name, spec):
        sz = float(spec.get('tamano', 0.14))
        self.name, self.sz = name, sz
        self.root = Joint(name, M_world((0, 0, 0)))
        leg_h = 0.12 * sz
        self.half_h = 0.45 * sz
        pearl = clay('nuevo_perla', spec.get('color', '#ECE8E0'), rough=0.38, prints=0.5, spec=0.5, coat=0.35, sheen=0.0)
        grey = clay('nuevo_gris', '#9A968F', rough=0.45, prints=0.3)
        visor = clay('nuevo_visor', '#101114', rough=0.12, prints=0, spec=0.7, coat=0.8, sheen=0.0)
        light = simple('nuevo_luz', '#FFF6E8', rough=0.3, emit='#FFF1DA', estr=1.6)
        amber = clay('nuevo_ambar', spec.get('placa', '#E89A4A'), rough=0.4, prints=0.3)
        self.legs = []
        for sd in (-1, 1):
            j = child_joint(f'{name}_pata{sd}', self.root, (sd * 0.17 * sz, 0, leg_h))
            j.attach(superbox(f'{name}_leg{sd}', grey, (0, 0, -0.5 * leg_h), (0.075 * sz, 0.08 * sz, 0.5 * leg_h), None, e=0.35,
                              disp=0.0006), 'local')
            self.legs.append(j)
        self.body = child_joint(f'{name}_cuerpo', self.root, (0, 0, leg_h))
        bz = 0.36 * sz
        self.body.attach(superbox(f'{name}_body', pearl, (0, 0, bz), (0.3 * sz, 0.22 * sz, 0.36 * sz), None, e=0.38, disp=0.0012,
                                  dscale=0.05), 'local')
        fy = -0.22 * sz
        # placa del pecho con letras
        self.body.attach(superbox(f'{name}_plate', amber, (0, fy - 0.004 * sz, 0.2 * sz), (0.17 * sz, 0.02 * sz, 0.075 * sz), None,
                                  e=0.3, disp=0), 'local')
        if spec.get('letras', 'AGI'):
            t = text(f'{name}_plate_t', spec.get('letras', 'AGI'), clay('nuevo_letras', '#2A2420', rough=0.4, prints=0),
                     (0, fy - 0.026 * sz, 0.2 * sz), 0.085 * sz, None, extrude=0.003 * sz, font=FONT_BOLD)
            self.body.attach(t, 'local')
        # visor
        vz = 0.5 * sz
        self.body.attach(superbox(f'{name}_visor', visor, (0, fy - 0.004 * sz, vz), (0.25 * sz, 0.03 * sz, 0.12 * sz), None, e=0.3,
                                  disp=0), 'local')
        self.eyes = {}
        for sd in (-1, 1):
            j = child_joint(f'{name}_ojo{sd}', self.body, (sd * 0.1 * sz, fy - 0.036 * sz, vz + 0.025 * sz))
            j.attach(superbox(f'{name}_eye{sd}', light, (0, 0, 0), (0.035 * sz, 0.006 * sz, 0.05 * sz), None, e=0.45, disp=0), 'local')
            self.eyes[sd] = j
        self.eye_dx = 0.1 * sz
        self.eyes_local = Vector((0, fy - 0.03 * sz, vz))
        self.mouth = child_joint(f'{name}_bocaJ', self.body, (0, fy - 0.036 * sz, vz - 0.065 * sz))
        self.mouth_open = child_joint(f'{name}_bocaAbierta', self.mouth, (0, 0, 0))
        self.mouth_open.attach(superbox(f'{name}_mouth', light, (0, 0, 0), (0.07 * sz, 0.005 * sz, 0.012 * sz), None, e=0.45, disp=0),
                               'local')
        self.mouth_slot = self.mouth_open
        # antena con foco
        top = 0.72 * sz
        self.body.attach([tube(f'{name}_ant', grey, [(0, 0, top - 0.01 * sz), (0.01 * sz, 0, top + 0.08 * sz), (0.02 * sz, 0, top + 0.14 * sz)],
                               0.012 * sz, None, disp=0),
                          sphere(f'{name}_antball', simple('nuevo_foco', '#FFC27A', rough=0.3, emit='#FFB45A', estr=3.0),
                                 (0.02 * sz, 0, top + 0.16 * sz), 0.035 * sz, None, disp=0)], 'local')
        self.arms = {}
        for sd in (-1, 1):
            j = child_joint(f'{name}_hombro{sd}', self.body, (sd * 0.31 * sz, 0, 0.46 * sz))
            j.attach(superbox(f'{name}_arm{sd}', pearl, (sd * 0.03 * sz, 0, -0.13 * sz), (0.055 * sz, 0.06 * sz, 0.14 * sz), None,
                              e=0.4, disp=0.0006), 'local')
            self.arms[sd] = j

    def apply(self, p, t):
        R = self.root
        R.loc = Vector(p.get('pos', (0, 0, 0)))
        R.rot = qe(D(p.get('pitch', 0)), D(p.get('roll', 0)), D(p.get('yaw', 0)), 'XYZ')
        R.scl = Vector((1, 1, 1)) * (TINY if p.get('hide') else p.get('scale', 1.0))
        sq = p.get('squash', 0.0)
        o = max(0.0, min(1.0, p.get('mouth', 0.0)))
        self.body.scl = Vector((1 - 0.3 * sq, 1 - 0.2 * sq, 1 + sq))
        self.body.loc = Vector((0, 0, p.get('bob', 0.0)))
        self.body.rot = qe(D(p.get('tilt', 0)), D(p.get('lean_side', 0)), D(p.get('twist', 0)))
        for sd, j in self.arms.items():
            up, fw = p.get('armL' if sd > 0 else 'armR', (0, 0))
            j.rot = qe(D(-fw), D(-up * sd), 0)
        ph, amp = p.get('legphase', 0.0), p.get('legamp', 0.0)
        for i, j in enumerate(self.legs):
            j.rot = qe(D(amp * math.sin(ph + math.pi * i)), 0, 0)
        ex = p.get('eyes', 'normal')
        blink = p.get('blink', 0.0)
        gx, gz = p.get('gaze', (0.0, 0.0))
        k = {'normal': 1.0, 'calm': 0.55, 'happy': 0.45, 'wide': 1.25, 'sad': 0.75, 'determined': 0.65, 'suspicious': 0.4}.get(ex, 1.0)
        k = max(0.1, k * (1 - 0.9 * blink))
        for sd, j in self.eyes.items():
            j.scl = Vector((1, 1, k))
            j.loc = Vector((gx * 0.03 * self.sz, 0, gz * 0.02 * self.sz))
            j.rot = qe(0, D((-14 if ex == 'determined' else 0) * sd), 0)
        self.mouth_open.scl = Vector((0.7 + 0.4 * o, 1, 0.6 + 2.0 * o)) if o > 0.06 else Vector((1, 1, 1)) * TINY

    def record(self, f):
        for j in (self.root, self.body, self.mouth, self.mouth_open):
            j.record(f)
        for j in self.eyes.values():
            j.record(f)
        for j in self.arms.values():
            j.record(f, scale=False)
        for j in self.legs:
            j.record(f, scale=False)


# ================================================================ DeepSeek (ballena azul del logo)
class DeepSeekBallena(Mascot):
    """ballenita azul de plastilina (el logo de DeepSeek): cuerpo redondo, panza clara, cola que se enrosca por encima
    de la cabeza como en el logo, aletas como bracitos, ojos de canica y boca grande"""
    kind = 'deepseek'

    def __init__(self, name, spec):
        sz = float(spec.get('tamano', 0.15))
        self.name, self.sz = name, sz
        self.root = Joint(name, M_world((0, 0, 0)))
        blue = clay('deepseek_azul', spec.get('color', '#4D6BFE'), rough=0.5, prints=0.9, spec=0.35)
        belly = clay('deepseek_panza', '#DCE3FF', rough=0.55, prints=0.6)
        bz = 0.24 * sz
        self.half_h = bz
        self.body = child_joint(f'{name}_cuerpo', self.root, (0, 0, 0))
        self.body.attach([sphere(f'{name}_body', blue, (0, 0, bz), (0.32 * sz, 0.27 * sz, 0.24 * sz), None, disp=0.001),
                          sphere(f'{name}_belly', belly, (0, -0.12 * sz, 0.16 * sz), (0.23 * sz, 0.16 * sz, 0.13 * sz), None,
                                 disp=0)], 'local')
        # cola: sale por detrás y se enrosca por encima de la cabeza; aleta caudal al final
        pts = [(0, 0.22 * sz, 0.3 * sz), (0, 0.33 * sz, 0.46 * sz), (0, 0.27 * sz, 0.62 * sz), (0, 0.12 * sz, 0.68 * sz)]
        self.tail = child_joint(f'{name}_cola', self.body, (0, 0.2 * sz, 0.3 * sz))
        tail_objs = [tube(f'{name}_tail', blue, [(a, b - 0.2 * sz, c - 0.3 * sz) for a, b, c in pts],
                          [0.08 * sz, 0.065 * sz, 0.05 * sz, 0.04 * sz], None, ring=12, per=5, disp=0.0006)]
        for sd in (-1, 1):
            tail_objs.append(sphere(f'{name}_fluke{sd}', blue, (sd * 0.075 * sz, 0.07 * sz - 0.2 * sz, 0.7 * sz - 0.3 * sz),
                                    (0.09 * sz, 0.035 * sz, 0.03 * sz), None, disp=0))
        self.tail.attach(tail_objs, 'local')
        er = 0.065 * sz
        self.eye_dx = 0.12 * sz
        self.eyes = {}
        for sd in (+1, -1):
            j = child_joint(f'{name}_ojo{sd}', self.body, (sd * self.eye_dx, -0.235 * sz, 0.33 * sz))
            j.attach([sphere(f'{name}_eye{sd}', marble('canica_blanca', '#F5F0E8'), (0, 0, 0), er, None, disp=0),
                      sphere(f'{name}_pup{sd}', marble('canica_negra', '#0B0A0A'), (0, -0.8 * er, 0.04 * er), er * 0.52, None,
                             disp=0)], 'local')
            self.eyes[sd] = j
        self.eyes_local = Vector((0, -0.24 * sz, 0.33 * sz))
        ink = clay('deepseek_boca', '#1B1440', rough=0.5, prints=0)
        self.mouth = child_joint(f'{name}_bocaJ', self.body, (0, -0.27 * sz, 0.22 * sz))
        self.mouth_slot = child_joint(f'{name}_bocaRanura', self.mouth, (0, 0, 0))
        sm = [Vector((-0.08, 0, 0.02)), Vector((0, 0, -0.02)), Vector((0.08, 0, 0.02))]
        self.mouth_slot.attach(tube(f'{name}_smile', ink, [v * sz for v in sm], 0.013 * sz, None, ring=8, per=4, disp=0), 'local')
        self.mouth_open = child_joint(f'{name}_bocaAbierta', self.mouth, (0, 0, -0.01 * sz))
        self.mouth_open.attach([sphere(f'{name}_mouthIn', ink, (0, 0, 0), (0.07 * sz, 0.02 * sz, 0.045 * sz), None, disp=0),
                                sphere(f'{name}_tongue', clay('deepseek_lengua', '#E0607A', rough=0.5, prints=0),
                                       (0, -0.004 * sz, -0.025 * sz), (0.04 * sz, 0.015 * sz, 0.018 * sz), None, disp=0)], 'local')
        self.arms = {}
        for sd in (-1, 1):
            j = child_joint(f'{name}_aleta{sd}', self.body, (sd * 0.3 * sz, -0.05 * sz, 0.17 * sz))
            j.attach(sphere(f'{name}_fin{sd}', blue, (sd * 0.06 * sz, 0, -0.02 * sz), (0.08 * sz, 0.035 * sz, 0.03 * sz), None,
                            disp=0), 'local')
            self.arms[sd] = j

    def apply(self, p, t):
        sz = self.sz
        R = self.root
        R.loc = Vector(p.get('pos', (0, 0, 0)))
        R.rot = qe(D(p.get('pitch', 0)), D(p.get('roll', 0)), D(p.get('yaw', 0)), 'XYZ')
        R.scl = Vector((1, 1, 1)) * (TINY if p.get('hide') else p.get('scale', 1.0))
        o = max(0.0, min(1.0, p.get('mouth', 0.0)))
        sq = p.get('squash', 0.0)
        self.body.scl = Vector((1 - 0.3 * sq, 1 - 0.2 * sq, 1 + sq))
        self.body.loc = Vector((0, 0, p.get('bob', 0.0)))
        self.body.rot = qe(D(p.get('tilt', 0)), D(p.get('lean_side', 0)), D(p.get('twist', 0)))
        self.tail.rot = qe(D(6 * math.sin(t * 2.4)), 0, D(8 * math.sin(t * 1.7)))
        for sd, j in self.arms.items():
            up, fw = p.get('armL' if sd > 0 else 'armR', (0, 0))
            j.rot = qe(D(-fw * 0.5), D(-up * sd), 0)
        ex = p.get('eyes', 'normal')
        blink = p.get('blink', 0.0)
        gx, gz = p.get('gaze', (0.0, 0.0))
        es = {'normal': (1, 1, 1), 'calm': (1.05, 1, 0.6), 'happy': (1.1, 1, 0.45), 'wide': (1.25, 1.1, 1.25),
              'sad': (1, 1, 0.75), 'determined': (1.05, 1, 0.7), 'suspicious': (1.1, 1, 0.45)}.get(ex, (1, 1, 1))
        for sd, j in self.eyes.items():
            j.scl = Vector((es[0], es[1], max(0.1, es[2] * (1 - 0.9 * blink))))
            j.rot = qe(0, D((14 if ex == 'sad' else 0) * sd), D(gx * 14))
            j.loc = Vector((0, 0, gz * 0.012 * sz))
        if o > 0.06:
            self.mouth_slot.scl = Vector((1, 1, 1)) * TINY
            self.mouth_open.scl = Vector((0.8 + 0.3 * o, 1, 0.4 + 1.2 * o))
        else:
            self.mouth_slot.rot = qe(0, D(180), 0) if ex == 'sad' else Quaternion()
            self.mouth_slot.scl = Vector((1, 1, 1.4 if ex == 'happy' else 1.0))
            self.mouth_open.scl = Vector((1, 1, 1)) * TINY

    def record(self, f):
        for j in (self.root, self.body, self.tail, self.mouth, self.mouth_slot, self.mouth_open):
            j.record(f)
        for j in self.eyes.values():
            j.record(f)
        for j in self.arms.values():
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
    if t == 'metaai':
        return MetaAI(name, spec)
    if t == 'muse':
        return Muse(name, spec)
    if t == 'grok':
        return GrokBot(name, spec)
    if t == 'deepseek':
        return DeepSeekBallena(name, spec)
    if t in ('nuevo', 'agi'):
        return NuevoModelo(name, spec)
    return Critter(name, spec)
