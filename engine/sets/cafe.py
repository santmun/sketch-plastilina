# cafe.py — cafetería de maqueta (cartón pluma + plastilina): barra al frente, cafetera y repisas al fondo,
# ventana con la calle, lámparas colgantes cálidas, mesitas y bancos. Set genérico de prueba de la interfaz de sets.
# Persona de pie tras la barra en 'tras_barra' (0, 0.65) mirando a -Y; la cámara principal vive en -Y.
import bpy, math, random
from mathutils import Vector, Matrix
from clay import (D, hexc, mat4, blob, sphere, superbox, box, cylinder, tube, text, clay, simple, card, node, FONT_BOLD)
from rig import Joint, qe
from characters.props import mug
from sets.common import (emis, add_light, plant, simple_chair, office_chair, paper, aim, recolor_card, set_emit,
                         city_window, Prop, FONT_TITLE)

BW = 1.6            # pared del fondo
BAR_Z = 1.0         # altura de la barra
BACK_Z = 0.95       # altura de la contrabarra


def checker_mat(name, c1, c2, scale=6.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes['Principled BSDF']
    bs.inputs['Roughness'].default_value = 0.55
    tc = node(nt, 'ShaderNodeTexCoord')
    ch = node(nt, 'ShaderNodeTexChecker', {'Scale': scale, 'Color1': hexc(c1), 'Color2': hexc(c2)})
    nt.links.new(tc.outputs['Object'], ch.inputs['Vector'])
    n1 = node(nt, 'ShaderNodeTexNoise', {'Scale': 9.0, 'Detail': 3.0})
    nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
    mix = node(nt, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mix.inputs['Factor'].default_value = 0.25
    nt.links.new(ch.outputs['Color'], mix.inputs['A'])
    nt.links.new(n1.outputs['Color'], mix.inputs['B'])
    nt.links.new(mix.outputs['Result'], bs.inputs['Base Color'])
    bp = node(nt, 'ShaderNodeBump', {'Strength': 0.15, 'Distance': 0.003})
    nt.links.new(n1.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], bs.inputs['Normal'])
    return m


def glass_mat():
    m = bpy.data.materials.get('vidrio')
    if m:
        return m
    m = simple('vidrio', '#DDE8E6', rough=0.05, trans=1.0)
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Alpha'].default_value = 0.35
    return m


def pendant(name, x, y, z=1.95):
    cord = clay('cable', '#1E1B19', rough=0.5, prints=0)
    tube(f'{name}_cable', cord, [(x, y, 2.7), (x, y, z + 0.12)], 0.006, None, ring=8, per=2, disp=0)
    shade_m = clay('pantalla_lampara', '#2F4A3F', rough=0.45, prints=0.6)
    blob(f'{name}_shade', shade_m, mat4((x, y, z + 0.07), (0, 0, 0), (0.13, 0.13, 0.1)), None, cut=((0, 0, -0.25), (0, 0, 1)),
         disp=0.002)
    sphere(f'{name}_bulb', simple('foco_calido', '#FFE2B0', emit='#FFC98A', estr=18.0), (x, y, z - 0.005), 0.045, disp=0, sub=0)
    L = add_light(f'{name}_L', 'SPOT', (x, y, z - 0.02), (0, 0, 0), 40, (1.0, 0.74, 0.46), 0.06, spot=(D(110), 0.6))
    aim(L, (x, y, 0))
    return L


def stool(name, x, y):
    m = clay('banco', '#3A3633', rough=0.5)
    seat = clay('asiento_banco', '#8E3B2C', rough=0.6)
    cylinder(f'{name}_seat', seat, (x, y, 0.72), 0.17, 0.05, None, sub=1, disp=0.002, bevel=0.01)
    tube(f'{name}_stem', m, [(x, y, 0.05), (x, y, 0.7)], 0.025, None)
    cylinder(f'{name}_foot', m, (x, y, 0.02), 0.15, 0.03, None, bevel=0.005)
    tube(f'{name}_ring', m, [(x + 0.13 * math.cos(a), y + 0.13 * math.sin(a), 0.3) for a in [i * math.pi / 5 for i in range(10)]],
         0.01, None, closed=True, ring=8, per=3, disp=0)


def bistro_table(name, x, y):
    m = clay('mesa_metal', '#2B2826', rough=0.4)
    top = card('mesa_madera', '#A9744A', rough=0.6)
    cylinder(f'{name}_top', top, (x, y, 0.74), 0.32, 0.03, None, bevel=0.006)
    tube(f'{name}_leg', m, [(x, y, 0.03), (x, y, 0.73)], 0.03, None)
    cylinder(f'{name}_base', m, (x, y, 0.015), 0.2, 0.03, None, bevel=0.006)


def pastry(name, loc, kind, s=1.0):
    if kind == 'croissant':
        m = clay('croissant', '#C98A3E', rough=0.55)
        pts = [(loc[0] + 0.05 * s * math.cos(a), loc[1] + 0.03 * s * math.sin(a), loc[2] + 0.015 * s) for a in
               [math.pi * (0.1 + 0.8 * i / 6) for i in range(7)]]
        return tube(name, m, pts, [0.01 * s, 0.018 * s, 0.024 * s, 0.026 * s, 0.024 * s, 0.018 * s, 0.01 * s], None, ring=12,
                    per=4, disp=0.002)
    if kind == 'concha':
        base = clay('concha_pan', '#D9A25E', rough=0.6)
        top = clay('concha_azucar', '#F1D9C4', rough=0.7)
        sphere(f'{name}_b', base, loc, (0.045 * s, 0.045 * s, 0.022 * s), cut=((0, 0, -0.3), (0, 0, 1)), disp=0.002)
        return sphere(f'{name}_t', top, (loc[0], loc[1], loc[2] + 0.008 * s), (0.042 * s, 0.042 * s, 0.02 * s),
                      cut=((0, 0, 0.2), (0, 0, 1)), disp=0.002)
    m = clay('dona', '#C77D4A', rough=0.5)
    return tube(name, m, [(loc[0] + 0.03 * s * math.cos(a), loc[1] + 0.03 * s * math.sin(a), loc[2] + 0.015 * s)
                          for a in [i * math.pi / 6 for i in range(12)]], 0.016 * s, None, closed=True, ring=10, per=3)


def build_cafe(params):
    rnd = random.Random(11)
    R = {}
    # ---- piso de ajedrez, paredes, techo
    box('floor', checker_mat('piso_ajedrez', '#D8CDB8', '#3A3532', 7.0), (0, 0, -0.01), (3.2, 3.2, 0.01), bevel=0)
    wall = card('pared_cafe', params.get('pared', '#A65A3E'))
    box('backwall', wall, (0, BW, 1.35), (3.2, 0.03, 1.35), bevel=0.002)
    box('wall_left', card('pared_cafe_lat', '#8E4E38'), (-3.0, 0.0, 1.35), (0.03, 2.4, 1.35), bevel=0)
    box('wall_right', card('pared_cafe_lat', '#8E4E38'), (3.0, 0.0, 1.35), (0.03, 2.4, 1.35), bevel=0)
    box('wainscot', card('lambrin', '#3F5A4E'), (0, BW - 0.035, 0.45), (3.2, 0.01, 0.45), bevel=0.002)
    box('ceiling', card('techo_cafe', '#D9CDB6', rough=0.95), (0, 0.0, 2.71), (3.2, 2.4, 0.01), bevel=0)
    # ---- barra (frente con duelas) + cubierta
    wood = card('barra_madera', '#7A4A2E', rough=0.6)
    top = card('barra_cubierta', '#8F8371', rough=0.6, grain=0.5)
    box('bar_body', wood, (0, 0.0, BAR_Z / 2), (1.35, 0.28, BAR_Z / 2 - 0.02), bevel=0.004)
    for i in range(18):
        x = -1.28 + i * 0.151
        box(f'bar_slat{i}', card('duela', '#8C5634' if i % 2 else '#7E4C2F'), (x, -0.285, 0.48), (0.07, 0.006, 0.4), bevel=0.003)
    box('bar_top', top, (0, 0.0, BAR_Z), (1.42, 0.33, 0.025), bevel=0.006)
    box('bar_kick', clay('zoclo_barra', '#2B2826'), (0, -0.25, 0.04), (1.35, 0.04, 0.04), bevel=0.003)
    # ---- objetos sobre la barra
    tz = BAR_Z + 0.025
    mug('cup_bar', mat4((0.35, -0.12, tz + 0.04), (0, 0, D(200))), label='', r=0.04, color='#EFE6D6')
    cylinder('saucer', clay('plato', '#EFE6D6', rough=0.35), (0.35, -0.12, tz + 0.006), 0.07, 0.01, None, bevel=0.003)
    # tarro de propinas (vidrio) con monedas
    g = glass_mat()
    cylinder('tipjar', g, (-0.55, -0.1, tz + 0.08), 0.07, 0.16, None, bevel=0.004)
    for i in range(7):
        cylinder(f'coin{i}', clay('moneda', '#C8A04A', rough=0.3, spec=0.7), (-0.55 + rnd.uniform(-0.04, 0.04),
                 -0.1 + rnd.uniform(-0.04, 0.04), tz + 0.006 + 0.005 * i), 0.016, 0.004, None, rot=(rnd.uniform(-0.3, 0.3), 0, 0), bevel=0)
    text('tipjar_txt', 'PROPINAS', clay('etiqueta', '#2A2420', prints=0), (-0.55, -0.172, tz + 0.1), 0.022, extrude=0.0008,
         font=FONT_BOLD)
    # vitrina de pan dulce (domo de vidrio)
    cylinder('dome_base', card('base_vitrina', '#5A3A28'), (-0.98, -0.05, tz + 0.012), 0.2, 0.024, None, bevel=0.004)
    blob('dome', g, mat4((-0.98, -0.05, tz + 0.025), (0, 0, 0), (0.19, 0.19, 0.17)), None, cut=((0, 0, 0.0), (0, 0, 1)), disp=0,
         sub=1)
    for i, (dx, dy, k) in enumerate(((-0.12, -0.03, 'concha'), (0.12, 0.0, 'croissant'), (0.0, 0.12, 'dona'), (-0.09, 0.1, 'concha'))):
        pastry(f'pan{i}', (-0.98 + dx, -0.05 + dy, tz + 0.03), k)
    # caja registradora
    reg = clay('caja_registradora', '#3B4A44', rough=0.5)
    superbox('register', reg, (0.92, 0.0, tz + 0.09), (0.15, 0.13, 0.09), e=0.25, disp=0.001)
    superbox('register_scr', emis('pantalla_caja', '#9FE0B5', 1.4), (0.92, -0.08, tz + 0.21), (0.08, 0.01, 0.04), e=0.2, disp=0)
    superbox('napkins', clay('servilletero', '#C9C2B4', rough=0.4), (0.62, -0.05, tz + 0.05), (0.05, 0.03, 0.05), e=0.3, disp=0)
    # ---- contrabarra + cafetera + repisas
    box('back_counter', wood, (0, BW - 0.25, BACK_Z / 2), (1.6, 0.22, BACK_Z / 2), bevel=0.004)
    box('back_top', top, (0, BW - 0.25, BACK_Z), (1.62, 0.24, 0.02), bevel=0.005)
    red = clay('cafetera_roja', params.get('cafetera', '#B9322A'), rough=0.35, coat=0.4, spec=0.6)
    chrome = simple('cromo', '#C9C6C0', rough=0.18, metal=1.0)
    mx, my = 0.0, BW - 0.27
    superbox('machine', red, (mx, my, BACK_Z + 0.2), (0.32, 0.18, 0.2), e=0.22, disp=0.001)
    box('machine_top', chrome, (mx, my, BACK_Z + 0.41), (0.3, 0.17, 0.012), bevel=0.004)
    for i, x in enumerate((-0.15, 0.15)):
        cylinder(f'group{i}', chrome, (mx + x, my - 0.19, BACK_Z + 0.24), 0.04, 0.06, None, bevel=0.004)
        tube(f'portafilter{i}', clay('mango_negro', '#151414', rough=0.4), [(mx + x, my - 0.22, BACK_Z + 0.19),
                                                                          (mx + x, my - 0.36, BACK_Z + 0.18)], 0.014, None)
        mug(f'shotcup{i}', mat4((mx + x, my - 0.2, BACK_Z + 0.06), (0, 0, D(180))), label='', r=0.028)
    box('driptray', chrome, (mx, my - 0.2, BACK_Z + 0.03), (0.28, 0.06, 0.01), bevel=0.003)
    for i, x in enumerate((-0.22, 0.22)):
        cylinder(f'gauge{i}', chrome, (mx + x, my - 0.185, BACK_Z + 0.33), 0.035, 0.012, None, rot=(D(90), 0, 0), bevel=0.003)
        cylinder(f'gaugeface{i}', simple('carátula', '#F3EEE3', rough=0.3), (mx + x, my - 0.193, BACK_Z + 0.33), 0.028, 0.004,
                 None, rot=(D(90), 0, 0), bevel=0)
    cylinder('grinder', clay('molino', '#2B2826', rough=0.4), (0.62, BW - 0.27, BACK_Z + 0.15), 0.07, 0.3, None, sub=1)
    blob('grinder_hopper', g, mat4((0.62, BW - 0.27, BACK_Z + 0.36), (0, 0, 0), (0.08, 0.08, 0.1)), None, disp=0)
    for i in range(4):
        for j in range(3):
            mug(f'stack{i}_{j}', mat4((-0.65 + 0.11 * i, BW - 0.3, BACK_Z + 0.045 + 0.075 * j), (0, 0, D(rnd.uniform(160, 220)))),
                label='', r=0.036, color=('#EFE6D6', '#3F5A4E', '#D9A13B')[(i + j) % 3])
    shelf = card('repisa_madera', '#6B4128')
    jar_cols = ('#5A3A28', '#C98A3E', '#3F5A4E', '#E3D9C6', '#8E3B2C')
    for k, z in enumerate((1.62, 1.98)):
        box(f'shelf{k}', shelf, (-0.55, BW - 0.12, z), (0.75, 0.1, 0.015), bevel=0.003)
        for i in range(6):
            x = -1.15 + i * 0.24
            if rnd.random() < 0.25:
                plant(f'shelfplant{k}{i}', (x, BW - 0.12, z + 0.015), s=0.55)
                continue
            cylinder(f'jar{k}{i}', g, (x, BW - 0.12, z + 0.09), 0.055, 0.15, None, bevel=0.004)
            cylinder(f'jarfill{k}{i}', clay(f'grano{i % 5}', jar_cols[(i + k) % 5], rough=0.7), (x, BW - 0.12, z + 0.06), 0.048,
                     0.09, None, bevel=0.002)
            cylinder(f'jarlid{k}{i}', clay('tapa', '#2B2826'), (x, BW - 0.12, z + 0.17), 0.058, 0.02, None, bevel=0.004)
    # pizarrón con el menú
    bx, bz = -1.85, 1.75
    box('menuboard_frame', card('marco_pizarra', '#5A3A28'), (bx, BW - 0.04, bz), (0.55, 0.012, 0.45), bevel=0.004)
    box('menuboard', card('pizarra', '#1E2422', rough=0.9), (bx, BW - 0.054, bz), (0.5, 0.004, 0.4), bevel=0)
    chalk = clay('gis', '#EDE8DD', rough=0.9, prints=0)
    text('menu_title', params.get('menu_titulo', 'MENÚ'), chalk, (bx, BW - 0.06, bz + 0.28), 0.09, extrude=0.0008, font=FONT_TITLE)
    for i, ln in enumerate(params.get('menu', ['Café de olla', 'Americano', 'Capuchino', 'Pan dulce'])):
        text(f'menu_l{i}', ln, chalk, (bx - 0.05, BW - 0.06, bz + 0.13 - i * 0.12), 0.055, extrude=0.0006, font=FONT_TITLE)
        text(f'menu_p{i}', f'${35 + 10 * i}', chalk, (bx + 0.38, BW - 0.06, bz + 0.13 - i * 0.12), 0.05, extrude=0.0006,
             font=FONT_TITLE)
    # letrero
    text('sign', params.get('letrero', 'CAFÉ'), emis('letrero', '#FFB45A', 3.0), (1.6, BW - 0.04, 2.45), 0.2, extrude=0.004,
         font=FONT_TITLE)
    # ---- mobiliario del frente
    for i, x in enumerate((-0.6, 0.6)):
        stool(f'stool{i}', x, -0.62)
    bistro_table('table1', -1.75, -1.25)
    bistro_table('table2', 1.85, -1.1)
    mug('cup_t1', mat4((-1.7, -1.25, 0.8), (0, 0, D(30))), label='', r=0.04, color='#3F5A4E')
    plant('plant_corner', (2.6, 1.2, 0), s=2.0)
    plant('plant_corner2', (-2.6, -0.4, 0), s=1.7)
    for i, x in enumerate((-0.9, 0.0, 0.9)):
        pendant(f'pendant{i}', x, 0.05, 1.95)
    return R


def build(ctx):
    params = ctx.get('params', {})
    build_cafe(params)
    occupied = ctx.get('occupied', set())
    seats = {'mesa_1': dict(pos=(-1.75, -0.8, 0), yaw=0, chair=None), 'mesa_2': dict(pos=(1.85, -0.65, 0), yaw=0, chair=None)}
    for n, s in seats.items():
        simple_chair(f'{n}_silla', s['pos'], 0.0)
    A = lambda p, yaw=None, **kw: dict(pos=p, yaw=yaw, **kw)
    tz = BAR_Z + 0.025
    anchors = {
        # marcas de pie
        'tras_barra': A((0.0, 0.62, 0.0), 0), 'tras_barra_izq': A((-0.75, 0.62, 0.0), 0),
        'tras_barra_der': A((0.75, 0.62, 0.0), 0), 'cafetera_frente': A((0.0, 0.95, 0.0), 180),
        'cliente': A((0.25, -0.85, 0.0), 180), 'entrada': A((2.4, -1.8, 0.0), 120),
        # escondites de mascota
        'barra': A((0.12, -0.08, tz)), 'barra_izq': A((-0.3, -0.12, tz)), 'barra_der': A((0.62, -0.16, tz)),
        'tarro': A((-0.55, -0.1, tz + 0.025)), 'junto_taza': A((0.22, -0.16, tz)), 'vitrina': A((-0.72, -0.12, tz)),
        'tras_vitrina': A((-0.98, 0.2, tz)), 'dentro_vitrina': A((-0.98, -0.07, tz + 0.025)),
        'caja': A((0.92, -0.02, tz + 0.18)), 'cafetera': A((0.0, BW - 0.27, BACK_Z + 0.42)),
        'tras_cafetera': A((0.45, BW - 0.2, BACK_Z + 0.02)), 'repisa': A((-0.43, BW - 0.12, 1.635)),
        'bajo_barra': A((0.0, -0.55, 0.0)), 'banco': A((0.6, -0.62, 0.745)), 'mesa': A((-1.7, -1.32, 0.755)),
    }
    probes = {'cafetera': Vector((0.0, BW - 0.3, BACK_Z + 0.25)), 'barra': Vector((0.0, -0.05, BAR_Z + 0.1)),
              'tarro': Vector((-0.55, -0.1, tz + 0.1)), 'pizarra': Vector((-1.85, BW - 0.05, 1.75)),
              'vitrina': Vector((-0.98, -0.05, tz + 0.1))}
    return dict(seats=seats, anchors=anchors, props={}, probes=probes, looks={'noche': night, 'dia': day}, ambiente='cafe',
                publico=Vector((0.0, -1.0, 0.0)))


def night(SC, ctx):
    """café de noche: paredes en penumbra cálida, colgantes ámbar como luz práctica, calle fría por la ventana"""
    recolor_card('pared_cafe', '#6E3B2C')
    recolor_card('pared_cafe_lat', '#5A3226')
    recolor_card('techo_cafe', '#3E3A36')
    city_window(0.95, 2.6, 1.0, 2.3, BW - 0.045, name='win', light=30)
    for o in bpy.data.objects:
        if o.name.startswith('pendant') and o.type == 'LIGHT':
            o.data.energy = 45
    return {'win_glow': 0.3, 'pendant0_L': 0.25, 'pendant1_L': 0.25, 'pendant2_L': 0.25}


def day(SC, ctx):
    """café de día: luz de ventana amplia y cálida, colgantes tenues"""
    L = add_light('sun_window', 'AREA', (1.8, BW - 0.3, 1.8), (0, 0, 0), 260, (1.0, 0.92, 0.8), 1.6)
    aim(L, (0.0, 0.0, 0.9))
    f = add_light('fill_room', 'AREA', (-1.5, -2.0, 2.0), (0, 0, 0), 120, (0.95, 0.95, 1.0), 2.5)
    aim(f, (0, 0.3, 1.0))
    for o in bpy.data.objects:
        if o.name.startswith('pendant') and o.type == 'LIGHT':
            o.data.energy = 25
    return {}
