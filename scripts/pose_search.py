# pose_search.py — busca poses de mano junto a la cabeza/pecho SIN atravesar la cabeza ni el cuerpo, robustas a
# varias posiciones de cabeza, y (opcional) las guarda como gesto propio en blocking.json["gestos_custom"].
#   B=/Applications/Blender.app/Contents/MacOS/Blender
#   $B -b -P scripts/pose_search.py -- --project P --quien SANTI --lado R --zona nuca [--guardar rasca_santi]
#   zonas: nuca | mejilla | pecho | boca     lado: L | R | ambos
import bpy, sys, os, math, itertools, json
SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SK, 'engine'))
bpy.ops.wm.read_factory_settings(use_empty=True)
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from project import jload
from characters.humans import Human

ARGV = sys.argv[sys.argv.index('--') + 1:]


def arg(n, d=None):
    return ARGV[ARGV.index(n) + 1] if n in ARGV else d


P = os.path.abspath(arg('--project'))
who = arg('--quien')
side_arg = arg('--lado', 'R')
zona = arg('--zona', 'nuca')
cast = {k: v for k, v in jload(os.path.join(P, 'cast.json'))['personajes'].items() if not k.startswith('_')}
h = Human(who, cast[who])
JOINTS = [h.root, h.body, h.spine, h.neck, h.head] + [j for a in h.arms.values() for j in (a.sh, a.el, a.wr)]
tag = h.tag


def push():
    for j in JOINTS:
        r0 = j.rest_local.to_quaternion()
        t0 = j.rest_local.to_translation()
        j.obj.location = t0 + r0 @ j.loc
        j.obj.rotation_quaternion = r0 @ j.rot
        j.obj.scale = j.scl
    bpy.context.view_layer.update()


def tree(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for o in objs:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        t = bmesh.new()
        t.from_mesh(me)
        t.transform(oe.matrix_world)
        m2 = bpy.data.meshes.new('t')
        t.to_mesh(m2)
        t.free()
        bm.from_mesh(m2)
        bpy.data.meshes.remove(m2)
        oe.to_mesh_clear()
    tr = BVHTree.FromBMesh(bm)
    bm.free()
    return tr


def under(j):
    out = []
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        p = o.parent
        while p is not None:
            if p == j.obj:
                out.append(o)
                break
            p = p.parent
    return out


HEAD = under(h.head)
SIDES = ['L', 'R'] if side_arg == 'ambos' else [side_arg]
HAND = {k: [o for o in under(h.arms[k].wr)] for k in 'LR'}
ARM = {k: [o for o in under(h.arms[k].sh) if o not in HAND[k]] for k in 'LR'}
BODY = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == h.spine.obj]
# rejillas relativas a la cabeza / boca REALES del personaje (marco de la columna, lado derecho = -X)
sp_inv = h.spine.rest_world.inverted()
hc = sp_inv @ h.head.rest_world.to_translation()
mo = sp_inv @ (h.head.rest_world @ h.H.surf(0, h.F['mouth_sz'], 0.0))
rx = h.H.rx / 0.156
if zona == 'nuca':
    grid = itertools.product([x * rx for x in (0.12, 0.17, 0.22)], [hc.y + y for y in (0.06, 0.11, 0.16)],
                             [hc.z + z for z in (-0.17, -0.11, -0.05)],
                             (-30, 0, 30), (0, 30, 50), (-40, 0, 20), ((-1.0, -0.3, 0.6), (-1.0, 0.3, 0.6)))
elif zona == 'mejilla':
    grid = itertools.product([x * rx for x in (0.1, 0.13, 0.16)], [hc.y + y for y in (-0.2, -0.15, -0.1)],
                             [hc.z + z for z in (-0.3, -0.25, -0.2)],
                             (-30, 0, 30), (-30, 0, 30), (-90, -45, 0), ((-0.35, -0.6, -1.0), (-0.6, -0.3, -1.0)))
elif zona == 'boca':
    grid = itertools.product((0.04, 0.08, 0.12), [mo.y + y for y in (-0.07, -0.11, -0.15)], [mo.z + z for z in (-0.04, 0.0, 0.03)],
                             (0, 20), (0,), (-100, -60), ((-1.0, 0.2, -0.6), (-0.6, -0.3, -1.0)))
else:
    grid = itertools.product((0.0, 0.05, 0.1), (-0.17, -0.14), (0.2, 0.25, 0.3), (0,), (0,), (-90, -60), ((-1.0, 0.5, -0.5),))
HEADS = [(5, 0, 0), (20, 0, 0), (10, 30, 0), (10, -30, 0), (0, 0, 6)]   # (pitch, yaw, roll) de cabeza a resistir
REST = {'L': ((0.2, 0.0, 0.0), (0.6, 1.0, 0.0), (0, 0, 0)), 'R': ((-0.2, 0.0, 0.0), (-0.6, 1.0, 0.0), (0, 0, 0))}


def pose_for(k, g):
    x, y, z, rx, ry, rz, pole = g
    if k == 'R':
        return ((-x, y, z), pole, (rx, ry, rz))
    return ((x, y, z), (-pole[0], pole[1], pole[2]), (rx, -ry, -rz))


best = []
fails = {}
for g in grid:
    ok, score = True, 0.0
    for hp, hy, hr in HEADS:
        arms = dict(REST)
        for k in SIDES:
            arms[k] = pose_for(k, g)
        h.apply(dict(lean=10, head=(hp, hy, hr), arms=arms, arm_space={'L': 'spine', 'R': 'spine'}), 0)
        push()
        ht, bt = tree(HEAD), tree(BODY)
        for k in SIDES:
            hd = tree(HAND[k])
            why = 'mano-cabeza' if hd.overlap(ht) else 'brazo-cabeza' if tree(ARM[k]).overlap(ht) else \
                'mano-cuerpo' if hd.overlap(bt) else None
            if why:
                fails[why] = fails.get(why, 0) + 1
                ok = False
                break
            dg = bpy.context.evaluated_depsgraph_get()
            ref = bt if zona == 'pecho' else ht
            for o in HAND[k]:
                oe = o.evaluated_get(dg)
                c = oe.matrix_world @ (sum((Vector(b) for b in oe.bound_box), Vector()) / 8)
                score += ref.find_nearest(c)[3]
        if not ok:
            break
    if ok:
        best.append((score + 0.0004 * (abs(g[3]) + abs(g[4]) + abs(g[5])), g))
best.sort(key=lambda b: b[0])
for b in best[:5]:
    print('[gesto]', round(b[0], 3), {k: pose_for(k, b[1]) for k in SIDES}, flush=True)
print(f'[gesto] poses sin choque: {len(best)}  descartes: {fails}')
if not best:
    print('[gesto] sin solución: prueba el otro lado (--lado L|R), otra zona, o quita el objeto de esa mano en cast.json')
if best and arg('--guardar'):
    bp = os.path.join(P, 'blocking.json')
    B = jload(bp, {})
    kind = 'centro' if zona == 'pecho' else 'cabeza'
    g = {}
    for k in SIDES:
        tg, pole, wr = pose_for(k, best[0][1])
        g[k] = [list(tg), list(pole), list(wr), 'spine', kind]
    B.setdefault('gestos_custom', {})[arg('--guardar')] = g
    json.dump(B, open(bp, 'w'), ensure_ascii=False, indent=1)
    print(f"[gesto] guardado como gestos_custom.{arg('--guardar')} en blocking.json")
