# scene.py — construye y renderiza un sketch de plastilina desde un proyecto (Blender 5.2, EEVEE, sin interfaz).
#
#   B=/Applications/Blender.app/Contents/MacOS/Blender
#   $B -b -P engine/scene.py -- --project P --retratos [--res 720]          retratos de cada personaje (aprobar look)
#   $B -b -P engine/scene.py -- --project P --shotstills --res 360          un cuadro por plano -> P/test/shots/
#   $B -b -P engine/scene.py -- --project P --stills 2.5,10.1 --res 540     cuadros sueltos -> P/test/
#   $B -b -P engine/scene.py -- --project P --check                        choques (mascota-cuerpo, mano-cabeza) y planos tapados
#   $B -b -P engine/scene.py -- --project P --anim 0 239 --res 720 --samples 12 --out renders/c720_0000.mp4
#   (render por tramos con guardia de disco: engine/render.sh)
import bpy, sys, os, math, time, json, random
ENGINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE)
from mathutils import Vector, Matrix

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
random.seed(1234)          # determinista: cada tramo se renderiza en otro proceso
import clay
from clay import D, hexc, mat4
from rig import REC, Joint
from project import Project
from characters.humans import Human
from characters import mascots
from characters.parts import luminance, TINY
import sets
import perform
import cameras
import looks

PRJ_DIR = arg('--project')
assert PRJ_DIR, 'falta --project <carpeta>'
prj = Project(PRJ_DIR)
FPS = prj.fps
SC = bpy.context.scene
SC.render.fps = FPS
look = prj.look
LUZ = os.environ.get('LOOK', look.get('luz', 'noche'))


def warn_colors():
    """la piel y la ropa clara se queman a blanco bajo la lámpara y los monitores: avisar antes de renderizar"""
    for n, s in prj.cast.items():
        if s.get('tipo', 'humano') != 'humano':
            continue
        cols = {'piel': s.get('piel', '#D4956C')}
        for k, v in s.get('ropa', {}).items():
            if isinstance(v, str) and v.startswith('#'):
                cols[f'ropa.{k}'] = v
        for k, v in cols.items():
            lim = 0.72 if k == 'piel' else 0.80
            if luminance(v) > lim and not k.endswith(('camisa', 'zapatos')):
                print(f'[aviso] {n}.{k} = {v} (luminancia {luminance(v):.2f} > {lim}): se va a quemar a blanco con la luz; '
                      f'oscurécelo (la camiseta crema de Santi se bajó de #EFE4CF a #D6C7A8)')


def build_chars(seats):
    chars = {}
    for name, spec in prj.cast.items():
        if spec.get('tipo', 'humano') == 'humano':
            lug0 = None
            b = prj.blocking.get('personajes', {}).get(name, {})
            if b.get('lugar'):
                lug0 = b['lugar'][0][1]
            lug0 = lug0 or spec.get('lugar')
            chair = None
            if spec.get('postura', 'sentado') == 'sentado' and lug0 in seats:
                chair = seats[lug0].get('chair')
            chars[name] = Human(name, spec, chair_fn=chair)
        else:
            tex = spec.get('recibo_textura')
            chars[name] = mascots.build(name, spec, prj.path(tex) if tex else None)
    return chars


def occupied_seats():
    out = set()
    for name, spec in prj.cast.items():
        b = prj.blocking.get('personajes', {}).get(name, {})
        lug = b['lugar'][0][1] if b.get('lugar') else spec.get('lugar')
        if lug:
            out.add(lug)
    return out


# ============================================================ retratos para aprobar el look (no necesitan audio)
if arg('--retratos'):
    from sets.common import add_light, aim
    res = int(arg('--res', 720))
    looks.render_settings(SC, res, int(arg('--samples', 32)))
    SC.render.resolution_y = res
    try:
        SC.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    w = bpy.data.worlds.new('w')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = hexc('#2A3036')
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
    SC.world = w
    chars = build_chars({})
    outdir = prj.path('look')
    os.makedirs(outdir, exist_ok=True)
    names = list(chars)
    for i, name in enumerate(names):
        ch = chars[name]
        x = (i - (len(names) - 1) / 2) * 1.4
        if ch.kind == 'humano':
            sit = ch.sit
            arms = {'L': (((0.1, -0.24, 0.62) if sit else (0.2, 0.0, 0.0)), (0.5, 1.0, 0.0), (0, 0, 0)),
                    'R': (((-0.1, -0.24, 0.62) if sit else (-0.2, 0.0, 0.0)), (-0.5, 1.0, 0.0), (0, 0, 0))}
            ch.apply(dict(pos=(x, 0, 0), lean=4 if sit else 0, head=(-3, 0, 0), gaze=(6, 1), lidU=28, lidL=30,
                          mouth=dict(smile=0.35), arms=arms, arm_space={'L': 'root' if sit else 'spine', 'R': 'root' if sit else 'spine'}), 0)
        else:
            clay.box(f'pedestal_{name}', clay.card('pedestal', '#4A525A'), (x, 0, 0.37), (0.25, 0.25, 0.37), bevel=0.004)
            ch.apply(dict(pos=(x, 0, 0.74), eyes='happy' if ch.kind == 'clawd' else 'normal', armL=(10, 0), armR=(10, 0)), 0)
        ch.record(1)
    REC.write()
    SC.frame_set(1)
    bpy.context.view_layer.update()
    clay.box('bg', clay.card('fondo', '#4A525A', rough=0.95, grain=0.4), (0, 2.0, 1.0), (8, 0.02, 2.5), bevel=0)
    clay.box('piso', clay.card('piso_retrato', '#3A4046', rough=0.95), (0, 0, -0.01), (8, 4, 0.01), bevel=0)
    for i, name in enumerate(names):
        ch = chars[name]
        hw = ch.world_point('ojos')
        sm = 0.45 if ch.kind != 'humano' else 1.0
        lts = []
        for ln, off, e, c, sz in (('key', (-0.6, -0.9, 0.45), 55, (1.0, 0.86, 0.72), 0.8), ('rim', (0.6, 0.75, 0.35), 45, (0.75, 0.85, 1.0), 0.5),
                                  ('fill', (0.9, -0.9, 0.0), 22, (0.92, 0.95, 1.0), 1.5)):
            L = add_light(f'{ln}_{name}', 'AREA', tuple(hw + Vector(off) * sm), (0, 0, 0), e * sm * sm, c, sz * sm)
            aim(L, hw)
            lts.append(L)
        cd = bpy.data.cameras.new(f'c_{name}')
        cd.lens = 85
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = 4.0
        co = bpy.data.objects.new(f'cam_{name}', cd)
        SC.collection.objects.link(co)
        yaw = float(arg('--yaw', 20))
        dvec = Vector((math.sin(D(yaw)), -math.cos(D(yaw)), 0.05)).normalized()
        if ch.kind == 'humano':
            tgt = hw + Vector((0, 0.02, -0.12 if arg('--cuerpo') else 0.03))
            dist = 2.6 if arg('--cuerpo') else 1.45
        else:
            tgt = ch.world_point('centro')
            dist = 0.9 * (ch.half_h / 0.06)
        co.location = tgt + dvec * dist
        co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
        cd.dof.focus_distance = (tgt - co.location).length
        SC.camera = co
        for other in bpy.data.objects:
            if other.type == 'LIGHT':
                other.hide_render = other not in lts
        SC.render.filepath = os.path.join(outdir, f'{name}.png')
        bpy.ops.render.render(write_still=True)
        print(f'[retrato] {SC.render.filepath}')
    sys.exit(0)

# ============================================================ escena completa
assert prj.lines, 'falta build/timeline.json (corre scripts/timeline.py tras el TTS)'
SC.name = os.path.basename(prj.root)
SC.frame_start = 0
SC.frame_end = prj.n_frames - 1
warn_colors()
set_name = look.get('set', 'office_night')
ctx = dict(prj=prj, params=look.get('set_params', {}), cast=prj.cast, occupied=occupied_seats(), look=look)
SETI = sets.load(set_name).build(ctx)
chars = build_chars(SETI['seats'])
order = [n for n, c in chars.items() if c.kind == 'humano'] + [n for n, c in chars.items() if c.kind != 'humano']
perf = perform.Performer(prj, chars, SETI)
SHOTS = cameras.resolve_shots(prj, prj.shots_spec)
assert SHOTS, 'shots.json vacío (genera un borrador con scripts/auto_shots.py)'


def shot_at(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if t >= s['t'] - 1e-6:
            cur = s
    return cur


def apply_cheat(p, cheat):
    if not cheat:
        return p
    cheat = dict(cheat)
    for k in ('yaw', 'tilt', 'lean'):
        if 'd' + k in cheat:
            p[k] = p.get(k, 0) + cheat.pop('d' + k)
    if 'dpos' in cheat:
        p['pos'] = tuple(Vector(p['pos']) + Vector(cheat.pop('dpos')))
    p.update(cheat)
    return p


# pre-pase: estado inicial (miradas y anclajes dependen de dónde están los demás)
for _ in range(2):
    for n in order:
        chars[n].apply(perf.pose(n, 0.0), 0.0)
perf.state = {n: {} for n in chars}
for n in order:
    chars[n].apply(perf.pose(n, 0.0), 0.0)
EYES_LOCAL = {n: chars[n].root.world().inverted() @ chars[n].world_point('ojos') for n in chars}

# puntos que piden las cámaras
PROBE_SPECS = set()
for s in SHOTS:
    for k in ('tgt', 'objetivo', 'focus'):
        v = s.get(k)
        if isinstance(v, str):
            PROBE_SPECS.add(v)


def probe_now(spec):
    if isinstance(spec, (list, tuple)):
        return Vector(spec)
    if '|' in spec:
        ps = [probe_now(x) for x in spec.split('|')]
        return sum(ps, Vector()) / len(ps)
    key = spec[4:] if spec.startswith('set:') else spec
    if key in SETI['probes']:
        return Vector(SETI['probes'][key])
    who = spec.split('.')[0]
    if who in chars:
        return chars[who].world_point(spec.split('.', 1)[1] if '.' in spec else 'ojos')
    if key in SETI['anchors']:
        p, _, _ = perf.anchor_point(key, 0.0)
        return p + Vector((0, 0, 0.05))
    raise KeyError(f'objetivo de cámara desconocido: {spec}')


t1 = time.time()
PROBES, FACING, EYES = {}, {}, {}
for f in range(0, prj.n_frames + 1, 2):
    t = f / FPS
    sh = shot_at(t)
    for n in order:
        p = apply_cheat(perf.pose(n, t), sh.get('trucos', {}).get(n))
        chars[n].apply(p, t)
        chars[n].record(f)
    for k, prop in SETI['props'].items():
        prop.apply(perf.props[k](t) if k in perf.props else prop.default)
        prop.record(f)
    PROBES[f] = {s: probe_now(s) for s in PROBE_SPECS}
    FACING[f] = {n: (c.head.world().to_3x3() @ Vector((0, -1, 0))).normalized() if c.kind == 'humano' else c.facing()
                 for n, c in chars.items()}
    EYES[f] = {n: c.world_point('ojos') for n, c in chars.items()}
print(f'[anim] poses {time.time() - t1:.1f}s')


def _fe(f):
    return max(0, min(f - (f % 2), max(PROBES)))


def probe(spec, f):
    if isinstance(spec, (list, tuple)):
        return Vector(spec)
    return PROBES[_fe(f)][spec].copy()


def facing(spec, f):
    fe = _fe(f)
    if isinstance(spec, str) and '|' in spec:
        a, b = [x.split('.')[0] for x in spec.split('|')[:2]]
        if a in chars and b in chars:
            pa, pb = EYES[fe][a], EYES[fe][b]
            ab = Vector((0, 0, 0))
            for x, w in ((a, 1), (b, 1)):
                ab += Vector((FACING[fe][x].x, FACING[fe][x].y, 0)) * w
            n = Vector((-(pb - pa).y, (pb - pa).x, 0))
            if n.length < 1e-6:
                return ab
            n.normalize()
            return n if n.dot(ab) >= 0 else -n
    who = spec.split('.')[0] if isinstance(spec, str) else None
    if who in chars:
        return FACING[fe][who]
    return Vector((0, -1, 0))


def part_map():
    """objeto malla -> (personaje, parte) caminando la jerarquía de articulaciones"""
    owner = {}
    for n, ch in chars.items():
        head = ch.head.obj if hasattr(ch, 'head') else None
        arms = set()
        if hasattr(ch, 'arms') and ch.kind == 'humano':
            for a in ch.arms.values():
                arms |= {a.sh.obj, a.el.obj, a.wr.obj}
        for o in bpy.data.objects:
            if o.type not in ('MESH', 'CURVE', 'FONT'):
                continue
            p, part = o.parent, None
            while p is not None:
                if head is not None and p == head:
                    part = 'cabeza'
                    break
                if p in arms:
                    part = 'mano' if 'hand' in o.name else 'brazo'
                    break
                if p == ch.root.obj:
                    part = 'cuerpo' if ch.kind == 'humano' else 'mascota'
                    break
                p = p.parent
            if part:
                owner[o.name] = (n, part)
    return owner



nk_chars = REC.write()          # claves de personajes/props: ya se puede evaluar cualquier cuadro (para los rayos)
OWNER = part_map()


def path_block(tgt, pos, target_spec):
    """distancia desde el objetivo hasta el primer objeto que tapa la vista (ignora al propio sujeto), o None"""
    who_ok = {x.split('.')[0] for x in str(target_spec).split('|')} if isinstance(target_spec, str) else set()
    dg = bpy.context.evaluated_depsgraph_get()
    d = pos - tgt
    dist = d.length
    if dist < 1e-4:
        return None
    dn = d / dist
    o, travelled = tgt + dn * 0.02, 0.02
    for _ in range(12):
        hit, loc, nor, idx, ob, mw = SC.ray_cast(dg, o, dn, distance=dist - travelled)
        if not hit:
            return None
        mat = ob.active_material.name if ob.active_material else ''
        if OWNER.get(ob.name, (None,))[0] in who_ok or mat.startswith(('vidrio', 'viraje')) or ob.name.startswith('CAM_'):
            step = (loc - o).length + 0.003
            o, travelled = loc + dn * 0.003, travelled + step
            continue
        return travelled + (loc - o).length
    return None


def free_camera(s, tgt, pos, f, spec):
    """encuadre automático sin muebles enfrente: prueba otros ángulos/alturas; si nada sirve, acerca la cámara"""
    SC.frame_set(f)
    if path_block(tgt, pos, spec) is None and pos.z > 0.05:
        return pos, None
    rel = pos - tgt
    # candidatos ordenados por «costo»: primero subir un poco o acercarse sin girar; girar mucho es lo último
    cands = []
    for k in (1.0, 0.85, 0.7):
        for dz in (0.0, 0.1, 0.2, -0.08):
            for ang in (0, 15, -15, 30, -30, 45, -45, 70, -70, 90, -90):
                if (k, dz, ang) == (1.0, 0.0, 0):
                    continue
                cands.append((abs(ang) / 15 + abs(dz) / 0.1 * 0.8 + (1 - k) / 0.15, k, dz, ang))
    for _, k, dz, ang in sorted(cands):
        c, sn = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        r = Vector((rel.x * c - rel.y * sn, rel.x * sn + rel.y * c, rel.z)) * k + Vector((0, 0, dz))
        p = tgt + r
        if p.z < 0.05:
            continue
        if path_block(tgt, p, spec) is None:
            return p, f'ángulo {ang:+d}°, altura {dz:+.2f}, distancia x{k:.2f}'
    hb = path_block(tgt, pos, spec)
    if hb and hb > 0.3 * rel.length:
        return tgt + rel.normalized() * (hb - 0.04), 'acercada'
    return pos, 'tapada (revisa a mano)'


looks.apply(SC, LUZ, SETI, ctx, chars, EYES_LOCAL)
DOFK = float(look.get('dof', 0.6 if LUZ == 'noche' else 1.0))


def subject_k(spec):
    """tamaño relativo del sujeto para encuadres automáticos (humano = 1; mascotas según su altura)"""
    if not isinstance(spec, str) or '|' in spec:
        return 1.0
    w = spec.split('.')[0]
    if w in chars and chars[w].kind != 'humano':
        return 0.85 * max(0.35, min(1.0, 2 * chars[w].half_h * float(prj.cast[w].get('escala', 1.0)) / 0.16))
    return 1.0


CAMS = cameras.build(SC, SHOTS, probe, facing, FPS, DOFK, subject_k, free_camera, SETI.get('publico', Vector((0, -1, 0))))
for s in SHOTS:
    print(f"[plano] {s['n'][:30]:30s} t={s['t']:6.2f}-{s['end']:6.2f} lente={s['lens']:4.0f} cam={s['_cam']} obj={s['_tgt']}"
          + (f"  [ajuste: {s['_ajuste']}]" if s.get('_ajuste') else ''))
nk = nk_chars + REC.write()
print(f'[anim] {nk} keyframes, build total {time.time() - T0:.1f}s')

os.makedirs(prj.path('build'), exist_ok=True)
with open(prj.path('build', 'shots_resolved.json'), 'w') as fh:
    json.dump([dict(n=s['n'], t=s['t'], end=s['end'], sub=s.get('sub', 'low'), lens=round(s['lens'], 1)) for s in SHOTS], fh,
              ensure_ascii=False, indent=1)
with open(prj.path('build', 'eventos.json'), 'w') as fh:
    json.dump(perf.hop_events(), fh, ensure_ascii=False, indent=1)

res = int(arg('--res', 540))
samples = int(arg('--samples', 16))
looks.render_settings(SC, res, samples, float(arg('--exposure', look.get('exposicion', 0.0))))
if LUZ == 'noche':
    try:
        SC.view_settings.look = 'AgX - Punchy'
    except Exception:
        pass
if arg('--save'):
    bpy.ops.wm.save_as_mainfile(filepath=prj.path('build', 'scene.blend'))
    print('[save] build/scene.blend')


def render_still(f, path):
    SC.frame_set(f)
    SC.render.image_settings.file_format = 'JPEG'
    SC.render.image_settings.quality = 88
    SC.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ============================================================ revisión automática de choques y planos tapados
def run_check():
    from mathutils.bvhtree import BVHTree
    import bmesh
    owner = OWNER
    groups = {}
    for on, (n, part) in owner.items():
        groups.setdefault((n, part), []).append(bpy.data.objects[on])

    def tree(objs, dg, shrink=0.0):
        """BVH en mundo; shrink > 0 encoge la malla hacia adentro (tolera contacto superficial, no penetración)"""
        bm = bmesh.new()
        for o in objs:
            oe = o.evaluated_get(dg)
            try:
                me = oe.to_mesh()
            except RuntimeError:
                continue
            tb = bmesh.new()
            tb.from_mesh(me)
            tb.transform(oe.matrix_world)
            if shrink:
                tb.normal_update()
                for v in tb.verts:
                    v.co -= v.normal * shrink
            m2 = bpy.data.meshes.new('tmp')
            tb.to_mesh(m2)
            tb.free()
            bm.from_mesh(m2)
            bpy.data.meshes.remove(m2)
            oe.to_mesh_clear()
        tr = BVHTree.FromBMesh(bm)
        bm.free()
        return tr

    issues = []
    step = int(arg('--check-step', 6))
    humans = [n for n in chars if chars[n].kind == 'humano']
    masc = [n for n in chars if chars[n].kind != 'humano']
    for f in range(0, prj.n_frames, step):
        t = f / FPS
        SC.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        vis = {n: not perf.is_hidden(n, t) for n in chars}
        T = {}

        def g(n, part, shrink=0.0):
            if (n, part, shrink) not in T:
                T[(n, part, shrink)] = tree(groups.get((n, part), []), dg, shrink)
            return T[(n, part, shrink)]
        for m in masc:
            if not vis[m]:
                continue
            for h in humans:
                if not vis[h]:
                    continue
                for part in ('cuerpo', 'cabeza', 'brazo', 'mano'):
                    # sostener a la mascota está bien (contacto); atravesarla no: 6 mm de tolerancia en manos, 2 mm en el resto
                    tol = 0.006 if part == 'mano' else 0.002
                    if groups.get((h, part)) and g(m, 'mascota', tol).overlap(g(h, part)):
                        culp = next((o.name for o in groups[(h, part)] if g(m, 'mascota', tol).overlap(tree([o], dg))), '?')
                        issues.append(dict(t=round(t, 2), tipo='mascota-cuerpo', quien=m, con=f'{h}.{part}', obj=culp))
        for h in humans:
            if vis[h] and (g(h, 'mano').overlap(g(h, 'cabeza')) or g(h, 'brazo').overlap(g(h, 'cabeza'))):
                issues.append(dict(t=round(t, 2), tipo='mano-cabeza', quien=h))
    # planos tapados: rayo desde la cámara al objetivo a mitad del plano
    for i, s in enumerate(SHOTS):
        f = int(round((s['t'] + s['end']) / 2 * FPS))
        SC.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        co = CAMS[i]
        cp = co.matrix_world.to_translation()
        tg = probe(s.get('tgt', s.get('objetivo')), f)
        d = tg - cp
        hit, loc, nor, idx, ob, mw = SC.ray_cast(dg, cp, d.normalized(), distance=d.length)
        mat = ob.active_material.name if (hit and ob.active_material) else ''
        if hit and (loc - cp).length < 0.85 * d.length and not mat.startswith(('vidrio', 'viraje')):
            who = owner.get(ob.name, (None,))[0]
            tws = [x.split('.')[0] for x in str(s.get('tgt', s.get('objetivo', ''))).split('|')]
            if who not in tws and not ob.name.startswith(co.name):
                issues.append(dict(t=round(s['t'], 2), tipo='plano-tapado', plano=s['n'], por=ob.name,
                                   a=round((loc - cp).length, 2), de=round(d.length, 2)))
    # resumen compacto: agrupa choques contiguos
    seen = {}
    objs = {}
    for it in issues:
        k = (it['tipo'], it.get('quien'), it.get('con'), it.get('plano'))
        seen.setdefault(k, []).append(it['t'])
        if it.get('obj') or it.get('por'):
            objs.setdefault(k, set()).add(it.get('obj') or it.get('por'))
    report = [dict(tipo=k[0], quien=k[1], con=k[2], plano=k[3], objetos=sorted(objs.get(k, []))[:6], tiempos=v[:12], n=len(v))
              for k, v in seen.items()]
    with open(prj.path('build', 'check.json'), 'w') as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    for r in report:
        print('[check]', json.dumps(r, ensure_ascii=False))
    print(f'[check] {len(report)} problemas -> build/check.json')


if arg('--vista'):
    # cámara de depuración fija (no la del plano): --vista "x,y,z;tx,ty,tz" [--lente 35]  (para revisar choques de cerca)
    a_, b_ = str(arg('--vista')).split(';')
    cdv = bpy.data.cameras.new('CAM_vista')
    cdv.lens = float(arg('--lente', 35))
    cov = bpy.data.objects.new('CAM_vista', cdv)
    SC.collection.objects.link(cov)
    cov.location = Vector([float(x) for x in a_.split(',')])
    cov.rotation_euler = (Vector([float(x) for x in b_.split(',')]) - cov.location).to_track_quat('-Z', 'Y').to_euler()
    for m in SC.timeline_markers:
        m.camera = cov
    SC.camera = cov
if arg('--check'):
    run_check()
if arg('--stills'):
    os.makedirs(prj.path('test'), exist_ok=True)
    for tt in str(arg('--stills')).split(','):
        f = int(round(prj.T(tt) * FPS))
        render_still(f, prj.path('test', f'still_{f / FPS:05.2f}.jpg'))
if arg('--shotstills'):
    d = prj.path('test', 'shots')
    os.makedirs(d, exist_ok=True)
    only = str(arg('--only', '')).split(',') if arg('--only') else None
    for i, s in enumerate(SHOTS):
        if only and str(i + 1) not in only:
            continue
        for k, fr_ in enumerate(s.get('probe_frac', [0.5])):
            f = int(round((s['t'] + (s['end'] - s['t']) * fr_) * FPS))
            render_still(f, os.path.join(d, f'{i + 1:02d}_{k}.jpg'))
if arg('--frames'):
    a_, b_, st = [float(x) for x in str(arg('--frames')).split(':')]
    d = prj.path('test', 'frames')
    os.makedirs(d, exist_ok=True)
    tt = a_
    while tt <= b_ + 1e-6:
        render_still(int(round(tt * FPS)), os.path.join(d, f'f_{tt:05.2f}.jpg'))
        tt += st
if arg('--anim'):
    i = ARGV.index('--anim')
    fa, fb = int(ARGV[i + 1]), int(ARGV[i + 2])
    SC.frame_start, SC.frame_end = fa, fb
    out = prj.path(str(arg('--out', 'renders/chunk.mp4')))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    try:
        SC.render.image_settings.media_type = 'VIDEO'
    except Exception:
        pass
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
