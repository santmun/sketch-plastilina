# «A escondidas» — sketch de plastilina stop-motion (Blender 5.2, EEVEE). Construye TODO desde cero.
#
#   Blender -b -P scene.py -- --save                         -> construye y guarda scene.blend
#   Blender -b -P scene.py -- --shotstills --res 360          -> un cuadro por plano en test/shots/
#   Blender -b -P scene.py -- --stills 2.5,10.1 --res 540     -> cuadros sueltos en test/
#   Blender -b -P scene.py -- --anim 0 240 --res 720 --samples 12 --out renders/c00.mp4
#   (render final: --res 1080 --samples 40; ver NOTAS.md y render.sh)
import bpy, sys, os, math, time, json, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mathutils import Vector, Matrix, Euler, Quaternion

ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def arg(name, default=None):
    if name in ARGV:
        i = ARGV.index(name)
        if i + 1 < len(ARGV) and not ARGV[i + 1].startswith('--'):
            return ARGV[i + 1]
        return True
    return default


T0 = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
import clay
from clay import D, hexc, mat4
import rig
from rig import REC, ease
import chars
import office
import perf
from perf import FPS, SHOTS, N_FRAMES

SC = bpy.context.scene
SC.name = 'a_escondidas'
SC.render.fps = FPS
SC.frame_start = 0
SC.frame_end = N_FRAMES - 1

# ============================================================ mundo + render
def setup_render(res_x, samples):
    SC.render.engine = 'BLENDER_EEVEE'
    SC.render.resolution_x = res_x
    SC.render.resolution_y = int(round(res_x * 16 / 9))
    SC.render.resolution_percentage = 100
    SC.view_settings.view_transform = 'AgX'
    try:
        SC.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    SC.view_settings.exposure = float(arg('--exposure', 0.0))
    ee = SC.eevee
    ee.taa_render_samples = samples
    for k, v in (('use_raytracing', True), ('use_shadows', True), ('shadow_ray_count', 2), ('shadow_step_count', 6),
                 ('use_fast_gi', True), ('fast_gi_method', 'GLOBAL_ILLUMINATION')):
        try:
            setattr(ee, k, v)
        except Exception as e:
            print('[skip]', k, e)
    SC.render.film_transparent = False


w = bpy.data.worlds.new('mundo')
w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = hexc('#3A2A20')
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.45
SC.world = w

# ============================================================ set
R = office.build_office()
CW_SPECS = [('Mariana', (-1.85, 0.25), 0.0, '#E2B798', '#7E9A8A', 'bun', '#3A2618', True, False, False, 1),
            ('Beto', (1.95, 0.35), 0.0, '#C78C66', '#5B6E8C', 'short', '#2A1E16', False, False, True, 2),
            ('Lupe', (-2.0, 2.15), 0.0, '#EDC6AA', '#B5654A', 'bob', '#9A948E', True, True, False, 3),
            ('Ivan', (1.9, 2.25), 0.0, '#8C5C40', '#D9A13B', 'curly', '#1D1611', False, False, False, 4)]
office.build_coworker_desks([(n, p, D(y), seed) for n, p, y, *_r, seed in CW_SPECS])
coworkers = []
for n, (x, y), yw, sk, sh, hs, hc, fem, gl, bd, seed in CW_SPECS:
    office.simple_chair(f'{n}_silla', (x, y, 0), D(yw))
    coworkers.append(chars.Coworker(n, (x, y, 0), D(yw), sk, sh, hs, hc, female=fem, glasses=gl, beard=bd))
# sus IA (aparecen en el remate)
critters = [chars.Critter('IA_Mariana', 'gemini', Matrix.Translation((-1.63, 0.26, 0.975))),   # Gemini en su hombro
            chars.Critter('IA_Beto', 'whale', Matrix.Translation((1.66, 0.12, 1.18)) @ Matrix.Rotation(D(-30), 4, 'Z')),
            chars.Critter('IA_Lupe', 'ghost', Matrix.Translation((-1.34, 1.24, 0.09)) @ Matrix.Rotation(D(25), 4, 'Z')),
            chars.Critter('IA_Ivan', 'bot', Matrix.Translation((2.0, 1.41, 1.27)))]

# ---- duelo de western: bola de papel rodando (tumbleweed) y papeles que vuela el viento
DUEL = (perf.V(41.68), perf.V(43.28))
tw = clay.blob('tumbleweed', clay.clay('papel_bola', '#EDE6D6', rough=0.8, prints=0.3), mat4((0, 0, 0), (0, 0, 0), (0.045,) * 3),
               None, deform=lambda v: v * (1 + 0.22 * math.sin(7 * v.x) * math.sin(5 * v.y + 1) * math.sin(6 * v.z + 2)),
               seg=(18, 10), sub=1, disp=0.004, dscale=0.05)
tw.rotation_mode = 'XYZ'
for f in range(int(DUEL[0] * 24) - 2, int(DUEL[1] * 24) + 3):
    x = (f / 24 - DUEL[0]) / (DUEL[1] - DUEL[0])
    tw.location = (-1.0 + 2.3 * x, 0.42 + 0.05 * math.sin(x * 9), 0.045 + 0.03 * abs(math.sin(x * 14)))
    tw.rotation_euler = (0, 2.3 * x / 0.045, 0.3 * x)
    tw.keyframe_insert('location', frame=f)
    tw.keyframe_insert('rotation_euler', frame=f)
for f, h in ((0, True), (int(DUEL[0] * 24) - 1, True), (int(DUEL[0] * 24), False), (int(DUEL[1] * 24) + 1, True)):
    tw.hide_render = h
    tw.keyframe_insert('hide_render', frame=f)
for i in range(4):
    o = bpy.data.objects.get(f'sheet{i}')
    if not o:
        continue
    r0 = o.rotation_euler.copy()
    l0 = o.location.copy()
    for f in range(int(DUEL[0] * 24) - 1, int(DUEL[1] * 24) + 4):
        t = f / 24
        k = max(0.0, min(1.0, (t - DUEL[0]) / 0.2)) * max(0.0, min(1.0, (DUEL[1] + 0.1 - t) / 0.2))
        o.rotation_euler = (r0.x + D(10) * k * math.sin(t * 23 + i) * (i == 3), r0.y + D(6) * k * math.sin(t * 19 + i),
                            r0.z + D(5) * k * math.sin(t * 17 + 2 * i))
        o.location = l0 + Vector((0, 0, 0.01 * k * (i == 3) * abs(math.sin(t * 21))))
        o.keyframe_insert('rotation_euler', frame=f)
        o.keyframe_insert('location', frame=f)

# diapositiva en el monitor de Santi
slideJ = rig.Joint('slideJ', R['scr_world'])
_before = set(bpy.data.objects)
office.slide(None)
slide_objs = [o for o in bpy.data.objects if o not in _before]
slideJ.attach(slide_objs, 'local')

# ============================================================ personajes
santi = chars.Santi((0, 0, 0), 0.0, chair=office.office_chair)
clawd = chars.Clawd('Clawd', u=0.026)
boss = chars.Boss((0, 0, 0), 0.0)
gpt = chars.GPT('GPT', 0.11, parent=boss.spine, local=(0, 0, 0))

# ============================================================ luces (cálidas, dirección marcada)
L = office.add_light
L('key', 'AREA', (-1.5, -1.9, 2.3), (D(55), 0, D(-38)), 130, (1.0, 0.88, 0.74), 1.4)
L('fill', 'AREA', (1.6, -2.2, 1.3), (D(75), 0, D(36)), 35, (0.95, 0.93, 0.9), 2.0)
L('rim', 'SPOT', (0.7, 1.3, 2.1), (D(-42), 0, D(155)), 120, (1.0, 0.76, 0.5), 0.3, spot=(D(55), 0.6))
L('rim2', 'SPOT', (-0.9, 1.1, 1.9), (D(-45), 0, D(-150)), 70, (1.0, 0.8, 0.55), 0.3, spot=(D(55), 0.6))
face = L('face_fill', 'AREA', (0.0, -1.0, 0.92), (0, 0, 0), 14, (1.0, 0.9, 0.78), 0.9)
face.rotation_euler = (Vector((0, -0.25, 1.05)) - face.location).to_track_quat('-Z', 'Y').to_euler()
L('desk_bounce', 'AREA', (0.0, -0.75, 0.62), (D(-75), 0, 0), 10, (1.0, 0.86, 0.7), 0.7)

# look v2: oficina de noche (LOOK=dia conserva la versión anterior)
LOOK = os.environ.get('LOOK', 'noche')
if LOOK == 'noche':
    import night
    night.apply(SC, critters, perf.AI_POP, FPS, perf.SHOTS)
DOFK = 0.6 if LOOK == 'noche' else 1.0

# ============================================================ actuación -> keyframes
def probe():
    hw = santi.head.world()
    u = clawd.u
    return {
        'santi_head': hw.to_translation(),
        'santi_face': hw @ Vector((0, -0.10, -0.02)),
        'santi_lap': santi.root.world() @ Vector((0, -0.25, 0.62)),
        'santi_chest': santi.spine.world() @ Vector((0, -0.06, 0.32)),
        'clawd_eyes': clawd.body.world() @ Vector((0, -1.6 * u, 2.5 * clawd.TALL * u)),
        'clawd_eyeR': clawd.body.world() @ Vector((-3.5 * u, -1.6 * u, 2.5 * clawd.TALL * u)),
        'clawd_eyeL': clawd.body.world() @ Vector((3.5 * u, -1.6 * u, 2.5 * clawd.TALL * u)),
        'boss_head': boss.head.world().to_translation(),
        'gpt': gpt.root.world().to_translation(),
        'boss_gpt': (boss.head.world().to_translation() + gpt.root.world().to_translation()) / 2,
        'monitor': R['scr_world'].to_translation(),
        'receipt_end': gpt.receipt.world() @ Vector((0, -0.05, -chars.RECEIPT_LEN + 0.06)),
        'gemini': critters[0].root.world().to_translation(),
        'mariana_face': coworkers[0].head.world() @ Vector((0, -0.12, -0.02)),
        'gemini_mariana': (coworkers[0].head.world().to_translation() + critters[0].root.world().to_translation()) / 2,
    }


def shot_at(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if t >= s['t'] - 1e-6:
            cur = s
    return cur


t1 = time.time()
PROBES = {}
for f in range(0, N_FRAMES + 1, 2):
    t = f / FPS
    sh = shot_at(t)
    santi.apply(perf.santi(t, sh.get('cheat_santi')), t)
    santi.record(f)
    clawd.apply(perf.clawd(t, sh.get('cheat_clawd')), t)
    clawd.record(f)
    boss.apply(perf.boss(t), t)
    boss.record(f)
    gpt.apply(perf.gpt(t), t)
    gpt.record(f)
    for i, cw in enumerate(coworkers):
        cw.apply(perf.coworker(i, t), t)
        cw.record(f)
    for i, cr in enumerate(critters):
        cr.apply(perf.critter(i, t), t)
        cr.record(f)
    # puerta: entreabierta, se azota al entrar el jefe
    ta = perf.U(t)   # tiempo de autor
    dang = perf.K((0, -72), (33.85, -72), (34.02, -118, 'out'), (34.3, -108), (71, -108))(ta)
    R['drawer'].loc = Vector((0, perf.DRAWER(ta), 0))
    R['drawer'].record(f, scale=False)
    R['paw'].scl = Vector((1, 1, 1)) * max(1e-4, perf.PAW(ta))
    R['paw'].record(f)
    R['door'].rot = rig.qe(0, 0, D(dang))
    R['door'].record(f, scale=False)
    slideJ.scl = Vector((1, 1, 1)) * (1.0 if t >= perf.V(perf.W(21.9)) else 1e-4)
    slideJ.record(f)
    PROBES[f] = probe()
print(f'[anim] poses {time.time() - t1:.1f}s')


# ============================================================ cámaras (una por plano, con marcadores)
def resolve(spec, f):
    if isinstance(spec, str):
        fe = max(0, min(f - (f % 2), max(PROBES)))
        return PROBES[fe][spec].copy()
    return Vector(spec)


def noise(seed, t):
    return sum(math.sin(t * fr + seed * ph) * a for fr, ph, a in ((23.0, 1.3, 0.5), (37.0, 2.1, 0.3), (51.0, 0.7, 0.2)))


def western_overlays(co, cd, f0, f1):
    """letterbox + viraje cálido pegados a la cámara del plano del duelo"""
    d = 0.02
    bars = clay.simple('letterbox', '#000000', rough=1.0)
    tint = bpy.data.materials.get('viraje_western')
    if tint is None:
        tint = bpy.data.materials.new('viraje_western')
        tint.use_nodes = True
        nt = tint.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        tr.inputs['Color'].default_value = (1.0, 0.78, 0.5, 1)
        nt.links.new(tr.outputs[0], out.inputs[0])
        try:
            tint.surface_render_method = 'BLENDED'   # no escribe profundidad: no engaña al desenfoque
        except Exception:
            pass
    # tamaño del cuadro a distancia d (sensor 36 mm en el lado largo = vertical)
    hh = d * 18.0 / cd.lens
    hw = hh * 9 / 16
    bh = hh * 0.12
    for k, sgn in (('top', 1), ('bot', -1)):
        clay.box(f'{co.name}_lb_{k}', bars, (0, sgn * (hh - bh), -d), (hw * 1.3, bh, 0.0002), co, bevel=0)
    clay.box(f'{co.name}_tinte', tint, (0, 0, -d * 1.02), (hw * 1.5, hh * 1.2, 0.0002), co, bevel=0)
    cd.clip_start = 0.005


CAMS = []
for i, s in enumerate(SHOTS):
    f0 = int(round(s['t'] * FPS))
    f1 = int(round(s['end'] * FPS))
    cd = bpy.data.cameras.new(f'CAM_{i + 1:02d}')
    cd.lens = s['lens']
    cd.sensor_width = 36
    cd.sensor_fit = 'AUTO'
    cd.clip_start = 0.01
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = max(1.4, s.get('f', 2.8) * DOFK)
    cd.dof.aperture_blades = 6
    co = bpy.data.objects.new(f'CAM_{i + 1:02d}', cd)
    SC.collection.objects.link(co)
    co.rotation_mode = 'XYZ'
    mid = (f0 + f1) // 2
    fixed_tgt = resolve(s['tgt'], mid if not s.get('tgt_at') else int(s['tgt_at'] * FPS))
    if 'pos' in s:
        base_pos = Vector(s['pos'])
    else:
        base_pos = fixed_tgt + Vector(s['off'])
    prev = None
    for f in range(f0 - 1, f1 + 2):
        t = f / FPS
        x = (f - f0) / max(1, (f1 - f0))
        xe = ease(min(1.0, (t - s['t']) / s['ease_dur'])) if 'ease_dur' in s else x
        tgt = resolve(s['tgt'], f) if s.get('track') else fixed_tgt.copy()
        if s.get('track') and prev is not None:
            tgt = prev.lerp(tgt, 0.25)
        prev = tgt.copy()
        if 'end_off' in s:
            pos = fixed_tgt + Vector(s['off']).lerp(Vector(s['end_off']), xe)
            REC.key(cd, 'lens', 0, f, s['lens'] + (s.get('end_lens', s['lens']) - s['lens']) * xe, 'LINEAR')
        elif 'pos' in s and not s.get('track'):
            pos = base_pos.copy()
        elif 'pos' in s:
            pos = base_pos.copy()
        else:
            pos = base_pos.copy()
        push = s.get('push', 1.0)
        if push != 1.0:
            pos = tgt + (pos - tgt) * (1 + (push - 1) * ease(x))
        if 'drift' in s:
            pos = pos + Vector(s['drift']) * ease(x)
        if not s.get('western'):
            # micro movimiento constante (como el referente): 4 % de dolly lineal, alternando entrada/salida,
            # más 1.5 % de deriva lateral; se suma encima de cualquier movimiento propio del plano
            d0 = (pos - tgt).length
            sgn = -1 if i % 2 == 0 else 1
            pos = tgt + (pos - tgt) * (1 + sgn * 0.04 * x)
            side = (tgt - pos).cross(Vector((0, 0, 1)))
            if side.length > 1e-6:
                pos = pos + side.normalized() * (0.015 * d0 * (x - 0.5) * (1 if i % 3 else -1))
        rot = (tgt - pos).to_track_quat('-Z', 'Y')
        if 'dutch' in s:   # ángulo holandés (duelo)
            rot = rot @ Quaternion((0, 0, 1), D(s['dutch']))
        rot = rot.to_euler()
        if 'shake' in s:
            ts, amp = s['shake']
            if t >= ts:
                k = amp * math.exp(-(t - ts) * 5.0)
                rot.x += D(1.4) * k * noise(1, t)
                rot.y += D(1.0) * k * noise(2, t)
                rot.z += D(1.4) * k * noise(3, t)
        # respiración de cámara en mano, muy leve
        rot.x += D(0.12) * math.sin(t * 1.7 + i)
        rot.z += D(0.12) * math.sin(t * 1.3 + 2 * i)
        for k in range(3):
            REC.key(co, 'location', k, f, pos[k], 'LINEAR')
            REC.key(co, 'rotation_euler', k, f, rot[k], 'LINEAR')
        fp = resolve(s['focus'], f) if 'focus' in s else tgt
        REC.key(cd, 'dof.focus_distance', 0, f, max(0.05, (fp - pos).length), 'LINEAR')
    m = SC.timeline_markers.new(s['n'], frame=f0)
    m.camera = co
    CAMS.append(co)
    if s.get('western'):
        western_overlays(co, cd, f0, f1)
SC.camera = CAMS[0]
nk = REC.write()
print(f'[anim] {nk} keyframes, build total {time.time() - T0:.1f}s')

# metadatos de planos para subtítulos y mezcla
with open(os.path.join(HERE, 'shots.json'), 'w') as fh:
    json.dump([dict(n=s['n'], t=s['t'], end=s['end'], sub=s.get('sub', 'low')) for s in SHOTS], fh, ensure_ascii=False,
              indent=1)

# ============================================================ salidas
res = int(arg('--res', 540))
samples = int(arg('--samples', 16))
setup_render(res, samples)
if arg('--save'):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'scene.blend'))
    print('[save] scene.blend')


def render_still(f, path):
    SC.frame_set(f)
    SC.render.image_settings.file_format = 'JPEG'
    SC.render.image_settings.quality = 88
    SC.render.filepath = path
    bpy.ops.render.render(write_still=True)


if arg('--probe'):
    # diagnóstico: posición de cámara, objetivo y primer objeto que cruza el rayo cámara->objetivo
    dg = bpy.context.evaluated_depsgraph_get()
    for i, s in enumerate(SHOTS):
        f = int(round((s['t'] + s['end']) / 2 * FPS))
        SC.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        co = CAMS[i]
        cp = co.matrix_world.to_translation()
        fwd = co.matrix_world.to_3x3() @ Vector((0, 0, -1))
        hit, loc, nor, idx, ob, mw = SC.ray_cast(dg, cp, fwd, distance=20)
        pr = PROBES[max(0, min(f - f % 2, max(PROBES)))]
        print(f"[probe] {i + 1:02d} {s['n'][:26]:26s} cam=({cp.x:+.2f},{cp.y:+.2f},{cp.z:+.2f}) "
              f"hit={ob.name if hit else '-':22s} d={(loc - cp).length if hit else -1:.2f} "
              f"head=({pr['santi_head'].x:+.2f},{pr['santi_head'].y:+.2f},{pr['santi_head'].z:+.2f}) "
              f"clawd=({pr['clawd_eyes'].x:+.2f},{pr['clawd_eyes'].y:+.2f},{pr['clawd_eyes'].z:+.2f}) "
              f"boss=({pr['boss_head'].x:+.2f},{pr['boss_head'].y:+.2f},{pr['boss_head'].z:+.2f})")
if arg('--stills'):
    os.makedirs(os.path.join(HERE, 'test'), exist_ok=True)
    for tt in str(arg('--stills')).split(','):
        f = int(round(float(tt) * FPS))
        render_still(f, os.path.join(HERE, 'test', f'still_{float(tt):05.2f}.jpg'))
if arg('--shotstills'):
    d = os.path.join(HERE, 'test', 'shots')
    os.makedirs(d, exist_ok=True)
    only = str(arg('--only', '')).split(',') if arg('--only') else None
    for i, s in enumerate(SHOTS):
        if only and str(i + 1) not in only:
            continue
        fr = s.get('probe_frac', [0.5])
        for k, fr_ in enumerate(fr if isinstance(fr, list) else [fr]):
            f = int(round((s['t'] + (s['end'] - s['t']) * fr_) * FPS))
            render_still(f, os.path.join(d, f'{i + 1:02d}_{k}.jpg'))
if arg('--keyshots'):
    # planos clave en PNG: --keyshots 05:0.5,13:0.5 -> look/plano-05.png ...
    os.makedirs(os.path.join(HERE, 'look'), exist_ok=True)
    SC.render.image_settings.file_format = 'PNG'
    kdir = os.path.join(HERE, str(arg('--keydir', 'look')))
    os.makedirs(kdir, exist_ok=True)
    for item in str(arg('--keyshots')).split(','):
        n, fr_ = item.split(':')[:2]
        out = item.split(':')[2] if item.count(':') > 1 else None
        s = [x for x in SHOTS if x['n'].split(' ')[0] == n][0] if n.startswith('S') else SHOTS[int(n) - 1]
        SC.frame_set(int(round((s['t'] + (s['end'] - s['t']) * float(fr_)) * FPS)))
        SC.render.filepath = os.path.join(kdir, out or f"plano-{s['n'].split(' ')[0][1:]}.png")
        bpy.ops.render.render(write_still=True)
if arg('--santiframes'):
    # tira de revisión de manos: cámara fija sobre Santi (no la del plano): --santiframes 13.4:15.6:0.1
    a_, b_, st = [float(x) for x in str(arg('--santiframes')).split(':')]
    d = os.path.join(HERE, 'test', 'manos')
    os.makedirs(d, exist_ok=True)
    cdm = bpy.data.cameras.new('CAM_manos'); cdm.lens = 30
    com = bpy.data.objects.new('CAM_manos', cdm); SC.collection.objects.link(com)
    for m in SC.timeline_markers:
        m.camera = com
    SC.camera = com
    tt = a_
    while tt <= b_ + 1e-6:
        f = int(round(tt * FPS))
        SC.frame_set(f)
        hd = PROBES[max(0, min(f - f % 2, max(PROBES)))]['santi_head']
        front = Vector((-0.42, -0.85, 0.12)) if tt < perf.V(34.6) else Vector((0.5, 0.62, 0.12))
        com.location = hd + front
        com.rotation_euler = (hd - Vector((0, 0, 0.12)) - com.location).to_track_quat('-Z', 'Y').to_euler()
        render_still(f, os.path.join(d, f'm_{tt:05.2f}.jpg'))
        tt += st
if arg('--frames'):
    # tira de cuadros: --frames 10.0:12.0:0.25
    a_, b_, st = [float(x) for x in str(arg('--frames')).split(':')]
    d = os.path.join(HERE, 'test', 'frames')
    os.makedirs(d, exist_ok=True)
    tt = a_
    while tt <= b_ + 1e-6:
        render_still(int(round(tt * FPS)), os.path.join(d, f'f_{tt:05.2f}.jpg'))
        tt += st
if arg('--anim'):
    i = ARGV.index('--anim')
    fa, fb = int(ARGV[i + 1]), int(ARGV[i + 2])
    SC.frame_start, SC.frame_end = fa, fb
    out = os.path.join(HERE, str(arg('--out', 'renders/chunk.mp4')))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    SC.render.image_settings.media_type = 'VIDEO' if hasattr(SC.render.image_settings, 'media_type') else None
    SC.render.image_settings.file_format = 'FFMPEG'
    SC.render.ffmpeg.format = 'MPEG4'
    SC.render.ffmpeg.codec = 'H264'
    SC.render.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS' if arg('--hq') else 'HIGH'
    SC.render.ffmpeg.ffmpeg_preset = 'GOOD'
    SC.render.ffmpeg.audio_codec = 'NONE'
    SC.render.filepath = out
    SC.render.use_file_extension = False
    t2 = time.time()
    bpy.ops.render.render(animation=True)
    print(f'[render] frames {fa}-{fb} en {time.time() - t2:.1f}s -> {out}')
