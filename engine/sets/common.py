# common.py — piezas de maqueta reutilizables por cualquier set (cartón pluma + plastilina): luces, pantallas,
# escritorios, sillas, plantas, papeles, lámparas. Extraído de office.py de «A escondidas».
import bpy, math, random
from mathutils import Vector, Matrix, Euler
from clay import (D, hexc, link, empty, mat4, blob, sphere, superbox, box, cylinder, tube, text, clay, simple, card,
                  node, FONT_BOLD, load_font)
from rig import Joint, child_joint, qe

FONT_TITLE = load_font('/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf') or FONT_BOLD     # fuera de macOS: FONT_BOLD


def foam_wall(name, loc, size, color, rot=(0, 0, 0)):
    root = empty(name, loc, rot)
    box(f'{name}_panel', card(f'carton_{color}', color), (0, 0, 0), size, root, bevel=0.003)
    box(f'{name}_core', card('nucleo_espuma', '#F4F1EA', rough=0.95), (0, 0, size[2] + 0.002),
        (size[0] + 0.001, size[1] * 0.75, 0.003), root, bevel=0.001)
    return root


def emis(name, color, strength):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, 'ShaderNodeOutputMaterial')
    em = node(nt, 'ShaderNodeEmission', {'Color': hexc(color), 'Strength': strength})
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def add_light(name, kind, loc, rot, energy, color=(1, 0.85, 0.7), size=0.5, spot=None, parent=None):
    L = bpy.data.lights.new(name, kind)
    L.energy = energy
    L.color = color
    if kind == 'AREA':
        L.size = size
    else:
        L.shadow_soft_size = size
    if spot:
        L.spot_size, L.spot_blend = spot
    o = bpy.data.objects.new(name, L)
    link(o, parent)
    o.location = loc
    o.rotation_euler = rot
    return o


def desk_lamp(name, loc, rot_z, color='#D9A13B', light=30.0):
    root = empty(name, loc, (0, 0, rot_z))
    m = clay(f'lampara_{color}', color, rough=0.5, prints=0.8)
    cylinder(f'{name}_base', m, (0, 0, 0.012), 0.07, 0.024, root, sub=1, disp=0.001)
    tube(f'{name}_arm1', m, [(0, 0, 0.02), (0.03, 0, 0.2), (0.05, 0, 0.32)], 0.012, root)
    tube(f'{name}_arm2', m, [(0.05, 0, 0.32), (0.13, 0, 0.36), (0.2, 0, 0.33)], 0.011, root)
    sphere(f'{name}_joint', m, (0.05, 0, 0.32), 0.02, root)
    blob(f'{name}_shade', m, mat4((0.23, 0, 0.3), (0, D(-120), 0), (0.075, 0.075, 0.06)), root,
         cut=((0, 0, -0.1), (0, 0, 1)), disp=0.002)
    sphere(f'{name}_bulb', simple('bombilla', '#FFE2B0', emit='#FFD49A', estr=20.0), (0.245, 0, 0.27), 0.03, root,
           sub=0, disp=0)
    add_light(f'{name}_L', 'SPOT', (0.25, 0, 0.255), (0, D(30), 0), light, (1.0, 0.78, 0.52), 0.05,
              spot=(D(120), 0.7), parent=root)
    return root


def plant(name, loc, s=1.0):
    root = empty(name, loc)
    root.scale = (s, s, s)
    pot = clay('maceta', '#B8603E', rough=0.7)
    cylinder(f'{name}_pot', pot, (0, 0, 0.06), 0.06, 0.12, root, r2=0.075, sub=1, disp=0.002)
    leaf = clay('hoja', '#6F7D3A', rough=0.6)
    rnd = random.Random(sum(map(ord, name)))
    for i in range(7):
        a = i * D(51) + rnd.uniform(-0.2, 0.2)
        h = rnd.uniform(0.18, 0.3)
        tube(f'{name}_leaf{i}', leaf, [(0, 0, 0.1), (0.04 * math.cos(a), 0.04 * math.sin(a), 0.1 + h * 0.6),
                                      (0.1 * math.cos(a), 0.1 * math.sin(a), 0.1 + h)],
             [0.012, 0.024, 0.008], root, flat=0.45, ring=12, per=5, disp=0.002)
    return root


def code_screen(name, parent, w, h, seed=1, light=True):
    """pantalla de editor: fondo oscuro emisivo + renglones de código en colores cálidos"""
    box(f'{name}_bg', emis('pantalla_oscura', '#24201D', 1.0), (0, 0, 0), (w, 0.001, h), parent, bevel=0)
    rnd = random.Random(seed)
    cols = ['#E8A35C', '#F1E4CC', '#C98B6B', '#9FB08A', '#F1E4CC']
    y = h - 0.03
    i = 0
    while y > -h + 0.02:
        x0 = -w + 0.03 + (0.03 if rnd.random() < 0.4 else 0) + (0.03 if rnd.random() < 0.2 else 0)
        ln = rnd.uniform(0.08, 0.6) * w
        c = cols[rnd.randrange(len(cols))]
        box(f'{name}_ln{i}', emis(f'codigo_{c}', c, 1.6), (x0 + ln / 2, -0.0015, y), (ln / 2, 0.0006, 0.0065), parent,
            bevel=0)
        y -= 0.026
        i += 1


def monitor(name, loc, rot_z, seed=1, screen_fn=None):
    root = empty(name, loc, (0, 0, rot_z))
    g = clay('monitor', '#3C3A38', rough=0.5, prints=0.7)
    superbox(f'{name}_frame', g, (0, 0, 0.3), (0.26, 0.025, 0.17), root, e=0.18, disp=0.0015)
    scr = empty(f'{name}_scr', (0, -0.027, 0.305), parent=root)
    if screen_fn:
        screen_fn(scr)
    else:
        code_screen(f'{name}_code', scr, 0.235, 0.145, seed)
    tube(f'{name}_neck', g, [(0, 0.02, 0.0), (0, 0.03, 0.15)], 0.025, root)
    superbox(f'{name}_foot', g, (0, 0.0, 0.01), (0.1, 0.07, 0.012), root, disp=0.001)
    L = bpy.data.lights.new(f'{name}_glow', 'AREA')
    L.energy = 5.0
    L.color = (1.0, 0.78, 0.58)
    L.size = 0.45
    lo = bpy.data.objects.new(f'{name}_glow', L)
    link(lo, root)
    lo.location = (0, -0.07, 0.3)
    lo.rotation_euler = (D(90), 0, 0)
    return root, scr


def office_chair(W, color='#2F2D2B'):
    """silla de oficina construida en coordenadas de mundo con la matriz W (para pegarla a Santi)"""
    m = clay(f'silla_{color}', color, rough=0.55)
    objs = [superbox('chair_seat', m, (0, -0.02, 0.43), (0.21, 0.2, 0.04), None, disp=0.002),
            superbox('chair_back', m, (0, 0.2, 0.75), (0.19, 0.04, 0.24), None, rot=(D(-8), 0, 0), disp=0.002),
            tube('chair_stem', m, [(0, 0, 0.08), (0, 0, 0.42)], 0.025, None),
            tube('chair_spine', m, [(0, 0.02, 0.4), (0, 0.18, 0.44), (0, 0.21, 0.55)], 0.02, None)]
    for i in range(5):
        a = D(72) * i + D(18)
        objs.append(tube(f'chair_leg{i}', m, [(0, 0, 0.08), (0.25 * math.cos(a), 0.25 * math.sin(a), 0.05)], 0.018, None))
        objs.append(sphere(f'chair_wheel{i}', m, (0.25 * math.cos(a), 0.25 * math.sin(a), 0.03), 0.028, None))
    for o in objs:
        o.matrix_basis = W @ o.matrix_basis
    return objs


def simple_chair(name, loc, yaw):
    root = empty(name, loc, (0, 0, yaw))
    m = clay('silla2', '#3A3633', rough=0.55)
    superbox(f'{name}_seat', m, (0, -0.02, 0.43), (0.21, 0.2, 0.04), root, disp=0.002)
    superbox(f'{name}_back', m, (0, 0.2, 0.75), (0.19, 0.04, 0.24), root, rot=(D(-8), 0, 0), disp=0.002)
    tube(f'{name}_stem', m, [(0, 0, 0.06), (0, 0, 0.42)], 0.025, root)
    tube(f'{name}_spine', m, [(0, 0.02, 0.4), (0, 0.18, 0.44), (0, 0.21, 0.55)], 0.02, root)
    for i in range(5):
        a = D(72) * i + D(18)
        tube(f'{name}_leg{i}', m, [(0, 0, 0.08), (0.25 * math.cos(a), 0.25 * math.sin(a), 0.05)], 0.018, root)
    return root


def paper(name, loc, size, rot=(0, 0, 0), parent=None, color='#F3EEE3'):
    return box(name, card(f'papel_{color}', color, rough=0.9, grain=0.5), loc, size, parent, rot, bevel=0)


def desk(name, c, w=0.7, d=0.35, modesty=True, color='#B98B5E', legs=False):
    m = card('escritorio', color, rough=0.6)
    box(f'{name}_top', m, (c.x, c.y, 0.73), (w, d, 0.022), bevel=0.004)
    if legs:
        lm = clay('pata_metal', '#3A3633', rough=0.4, prints=0.3)
        for sx in (-1, 1):
            for sy in (-1, 1):
                tube(f'{name}_leg{sx}{sy}', lm, [(c.x + (w - 0.05) * sx, c.y + (d - 0.05) * sy, 0.0),
                                                 (c.x + (w - 0.05) * sx, c.y + (d - 0.05) * sy, 0.71)], 0.02, None,
                     ring=10, per=2, disp=0)
    else:
        for sx in (-1, 1):
            box(f'{name}_side{sx}', m, (c.x + (w - 0.03) * sx, c.y, 0.36), (0.02, d - 0.02, 0.36), bevel=0.003)
    if modesty:
        box(f'{name}_front', m, (c.x, c.y - d + 0.03, 0.47), (w - 0.04, 0.012, 0.24), bevel=0.003)




def aim(o, tgt):
    o.rotation_euler = (Vector(tgt) - o.location).to_track_quat('-Z', 'Y').to_euler()


def recolor_card(name, color, k=1.0):
    m = bpy.data.materials.get(name)
    if not m:
        return
    for n in m.node_tree.nodes:
        if n.type == 'VALTORGB':
            base = Vector(hexc(color)[:3]) * k
            n.color_ramp.elements[0].color = (*(base * 0.88), 1)
            n.color_ramp.elements[1].color = (*(base * 1.06), 1)


def set_emit(name, color, strength):
    m = bpy.data.materials.get(name)
    if not m:
        return
    for n in m.node_tree.nodes:
        if n.type == 'EMISSION':
            n.inputs['Color'].default_value = hexc(color)
            n.inputs['Strength'].default_value = strength
        if n.type == 'BSDF_PRINCIPLED':
            n.inputs['Emission Color'].default_value = hexc(color)
            n.inputs['Emission Strength'].default_value = strength


def city_window(x0, x1, z0, z1, y, seed=7, name='win', facing=-1, light=35):
    """ventana con la ciudad de noche (plano XZ en y): cielo añil, edificios, ventanas encendidas y bokeh de calle"""
    rnd = random.Random(seed)
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    hw, hh = (x1 - x0) / 2, (z1 - z0) / 2
    s = -facing      # profundidad hacia afuera de la ventana
    box(f'{name}_sky', emis('cielo_noche', '#16304E', 0.9), (cx, y + 0.012 * s, cz), (hw, 0.002, hh), bevel=0)
    bld = simple('edificio', '#070C14', rough=0.9)
    lit_w = emis('ventana_calida', '#FFC37A', 5.0)
    lit_c = emis('ventana_fria', '#A9D2FF', 4.0)
    x, i = x0, 0
    while x < x1:
        w = rnd.uniform(0.14, 0.32)
        top = z0 + rnd.uniform(0.25, 0.95) * (z1 - z0)
        bx = min(x + w, x1)
        box(f'{name}_bld{i}', bld, ((x + bx) / 2, y + 0.008 * s, (z0 + top) / 2), ((bx - x) / 2, 0.002, (top - z0) / 2), bevel=0)
        for row in range(int((top - z0) / 0.06)):
            for col in range(max(1, int((bx - x) / 0.05))):
                if rnd.random() < 0.28:
                    m = lit_w if rnd.random() < 0.7 else lit_c
                    box(f'{name}_lt{i}_{row}_{col}', m, (x + 0.025 + col * 0.05, y + 0.005 * s, z0 + 0.04 + row * 0.06),
                        (0.011, 0.001, 0.014), bevel=0)
        x = bx + rnd.uniform(0.0, 0.05)
        i += 1
    for k in range(26):
        c = '#FFB866' if rnd.random() < 0.6 else '#FF5A4A' if rnd.random() < 0.4 else '#BFE0FF'
        sphere(f'{name}_bokeh{k}', emis(f'bokeh_{c}', c, 9.0), (rnd.uniform(x0 + 0.05, x1 - 0.05), y + 0.004 * s,
                                                            z0 + rnd.uniform(0.02, 0.18)), 0.012, disp=0, sub=0)
    fr = simple('marco_ventana', '#1A1F26', rough=0.6)
    for xx in (x0, cx, x1):
        box(f'{name}_mull{xx:.2f}', fr, (xx, y - 0.01 * s, cz), (0.025, 0.02, hh + 0.025), bevel=0.003)
    for zz in (z0, z1):
        box(f'{name}_rail{zz:.2f}', fr, (cx, y - 0.01 * s, zz), (hw + 0.025, 0.02, 0.025), bevel=0.003)
    box(f'{name}_sill', simple('repisa', '#2A2F36', rough=0.7), (cx, y - 0.06 * s, z0 - 0.03), (hw + 0.06, 0.07, 0.015), bevel=0.003)
    L = add_light(f'{name}_glow', 'AREA', (cx, y - 0.15 * s, cz), (0, 0, 0), light, (0.5, 0.68, 1.0), max(hw, hh) * 2)
    L.data.shape = 'RECTANGLE'
    L.data.size, L.data.size_y = hw * 2, hh * 2
    aim(L, (cx, y - 2.0 * s, cz))
    return L


class Prop:
    """prop animable de un set: valor escalar por cuadro (ángulo, apertura, visibilidad...)"""

    def __init__(self, joint, fn, scale=False, default=0.0):
        self.j, self.fn, self.scale, self.default = joint, fn, scale, default

    def apply(self, v):
        self.fn(self.j, v)

    def record(self, f):
        self.j.record(f, scale=self.scale)
