# office_night.py — la oficina de «A escondidas» (maqueta de cartón pluma + plastilina) con su look de noche.
# Asiento principal en el origen mirando a -Y; escritorio delante; puerta del despacho del jefe al fondo (+Y).
import bpy, math, random
from mathutils import Vector, Matrix, Euler
from clay import (D, hexc, link, empty, mat4, blob, sphere, superbox, box, cylinder, tube, text, clay, simple, card, node,
                  FONT_BOLD)
from rig import Joint, child_joint, qe
from characters.props import mug
from sets.common import (foam_wall, emis, add_light, desk_lamp, plant, code_screen, monitor, office_chair, simple_chair,
                         paper, desk, aim, recolor_card, set_emit, city_window, Prop, FONT_TITLE)

WY = 3.6          # pared del fondo
DOOR_X = -0.85    # centro de la puerta del jefe
SANTI_DESK = Vector((0.05, -0.98))
DESK_Z = 0.752
COWORKER_SEATS = {'cubiculo_1': ((-1.85, 0.25), 1), 'cubiculo_2': ((1.95, 0.35), 2), 'cubiculo_3': ((-2.0, 2.15), 3),
                  'cubiculo_4': ((1.9, 2.25), 4)}


def slide(parent, title=('Mi', 'presentación'), by='', pixel_clawd=True):
    """diapositiva con título de 2 renglones y la cara pixel de Clawd (va delante de la pantalla principal)"""
    w, h = 0.235, 0.145
    box('slide_bg', emis('slide_crema', '#F4ECDC', 1.25), (0, -0.004, 0), (w, 0.001, h), parent, bevel=0)
    ink = emis('slide_tinta', '#2A2420', 1.0)
    amber = emis('slide_ambar', '#D6572D', 0.95)
    t1 = text('slide_t1', title[0], ink, (0, -0.0058, 0.092), 0.034, parent, extrude=0.0, font=FONT_TITLE)
    t2 = text('slide_t2', title[1] if len(title) > 1 else '', ink, (0, -0.0058, 0.056), 0.034, parent, extrude=0.0, font=FONT_TITLE)
    # Clawd en píxeles (mismo grid del ref), centrado abajo
    u = 0.0105
    cells = []
    for cx in range(2, 14):
        for cz in range(4):
            if (cx, cz) in ((4, 2), (11, 2)):
                continue
            cells.append((cx, cz))
    for cx in (0, 1, 14, 15):
        cells.append((cx, 1))
    legs = [(3, -1), (5, -1), (10, -1), (12, -1)]
    for i, (cx, cz) in enumerate(cells + legs):
        box(f'slide_px{i}', amber, ((cx - 7.5) * u, -0.0055, -0.035 + (cz - 1.5) * u * 1.0 - 0.0), (u / 2, 0.0006, u / 2),
            parent, bevel=0)
    for i, cx in enumerate((4, 11)):
        box(f'slide_eye{i}', ink, ((cx - 7.5) * u, -0.0058, -0.035 + (2 - 1.5) * u), (u / 2, 0.0006, u / 2), parent, bevel=0)
    text('slide_by', by, emis('slide_gris', '#8C7F72', 1.0), (0.0, -0.0058, -0.115), 0.016, parent, extrude=0.0,
         font=FONT_TITLE)
    for o in (t1, t2):
        o.data.align_x = 'CENTER'


class StatesProp:
    """prop de estados: índice del estado visible (los demás se encogen a 0)"""

    def __init__(self, joints, default=0.0):
        self.js, self.default, self.scale = joints, default, True

    def apply(self, v):
        k = int(round(v))
        for i, j in enumerate(self.js):
            j.scl = Vector((1, 1, 1)) * (1.0 if i == k else 1e-4)

    def record(self, f):
        for j in self.js:
            j.record(f, scale=True)


def chat_screen(rest, prompt, greeting='¿En qué te ayudo hoy?'):
    """chat en el monitor: el prompt se escribe letra por letra (estados 0..N) y el estado N+1 es «enviado»
    (burbuja del usuario arriba + «Pensando…»). Devuelve las articulaciones de cada estado."""
    w, h = 0.235, 0.145
    ink = emis('chat_tinta', '#2A2420', 1.0)
    grey = emis('chat_gris', '#8C7F72', 1.0)
    amber = emis('chat_ambar', '#D6572D', 1.0)
    base = Joint('chat_base', rest)
    o = [box('chat_bg', emis('slide_crema', '#F4ECDC', 1.25), (0, -0.004, 0), (w, 0.001, h), None, bevel=0)]
    base.attach(o, 'local')
    J = []

    def state(k):
        j = Joint(f'chat_s{k}', rest)
        J.append(j)
        return j

    def inputbox(tag, txt, cursor):
        objs = [box(f'{tag}_box', emis('chat_caja', '#FFFDF8', 1.35), (0, -0.0052, -0.045), (0.2, 0.0006, 0.032), None, bevel=0),
                box(f'{tag}_borde', emis('chat_borde', '#CBBFAE', 1.0), (0, -0.0049, -0.045), (0.203, 0.0006, 0.035), None, bevel=0),
                box(f'{tag}_send', amber, (0.175, -0.0058, -0.045), (0.014, 0.0005, 0.014), None, bevel=0)]
        t = txt + ('|' if cursor else '')
        if t:
            objs.append(text(f'{tag}_t', t, ink, (-0.12, -0.0062, -0.05), 0.034, None, extrude=0.0, align='LEFT', font=FONT_TITLE))
        return objs
    n = len(prompt)
    for k in range(n + 1):
        j = state(k)
        objs = [text(f'chat_g{k}', greeting, ink, (0, -0.006, 0.055), 0.026, None, extrude=0.0, font=FONT_TITLE)]
        objs += inputbox(f'chat_in{k}', prompt[:k], True)
        j.attach(objs, 'local')
    j = state(n + 1)
    objs = [box('chat_bubble', emis('chat_burbuja', '#E6DACA', 1.2), (0.09, -0.0052, 0.085), (0.11, 0.0006, 0.024), None, bevel=0),
            text('chat_bubble_t', prompt, ink, (0.09, -0.0062, 0.082), 0.026, None, extrude=0.0, font=FONT_TITLE),
            text('chat_think', 'Pensando…', grey, (-0.16, -0.0062, 0.02), 0.02, None, extrude=0.0, align='LEFT', font=FONT_TITLE),
            box('chat_spark', amber, (-0.19, -0.0058, 0.024), (0.009, 0.0005, 0.009), None, rot=(0, D(45), 0), bevel=0)]
    objs += inputbox('chat_inS', '', False)
    j.attach(objs, 'local')
    return J


def build_office(params=None):
    params = params or {}
    R = {}
    # piso alfombra + paredes de cartón pluma
    box('floor', card('alfombra', '#6E5D4E', rough=1.0, grain=3.0), (0, 1.0, -0.01), (4.2, 4.8, 0.01), bevel=0)
    wallm = card('pared', '#D3C4A8')
    box('backwall_L', wallm, (-2.75, WY, 1.35), (1.45, 0.03, 1.35), bevel=0.002)
    box('backwall_R', wallm, (1.95, WY, 1.35), (2.35, 0.03, 1.35), bevel=0.002)
    box('backwall_T', wallm, (DOOR_X, WY, 2.47), (0.46, 0.03, 0.23), bevel=0.002)
    box('wall_left', card('pared_lateral', '#CBB99C'), (-3.3, 0.2, 1.35), (0.03, 3.4, 1.35), bevel=0)
    box('wall_right', card('pared_lateral', '#CBB99C'), (3.3, 0.2, 1.35), (0.03, 3.4, 1.35), bevel=0)
    box('baseboard', card('zoclo', '#8A6A4E'), (0.4, WY - 0.035, 0.05), (3.9, 0.008, 0.05), bevel=0)
    # techo con paneles de luz
    box('ceiling', card('techo', '#E6DCCB', rough=0.95), (0, 0.5, 2.71), (3.4, 3.2, 0.01), bevel=0)
    pm = emis('panel_luz', '#FFF1DA', 2.2)
    for i, (x, y) in enumerate(((-1.4, -0.6), (1.4, -0.6), (-1.4, 1.8), (1.4, 1.8), (0.0, 0.6))):
        box(f'lightpanel{i}', pm, (x, y, 2.698), (0.45, 0.25, 0.003), bevel=0)
        add_light(f'ceil_L{i}', 'AREA', (x, y, 2.66), (0, 0, 0), 70, (1.0, 0.92, 0.80), 0.8)
    # puerta del despacho del jefe
    wood = card('marco_madera', '#7A5135', rough=0.7)
    for x in (DOOR_X - 0.48, DOOR_X + 0.48):
        box(f'doorjamb{x:.2f}', wood, (x, WY - 0.02, 1.12), (0.04, 0.06, 1.12), bevel=0.003)
    box('doorhead', wood, (DOOR_X, WY - 0.02, 2.26), (0.52, 0.06, 0.04), bevel=0.003)
    door = Joint('door_pivot', Matrix.Translation((DOOR_X + 0.44, WY + 0.02, 0)))
    dp = [box('door', card('puerta', '#9A6B48', rough=0.7), (-0.44, 0.0, 1.11), (0.43, 0.025, 1.1), None, bevel=0.004),
          superbox('doorknob', clay('perilla', '#C8A04A', rough=0.3, prints=0.3), (-0.8, -0.045, 1.0), (0.025, 0.03, 0.025)),
          superbox('doorknob2', clay('perilla', '#C8A04A', rough=0.3, prints=0.3), (-0.8, 0.045, 1.0), (0.025, 0.03, 0.025))]
    for o in dp:
        o.matrix_basis = door.rest_world @ o.matrix_basis
    door.attach(dp, 'world')
    R['door'] = door
    box('plaque', card('placa', '#2E2A26', rough=0.5), (DOOR_X, WY - 0.04, 2.42), (0.2, 0.004, 0.05), bevel=0.002)
    text('plaque_txt', 'DIRECCIÓN', simple('letras_doradas', '#E2B864', rough=0.4, metal=0.6),
         (DOOR_X, WY - 0.046, 2.42), 0.055, font=FONT_BOLD, extrude=0.001)
    # despacho del jefe
    OY = WY + 1.8
    box('office_back', card('pared_jefe', '#B9874F'), (DOOR_X, OY, 1.35), (1.6, 0.03, 1.35), bevel=0)
    box('office_sideL', card('pared_jefe', '#B9874F'), (DOOR_X - 1.6, WY + 0.9, 1.35), (0.03, 0.9, 1.35), bevel=0)
    box('office_sideR', card('pared_jefe', '#B9874F'), (DOOR_X + 1.6, WY + 0.9, 1.35), (0.03, 0.9, 1.35), bevel=0)
    box('office_floor', card('piso_jefe', '#5A3E2C'), (DOOR_X, WY + 0.9, -0.005), (1.6, 0.9, 0.01), bevel=0)
    box('office_ceiling', card('techo', '#E6DCCB'), (DOOR_X, WY + 0.9, 2.71), (1.6, 0.9, 0.01), bevel=0)
    bd = Vector((DOOR_X - 0.1, WY + 1.05))
    desk('bossdesk', bd, w=0.75, d=0.35, color='#6E4630')
    monitor('bossmon', (bd.x - 0.4, bd.y - 0.02, 0.752), D(165), seed=9)
    box('office_shelf', wood, (DOOR_X - 0.6, OY - 0.1, 1.35), (0.45, 0.08, 0.02))
    for i in range(7):
        superbox(f'book{i}', clay(f'libro{i % 3}', ('#7D2E28', '#3E4A3A', '#C08A3A')[i % 3]),
                 (DOOR_X - 0.95 + i * 0.065, OY - 0.1, 1.47), (0.024, 0.07, 0.1 + 0.012 * (i % 2)), e=0.35)
    trophy = clay('trofeo', '#D4A84A', rough=0.3, spec=0.8)
    cylinder('trophy_base', clay('trofeo_base', '#3A2A20'), (DOOR_X - 0.2, OY - 0.1, 1.39), 0.04, 0.04, None)
    blob('trophy_cup', trophy, mat4((DOOR_X - 0.2, OY - 0.1, 1.47), (0, 0, 0), (0.045, 0.045, 0.06)), None,
         cut=((0, 0, -0.6), (0, 0, 1)))
    box('boss_poster', card('poster_jefe', '#2F4A3F'), (DOOR_X + 0.75, OY - 0.035, 1.55), (0.3, 0.004, 0.4), bevel=0.002)
    text('boss_poster_txt', 'LIDERAZGO', simple('letras_crema', '#F6EBD6', rough=0.6), (DOOR_X + 0.75, OY - 0.04, 1.62),
         0.075, font=FONT_BOLD, extrude=0.001)
    add_light('office_key', 'AREA', (DOOR_X, WY + 0.9, 2.5), (0, 0, 0), 140, (1.0, 0.82, 0.6), 1.2)
    plant('plant_boss', (DOOR_X + 1.2, OY - 0.3, 0), s=1.6)
    simple_chair('bosschair', (bd.x, bd.y + 0.55, 0), D(180 + 180))
    # pared del fondo: reloj, póster
    clk = empty('clock', (1.15, WY - 0.04, 2.0), (D(90), 0, 0))
    cylinder('clock_body', clay('reloj', '#E9DFCB', rough=0.5), (0, 0, 0), 0.16, 0.03, clk, sub=1, disp=0.002)
    tube('clock_rim', clay('reloj_borde', '#2F2B28'), [(0.16 * math.cos(a), 0.16 * math.sin(a), 0.015)
                                                       for a in [i * math.pi / 6 for i in range(12)]], 0.014, clk, closed=True)
    tube('clock_h', clay('reloj_borde', '#2F2B28'), [(0, 0, 0.02), (0.06, 0.06, 0.02)], 0.007, clk)
    tube('clock_m', clay('reloj_borde', '#2F2B28'), [(0, 0, 0.02), (-0.02, 0.12, 0.02)], 0.005, clk)
    box('poster', card('poster', '#E9873F'), (2.2, WY - 0.035, 1.6), (0.3, 0.004, 0.4), bevel=0.002)
    text('poster_txt', 'SINERGIA', simple('letras_crema', '#F6EBD6', rough=0.6), (2.2, WY - 0.04, 1.7), 0.09,
         font=FONT_BOLD, extrude=0.001)
    sphere('poster_dot', clay('poster_sol', '#F6EBD6'), (2.2, WY - 0.04, 1.45), (0.1, 0.006, 0.1), disp=0)
    box('whiteboard', card('pizarron', '#F1EEE6', rough=0.4), (0.2, WY - 0.03, 1.55), (0.45, 0.006, 0.3), bevel=0.004)
    for i, (x, z, w, c) in enumerate(((0.0, 1.7, 0.25, '#B9322A'), (0.1, 1.6, 0.3, '#3D4B6A'), (0.05, 1.5, 0.18, '#3D4B6A'),
                                       (0.35, 1.45, 0.12, '#B9322A'))):
        box(f'wb_line{i}', clay(f'plumon_{c}', c, prints=0), (x, WY - 0.038, z), (w / 2, 0.002, 0.006), bevel=0)
    plant('plant_bg', (2.9, 3.2, 0), s=1.7)
    plant('plant_bg2', (-2.95, 3.2, 0), s=1.5)
    # bebedero / archivero al fondo
    superbox('cabinet', clay('archivero', '#8E8B80', rough=0.5), (-2.9, 1.0, 0.5), (0.22, 0.3, 0.5), e=0.2, disp=0.001)
    for i in range(3):
        box(f'cab_handle{i}', clay('jaladera', '#3A3633'), (-2.67, 1.0, 0.25 + 0.3 * i), (0.01, 0.06, 0.012), bevel=0.003)
    # ---- escritorio principal
    c = SANTI_DESK
    desk('sdesk', c, w=0.72, d=0.36, legs=True)
    foam_wall('cub_main', (c.x + 0.83, c.y + 0.3, 0.62), (0.62, 0.02, 0.62), '#A7A08D', rot=(0, 0, D(90)))
    for i, (z, y, col) in enumerate(((1.02, -0.75, '#F2C94C'), (0.94, -0.6, '#F29E5A'), (1.07, -0.45, '#F2C94C'),
                                      (0.9, -0.3, '#F2C94C'))):
        paper(f'postit{i}', (c.x + 0.806, y + c.y + 0.78, z), (0.002, 0.035, 0.035), (D(random.uniform(-8, 8)), 0, 0), color=col)
    mpos = Vector((c.x + 0.24, c.y - 0.16))
    yaw = math.atan2(-mpos.x, mpos.y)
    smon, sscr = monitor('smonitor', (mpos.x, mpos.y, 0.752), yaw, seed=3)
    R['monitor'] = smon
    R['scr_world'] = (Matrix.Translation((mpos.x, mpos.y, 0.752)) @ Matrix.Rotation(yaw, 4, 'Z')
                      @ Matrix.Translation((0, -0.027, 0.305)))
    superbox('keyboard', clay('teclado', '#D8D0C0', rough=0.55), (c.x - 0.08, c.y + 0.12, 0.765), (0.19, 0.06, 0.012),
             rot=(0, 0, D(4)), disp=0.001)
    for i in range(3):
        for j in range(10):
            superbox(f'key{i}_{j}', clay('tecla', '#EFE8DA', rough=0.5, prints=0.3),
                     (c.x - 0.08 - 0.16 + j * 0.035, c.y + 0.12 - 0.035 + i * 0.033, 0.779), (0.013, 0.012, 0.004),
                     rot=(0, 0, D(4)), disp=0, e=0.35)
    mug('deskmug', mat4((c.x - 0.45, c.y + 0.05, 0.812), (0, 0, D(200))), label=params.get('taza', 'LUN'))
    for i in range(4):
        paper(f'sheet{i}', (c.x + 0.48, c.y + 0.02 + 0.003 * i, 0.755 + 0.003 * i), (0.105, 0.15, 0.0015),
              (0, 0, D(-12 + 6 * i)))
    desk_lamp('lamp', (c.x + 0.62, c.y - 0.22, 0.752), D(200), light=28)
    # cajón (Clawd se esconde aquí cuando entra el jefe); se anima en Y desde scene.py
    wood = card('escritorio', '#B98B5E', rough=0.6)
    dr = Joint('drawer', Matrix.Identity(4))
    dx, dy0 = -0.38, c.y + 0.36            # frente del cajón al ras del borde del escritorio (lado del asiento principal)
    parts = [box('drawer_front', wood, (dx, dy0 + 0.005, 0.615), (0.215, 0.01, 0.088), bevel=0.003),
             box('drawer_bottom', wood, (dx, dy0 - 0.17, 0.532), (0.2, 0.17, 0.006), bevel=0.002),
             box('drawer_back', wood, (dx, dy0 - 0.335, 0.6), (0.2, 0.006, 0.07), bevel=0.002),
             superbox('drawer_knob', clay('perilla', '#C8A04A', rough=0.3, prints=0.3), (dx, dy0 + 0.025, 0.62),
                      (0.035, 0.012, 0.012), e=0.4)]
    for sx in (-1, 1):
        parts.append(box(f'drawer_side{sx}', wood, (dx + 0.2 * sx, dy0 - 0.17, 0.6), (0.006, 0.17, 0.07), bevel=0.002))
    dr.attach(parts, 'world')
    R['drawer'] = dr
    paw = Joint('drawer_paw', Matrix.Translation((dx + 0.07, dy0 + 0.012, 0.705)), dr)
    paw.attach([superbox('clawd_paw', clay('clawd_pata_cajon', params.get('pata_color', '#D6572D'), rough=0.62, sss=0.0, sheen=0.0, prints=1.2, spec=0.3),
                         (0, 0.012, -0.012), (0.013, 0.018, 0.016), e=0.24, disp=0.0008)], 'local')
    R['paw'] = paw
    plant('plant_desk', (c.x - 0.58, c.y - 0.24, 0.752), s=0.6)
    cylinder('pencilcup', clay('lapicero', '#3D4B6A'), (c.x - 0.3, c.y - 0.22, 0.8), 0.035, 0.1, None, sub=1)
    for i, col in enumerate(('#E8A35C', '#B9322A', '#F2C94C')):
        tube(f'pencil{i}', clay(f'lapiz_{col}', col, prints=0), [(c.x - 0.3 + 0.01 * (i - 1), c.y - 0.22, 0.8),
                                                                 (c.x - 0.3 + 0.03 * (i - 1), c.y - 0.22 + 0.01 * i, 0.92)],
             0.006, None, ring=8, per=2)
    return R


def build_coworker_desks(specs):
    """specs: lista de (tag, centro silla (x,y), yaw). Escritorio delante (−Y local)."""
    for tag, (x, y), yaw, seed in specs:
        c = Vector((x, y - 0.72))
        desk(f'{tag}_desk', c, w=0.6, d=0.33, modesty=True, color='#B08458')
        monitor(f'{tag}_mon', (c.x + 0.1, c.y - 0.12, 0.752), D(180), seed=seed)
        mug(f'{tag}_mug', mat4((c.x - 0.35, c.y + 0.05, 0.812), (0, 0, D(30 * seed))), label=('#1', 'HOLA', 'CAFÉ', 'LUN')[seed % 4])
        for i in range(2):
            paper(f'{tag}_sheet{i}', (c.x - 0.15, c.y + 0.1 + 0.004 * i, 0.755 + 0.003 * i), (0.105, 0.15, 0.0015),
                  (0, 0, D(-8 + 12 * i)))
        foam_wall(f'{tag}_cub', (x + (0.68 if x > 0 else -0.68), y - 0.6, 0.6), (0.5, 0.02, 0.6), '#A7A08D',
                  rot=(0, 0, D(90)))


def build(ctx):
    params = ctx.get('params', {})
    R = build_office(params)
    occupied = ctx.get('occupied', set())
    build_coworker_desks([(n, p, 0.0, seed) for n, (p, seed) in COWORKER_SEATS.items()])
    for n, ((x, y), seed) in COWORKER_SEATS.items():
        simple_chair(f'{n}_silla', (x, y, 0), 0.0)
    # placas de escritorio opcionales: set_params.placas = {"cubiculo_2": "DIRECTORA"}
    for n, label in params.get('placas', {}).items():
        (x, y), _ = COWORKER_SEATS[n]
        c = Vector((x, y - 0.72))
        box(f'{n}_placa', card(f'{n}_placa_m', '#2E2A26', rough=0.5), (c.x - 0.12, c.y - 0.14, DESK_Z + 0.03),
            (0.11, 0.012, 0.03), rot=(D(-18), 0, 0), bevel=0.002)
        text(f'{n}_placa_t', label, simple(f'{n}_placa_letras', '#E2B864', rough=0.4, metal=0.6),
             (c.x - 0.12, c.y - 0.155, DESK_Z + 0.03), 0.024, rot=(D(72), 0, 0), font=FONT_BOLD, extrude=0.001)
    if 'principal' not in occupied:
        office_chair(Matrix.Identity(4))
    # diapositiva en el monitor principal (prop 'diapositiva' 0/1)
    slideJ = Joint('slideJ', R['scr_world'])
    before = set(bpy.data.objects)
    slide(None, tuple(params.get('diapositiva', ['Mi', 'presentación'])), params.get('diapositiva_por', ''))
    slideJ.attach([o for o in bpy.data.objects if o not in before], 'local')

    def _scale(j, v):
        j.scl = Vector((1, 1, 1)) * max(1e-4, v)
    chat = None
    if params.get('chat'):          # chat en el monitor (prop 'tecleo': letras escritas; len+1 = enviado)
        chat = chat_screen(R['scr_world'] @ Matrix.Translation((0, -0.002, 0)), params['chat'].get('prompt', ''),
                           params['chat'].get('saludo', '¿En qué te ayudo hoy?'))

    def _door(j, v):
        j.rot = qe(0, 0, D(v))

    def _drawer(j, v):
        j.loc = Vector((0, v, 0))
    props = {'puerta': Prop(R['door'], _door, default=-72.0), 'cajon': Prop(R['drawer'], _drawer),
             'pata': Prop(R['paw'], _scale, scale=True), 'diapositiva': Prop(slideJ, _scale, scale=True)}
    if chat:
        props['tecleo'] = StatesProp(chat, 0.0)
    seats = {'principal': dict(pos=(0, 0, 0), yaw=0, chair=office_chair)}
    for n, ((x, y), seed) in COWORKER_SEATS.items():
        seats[n] = dict(pos=(x, y, 0), yaw=0, chair=None)
    A = lambda p, yaw=None, **kw: dict(pos=p, yaw=yaw, **kw)
    anchors = {
        # escondites de mascota alrededor del escritorio principal
        'bajo_escritorio': A((0.0, -1.02, 0.0)), 'asomado': A((0.0, -0.74, 0.0)), 'lado_escritorio': A((-0.8, -0.86, 0.0)),
        'escritorio': A((0.02, -1.02, DESK_Z)), 'pantalla': A((-0.15, -1.08, DESK_Z)), 'orilla': A((0.6, -0.92, DESK_Z)),
        'cubiculo_alto': A((0.875, -0.36, 1.246)), 'taza': A((-0.15, -0.99, DESK_Z)),
        'cajon': A((-0.38, -0.71, 0.545), sigue='cajon'), 'cajon_asoma': A((-0.38, -0.67, 0.64), sigue='cajon'),
        'cajon_habla': A((-0.38, -0.67, 0.66), sigue='cajon'),
        # marcas para personajes de pie
        'despacho': A((-1.08, 5.1, 0.0), 8), 'puerta': A((-0.85, 3.95, 0.0), 0), 'junto_principal': A((-0.38, 1.0, 0.0), 22),
        'pasillo': A((0.9, 1.6, 0.0), 160),
    }
    for n, ((x, y), seed) in COWORKER_SEATS.items():      # mascota sobre el escritorio de cada cubículo, junto al monitor
        anchors[f'{n}_escritorio'] = A((x + 0.32, y - 0.64, DESK_Z))
    probes = {'monitor': R['scr_world'].to_translation(), 'puerta': Vector((DOOR_X, WY, 1.1)),
              'escritorio': Vector((SANTI_DESK.x, SANTI_DESK.y, 0.9)), 'cajon': Vector((-0.38, -0.62, 0.62))}
    return dict(seats=seats, anchors=anchors, props=props, probes=probes, looks={'noche': night, 'dia': day},
                ambiente='oficina', publico=Vector((-0.85, -0.5, 0.0)).normalized())


def night(SC, ctx):
    """oficina de noche: muros en penumbra azul petróleo, techo apagado, ventana con ciudad, monitores fríos,
    lámpara cálida, pasillo cálido detrás de la puerta del jefe (entra a contraluz)"""
    recolor_card('pared', '#55646E')
    recolor_card('pared_lateral', '#4A5963')
    recolor_card('techo', '#3E4A55')
    recolor_card('alfombra', '#2B323A')
    recolor_card('zoclo', '#2A2E33')
    set_emit('panel_luz', '#3A4652', 0.15)
    for o in bpy.data.objects:
        if o.name.startswith('ceil_L'):
            o.data.energy = 0.0
        if o.name == 'whiteboard' or o.name.startswith('wb_line') or o.name.startswith('clock'):
            o.hide_render = True
    city_window(-0.25, 2.65, 0.95, 2.35, WY - 0.045, name='win')
    set_emit('pantalla_oscura', '#16263A', 1.6)
    for m in list(bpy.data.materials):
        if m.name.startswith('codigo_'):
            for n in m.node_tree.nodes:
                if n.type == 'EMISSION':
                    n.inputs['Strength'].default_value = 3.2
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and o.name.endswith('_glow') and o.name != 'win_glow':
            o.data.energy = 9.0
            o.data.color = (0.55, 0.72, 1.0)
            o.data.size = 0.5
            o.rotation_euler = (D(-90), 0, 0)
    lamp = bpy.data.objects.get('lamp_L')
    if lamp:
        lamp.data.energy = 60.0
        lamp.data.color = (1.0, 0.66, 0.38)
    k3 = add_light('n_underdesk', 'SPOT', (0.22, -0.72, 0.42), (0, 0, 0), 9, (1.0, 0.72, 0.48), 0.08, spot=(D(34), 0.6))
    aim(k3, (0.0, -0.33, 0.72))
    ok = bpy.data.objects.get('office_key')
    if ok:
        ok.data.energy = 90.0
        ok.data.color = (1.0, 0.86, 0.66)
    hall = add_light('n_hall', 'SPOT', (DOOR_X, WY + 1.2, 1.9), (0, 0, 0), 1100, (1.0, 0.88, 0.7), 0.35, spot=(D(42), 0.35))
    aim(hall, (DOOR_X, WY - 0.9, 0.0))
    return {'n_hall': 0.35, 'win_glow': 0.3, 'office_key': 0.3, 'lamp_L': 0.15}


def day(SC, ctx):
    """la versión de día original (look v1): techo encendido, luces cálidas de dirección marcada"""
    L = add_light
    L('key', 'AREA', (-1.5, -1.9, 2.3), (D(55), 0, D(-38)), 130, (1.0, 0.88, 0.74), 1.4)
    L('fill', 'AREA', (1.6, -2.2, 1.3), (D(75), 0, D(36)), 35, (0.95, 0.93, 0.9), 2.0)
    L('desk_bounce', 'AREA', (0.0, -0.75, 0.62), (D(-75), 0, 0), 10, (1.0, 0.86, 0.7), 0.7)
    return {}
