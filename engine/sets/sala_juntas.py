# sala_juntas.py — sala de capacitación de maqueta (cartón pluma + plastilina) para «La capacitación» (cap. 2):
# pantalla de proyector al frente (+Y) con diapositivas animables, atril de madera con hueco trasero (escondite de
# Clawd) y ranura lateral (la pata asoma), dos filas de sillas mirando al frente, ventanales con la ciudad al
# atardecer a la derecha (+X) y al fondo (-Y). El presentador se para en 'atril' mirando a -Y (al público).
import bpy, math, random
from mathutils import Vector, Matrix
from clay import (D, hexc, link, empty, mat4, blob, sphere, superbox, box, cylinder, tube, text, clay, simple, card, node,
                  FONT_BOLD)
from rig import Joint, qe
from characters.props import mug
from sets.common import (emis, add_light, plant, office_chair, simple_chair, paper, aim, recolor_card, set_emit, Prop,
                         FONT_TITLE)

FW = 2.25            # pared del frente (pantalla)
BACK = -2.45         # ventanal del fondo
RW = 2.7             # ventanal derecho
LW = -2.7            # pared izquierda (puerta)
LECT = Vector((-0.95, 1.2))     # centro del atril
LECT_H = 0.74
SCREEN = Vector((0.55, FW - 0.06, 1.62))
SW, SH = 1.02, 0.574           # semiejes de la pantalla (16:9)
CHAIR_Y1, CHAIR_Y2 = -0.25, -1.2
SEATS = {'fila1_izq': (-0.6, CHAIR_Y1), 'fila1_der': (0.45, CHAIR_Y1), 'fila2_izq': (-0.95, CHAIR_Y2),
         'fila2_der': (0.1, CHAIR_Y2)}
EMPTY = [(-1.6, CHAIR_Y1), (1.45, CHAIR_Y1), (-1.95, CHAIR_Y2), (0.72, CHAIR_Y2), (1.5, CHAIR_Y2)]

INK, AMBER, CREAM, GREY = '#2A2420', '#D6572D', '#F4ECDC', '#8C7F72'
NIGHT = [False]      # set_params.hora == 'noche': ciudad de noche en los ventanales


def sunset_window(x0, x1, z0, z1, plane, at, seed=5, name='win', inward=Vector((0, 1, 0))):
    """ventanal con cielo de atardecer (degradado durazno → lavanda), sol bajo y siluetas de edificios.
    plane='xz' (pared en y=at) o 'yz' (pared en x=at); inward = hacia adentro de la sala"""
    rnd = random.Random(seed)
    night = NIGHT[0]

    def P(u, v, d=0.0):
        """u a lo largo de la pared, v altura, d profundidad hacia afuera"""
        out = -inward * d
        return (u + out.x, at + out.y, v) if plane == 'xz' else (at + out.x, u + out.y, v)

    def S(hu, hv, hd=0.002):
        return (hu, hd, hv) if plane == 'xz' else (hd, hu, hv)
    cu, cv = (x0 + x1) / 2, (z0 + z1) / 2
    hu, hv = (x1 - x0) / 2, (z1 - z0) / 2
    # cielo en bandas (de abajo arriba): naranja, durazno, rosa, lavanda
    bands = (['#1C3354', '#18294A', '#132240', '#0F1B36', '#0B152C'] if night else
             ['#FF9A4D', '#FFB875', '#F7A1A0', '#B58CC4', '#7C6FB0'])
    for i, c in enumerate(bands):
        v0 = z0 + (z1 - z0) * i / len(bands)
        v1 = z0 + (z1 - z0) * (i + 1) / len(bands)
        box(f'{name}_sky{i}', emis(f'cielo_{c}', c, 1.1 if night else 2.2), P(cu, (v0 + v1) / 2, 0.06), S(hu, (v1 - v0) / 2 + 0.002),
            bevel=0)
    if night:     # luna en vez de sol
        sphere(f'{name}_sun', emis('luna', '#E8EEF8', 6.0), P(x0 + 0.7 * (x1 - x0), z0 + 0.8 * (z1 - z0), 0.055), 0.07, disp=0, sub=1)
    else:         # sol bajo
        sphere(f'{name}_sun', emis('sol', '#FFE2A8', 14.0), P(x0 + 0.62 * (x1 - x0), z0 + 0.32 * (z1 - z0), 0.055), 0.11, disp=0,
               sub=1)
    # edificios en silueta (violeta al atardecer, casi negros de noche) con ventanas cálidas
    bld = simple('edificio_tarde', '#141A28' if night else '#4A3550', rough=0.9)
    bld2 = simple('edificio_tarde2', '#0A0E18' if night else '#2E2238', rough=0.9)
    lit = emis('ventana_tarde', '#FFC680', 5.0 if night else 4.0)
    u, i = x0, 0
    while u < x1:
        w = rnd.uniform(0.12, 0.3)
        top = z0 + rnd.uniform(0.15, 0.62) * (z1 - z0)
        b = min(u + w, x1)
        far = rnd.random() < 0.5
        box(f'{name}_bld{i}', bld if far else bld2, P((u + b) / 2, (z0 + top) / 2, 0.045 if far else 0.035),
            S((b - u) / 2, (top - z0) / 2), bevel=0)
        for row in range(int((top - z0) / 0.07)):
            for col in range(max(1, int((b - u) / 0.06))):
                if rnd.random() < (0.3 if night else 0.18):
                    box(f'{name}_lt{i}_{row}_{col}', lit, P(u + 0.03 + col * 0.06, z0 + 0.05 + row * 0.07, 0.03),
                        S(0.012, 0.014, 0.001), bevel=0)
        u = b + rnd.uniform(0.0, 0.04)
        i += 1
    # cancelería
    fr = simple('cancel', '#2B2A2E', rough=0.5, metal=0.3)
    n = max(2, int((x1 - x0) / 0.9))
    for k in range(n + 1):
        uu = x0 + (x1 - x0) * k / n
        box(f'{name}_mull{k}', fr, P(uu, cv, 0.0), S(0.022, hv + 0.02, 0.02), bevel=0.003)
    for vv in (z0, z1, z0 + 0.35 * (z1 - z0)):
        box(f'{name}_rail{vv:.2f}', fr, P(cu, vv, 0.0), S(hu + 0.02, 0.018, 0.02), bevel=0.003)


def pixel_clawd(prefix, parent, cx, cz, u, mat, ink, y):
    """Clawd en píxeles (rejilla del logo) centrado en (cx, cz)"""
    cells = [(x, z) for x in range(2, 14) for z in range(4) if (x, z) not in ((4, 2), (11, 2))]
    cells += [(x, 1) for x in (0, 1, 14, 15)] + [(3, -1), (5, -1), (10, -1), (12, -1)]
    for i, (x, z) in enumerate(cells):
        box(f'{prefix}_px{i}', mat, (cx + (x - 7.5) * u, y, cz + (z - 1.5) * u), (u / 2, 0.0006, u / 2), parent, bevel=0)
    for i, x in enumerate((4, 11)):
        box(f'{prefix}_eye{i}', ink, (cx + (x - 7.5) * u, y - 0.0003, cz + 0.5 * u), (u / 2, 0.0006, u / 2), parent, bevel=0)


def slides(parent, params):
    """6 diapositivas apiladas frente a la pantalla; el prop 'diapositiva' (0-5) muestra una a la vez"""
    ink = emis('slide_tinta', INK, 1.0)
    amber = emis('slide_ambar', AMBER, 1.0)
    grey = emis('slide_gris', GREY, 1.0)
    J = []

    def title(name, s, z, size, mat, par):
        o = text(name, s, mat, (0, -0.012, z), size, par, extrude=0.0, font=FONT_TITLE)
        o.data.align_x = 'CENTER'
        return o
    for k in range(6):
        j = Joint(f'slide{k}', parent.rest_world.copy())
        before = set(bpy.data.objects)
        j.attach([], 'local')
        J.append((j, before))
    built = []
    # 0: portada
    objs = [title('s0_t1', params.get('titulo1', 'Cómo soy'), 0.17, 0.15, ink, None),
            title('s0_t2', params.get('titulo2', 'tan productivo'), -0.02, 0.15, ink, None),
            title('s0_by', params.get('por', 'por Santi'), -0.27, 0.07, grey, None)]
    built.append(objs)
    # 1: MI MÉTODO + cara de Clawd grande
    o = [title('s1_t', params.get('s1_titulo', 'MI MÉTODO'), 0.36, 0.13, ink, None)]
    if params.get('s1_sub'):
        o.append(title('s1_s', params['s1_sub'], 0.22, 0.065, amber, None))
    b = set(bpy.data.objects)
    pixel_clawd('s1', None, 0.0, -0.1, 0.065, amber, ink, -0.011)
    o += [x for x in bpy.data.objects if x not in b]
    built.append(o)
    # 2: MI EQUIPO + cinco Clawds
    o = [title('s2_t', 'MI EQUIPO', 0.36, 0.13, ink, None)]
    b = set(bpy.data.objects)
    for i in range(5):
        pixel_clawd(f's2_{i}', None, -0.76 + 0.38 * i, -0.1, 0.021, amber, ink, -0.011)
    o += [x for x in bpy.data.objects if x not in b]
    built.append(o)
    # 3: la de Santi
    built.append([title('s3_t', '¡Gracias!', 0.06, 0.2, ink, None), title('s3_q', '¿Preguntas?', -0.2, 0.08, grey, None)])
    # 4: el correo ya se mandó
    o = [title('s4_t', 'Resumen de la junta', 0.3, 0.1, ink, None)]
    env = emis('slide_sobre', '#E9DCC4', 1.0)
    o.append(box('s4_env', env, (0, -0.011, -0.05), (0.26, 0.0005, 0.17), None, bevel=0))
    for sd in (-1, 1):
        o.append(box(f's4_flap{sd}', ink, (0.13 * sd, -0.0115, 0.02), (0.15, 0.0005, 0.006), None, rot=(0, D(-33 * sd), 0),
                     bevel=0))
    o.append(title('s4_s', 'ENVIADO A: TODOS', -0.36, 0.065, amber, None))
    built.append(o)
    # 5: capacitación para el jefe
    built.append([title('s5_l', 'NIVEL 1', 0.2, 0.08, amber, None), title('s5_t', '¿Qué es un prompt?', -0.02, 0.13, ink, None)])
    bg = emis('slide_crema', CREAM, 1.35)
    for k, objs in enumerate(built):
        objs.append(box(f's{k}_bg', bg, (0, -0.008, 0), (SW, 0.0005, SH), None, bevel=0))
        j = J[k][0]
        for x in objs:
            x.matrix_basis = parent.rest_world @ x.matrix_basis
        j.attach(objs, 'world')
    return [j for j, _ in J]


class SlideProp:
    """prop 'diapositiva': índice de la diapositiva visible (las demás se encogen a 0)"""

    def __init__(self, joints, default=0.0):
        self.js, self.default = joints, default
        self.scale = True

    def apply(self, v):
        k = int(round(v))
        for i, j in enumerate(self.js):
            j.scl = Vector((1, 1, 1)) * (1.0 if i == k else 1e-4)

    def record(self, f):
        for j in self.js:
            j.record(f, scale=True)


def lectern(params):
    """atril de madera con hueco trasero (lado del presentador), repisa a media altura y ranura lateral izquierda"""
    wood = card('atril_madera', '#8A5A3A', rough=0.6)
    dark = card('atril_oscuro', '#5E3B26', rough=0.7)
    x, y = LECT.x, LECT.y
    w, d = 0.27, 0.19
    box('lect_front', wood, (x, y - d, LECT_H / 2), (w, 0.02, LECT_H / 2 - 0.02), bevel=0.004)
    for sd in (-1, 1):
        box(f'lect_side{sd}', wood, (x + w * sd, y, LECT_H / 2), (0.02, d, LECT_H / 2 - 0.02), bevel=0.004)
    box('lect_base', dark, (x, y, 0.03), (w + 0.04, d + 0.04, 0.03), bevel=0.006)
    box('lect_shelf', dark, (x, y + 0.01, 0.36), (w - 0.02, d - 0.02, 0.012), bevel=0.003)
    # cubierta inclinada hacia el presentador
    box('lect_top', card('atril_cubierta', '#9B6A45', rough=0.55), (x, y, LECT_H + 0.02), (w + 0.05, d + 0.05, 0.018),
        rot=(D(-10), 0, 0), bevel=0.005)
    box('lect_lip', dark, (x, y + d + 0.04, LECT_H - 0.01), (w + 0.05, 0.012, 0.025), bevel=0.003)
    # logo de la empresa al frente
    box('lect_badge', card('atril_placa', '#2E2A26', rough=0.5), (x, y - d - 0.022, 0.56), (0.14, 0.004, 0.05), bevel=0.002)
    text('lect_badge_t', params.get('empresa', 'CAPACITACIÓN'), simple('letras_doradas', '#E2B864', rough=0.4, metal=0.6),
         (x, y - d - 0.028, 0.545), 0.028, font=FONT_BOLD, extrude=0.001)
    # micrófono de cuello de ganso
    m = clay('micro', '#1E1C1B', rough=0.4)
    tube('lect_mic', m, [(x + 0.18, y + 0.1, LECT_H + 0.03), (x + 0.2, y + 0.02, LECT_H + 0.18), (x + 0.16, y - 0.06, LECT_H + 0.24)],
         0.007, None)
    sphere('lect_mic_head', m, (x + 0.155, y - 0.075, LECT_H + 0.245), 0.018)
    # control remoto y papeles sobre la cubierta
    paper('lect_notes', (x - 0.08, y + 0.02, LECT_H + 0.045), (0.105, 0.14, 0.0015), (D(-10), 0, D(8)))
    superbox('lect_remote', clay('control', '#2B2826', rough=0.45), (x + 0.12, y + 0.06, LECT_H + 0.05), (0.018, 0.05, 0.008),
             rot=(D(-10), 0, D(-14)), e=0.3)
    # pata de Clawd que asoma por la ranura lateral izquierda (prop 'pata')
    paw = Joint('lect_paw', Matrix.Translation((x - w - 0.03, y - 0.05, 0.4)))
    paw.attach([superbox('clawd_paw', clay('clawd_pata_atril', params.get('pata_color', '#D6572D'), rough=0.62, sss=0.0, sheen=0.0,
                                           prints=1.2, spec=0.3), (-0.012, 0, 0), (0.018, 0.013, 0.016), e=0.24, disp=0.0008)],
               'local')
    return paw


def build_room(params):
    R = {}
    box('floor', card('alfombra_sala', '#6B5B57', rough=1.0, grain=3.0), (0, 0, -0.01), (2.8, 2.6, 0.01), bevel=0)
    wallm = card('pared_sala', params.get('pared', '#D9C9B2'))
    box('frontwall', wallm, (0, FW, 1.35), (2.8, 0.03, 1.35), bevel=0.002)
    box('leftwall', card('pared_sala_lat', '#CDBB9F'), (LW, 0, 1.35), (0.03, 2.6, 1.35), bevel=0)
    box('ceiling', card('techo_sala', '#E3D8C7', rough=0.95), (0, 0, 2.71), (2.8, 2.6, 0.01), bevel=0)
    box('baseboard', card('zoclo_sala', '#6E5440'), (0, FW - 0.035, 0.05), (2.8, 0.008, 0.05), bevel=0)
    # ventanales: derecha y fondo (muro bajo + vidrio)
    sunset_window(-2.4, 2.2, 0.45, 2.55, 'yz', RW, seed=5, name='winR', inward=Vector((-1, 0, 0)))
    box('sill_R', card('antepecho', '#BFAE93'), (RW, -0.1, 0.22), (0.05, 2.5, 0.22), bevel=0.003)
    sunset_window(-2.7, 2.7, 0.45, 2.55, 'xz', BACK, seed=9, name='winB', inward=Vector((0, 1, 0)))
    box('sill_B', card('antepecho', '#BFAE93'), (0, BACK, 0.22), (2.8, 0.05, 0.22), bevel=0.003)
    for i, (x, y) in enumerate(((-1.3, 0.9), (1.3, 0.9), (-1.3, -1.1), (1.3, -1.1))):
        box(f'lightpanel{i}', emis('panel_sala', '#FFF1DA', 0.4), (x, y, 2.698), (0.45, 0.25, 0.003), bevel=0)
    # pantalla de proyección con marco y caja enrollable
    box('screen_box', clay('caja_pantalla', '#E9E4DA', rough=0.5), (SCREEN.x, FW - 0.08, SCREEN.z + SH + 0.12), (SW + 0.12, 0.05, 0.04))
    box('screen_frame', clay('marco_pantalla', '#2B2826', rough=0.5), (SCREEN.x, FW - 0.045, SCREEN.z), (SW + 0.03, 0.006, SH + 0.03),
        bevel=0.002)
    # proyector en el techo
    pj = clay('proyector', '#E6E1D6', rough=0.45)
    superbox('projector', pj, (SCREEN.x, -0.6, 2.5), (0.16, 0.13, 0.05), e=0.25)
    tube('projector_pole', clay('tubo', '#9B958C'), [(SCREEN.x, -0.6, 2.55), (SCREEN.x, -0.6, 2.7)], 0.015, None)
    cylinder('projector_lens', simple('lente', '#1A1C22', rough=0.1, emit='#FFF4DE', estr=6.0), (SCREEN.x, -0.47, 2.5), 0.035, 0.02,
             None, rot=(D(90), 0, 0))
    # puerta (pared izquierda) y detalles
    wood = card('marco_madera', '#7A5135', rough=0.7)
    # la puerta gira sobre su bisagra (y=1.45) hacia adentro: prop 'puerta' en grados
    door = Joint('doorJ', Matrix.Translation((LW + 0.035, 1.45, 0.0)))
    knob = clay('perilla', '#C8A04A', rough=0.3, prints=0.3)
    door.attach([box('door', card('puerta_sala', '#9A6B48', rough=0.7), (LW + 0.035, 1.0, 1.1), (0.02, 0.45, 1.1), bevel=0.004),
                 superbox('doorknob', knob, (LW + 0.07, 0.65, 1.0), (0.03, 0.025, 0.025)),
                 superbox('doorknob_out', knob, (LW, 0.65, 1.0), (0.03, 0.025, 0.025))], 'world')
    R['puerta'] = door
    for yy in (0.53, 1.47):
        box(f'doorjamb{yy}', wood, (LW + 0.04, yy, 1.12), (0.04, 0.04, 1.12), bevel=0.003)
    # pasillo detrás de la puerta (se ve cuando se abre)
    hallm = card('pasillo', '#CDB894', rough=0.9)
    box('hall_floor', card('pasillo_piso', '#8A7A6A', rough=1.0), (LW - 0.7, 1.0, -0.01), (0.7, 1.2, 0.01), bevel=0)
    box('hall_wall', hallm, (LW - 1.2, 1.0, 1.35), (0.02, 1.2, 1.35), bevel=0)
    for sd in (-1, 1):
        box(f'hall_side{sd}', hallm, (LW - 0.7, 1.0 + 1.2 * sd, 1.35), (0.7, 0.02, 1.35), bevel=0)
    box('hall_ceil', card('pasillo_techo', '#E3D8C7'), (LW - 0.7, 1.0, 2.71), (0.7, 1.2, 0.01), bevel=0)
    # apagador junto a la puerta
    box('switch_plate', clay('apagador', '#EFE9DE', rough=0.4), (LW + 0.035, 0.38, 1.12), (0.006, 0.04, 0.06))
    box('switch_key', clay('apagador_tecla', '#E2DACB', rough=0.4), (LW + 0.043, 0.38, 1.12), (0.004, 0.016, 0.03))
    box('wb', card('pizarron', '#F1EEE6', rough=0.4), (LW + 0.035, -0.9, 1.5), (0.006, 0.6, 0.38), bevel=0.004)
    for i, (y, z, w, c) in enumerate(((-1.1, 1.65, 0.3, '#B9322A'), (-0.85, 1.52, 0.4, '#3D4B6A'), (-0.95, 1.4, 0.25, '#3D4B6A'))):
        box(f'wb_line{i}', clay(f'plumon_{c}', c, prints=0), (LW + 0.043, y, z), (0.002, w / 2, 0.007), bevel=0)
    plant('plant_front', (2.25, 1.85, 0), s=2.1)
    plant('plant_back', (-2.35, -2.05, 0), s=1.9)
    # mesita con café y agua junto al atril
    tbl = card('mesita', '#7A5135', rough=0.6)
    box('sidetable', tbl, (-1.85, 1.55, 0.35), (0.25, 0.2, 0.35), bevel=0.004)
    if not params.get('mesita_vacia'):
        mug('side_mug', mat4((-1.9, 1.5, 0.74), (0, 0, D(200))), label='', r=0.04, color='#EFE6D6')
        cylinder('side_bottle', simple('botella', '#BFE3EC', rough=0.1, trans=0.6), (-1.75, 1.58, 0.82), 0.03, 0.16, None,
                 bevel=0.004)
    for x, y in EMPTY:
        simple_chair(f'empty_{x:.1f}_{y:.1f}', (x, y, 0), D(180))
    return R


def toy_box(spec):
    """caja de juguete. Por default tipo blíster (ventana de acetato al frente, abierta arriba); con cerrada=true es una
    caja de regalo opaca con tapa (prop 'tapa' 0..1 la avienta; 2 la desaparece) y una luz adentro (prop 'caja_luz').
    spec: pos [x, y, z] (centro de la base), ancho, alto, fondo, giro, color, banda, textos {arriba, abajo, letrita}"""
    x, y, z = spec.get('pos', (-1.85, 1.62, 0.7))
    w, h, d = spec.get('ancho', 0.17), spec.get('alto', 0.25), spec.get('fondo', 0.11)
    closed = bool(spec.get('cerrada'))
    yaw = D(spec.get('giro', 0))
    rest = Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, 'Z')
    J = Joint('toyboxJ', rest)
    c1 = card('caja_juguete', spec.get('color', '#2B2E4A'), rough=0.55)
    c2 = card('caja_juguete_banda', spec.get('banda', '#E89A4A'), rough=0.5)
    inner = card('caja_juguete_dentro', spec.get('dentro', '#E9E2D2'), rough=0.7)
    gold = emis('caja_letras', spec.get('letras', '#FFF3DC'), 1.6)
    amb = emis('caja_letras_ambar', spec.get('letras2', '#FFB45A'), 1.4)
    t = 0.006
    o = []
    hb = h if closed else h * 0.58 * 2
    o.append(box('tb_back', c1, (0, d / 2, hb / 2), (w / 2, t, hb / 2), None, bevel=0.002))
    o.append(box('tb_back_in', inner, (0, d / 2 - t - 0.001, h * 0.45), (w / 2 - t, 0.0008, h * 0.45 - t), None, bevel=0))
    for sd in (-1, 1):
        o.append(box(f'tb_side{sd}', c1, (sd * w / 2, 0, h / 2), (t, d / 2, h / 2), None, bevel=0.002))
    o.append(box('tb_base', c1, (0, 0, t), (w / 2, d / 2, t), None, bevel=0.002))
    fy = -d / 2 - t - 0.001
    if closed:
        o.append(box('tb_front', c1, (0, -d / 2, h / 2), (w / 2, t, h / 2), None, bevel=0.002))
        o.append(box('tb_band', c2, (0, -d / 2 - 0.0015, h * 0.62), (w / 2 + 0.0005, t, 0.032), None, bevel=0.001))
        o.append(text('tb_t1', spec.get('arriba', 'NUEVO MODELO'), gold, (0, fy - 0.0015, h * 0.62), 0.026, None,
                      font=FONT_BOLD, extrude=0.0006))
        o.append(text('tb_t2', spec.get('abajo', 'AHORA CON RAZONAMIENTO'), amb, (0, fy, h * 0.36), 0.016, None,
                      font=FONT_BOLD, extrude=0.0004))
        o.append(text('tb_t3', spec.get('letrita', ''), gold, (0, fy, 0.03), 0.0068, None, font=FONT_BOLD, extrude=0.0003))
        for side in (-1, 1):
            o.append(text(f'tb_s{side}', '?', gold, (side * (w / 2 + t + 0.001), 0, h * 0.55), 0.06, None,
                          rot=(D(90), 0, D(90 * side)), font=FONT_BOLD, extrude=0.0006))
    else:
        o.append(box('tb_top', c2, (0, -d / 2, h - 0.03), (w / 2, t, 0.03), None, bevel=0.002))
        o.append(box('tb_bot', c1, (0, -d / 2, 0.035), (w / 2, t, 0.035), None, bevel=0.002))
        o.append(box('tb_win', simple('acetato', '#E8F0F4', rough=0.05, alpha=0.12), (0, -d / 2 + 0.002, h * 0.5),
                     (w / 2 - t, 0.0006, h * 0.5 - 0.065), None, bevel=0))
        o.append(box('tb_hang', c1, (0, d / 2, h * 1.18), (0.035, t, 0.02), None, bevel=0.003))
        o.append(text('tb_t1', spec.get('arriba', 'NUEVO MODELO'), gold, (0, fy, h - 0.03), 0.021, None,
                      font=FONT_BOLD, extrude=0.0006))
        o.append(text('tb_t2', spec.get('abajo', 'AHORA CON RAZONAMIENTO'), amb, (0, fy, 0.047), 0.0115, None,
                      font=FONT_BOLD, extrude=0.0004))
        o.append(text('tb_t3', spec.get('letrita', '*AGI (aplican términos y condiciones)'), gold, (0, fy, 0.021),
                      0.0062, None, font=FONT_BOLD, extrude=0.0003))
    for x_ in o:
        x_.matrix_basis = J.rest_world @ x_.matrix_basis
    J.attach(o, 'world')
    lid = glow = None
    if closed:
        lid = Joint('toybox_lid', rest @ Matrix.Translation((0, 0, h)), J)
        lid.attach([box('tb_lid', c2, (0, 0, 0.008), (w / 2 + 0.008, d / 2 + 0.008, 0.008), None, bevel=0.002),
                    box('tb_lid_rim', c2, (0, -d / 2 - 0.006, -0.012), (w / 2 + 0.008, 0.003, 0.02), None, bevel=0.001)],
                   'local')
        glow = add_light('caja_glow', 'POINT', tuple(rest @ Vector((0, -d / 2 - 0.03, h + 0.02))), (0, 0, 0), 0.0,
                         (0.55, 0.65, 1.0), 0.04)
    return J, (x, y, z), (w, h, d), yaw, lid, glow


class ShakeProp:
    """prop de temblor: amplitud (grados) de un sacudón rápido de la articulación"""

    def __init__(self, joint, default=0.0):
        self.j, self.default, self.scale, self.v = joint, default, False, 0.0

    def apply(self, v):
        self.v = v

    def record(self, f):
        a = self.v
        self.j.rot = qe(D(a * 0.6 * math.sin(f * 2.3)), D(a * math.sin(f * 1.7 + 1.0)), D(a * 0.5 * math.sin(f * 3.1)))
        self.j.record(f, scale=False)


class LidProp:
    """tapa: 0 cerrada, 1 salió volando (arriba y girada), >=1.5 desaparece"""

    def __init__(self, joint, default=0.0):
        self.j, self.default, self.scale = joint, default, True

    def apply(self, v):
        k = min(1.0, max(0.0, v))
        self.j.loc = Vector((0.02 * k, 0.04 * k, 0.32 * k))
        self.j.rot = qe(D(-75 * k), D(25 * k), 0)
        self.j.scl = Vector((1, 1, 1)) * (1e-4 if v >= 1.5 else 1.0)

    def record(self, f):
        self.j.record(f, scale=True)


class LightValueProp:
    """luz con energía = valor (W)"""

    def __init__(self, light, default=0.0):
        self.L, self.default, self.scale, self.v = light, default, False, default

    def apply(self, v):
        self.v = v

    def record(self, f):
        from rig import REC
        REC.key(self.L.data, 'energy', 0, f, max(0.0, self.v), 'LINEAR')


class LightsProp:
    """prop 'luces' 0..1: el techo de la sala (paneles emisivos + luces de área) se apaga/prende"""

    def __init__(self, lights, mat, on):
        self.L, self.mat, self.on = lights, mat, on
        self.default = 1.0
        self.scale = False
        self.v = 1.0

    def apply(self, v):
        self.v = max(0.0, min(1.0, v))

    def record(self, f):
        from rig import REC
        for L, e in self.L:
            REC.key(L.data, 'energy', 0, f, e * self.v, 'LINEAR')
        if self.mat is not None:
            for n in self.mat.node_tree.nodes:
                if n.type == 'EMISSION':
                    REC.key(self.mat.node_tree, f'nodes["{n.name}"].inputs[1].default_value', 0, f,
                            0.05 + (self.on - 0.05) * self.v, 'LINEAR')


def build(ctx):
    params = ctx.get('params', {})
    NIGHT[0] = params.get('hora') == 'noche'
    R = build_room(params)
    paw = lectern(params)
    occupied = ctx.get('occupied', set())
    for n, (x, y) in SEATS.items():
        if n not in occupied:
            simple_chair(f'{n}_silla', (x, y, 0), D(180))
    scr = Joint('screenJ', Matrix.Translation(SCREEN))
    sj = slides(scr, params)

    def _scale(j, v):
        j.scl = Vector((1, 1, 1)) * max(1e-4, v)
    props = {'diapositiva': SlideProp(sj, 0.0), 'pata': Prop(paw, _scale, scale=True, default=0.0)}

    def _door(j, v):
        j.rot = qe(0, 0, D(v))
    props['puerta'] = Prop(R['puerta'], _door, scale=False, default=0.0)
    box_anchors = {}
    if params.get('caja_juguete'):
        tj, (bx, by, bz), (bw, bh, bd), byaw, lid, glow = toy_box(params['caja_juguete'])
        props['caja'] = ShakeProp(tj, 0.0)
        if lid is not None:
            props['tapa'] = LidProp(lid, 0.0)
            props['caja_luz'] = LightValueProp(glow, 0.0)
        fwd = Vector((math.sin(byaw), -math.cos(byaw), 0))
        box_anchors = {'caja_dentro': ((bx, by, bz + 0.012), None), 'caja_borde': ((bx, by, bz + bh + 0.01), None),
                       'caja_frente': (tuple(Vector((bx, by, bz)) + fwd * (bd / 2 + 0.09)), None)}
    seats = {n: dict(pos=(x, y, 0), yaw=180, chair=office_chair) for n, (x, y) in SEATS.items()}
    A = lambda p, yaw=None, **kw: dict(pos=p, yaw=yaw, **kw)
    x, y = LECT.x, LECT.y
    anchors = {
        # presentador
        'atril': A((x, y + 0.42, 0.0), 0), 'junto_pantalla': A((-0.15, 1.55, 0.0), 20), 'frente_jefe': A((-0.45, 0.62, 0.0), 0),
        # escondites de Clawd
        'atril_dentro': A((x, y + 0.04, 0.372)), 'atril_asoma': A((x, y + 0.12, 0.62)), 'atril_arriba': A((x, y + 0.02, LECT_H + 0.04)),
        'atril_piso': A((x + 0.05, y + 0.38, 0.0)), 'silla_junto_lucia': A((0.72, CHAIR_Y2 - 0.03, 0.47)), 'mesita': A((-1.85, 1.62, 0.7)),
        # puntos para mirar
        'pantalla': A(tuple(SCREEN)), 'atril_hueco': A((x, y + 0.05, 0.45)),
        # puerta: afuera (pasillo) y recién entrando
        'pasillo': A((LW - 0.75, 1.0, 0.0), 90), 'entrando': A((LW + 0.55, 0.95, 0.0), 90),
        'puerta': A((LW + 0.2, 1.0, 1.55)),
    }
    for k, (p_, yw) in box_anchors.items():
        anchors[k] = A(p_, yw)
    # techo: luces de área encima de los paneles (prop 'luces'; de día/atardecer quedan como estaban)
    ceil = []
    if NIGHT[0]:
        for i, (cx, cy) in enumerate(((-1.3, 0.9), (1.3, 0.9), (-1.3, -1.1), (1.3, -1.1))):
            L = add_light(f'sala_techo{i}', 'AREA', (cx, cy, 2.66), (0, 0, 0), 1.0, (1.0, 0.92, 0.8), 0.9)
            aim(L, (cx, cy, 0.0))
            ceil.append((L, float(params.get('luz_techo', 110.0))))
        props['luces'] = LightsProp(ceil, bpy.data.materials.get('panel_sala'), 2.2)
    probes = {'pantalla': SCREEN + Vector((0, -0.1, 0)), 'atril': Vector((x, y, LECT_H)), 'atril_hueco': Vector((x, y + 0.05, 0.45)),
              'sala': Vector((0, 0.2, 0.9))}
    return dict(seats=seats, anchors=anchors, props=props, probes=probes,
                looks={'atardecer': sunset, 'noche': night if NIGHT[0] else sunset, 'dia': sunset}, ambiente='oficina', publico=Vector((0.0, -1.0, 0.0)))


def sunset(SC, ctx):
    """atardecer: sol bajo y cálido entrando por el ventanal derecho (sombras largas de la cancelería),
    cielo durazno-lavanda, techo apagado, pantalla del proyector como luz práctica fría-crema"""
    lk = ctx.get('look', {})
    sun = bpy.data.lights.new('sun_tarde', 'SUN')
    sun.energy = float(lk.get('sol', 4.2))
    sun.color = (1.0, 0.62, 0.34)
    sun.angle = D(2.5)
    so = bpy.data.objects.new('sun_tarde', sun)
    link(so)
    so.rotation_euler = (D(78), 0, D(-118))
    for i, (pos, tgt) in enumerate((((RW - 0.2, 0.0, 1.5), (0, 0, 0.8)), ((0.0, BACK + 0.2, 1.5), (0, 0, 0.8)))):
        L = add_light(f'tarde_win{i}', 'AREA', pos, (0, 0, 0), float(lk.get('ventana', 160.0)), (1.0, 0.72, 0.5), 2.4)
        aim(L, tgt)
    sc = add_light('pantalla_glow', 'AREA', tuple(SCREEN + Vector((0, -0.25, 0))), (0, 0, 0), 60, (1.0, 0.95, 0.86), 1.6)
    aim(sc, (SCREEN.x, 0.0, 1.0))
    beam = add_light('proyector_L', 'SPOT', (SCREEN.x, -0.45, 2.5), (0, 0, 0), 120, (1.0, 0.96, 0.9), 0.04, spot=(D(36), 0.3))
    aim(beam, tuple(SCREEN))
    for o in bpy.data.objects:
        if o.name.startswith('ceil_L'):
            o.data.energy = 0.0
    return {'sun_tarde': 0.25, 'proyector_L': 0.6, 'tarde_win0': 0.2, 'tarde_win1': 0.15}


def night(SC, ctx):
    """sala de noche: techo apagado (prop 'luces'), proyector apagado, luna fría por los ventanales,
    pasillo cálido detrás de la puerta (Santi entra a contraluz)"""
    lk = ctx.get('look', {})
    for i, (pos, tgt) in enumerate((((RW - 0.2, 0.0, 1.6), (0, 0, 0.6)), ((0.0, BACK + 0.2, 1.6), (0, 0, 0.6)))):
        L = add_light(f'luna_win{i}', 'AREA', pos, (0, 0, 0), float(lk.get('ventana', 70.0)), (0.55, 0.68, 1.0), 2.4)
        aim(L, tgt)
    hall = add_light('n_hall', 'AREA', (LW - 0.7, 1.0, 2.5), (0, 0, 0), float(lk.get('pasillo', 160.0)), (1.0, 0.82, 0.6), 0.8)
    aim(hall, (LW - 0.7, 1.0, 0.0))
    for o in bpy.data.objects:
        if o.name.startswith('ceil_L'):
            o.data.energy = 0.0
    set_emit('lente', '#1A1C22', 0.0)
    return {'luna_win0': 0.25, 'luna_win1': 0.2, 'n_hall': 0.3}
