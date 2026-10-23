# humans.py — humano de plastilina genérico, construido desde una ficha de cast.json.
# Generaliza a Santi (sentado, delgado, cara A facetada) y al Jefe (parado, robusto, cara cuadrada) de «A escondidas».
import bpy, math, random
from mathutils import Vector, Matrix, Euler, Quaternion
from clay import (D, hexc, mat4, blob, sphere, superbox, box, cylinder, tube, clay, simple, Head, PlaneHead, hand)
from rig import Joint, child_joint, Arm, qe
from characters.parts import (TINY, M_world, shade, build_mouth, key_mouth, build_eye, pose_eye, rec_eye)
from characters import props


def _kx(ws):
    """anchos de silueta deseados (fracción de rx) -> factor sobre la esfera"""
    return [(z, w / max(0.2, math.sqrt(max(0.0, 1 - z * z)))) for z, w in ws]


# ---------------------------------------------------------------- caras (forma del cráneo + rasgos por defecto)
# A = la cara aprobada por Santi (look v2): facetas grandes de plastilina; con nariz −12 % (nariz 0.88) es el default.
FACES = {
    'A': dict(head=PlaneHead(0.156, 0.166, 0.226,
                             _kx([(-0.97, 0.30), (-0.86, 0.40), (-0.64, 0.70), (-0.42, 0.86), (-0.15, 1.04), (0.05, 1.0),
                                  (0.32, 1.0), (0.62, 0.90), (0.9, 0.52)]),
                             [(-1, 0.84), (-0.75, 0.90), (-0.4, 0.98), (0.0, 1.0), (1, 0.98)],
                             e=0.55, chin_z=-0.78, chin_flat=0.30, chin_fwd=0.07, cheek=0.06,
                             mesh=dict(ico=2, smooth=False, sub=0, bevel=0.0035, disp=0.0015)),
              eye_r=0.036, eye_sx=0.37, eye_sz=0.11, brow_sz=0.335, mouth_sz=-0.50, mouth_w=0.034,
              lip_r=(0.0048, 0.0068), nose='fina', hairline=0.165),
    # B: facetas finas
    'B': dict(head=PlaneHead(0.155, 0.166, 0.228,
                             _kx([(-0.97, 0.32), (-0.85, 0.42), (-0.62, 0.71), (-0.4, 0.87), (-0.15, 1.03), (0.3, 1.0),
                                  (0.62, 0.90), (0.9, 0.52)]),
                             [(-1, 0.86), (-0.75, 0.92), (-0.4, 0.98), (0.0, 1.0), (1, 0.98)],
                             e=0.66, chin_z=-0.79, chin_flat=0.38, chin_fwd=0.055, cheek=0.05,
                             mesh=dict(ico=3, smooth=False, sub=0, bevel=0.002, disp=0.0015)),
              eye_r=0.036, eye_sx=0.37, eye_sz=0.11, brow_sz=0.335, mouth_sz=-0.50, mouth_w=0.034,
              lip_r=(0.0048, 0.0068), nose='fina', hairline=0.165),
    # C: misma estructura, lisa (sin facetas)
    'C': dict(head=PlaneHead(0.154, 0.166, 0.23,
                             _kx([(-0.97, 0.34), (-0.84, 0.45), (-0.6, 0.73), (-0.15, 1.02), (0.3, 1.0), (0.62, 0.90),
                                  (0.9, 0.52)]),
                             [(-1, 0.88), (-0.75, 0.93), (-0.4, 0.98), (0.0, 1.0), (1, 0.98)],
                             e=0.76, chin_z=-0.8, chin_flat=0.45, chin_fwd=0.04, cheek=0.035,
                             mesh=dict(seg=(72, 40), sub=1, disp=0.003)),
              eye_r=0.036, eye_sx=0.37, eye_sz=0.11, brow_sz=0.335, mouth_sz=-0.50, mouth_w=0.036,
              lip_r=(0.005, 0.007), nose='fina', hairline=0.165),
    # cuadrada: la del Jefe v3 — mandíbula ancha, cejas gruesas, nariz grande
    'cuadrada': dict(head=PlaneHead(0.178, 0.172, 0.222,
                                    [(-0.97, 0.75), (-0.86, 0.95), (-0.62, 1.12), (-0.35, 1.08), (-0.1, 1.03), (0.3, 1.0),
                                     (0.62, 0.95), (0.9, 0.9)],
                                    [(-1, 0.9), (-0.7, 0.96), (-0.4, 1.0), (0.0, 1.0), (1, 0.98)],
                                    e=0.6, chin_z=-0.74, chin_flat=0.25, chin_fwd=0.03, cheek=0.02,
                                    mesh=dict(seg=(72, 40), sub=1, disp=0.003, dscale=0.1)),
                     eye_r=0.027, eye_sx=0.33, eye_sz=0.10, brow_sz=0.215, mouth_sz=-0.54, mouth_w=0.056,
                     lip_r=(0.0075, 0.0105), nose='grande', hairline=0.13, brows='gruesas'),
    # redonda: óvalo suave y amable (la de los compañeros de oficina, en versión con boca completa)
    'redonda': dict(head=PlaneHead(0.155, 0.16, 0.205,
                                   _kx([(-0.97, 0.36), (-0.8, 0.55), (-0.55, 0.82), (-0.2, 0.98), (0.3, 1.0), (0.62, 0.92),
                                        (0.9, 0.55)]),
                                   [(-1, 0.88), (-0.6, 0.95), (0.0, 1.0), (1, 0.98)],
                                   e=0.9, chin_z=-0.85, chin_flat=0.55, chin_fwd=0.02, cheek=0.04,
                                   mesh=dict(seg=(64, 36), sub=1, disp=0.0035)),
                    eye_r=0.034, eye_sx=0.37, eye_sz=0.11, brow_sz=0.33, mouth_sz=-0.53, mouth_w=0.038,
                    lip_r=(0.005, 0.007), nose='fina', hairline=0.16),
}

COMPLEXION = {'delgado': 0.0, 'medio': 0.45, 'robusto': 1.0}


def _lerp(a, b, k):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * k for x, y in zip(a, b))
    return a + (b - a) * k


class Human:
    kind = 'humano'

    def __init__(self, name, spec, chair_fn=None):
        """spec: ficha de cast.json. Se construye en el origen; perform.py lo coloca (asiento/anclaje) cada cuadro."""
        self.name = name
        self.spec = spec
        S = spec
        self.sit = S.get('postura', 'sentado') == 'sentado'
        self.escala = float(S.get('escala', 1.0))
        k = S.get('complexion', 'delgado')
        k = COMPLEXION.get(k, k) if isinstance(k, str) else float(k)
        self.k = k
        ropa = S.get('ropa', {})
        estilo = ropa.get('estilo', 'camiseta')
        self.estilo = estilo
        acc = set(S.get('accesorios', []))
        self.acc = acc
        tag = S.get('tag', name)
        self.tag = tag
        # raíz = asiento/posición (sin escala) -> cuerpo (con escala)
        self.root = Joint(name, M_world((0, 0, 0)))
        self.body = child_joint(f'{tag}_cuerpo', self.root, (0, 0, 0))
        skin_hex = S.get('piel', '#D4956C')
        skin = clay(f'piel_{name}', skin_hex, rough=0.56, sss=0.10, sheen=0.12, prints=0.2)
        self.skin = skin
        pelo = S.get('pelo', {})
        hair_hex = pelo.get('color', '#1A1511')
        hair = clay(f'pelo_{name}', hair_hex, rough=0.5, sheen=0.0, prints=1.1, spec=0.3)
        torso_hex = ropa.get('torso', '#D6C7A8')
        cloth = clay(f'torso_{name}', torso_hex, rough=0.72, sss=0.03, sheen=0.15 if estilo == 'saco' else 0.0)
        legs_hex = ropa.get('piernas', '#3C4250')
        legs = clay(f'piernas_{name}', legs_hex, rough=0.72, sheen=0.0)
        shoe = clay(f'zapatos_{name}', ropa.get('zapatos', '#2E2723'), rough=0.6)
        under = clay(f'camisa_{name}', ropa.get('camisa', '#EEE7DB'), rough=0.65)
        lip = clay(f'labio_{name}', S.get('labios', shade(skin_hex, 0.84)), rough=0.48)
        if chair_fn is not None and self.sit:
            self.root.attach(chair_fn(self.root.rest_world), 'world')
        B = self.body
        # ---------------------------------------------------------- medidas (delgado -> robusto)
        self.hip_h = 0.50 if self.sit else 0.54
        hip_h = self.hip_h
        torso_r = _lerp((0.142, 0.094, 0.225), (0.25, 0.18, 0.31), k)
        torso_z = _lerp(0.21, 0.25, k)
        self.sh_x = _lerp(0.15, 0.27, k)
        self.sh_z = _lerp(0.36, 0.46, k)
        l1, l2 = _lerp(0.25, 0.28, k), _lerp(0.235, 0.25, k)
        cap_c = (_lerp(0.125, 0.24, k), 0.0, _lerp(0.36, 0.47, k))
        cap_r = _lerp((0.045, 0.046, 0.04), (0.1, 0.095, 0.075), k)
        self.shoulder_top = (cap_c[0], cap_c[2] + cap_r[2])
        neck_r = _lerp(0.044, 0.075, k)
        neck_z = _lerp(0.43, 0.54, k)
        self.torso_r, self.torso_z = torso_r, torso_z
        self.neck_z = neck_z
        # ---------------------------------------------------------- piernas
        self.legs = {}
        if self.sit:
            parts = [sphere(f'{tag}_pelvis', legs, (0, 0.0, hip_h + 0.02), _lerp((0.135, 0.105, 0.08), (0.2, 0.15, 0.1), k))]
            for side in (+1, -1):
                hipp = Vector((_lerp(0.068, 0.1, k) * side, -0.01, hip_h))
                knee = Vector((_lerp(0.088, 0.12, k) * side, -0.40, hip_h + 0.03))
                ank = Vector((_lerp(0.098, 0.12, k) * side, -0.45, 0.085))
                lr = _lerp(1.0, 1.3, k)
                parts.append(tube(f'{tag}_leg{side}', legs, [hipp, hipp.lerp(knee, 0.5), knee, knee.lerp(ank, 0.5), ank],
                                  [0.066 * lr, 0.064 * lr, 0.058 * lr, 0.05 * lr, 0.048 * lr], None, ring=16, per=6))
                parts.append(superbox(f'{tag}_shoe{side}', shoe, ank + Vector((0, -0.045, -0.045)), (0.05, 0.095, 0.04),
                                      None, rot=(0, 0, D(6) * side), disp=0.003))
            B.attach(parts, 'local')
        else:
            for side in (+1, -1):
                j = child_joint(f'{tag}_cadera{side}', B, (_lerp(0.07, 0.1, k) * side, 0.0, hip_h))
                ank = Vector((_lerp(0.08, 0.11, k) * side, 0.0, 0.075)) - Vector((_lerp(0.07, 0.1, k) * side, 0, hip_h))
                lr = _lerp(0.066, 0.088, k)
                j.attach([tube(f'{tag}_leg{side}', legs, [(0, 0, 0.02), ank * 0.5, ank], [lr, lr * 0.9, lr * 0.8], None,
                               ring=16, per=6),
                          superbox(f'{tag}_shoe{side}', shoe, ank + Vector((0, -0.05, -0.045)), (0.055, 0.11, 0.038), None,
                                   rot=(0, 0, D(8) * side), disp=0.002)], 'local')
                self.legs[side] = j
        # ---------------------------------------------------------- torso
        self.spine = child_joint(f'{tag}_columna', B, (0, 0, hip_h))
        sp = []

        def tdef(v):
            kk = 1.0 + 0.14 * v.z
            return Vector((v.x * kk, v.y * (1.0 - 0.1 * v.z), v.z))

        def barrel(v):
            kk = 1.0 + 0.16 * math.exp(-((v.z - 0.35) / 0.45) ** 2) - 0.06 * math.exp(-((v.z + 0.6) / 0.3) ** 2)
            fy = 1.0 + (0.12 if v.y < 0 else 0.0) * math.exp(-((v.z - 0.25) / 0.4) ** 2)
            return Vector((v.x * kk, v.y * kk * fy, v.z))
        sp.append(blob(f'{tag}_torso', cloth, mat4((0, 0.0, torso_z), (0, 0, 0), torso_r), None,
                       deform=barrel if k > 0.55 else tdef, disp=0.004))
        sp.append(sphere(f'{tag}_pelvis2', legs, (0, 0.005, 0.02), _lerp((0.132, 0.096, 0.07), (0.19, 0.14, 0.09), k)))
        front_y = -torso_r[1] * 1.05          # superficie frontal aprox. del pecho
        top_z = torso_z + torso_r[2] * 0.93
        for side in (+1, -1):
            if k > 0.55:
                sp.append(superbox(f'{tag}_shcap{side}', cloth, (cap_c[0] * side, 0.0, cap_c[2]), cap_r, None, e=0.7, disp=0.003))
            else:
                sp.append(sphere(f'{tag}_shcap{side}', cloth, (cap_c[0] * side, 0.0, cap_c[2]), cap_r, disp=0.003))
        sp.append(tube(f'{tag}_neck', skin, [(0, 0.01 - 0.02 * k, top_z - 0.04), (0, -0.01 * k, neck_z + 0.04)], neck_r, None, caps=True))
        if estilo in ('camiseta', 'sueter', 'manga_larga'):
            sp.append(tube(f'{tag}_collar', clay(f'cuello_{name}', shade(torso_hex, 1.06), rough=0.7),
                           [(neck_r * 1.27 * math.cos(t), neck_r * 0.95 * math.sin(t) - 0.004, top_z - 0.002 - 0.012 * max(0, -math.sin(t)))
                            for t in [i * math.pi * 2 / 10 for i in range(10)]], 0.011, None, closed=True, ring=10, per=4))
        elif estilo == 'saco':
            sp.append(blob(f'{tag}_shirtV', under, mat4((0, front_y + 0.01, top_z - 0.05), (D(-10), 0, 0), (0.06, 0.03, 0.1)),
                           None, disp=0.002))
            lap = clay(f'solapa_{name}', shade(torso_hex, 1.12), rough=0.7)
            for side in (+1, -1):
                sp.append(tube(f'{tag}_lapel{side}', lap,
                               [(0.028 * side, front_y + 0.02, top_z - 0.02), (0.075 * side, front_y - 0.005, top_z - 0.13),
                                (0.085 * side, front_y - 0.025, top_z - 0.25), (0.06 * side, front_y - 0.03, top_z - 0.36)],
                               [0.016, 0.022, 0.02, 0.012], None, flat=0.45, ring=12, per=5))
                sp.append(sphere(f'{tag}_button{side}', clay('boton', '#121216', rough=0.3),
                                 (0.0, front_y - 0.035, top_z - 0.45 + 0.07 * (side + 1)), (0.012, 0.006, 0.012), None, disp=0))
                sp.append(tube(f'{tag}_collar{side}', under, [(0.06 * side, front_y + 0.05, top_z), (0.035 * side, front_y + 0.01, top_z - 0.025),
                                                             (0.01 * side, front_y - 0.005, top_z - 0.05)], 0.014, None))
        elif estilo == 'chef':
            sp.append(tube(f'{tag}_collar', cloth, [(neck_r * 1.2 * math.cos(t), neck_r * 0.95 * math.sin(t) - 0.002, top_z + 0.005)
                                                    for t in [i * math.pi * 2 / 12 for i in range(12)]], 0.016, None,
                           closed=True, ring=10, per=4))
            btn = clay(f'botones_{name}', ropa.get('botones', '#2E2A26'), rough=0.4, prints=0)
            for side in (+1, -1):
                for i in range(4):
                    z = top_z - 0.07 - i * 0.075
                    y = -torso_r[1] * (1.02 + 0.06 * math.exp(-((z - torso_z - 0.05) / 0.2) ** 2)) - 0.004
                    sp.append(sphere(f'{tag}_btn{side}{i}', btn, (0.045 * side, y, z), 0.009, None, disp=0))
        if 'corbata' in acc:
            tie = clay(f'corbata_{name}', S.get('corbata_color', '#7E1C1C'), rough=0.55)
            fy = front_y - (0.01 if estilo == 'saco' else 0.0)
            sp.append(tube(f'{tag}_tieknot', tie, [(-0.01, fy + 0.015, top_z - 0.04), (0.01, fy + 0.013, top_z - 0.043)], 0.017,
                           None, ring=12, per=3))
            sp.append(tube(f'{tag}_tie', tie, [(0.0, fy + 0.013, top_z - 0.06), (0.0, fy - 0.008, top_z - 0.15),
                                               (0.0, fy - 0.025, top_z - 0.26), (0.0, fy - 0.02, top_z - 0.36)],
                           [0.015, 0.02, 0.026, 0.026], None, flat=0.35, ref=(0, 1, 0), ring=12, per=5))
        if 'gafete' in acc:
            lan = clay('cordon', S.get('gafete_color', '#C9792F'), rough=0.6)
            fy = -torso_r[1] * 1.13
            sp.append(tube(f'{tag}_lan', lan, [(-0.05, -0.03, top_z), (-0.06, fy + 0.02, top_z - 0.09), (-0.01, fy, top_z - 0.18),
                                               (0.0, fy, top_z - 0.2), (0.01, fy, top_z - 0.18), (0.06, fy + 0.02, top_z - 0.09),
                                               (0.05, -0.03, top_z)], 0.0045, None, ring=8, per=4, disp=0))
            sp.append(superbox(f'{tag}_badge', clay('gafete', '#F6F1E7', rough=0.4), (0, fy, top_z - 0.235), (0.032, 0.006, 0.042),
                               None, rot=(D(-6), 0, 0), disp=0))
            sp.append(superbox(f'{tag}_badgeband', clay('gafete_naranja', '#E8873A', rough=0.5), (0, fy - 0.007, top_z - 0.21),
                               (0.028, 0.002, 0.008), None, rot=(D(-6), 0, 0), disp=0))
        if 'delantal' in acc:
            ap = clay(f'delantal_{name}', S.get('delantal_color', '#3D4B6A'), rough=0.75)
            fy = -torso_r[1] * 1.08

            def apron(v):
                return Vector((v.x * (1 + 0.15 * max(0.0, -v.z)), v.y, v.z))
            sp.append(blob(f'{tag}_apron', ap, mat4((0, fy, torso_z - 0.12), (D(-4), 0, 0), (torso_r[0] * 0.82, 0.012, 0.26)), None,
                           deform=apron, disp=0.002))
            sp.append(tube(f'{tag}_apronstrap', ap, [(-0.06, fy + 0.005, torso_z + 0.12), (-0.05, -0.02, top_z + 0.01),
                                                     (0.0, 0.03, top_z + 0.03), (0.05, -0.02, top_z + 0.01),
                                                     (0.06, fy + 0.005, torso_z + 0.12)], 0.006, None, ring=8, per=4, disp=0))
            sp.append(tube(f'{tag}_apronbelt', ap, [(torso_r[0] * math.cos(t) * 1.04, torso_r[1] * math.sin(t) * 1.1, torso_z - 0.1)
                                                    for t in [i * math.pi * 2 / 14 for i in range(14)]], 0.009, None,
                           closed=True, ring=8, per=4, disp=0))
        self.spine.attach(sp, 'local')
        # ---------------------------------------------------------- cabeza
        self.neck = child_joint(f'{tag}_cuello', self.spine, (0, -0.01 - 0.01 * k, neck_z))
        self.head = child_joint(f'{tag}_cabeza', self.neck, (0, -0.01 + 0.01 * k, 0.20))
        self.build_head(skin, hair, lip, hair_hex)
        # ---------------------------------------------------------- brazos
        long_sleeve = estilo in ('saco', 'chef', 'manga_larga', 'sueter')
        self.arms = {}
        hs = _lerp(1.0, 1.45, k) * float(S.get('manos', 1.0))
        for side, key in ((+1, 'L'), (-1, 'R')):
            a = Arm(f'{tag}_{key}', self.spine, (self.sh_x * side, 0.0, self.sh_z), l1, l2)
            ar = _lerp((0.034, 0.032, 0.030), (0.06, 0.055, 0.05), k)
            if long_sleeve:
                ar2 = tuple(r * 1.25 for r in ar)
                a.sh.attach(tube(f'{tag}_arm{key}', cloth, [(0, 0, 0), (0, 0, -l1 / 2), (0, 0, -l1)], ar2, None, ring=16, per=4), 'local')
                a.el.attach([tube(f'{tag}_fore{key}', cloth, [(0, 0, 0.0), (0, 0, -l2 * 0.55), (0, 0, -l2 * 0.92)],
                                  [ar2[1], ar2[2], ar2[2] * 0.95], None, ring=16, per=4),
                             tube(f'{tag}_cuff{key}', under if estilo == 'saco' else cloth, [(0, 0, -l2 * 0.9), (0, 0, -l2 * 1.02)],
                                  ar2[2] * 0.85, None, ring=14, per=2)], 'local')
            else:
                a.sh.attach([tube(f'{tag}_arm{key}', skin, [(0, 0, 0), (0, 0, -l1 / 2), (0, 0, -l1)], ar, None, ring=16, per=4),
                             tube(f'{tag}_sleeve{key}', cloth, [(0, 0, 0.02), (0, 0, -0.06), (0, 0, -0.12)],
                                  [ar[0] * 1.32] * 3, None, ring=16, per=4)], 'local')
                a.el.attach([tube(f'{tag}_fore{key}', skin, [(0, 0, 0), (0, 0, -l2 / 2), (0, 0, -l2)], [ar[1] * 0.94, ar[2] * 0.93, ar[2] * 0.83],
                                  None, ring=16, per=4)], 'local')
            a.wr.attach(hand(None, f'{tag}_hand{key}', skin, (0, 0, -0.045 * hs), (0, 0, -1), (-side, 0, 0), side=-side,
                             curl=0.3, s=hs), 'local')
            self.arms[key] = a
            item = S.get('mano_izq' if key == 'L' else 'mano_der')
            if item:
                pj = child_joint(f'{tag}_{key}_objeto', a.wr, (0.0, -0.06 * hs, -0.07 * hs))
                pj.attach(props.hand_item(f'{tag}_{key}_{item}', item, side), 'local')

    # ------------------------------------------------------------------ cabeza
    def build_head(self, skin, hair, lip, hair_hex):
        S = self.spec
        cara = S.get('cara', {})
        if isinstance(cara, str):
            cara = dict(preset=cara)
        F = dict(FACES[cara.get('preset', 'A')])
        H = F['head']
        hs = float(cara.get('tam', 1.0))
        if hs != 1.0:
            H = H.scaled(hs, hs, hs)
        self.H = H
        self.F = F
        tag = self.tag
        hj = self.head
        parts = [blob(f'{tag}_skull', skin, H.M(), None, deform=H.deform, **H.mesh)]
        # ojos
        r = F['eye_r'] * float(cara.get('ojos_tam', 1.0))
        iris = cara.get('ojos_color', '#4A2A18')
        self.eyes = {}
        for side in (+1, -1):
            c = H.surf(F['eye_sx'] * side, F['eye_sz'], out=-r * 0.58)
            self.eyes[side] = build_eye(f'{tag}_eye{side}', hj, c, r, skin, iris=iris, lash=shade(hair_hex, 1.2), lash_r=0.13)
        # cejas
        brow_m = clay(f'cejas_{self.name}', cara.get('cejas_color', hair_hex), rough=0.5, prints=0.8, sheen=0.0)
        gruesas = cara.get('cejas', F.get('brows', 'delgadas')) == 'gruesas'
        self.brows = {}
        bz = F['brow_sz']
        for side in (+1, -1):
            if gruesas:
                bc = H.surf(0.33 * side, bz, 0.028)
                pts = [H.surf(0.08 * side, bz - 0.015, 0.03), H.surf(0.3 * side, bz + 0.01, 0.034), H.surf(0.58 * side, bz, 0.024)]
                brad = [0.024, 0.028, 0.02]
            else:
                bc = H.surf(0.36 * side, bz, 0.012)
                pts = [H.surf(0.12 * side, bz - 0.005, 0.010), H.surf(0.30 * side, bz + 0.015, 0.013),
                       H.surf(0.52 * side, bz + 0.01, 0.011), H.surf(0.66 * side, bz - 0.025, 0.008)]
                brad = [0.0095, 0.0102, 0.009, 0.006]
            bj = child_joint(f'{tag}_ceja{side}', hj, bc)
            bj.attach(tube(f'{tag}_brow{side}', brow_m, [p - bc for p in pts], brad, None, ring=12, per=5, flat=0.55,
                           disp=0.0012, dscale=0.05), 'local')
            self.brows[side] = bj
        # orejas
        es = float(cara.get('orejas', 1.0))
        for side in (+1, -1):
            ec = Vector((H.rx * 0.93 * side, 0.025, 0.03))
            ear_rot = (0, D(-8) * side, D(-38) * side)
            parts.append(sphere(f'{tag}_ear{side}', skin, ec + Vector((0.018 * side, 0.0, 0)), (0.015 * es, 0.042 * es, 0.064 * es),
                                None, rot=ear_rot, disp=0.002, dscale=0.05))
            Mr = mat4(ec + Vector((0.018 * side, 0, 0)), ear_rot)
            pts = [Mr @ Vector((0.013 * side * es, 0.019 * es * math.cos(t), (0.047 * math.sin(t) + 0.004) * es))
                   for t in (D(-60), D(0), D(50), D(100), D(150), D(200))]
            parts.append(tube(f'{tag}_earRim{side}', skin, pts, 0.0075 * es, None, ring=10, per=4, disp=0.001))
        # nariz (nariz = factor de tamaño; 0.88 = la nariz −12 % aprobada en la cara A)
        nk = float(cara.get('nariz', 0.88 if F['nose'] == 'fina' else 1.0))
        if F['nose'] == 'grande':
            parts.append(tube(f'{tag}_nose', skin, [H.surf(0, 0.14, -0.004), H.surf(0, -0.02, 0.026 * nk), H.surf(0, -0.16, 0.046 * nk)],
                              [0.02 * nk, 0.026 * nk, 0.032 * nk], None, ring=16, per=6, disp=0.0015, dscale=0.05))
            parts.append(sphere(f'{tag}_nosetip', skin, H.surf(0, -0.17, 0.046 * nk), (0.034 * nk, 0.03 * nk, 0.028 * nk), None, disp=0.0015))
            for side in (+1, -1):
                parts.append(sphere(f'{tag}_nostril{side}', skin, H.surf(0.12 * side * nk, -0.2, 0.02 * nk),
                                    (0.018 * nk, 0.016 * nk, 0.014 * nk), None, disp=0.001))
        else:
            parts.append(tube(f'{tag}_nose', skin, [H.surf(0, 0.10 - 0.25 * (1 - nk), -0.006), H.surf(0, -0.04, 0.012 * nk),
                                                    H.surf(0, -0.15, 0.022 * nk)],
                              [0.014 * nk, 0.016 * nk, 0.019 * nk], None, ring=16, per=6, disp=0.0015, dscale=0.05))
            for side in (+1, -1):
                parts.append(sphere(f'{tag}_nostril{side}', skin, H.surf(0.085 * nk * side, -0.18, 0.012 * nk),
                                    (0.012 * nk, 0.012 * nk, 0.010 * nk), None, disp=0.001))
        if 'lunares' in self.acc:
            mole = clay('lunar', '#4A2A1C', rough=0.5)
            for i, (sx, sz) in enumerate(((0.30, -0.20), (-0.40, -0.34))):
                parts.append(sphere(f'{tag}_mole{i}', mole, H.surf(sx, sz, 0.0), 0.0048, None, disp=0))
        if 'lentes' in self.acc:
            gm = clay(f'lentes_{self.name}', S.get('lentes_color', '#2A2420'), rough=0.3, prints=0)
            rr = F['eye_r'] * 1.45
            cs = {}
            for side in (+1, -1):
                c = H.surf(F['eye_sx'] * side, F['eye_sz'], 0.022)
                cs[side] = c
                parts.append(tube(f'{tag}_glass{side}', gm, [c + Vector((rr * 1.15 * math.cos(t), 0, rr * 0.92 * math.sin(t)))
                                                             for t in [i * math.pi / 6 for i in range(12)]], 0.0055, None,
                                  closed=True, ring=8, per=3, disp=0))
                ear = Vector((H.rx * 0.97 * side, 0.02, F['eye_sz'] * H.rz))
                parts.append(tube(f'{tag}_temple{side}', gm, [c + Vector((rr * 1.15 * side, 0, 0)), ear], 0.004, None, ring=8, per=3,
                                  disp=0))
            mid = (cs[1] + cs[-1]) / 2 + Vector((0, -0.004, 0.004))
            parts.append(tube(f'{tag}_bridge', gm, [cs[1] - Vector((rr * 1.15, 0, 0)), mid, cs[-1] + Vector((rr * 1.15, 0, 0))],
                              0.004, None, ring=8, per=3, disp=0))
        hj.attach(parts, 'local')
        # boca (todos los que hablan tienen boca con labios, interior y dientes)
        mw = F['mouth_w'] * float(cara.get('boca_ancho', 1.0))
        self.mouth = build_mouth(f'{tag}_boca', H, F['mouth_sz'], mw, hj, lip_mat=lip, lip_r=F['lip_r'])
        self.stache = None
        if 'bigote' in self.acc:
            msz = F['mouth_sz']
            # bigote por ENCIMA de la boca: nunca la tapa (el lip-sync tiene que verse)
            k = float(S.get('bigote_tam', 1.0))
            sc = H.surf(0, msz + 0.24, 0.026)
            self.stache = child_joint(f'{tag}_bigoteJ', hj, sc)
            st = []
            for side in (+1, -1):
                st.append(tube(f'{tag}_stache{side}', hair, [H.surf(0.02 * side, msz + 0.26, 0.017) - sc, H.surf(0.2 * side, msz + 0.245, 0.018) - sc,
                                                             H.surf(0.33 * side, msz + 0.19, 0.011) - sc],
                               [0.017 * k, 0.016 * k, 0.009 * k], None, ring=14, per=6, disp=0.002, dscale=0.04))
            self.stache.attach(st, 'local')
        if 'barba' in self.acc:
            Hb = H.scaled(1.035, 1.045, 1.02)
            bc_ = Matrix.Translation((0, -0.012, -0.004)) @ Hb.M()
            hj.attach([blob(f'{tag}_beard', hair, bc_, None, deform=Hb.deform, seg=(56, 32), disp=0.003, dscale=0.04,
                            cut=(Vector((0, 0, -0.18)), Vector((0, 0.35, -1.0)).normalized()))], 'local')
        self.build_hair(hair)
        if 'gorro_chef' in self.acc:
            self.build_chef_hat()
        self.sweat = child_joint(f'{tag}_sudorJ', hj, (0, 0, 0))
        sw = clay('gota_sudor', '#BFD3D6', rough=0.08, prints=0, sss=0.3, coat=1.0)
        self.sweat.attach(sphere(f'{tag}_sweat', sw, H.surf(-0.74, 0.40, 0.014), (0.012, 0.012, 0.019), None,
                                 disp=0, rot=(0, D(-15), 0)), 'local')

    def _cap(self, hair, sx, sy, sz, p0, nrm, name='hair', seg=(64, 36), off=(0, 0.004, 0)):
        H = self.H
        capH = H.scaled(sx, sy, sz)
        CM = Matrix.Translation(off) @ capH.M()
        p0, nrm = Vector(p0), Vector(nrm).normalized()
        return blob(f'{self.tag}_{name}', hair, CM, None, deform=capH.deform, seg=seg, disp=0.0025,
                    cut=(Vector((p0.x / capH.rx, p0.y / capH.ry, p0.z / capH.rz)),
                         Vector((nrm.x / capH.rx, nrm.y / capH.ry, nrm.z / capH.rz)).normalized()))

    def build_hair(self, hair):
        S = self.spec
        style = S.get('pelo', {}).get('estilo', 'copete')
        if 'gorro_chef' in self.acc and style in ('copete', 'rizado', 'chongo'):
            style = 'corto'      # bajo el gorro no cabe volumen
        H, F, tag, hj = self.H, self.F, self.tag, self.head
        parts = []
        hl = F.get('hairline', 0.165)
        if style == 'copete':     # el de Santi: copete moderado hacia arriba y atrás, lados cortos
            parts.append(self._cap(hair, 1.075, 1.06, 1.035, (0, -0.12, hl), (0, 0.78, 1.0), seg=(72, 40)))
            e = 0.74

            def bxd(v):
                w = Vector([math.copysign(abs(c) ** e, c) for c in v])
                kk = 1.0 - 0.16 * max(0.0, -w.z)
                return Vector((w.x * kk, w.y * (1.0 - 0.08 * max(0.0, -w.z)), w.z))
            QM = mat4((-0.01, 0.004, H.rz * 0.876), (D(-15), 0, D(-5)), (H.rx * 1.006, H.ry * 0.94, 0.074))
            parts.append(blob(f'{tag}_quiff', hair, QM, None, deform=bxd, seg=(56, 32), disp=0.003, dscale=0.05))

            def on_q(x0, th, out):
                cx = math.sqrt(max(0.0, 1 - x0 * x0))
                v = Vector((x0, -math.cos(th) * cx, math.sin(th) * cx))
                p = QM @ bxd(v)
                q = QM @ bxd(v * 1.03)
                return p + (q - p).normalized() * out
            for i, x0 in enumerate((-0.55, -0.25, 0.05, 0.35, 0.65, 0.9)):
                pts = [on_q(max(-0.96, min(0.96, x0 - 0.45 * kk / 7)), D(-10) + D(130) * kk / 7, -0.004) for kk in range(8)]
                parts.append(tube(f'{tag}_lock{i}', hair, pts, [0.004, 0.009, 0.012, 0.013, 0.013, 0.012, 0.009, 0.004], None,
                                  ring=10, per=5, disp=0.001, dscale=0.05))
        elif style == 'atras':    # el del Jefe: peinado hacia atrás con surcos
            parts.append(self._cap(hair, 1.05, 1.06, 1.04, (0, -0.14, hl), (0, 0.42, 1.0)))
            for i, x in enumerate((-0.6, -0.3, 0.0, 0.3, 0.6)):
                pts = [H.surf(x, 0.62, 0.012), H.surf(x * 0.95, 0.9, 0.016), H.surf(x * 0.9, 0.7, 0.02, back=True)]
                parts.append(tube(f'{tag}_comb{i}', hair, pts, [0.006, 0.008, 0.006], None, ring=10, per=5, disp=0.001))
        elif style == 'corto':
            parts.append(self._cap(hair, 1.04, 1.05, 1.03, (0, -0.15, hl - 0.03), (0, 0.7, 1.0)))
        elif style in ('chongo', 'coleta'):
            parts.append(self._cap(hair, 1.06, 1.06, 1.05, (0, -0.16, hl), (0, 0.8, 1.0)))
            if style == 'chongo':
                parts.append(sphere(f'{tag}_bun', hair, (0, H.ry * 0.62, H.rz * 0.92), 0.072, None, disp=0.004))
            else:
                parts.append(sphere(f'{tag}_tie', hair, (0, H.ry * 1.0, H.rz * 0.35), 0.035, None, disp=0.003))
                parts.append(tube(f'{tag}_ponytail', hair, [(0, H.ry * 1.05, H.rz * 0.35), (0, H.ry * 1.35, H.rz * 0.0),
                                                           (0, H.ry * 1.3, -H.rz * 0.5)], [0.04, 0.045, 0.02], None, ring=14,
                                  per=5, disp=0.003))
        elif style == 'bob':
            parts.append(self._cap(hair, 1.15, 1.12, 1.05, (0, 0, -0.13 * H.rz / 0.2), (0, 0, 1.0), name='hair'))
            parts.append(superbox(f'{tag}_bangs', hair, (0, -H.ry * 0.98, H.rz * 0.62), (H.rx * 0.82, 0.025, 0.05), None, e=0.4,
                                  disp=0.002))
        elif style == 'rizado':
            rnd = random.Random(len(self.name) * 31 + 7)
            for i in range(30):
                a = rnd.uniform(0, 2 * math.pi)
                z = rnd.uniform(0.05, 1.0)
                el_ = math.asin(z)
                p = Vector((H.rx * 1.05 * math.cos(el_) * math.cos(a), H.ry * 1.05 * math.cos(el_) * math.sin(a), H.rz * 1.0 * z))
                if p.y < -0.06 and p.z < H.rz * 0.72:
                    continue
                parts.append(sphere(f'{tag}_curl{i}', hair, p, 0.05, None, disp=0.004))
        elif style == 'calvo':
            parts.append(tube(f'{tag}_fringe', hair, [H.surf(0.97, 0.15, 0.006), H.surf(0.8, 0.2, 0.01, back=True),
                                                      H.surf(0.0, 0.25, 0.012, back=True), H.surf(-0.8, 0.2, 0.01, back=True),
                                                      H.surf(-0.97, 0.15, 0.006)], 0.022, None, ring=12, per=5, disp=0.003))
        if parts:
            hj.attach(parts, 'local')

    def build_chef_hat(self):
        H, tag = self.H, self.tag
        white = clay(f'gorro_{self.name}', self.spec.get('gorro_color', '#D8D1C2'), rough=0.8, prints=0.5)
        zb = H.rz * 0.80          # la banda abraza la cabeza (no flota sobre el pelo)
        parts = [cylinder(f'{tag}_hatband', white, (0, 0.006, zb), H.rx * 1.05, 0.085, None, sub=1, disp=0.002, bevel=0.006)]

        def puff(v):
            return Vector((v.x, v.y, v.z * (1 + 0.12 * math.sin(5 * math.atan2(v.y, v.x)) * (v.z > 0))))
        parts.append(blob(f'{tag}_hatpuff', white, mat4((0, 0.006, zb + 0.1), (0, 0, 0), (H.rx * 1.22, H.ry * 1.18, 0.1)), None,
                          deform=puff, disp=0.004, dscale=0.06))
        self.head.attach(parts, 'local')

    # ------------------------------------------------------------------ puntos de anclaje
    def socket(self, name):
        """(articulación, punto local) de un anclaje del personaje"""
        sx, sz = self.shoulder_top
        if name in ('hombro_izq', 'hombro_der'):
            return self.spine, Vector(((sx if name == 'hombro_izq' else -sx), -0.01, sz))
        if name == 'regazo':
            return self.body, Vector((0, -0.275, 0.585)) if self.sit else Vector((0, -0.25, self.hip_h + 0.1))
        if name in ('cara', 'boca'):
            return self.head, Vector((0, -0.10, -0.02))
        if name == 'ojos':
            return self.head, Vector((0, -0.12, 0.025))
        if name == 'cabeza':
            return self.head, Vector((0, 0, 0))
        if name == 'coronilla':
            return self.head, Vector((0, 0, self.H.rz + 0.02))
        if name == 'pecho':
            return self.spine, Vector((0, -self.torso_r[1], self.torso_z + 0.08))
        if name in ('mano_izq', 'mano_der'):
            return self.arms['L' if name == 'mano_izq' else 'R'].wr, Vector((0, 0, -0.08))
        if name in ('pies', 'raiz'):
            return self.root, Vector((0, 0, 0))
        raise KeyError(f'{self.name}: anclaje desconocido «{name}»')

    def world_point(self, name):
        j, p = self.socket(name)
        return j.world() @ p

    def facing(self):
        """vector adelante (mundo) del cuerpo"""
        m = self.root.world().to_3x3()
        v = m @ Vector((0, -1, 0))
        v.z = 0
        return v.normalized()

    # ------------------------------------------------------------------ pose
    def apply(self, p, t):
        R = self.root
        R.rot = qe(0, 0, D(p.get('yaw', 0.0)))
        R.loc = Vector(p.get('pos', (0, 0, 0)))
        R.scl = Vector((1, 1, 1)) * (TINY if p.get('hide') else 1.0)
        self.body.scl = Vector((1, 1, 1)) * self.escala
        ph, amp = p.get('walkphase', 0.0), p.get('walkamp', 0.0)
        for side, j in self.legs.items():
            j.rot = qe(D(amp * math.sin(ph + (0 if side > 0 else math.pi))), 0, 0)
        bob = abs(math.sin(ph)) * 0.02 * (amp / 25.0) if self.legs else 0.0
        self.spine.loc = Vector((0, 0, bob))
        self.spine.rot = qe(D(p.get('lean', 0)), D(p.get('side', 0) + amp * 0.15 * math.sin(ph)), D(p.get('twist', 0)))
        hp, hy, hr = p.get('head', (0, 0, 0))
        self.neck.rot = qe(D(hp), D(hr), D(hy), 'ZXY')
        gy, gp = p.get('gaze', (0, 0))
        blink = p.get('blink', 0.0)
        for side, E in self.eyes.items():
            pose_eye(E, gy, gp, p.get('lidU', 32), p.get('lidL', 28), blink)
        worry = p.get('worry', 0.0)
        for side, bj in self.brows.items():
            raise_ = p.get('browL' if side > 0 else 'browR', p.get('brow', 0.0))
            bj.loc = Vector((0, 0, 0.012 * raise_ + 0.006 * worry))
            bj.rot = qe(0, D(-14 * worry * side + 10 * p.get('angry', 0) * side), 0)
        self.sweat.scl = Vector((1, 1, 1)) * (1.0 if p.get('sweat', 0) > 0.5 else TINY)
        self._mouth = p.get('mouth', {})
        if self.stache is not None:
            op = self._mouth.get('open', 0.0)
            self.stache.loc = Vector((0, 0, 0.006 * op))
            self.stache.rot = qe(D(-6 * op))
        spW = self.spine.local()
        for key, a in self.arms.items():
            tgt, pole, wr = p['arms'][key]
            T = Vector(tgt)
            if p.get('arm_space', {}).get(key) == 'root':
                T = spW.inverted() @ T
            a.solve(T, pole, qe(*[D(x) for x in wr]))

    def joints(self):
        js = [self.root, self.body, self.spine, self.neck, self.head, self.sweat] + list(self.legs.values())
        if self.stache is not None:
            js.append(self.stache)
        return js

    def record(self, f):
        for j in (self.root, self.body, self.spine, self.neck, self.sweat):
            j.record(f)
        if self.stache is not None:
            self.stache.record(f)
        key_mouth(self.mouth, f, self._mouth)
        for j in self.legs.values():
            j.record(f, scale=False)
        for bj in self.brows.values():
            bj.record(f, scale=False)
        for E in self.eyes.values():
            rec_eye(E, f)
        for a in self.arms.values():
            a.sh.record(f, scale=False)
            a.el.record(f, scale=False)
            a.wr.record(f, scale=False)

    def mesh_prefix(self):
        return f'{self.tag}_'
