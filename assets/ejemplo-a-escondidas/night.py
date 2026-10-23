# night.py — look v2 «oficina de noche» (21-10-2026), sobre la dirección de luz del referente:
# fondo añil/petróleo, monitores emisivos fríos, ciudad nocturna en bokeh por la ventana, lámpara cálida que esculpe
# las caras, contraluces fríos, bruma ligera, jefe a contraluz con la luz del pasillo y las IAs que brillan en el remate.
import bpy, math, random
from mathutils import Vector, Matrix
from clay import D, hexc, box, superbox, sphere, simple, node
from office import add_light, emis, WY, DOOR_X, SANTI_DESK
from timing import V   # tiempos de autor -> guion vigente

COLD = (0.45, 0.66, 1.0)
WARM = (1.0, 0.66, 0.38)


def _aim(o, tgt):
    o.rotation_euler = (Vector(tgt) - o.location).to_track_quat('-Z', 'Y').to_euler()


def _recolor_card(name, color, k=1.0):
    m = bpy.data.materials.get(name)
    if not m:
        return
    for n in m.node_tree.nodes:
        if n.type == 'VALTORGB':
            base = Vector(hexc(color)[:3]) * k
            n.color_ramp.elements[0].color = (*(base * 0.88), 1)
            n.color_ramp.elements[1].color = (*(base * 1.06), 1)


def _emit(name, color, strength):
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


def city_window(x0, x1, z0, z1, y=WY - 0.045, seed=7):
    """ventana con la ciudad de noche: cielo añil, siluetas de edificios y luces que el desenfoque vuelve bokeh"""
    rnd = random.Random(seed)
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    hw, hh = (x1 - x0) / 2, (z1 - z0) / 2
    box('win_sky', emis('cielo_noche', '#16304E', 0.9), (cx, y + 0.012, cz), (hw, 0.002, hh), bevel=0)
    bld = simple('edificio', '#070C14', rough=0.9)
    lit_w = emis('ventana_calida', '#FFC37A', 5.0)
    lit_c = emis('ventana_fria', '#A9D2FF', 4.0)
    x = x0
    i = 0
    while x < x1:
        w = rnd.uniform(0.14, 0.32)
        top = z0 + rnd.uniform(0.25, 0.95) * (z1 - z0)
        bx = min(x + w, x1)
        box(f'win_bld{i}', bld, ((x + bx) / 2, y + 0.008, (z0 + top) / 2), ((bx - x) / 2, 0.002, (top - z0) / 2), bevel=0)
        # ventanitas encendidas
        for row in range(int((top - z0) / 0.06)):
            for col in range(max(1, int((bx - x) / 0.05))):
                if rnd.random() < 0.28:
                    m = lit_w if rnd.random() < 0.7 else lit_c
                    box(f'win_lt{i}_{row}_{col}', m, (x + 0.025 + col * 0.05, y + 0.005, z0 + 0.04 + row * 0.06),
                        (0.011, 0.001, 0.014), bevel=0)
        x = bx + rnd.uniform(0.0, 0.05)
        i += 1
    # luces de calle / coches: puntos brillantes abajo
    for k in range(26):
        c = '#FFB866' if rnd.random() < 0.6 else '#FF5A4A' if rnd.random() < 0.4 else '#BFE0FF'
        sphere(f'win_bokeh{k}', emis(f'bokeh_{c}', c, 9.0), (rnd.uniform(x0 + 0.05, x1 - 0.05), y + 0.004,
                                                          z0 + rnd.uniform(0.02, 0.18)), 0.012, disp=0, sub=0)
    # marco y parteluces
    fr = simple('marco_ventana', '#1A1F26', rough=0.6)
    for xx in (x0, cx, x1):
        box(f'win_mull{xx:.2f}', fr, (xx, y - 0.01, cz), (0.025, 0.02, hh + 0.025), bevel=0.003)
    for zz in (z0, z1):
        box(f'win_rail{zz:.2f}', fr, (cx, y - 0.01, zz), (hw + 0.025, 0.02, 0.025), bevel=0.003)
    box('win_sill', simple('repisa', '#2A2F36', rough=0.7), (cx, y - 0.06, z0 - 0.03), (hw + 0.06, 0.07, 0.015),
        bevel=0.003)
    # resplandor frío de la ciudad hacia el cuarto
    L = add_light('city_glow', 'AREA', (cx, y - 0.15, cz), (D(-90), 0, 0), 35, (0.5, 0.68, 1.0), max(hw, hh) * 2)
    L.data.shape = 'RECTANGLE'
    L.data.size, L.data.size_y = hw * 2, hh * 2
    L.rotation_euler = (D(90), 0, 0)
    L.rotation_euler = (Vector((cx, 0, cz)) - L.location).to_track_quat('-Z', 'Y').to_euler()


def apply(SC, critters, ai_pop, fps, shots=()):
    # ---- mundo: añil profundo + bruma
    w = SC.world
    nt = w.node_tree
    nt.nodes['Background'].inputs['Color'].default_value = hexc('#0A1724')
    nt.nodes['Background'].inputs['Strength'].default_value = 0.35
    vol = node(nt, 'ShaderNodeVolumePrincipled', {'Density': 0.012, 'Anisotropy': 0.45})
    vol.inputs['Color'].default_value = hexc('#C9D6E6')
    out = [n for n in nt.nodes if n.type == 'OUTPUT_WORLD'][0]
    nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])
    ee = SC.eevee
    for k, v in (('volumetric_tile_size', '4'), ('volumetric_samples', 64), ('volumetric_end', 9.0),
                 ('volumetric_sample_distribution', 0.6), ('use_volumetric_shadows', False)):
        try:
            setattr(ee, k, v)
        except Exception as e:
            print('[skip]', k, e)

    try:
        SC.view_settings.look = 'AgX - Punchy'   # más saturación, como el referente
    except Exception as e:
        print('[skip] look', e)
    # ---- set: muros en penumbra azul petróleo, techo apagado
    _recolor_card('pared', '#55646E')
    _recolor_card('pared_lateral', '#4A5963')
    _recolor_card('techo', '#3E4A55')
    _recolor_card('alfombra', '#2B323A')
    _recolor_card('zoclo', '#2A2E33')
    _emit('panel_luz', '#3A4652', 0.15)
    for o in bpy.data.objects:
        if o.name.startswith('ceil_L'):
            o.data.energy = 0.0
        if o.name in ('key', 'fill', 'rim', 'rim2', 'face_fill', 'desk_bounce'):
            o.data.energy = 0.0
    # la ventana sustituye al pizarrón (detrás de Santi en sus primeros planos)
    for o in bpy.data.objects:
        if o.name == 'whiteboard' or o.name.startswith('wb_line') or o.name.startswith('clock'):
            o.hide_render = True
    city_window(-0.25, 2.65, 0.95, 2.35)

    # ---- monitores: emisivos y fríos (fuentes de luz)
    _emit('pantalla_oscura', '#16263A', 1.6)
    for m in list(bpy.data.materials):
        if m.name.startswith('codigo_'):
            for n in m.node_tree.nodes:
                if n.type == 'EMISSION':
                    n.inputs['Strength'].default_value = 3.2
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and o.name.endswith('_glow') and o.name != 'city_glow':
            o.data.energy = 9.0
            o.data.color = (0.55, 0.72, 1.0)
            o.data.size = 0.5
            o.rotation_euler = (D(-90), 0, 0)   # hacia el frente de la pantalla (antes apuntaba hacia el monitor)

    # ---- lámpara de escritorio = luz clave cálida que esculpe la cara de Santi (y a Clawd en el regazo)
    lamp = bpy.data.objects.get('lamp_L')
    if lamp:
        lamp.data.energy = 60.0
        lamp.data.color = WARM
    head = Vector((0.0, -0.25, 1.07))
    k = add_light('n_lampkey', 'AREA', (0.74, -0.58, 1.32), (0, 0, 0), 30, WARM, 0.2)
    _aim(k, head)
    k2 = add_light('n_lapwarm', 'AREA', (0.45, -0.85, 0.95), (0, 0, 0), 10, WARM, 0.18)
    _aim(k2, (0.0, -0.3, 0.68))
    # bajo el escritorio: rebote cálido tenue para Clawd
    k3 = add_light('n_underdesk', 'SPOT', (0.22, -0.72, 0.42), (0, 0, 0), 9, (1.0, 0.72, 0.48), 0.08,
                   spot=(D(34), 0.6))
    _aim(k3, (0.0, -0.33, 0.72))
    # contraluces fríos que recortan las siluetas
    r1 = add_light('n_rim_L', 'SPOT', (-0.75, 0.75, 1.75), (0, 0, 0), 150, COLD, 0.25, spot=(D(50), 0.5))
    _aim(r1, head)
    r2 = add_light('n_rim_R', 'SPOT', (0.8, 0.6, 1.6), (0, 0, 0), 110, COLD, 0.25, spot=(D(50), 0.5))
    _aim(r2, head)
    for L_, e0 in ((r1, 150), (r2, 110)):   # desde que entra el jefe, Santi lo mira y la cámara está de su lado
        for t, e in ((0, e0), (V(34.35), e0), (V(34.4), e0 * 0.25), (72, e0 * 0.25)):
            L_.data.energy = e
            L_.data.keyframe_insert('energy', frame=int(round(t * fps)))
    r3 = add_light('n_rim_low', 'AREA', (0.0, 0.25, 0.8), (0, 0, 0), 14, COLD, 0.3)
    _aim(r3, (0.0, -0.33, 0.7))
    # luz general muy baja y fría para que el cuarto no se pierda
    amb = add_light('n_amb', 'AREA', (0.0, 0.8, 2.6), (D(0), 0, 0), 70, (0.5, 0.62, 0.85), 4.0)
    _aim(amb, (0, 0.8, 0))
    for t, e in ((0, 32.0), (V(68.95), 32.0), (V(69.1), 70.0), (72, 70.0)):   # el remate se abre un poco más
        amb.data.energy = e
        amb.data.keyframe_insert('energy', frame=int(round(t * fps)))

    # ---- despacho / pasillo: luz cálida intensa detrás de la puerta -> el jefe entra a contraluz
    ok = bpy.data.objects.get('office_key')
    if ok:
        ok.data.energy = 90.0
        ok.data.color = (1.0, 0.86, 0.66)
    hall = add_light('n_hall', 'SPOT', (DOOR_X, WY + 1.2, 1.9), (0, 0, 0), 1100, (1.0, 0.88, 0.7), 0.35,
                     spot=(D(42), 0.35))
    _aim(hall, (DOOR_X, WY - 0.9, 0.0))   # recorta al jefe en la puerta y baña el piso, sin lavar a Santi
    # contraluz frío para el jefe cerca de Santi (posición final)
    jb = add_light('n_rim_boss', 'SPOT', (-0.9, 1.9, 1.9), (0, 0, 0), 120, COLD, 0.25, spot=(D(55), 0.5))
    _aim(jb, (-0.4, 1.05, 1.1))
    # contraluz frío que recorta el nudo negro de ChatGPT (más fuerte en el duelo)
    gr = add_light('n_rim_gpt', 'SPOT', (0.3, 1.8, 1.55), (0, 0, 0), 0, (0.5, 0.75, 1.0), 0.06, spot=(D(25), 0.4))
    _aim(gr, (-0.06, 1.09, 1.14))
    for t, e in ((0, 0.0), (V(35.9), 0.0), (V(36.2), 30.0), (V(41.6), 30.0), (V(41.68), 90.0), (V(43.2), 90.0), (V(43.28), 30.0), (72, 30.0)):
        gr.data.energy = e
        gr.data.keyframe_insert('energy', frame=int(round(t * fps)))
    jk = add_light('n_key_boss', 'SPOT', (0.5, 0.3, 1.4), (0, 0, 0), 22, WARM, 0.3, spot=(D(35), 0.5))
    _aim(jk, (-0.4, 1.05, 1.15))
    for t, e in ((0, 0.0), (V(35.2), 0.0), (V(36.0), 16.0), (72, 16.0)):   # solo cuando ya llegó junto a Santi
        jk.data.energy = e
        jk.data.keyframe_insert('energy', frame=int(round(t * fps)))

    # ---- compañeros: su monitor los ilumina; en el remate sus IA brillan
    glow_cols = {'ia_azul': '#5F8FFF', 'ia_verde': '#8FE06A', 'ia_ballena': '#5C7CFF', 'ia_violeta': '#B98CFF'}
    for n, c in glow_cols.items():
        _emit(n, c, 1.8)
    for i, cr in enumerate(critters):
        root = cr.root.obj
        kind_col = [(0.4, 0.55, 1.0), (0.4, 0.5, 1.0), (0.75, 0.55, 1.0), (0.55, 0.95, 0.45)][i]
        L = add_light(f'n_ia_glow{i}', 'POINT', (0, 0, 0), (0, 0, 0), 0.0, kind_col, 0.08, parent=root)
        t0 = V(ai_pop[i]) if ai_pop[i] > 0 else 0.0
        for t, e in sorted({max(0.0, t0 - 0.02): 0.0, 0.0: 0.0 if t0 > 0.1 else 5.0, t0 + 0.15: 9.0, t0 + 0.4: 5.0, 72: 5.0}.items()):
            L.data.energy = e
            L.data.keyframe_insert('energy', frame=int(round(t * fps)))
    for k, v in (('bokeh_max_size', 120.0), ('bokeh_threshold', 0.6), ('bokeh_neighbor_max', 12.0)):
        try:
            setattr(ee, k, v)
        except Exception as e:
            print('[skip]', k, e)
    # bruma: solo los contraluces y el pasillo la iluminan (las luces junto a cámara no velan la imagen)
    vf = {'n_hall': 0.35, 'n_rim_L': 0.5, 'n_rim_R': 0.5, 'n_rim_boss': 0.5, 'city_glow': 0.3, 'office_key': 0.3,
          'lamp_L': 0.15}
    # plano 07 trabajado a fondo (al final: ajusta energías ya definidas)
    for sh in shots:
        if sh['n'].startswith('S07 '):
            plano07(sh, fps)
    for o in bpy.data.objects:
        if o.type == 'LIGHT':
            o.data.volume_factor = vf.get(o.name, 0.0)
            # sombras solo en las luces que esculpen (evita llenar el búfer de sombras de EEVEE)
            if (o.name.endswith('_glow') or o.name.startswith('n_ia_glow') or o.name in ('n_amb', 'city_glow')
                    or o.name.startswith('ceil_L') or o.name in ('key', 'fill', 'rim', 'rim2', 'face_fill', 'desk_bounce')):
                o.data.use_shadow = False


def _keyed_vis(objs, t0, t1, fps):
    """visible solo dentro del plano [t0, t1)"""
    f0, f1 = int(round(t0 * fps)), int(round(t1 * fps))
    for o in objs:
        for f, h in ((0, True), (f0 - 1, True), (f0, False), (f1, True)):
            o.hide_render = h
            o.keyframe_insert('hide_render', frame=max(0, f))


def _keyed_energy(L, e, t0, t1, fps):
    f0, f1 = int(round(t0 * fps)), int(round(t1 * fps))
    for f, v in ((0, 0.0), (f0 - 1, 0.0), (f0, e), (f1 - 1, e), (f1, 0.0)):
        L.data.energy = v
        L.data.keyframe_insert('energy', frame=max(0, f))


def plano07(shot, fps):
    """luz trabajada del plano 07 (Santi con Clawd en el regazo): clave cálida fuerte que esculpe, contraluces de color
    y bokeh grande de colores al fondo. Todo existe solo durante el plano."""
    t0, t1 = shot['t'], shot['end']
    cam = Vector(shot['pos'])
    tgt = Vector(shot['tgt']) if not isinstance(shot['tgt'], str) else Vector((0, -0.33, 0.76))
    fwd = (tgt - cam).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd).normalized()
    rnd = random.Random(707)
    cols = [('#FFB050', 26), ('#FFC98A', 18), ('#6FD6FF', 22), ('#FF4FB8', 24), ('#A98BFF', 16), ('#FF7A3A', 20)]
    objs = []
    for k in range(70):
        c, e = cols[rnd.randrange(len(cols))]
        d = rnd.uniform(1.4, 3.6)
        p = cam + fwd * d + right * rnd.uniform(-1.1, 1.1) * d * 0.45 + up * rnd.uniform(-0.2, 1.0) * d * 0.4
        if p.z > 2.6 or p.z < 0.9:
            continue
        objs.append(sphere(f'b07_{k}', emis(f'bokeh07_{c}', c, e), tuple(p), rnd.uniform(0.016, 0.042), disp=0, sub=0))
    _keyed_vis(objs, t0, t1, fps)
    face = Vector((0.0, -0.25, 1.06))
    clawd = Vector((0.0, -0.33, 0.70))
    key = add_light('n07_key', 'SPOT', (0.72, -0.22, 1.16), (0, 0, 0), 0, (1.0, 0.6, 0.3), 0.1, spot=(D(38), 0.4))
    _aim(key, (face + clawd) / 2)
    _keyed_energy(key, 210, t0, t1, fps)
    kc = add_light('n07_clawd', 'SPOT', (0.5, -0.5, 0.82), (0, 0, 0), 0, (1.0, 0.6, 0.3), 0.06, spot=(D(30), 0.5))
    _aim(kc, clawd + Vector((0, -0.05, 0)))
    _keyed_energy(kc, 18, t0, t1, fps)
    rc = add_light('n07_rim_cian', 'SPOT', (-0.55, 0.45, 1.95), (0, 0, 0), 0, (0.35, 0.85, 1.0), 0.1, spot=(D(45), 0.4))
    _aim(rc, face + Vector((0, 0.05, -0.08)))
    _keyed_energy(rc, 650, t0, t1, fps)
    rm = add_light('n07_rim_magenta', 'SPOT', (0.6, 0.4, 1.9), (0, 0, 0), 0, (1.0, 0.3, 0.75), 0.1, spot=(D(45), 0.4))
    _aim(rm, face + Vector((0, 0.05, -0.12)))
    _keyed_energy(rm, 600, t0, t1, fps)
    rcl = add_light('n07_rim_clawd', 'SPOT', (-0.3, 0.05, 0.75), (0, 0, 0), 0, (0.45, 0.8, 1.0), 0.08, spot=(D(40), 0.4))
    _aim(rcl, clawd)
    _keyed_energy(rcl, 70, t0, t1, fps)
    for L in (key, kc, rc, rm, rcl):
        L.data.volume_factor = 0.0
    # durante el plano se apagan los rellenos frontales para que la clave esculpa
    f0, f1 = int(round(t0 * fps)), int(round(t1 * fps))
    for n, k in (('n_lapwarm', 0.0), ('n_underdesk', 0.0), ('smonitor_glow', 0.25), ('n_lampkey', 0.35)):
        L = bpy.data.objects.get(n)
        if not L:
            continue
        e0 = L.data.energy
        for f, v in ((0, e0), (f0 - 1, e0), (f0, e0 * k), (f1 - 1, e0 * k), (f1, e0)):
            L.data.energy = v
            L.data.keyframe_insert('energy', frame=max(0, f))
    # naranja de Clawd más saturado para la noche
    m = bpy.data.materials.get('clawd')
    if m:
        base = Vector(hexc('#E8541C')[:3])
        for n in m.node_tree.nodes:
            if n.type == 'VALTORGB':
                n.color_ramp.elements[0].color = (*(base * 0.92), 1)
                n.color_ramp.elements[1].color = (*(base * 1.04), 1)
