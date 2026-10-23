# props.py — objetos de plastilina que usan los personajes: taza con letrero, objetos en la mano,
# contornos extruidos (logos de IA) y el recibo térmico que se desenrolla (cuando el objeto ES el chiste, es un prop real).
import bpy, bmesh, math, os
from mathutils import Vector, Matrix, Euler
from clay import (D, hexc, link, mat4, bm_obj, blob, sphere, superbox, cylinder, tube, text, clay, FONT_BOLD)

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(os.path.dirname(ENGINE), 'assets')


def mug(name, M, label='#1 BOSS', r=0.055, color='#F2ECE2', ink='#B9322A'):
    objs = []
    white = clay(f'taza_{color}', color, rough=0.35, coat=0.3, prints=0.5)
    objs.append(cylinder(f'{name}_body', white, (0, 0, 0), r, 0.12 * r / 0.055, None, sub=1, disp=0.0015, bevel=0.006 * r / 0.055))
    s = r / 0.055
    objs.append(tube(f'{name}_handle', white, [(r - 0.005 * s, 0, 0.035 * s), (r + 0.04 * s, 0, 0.03 * s), (r + 0.043 * s, 0, -0.025 * s),
                                               (r - 0.005 * s, 0, -0.03 * s)], 0.012 * s, None, ring=12, per=5))
    objs.append(cylinder(f'{name}_coffee', clay('cafe', '#2B170D', rough=0.15, prints=0), (0, 0, 0.055 * s), r - 0.008 * s,
                         0.004, None, bevel=0))
    if label:
        red = clay(f'letras_{ink}', ink, rough=0.5, prints=0)
        widths = [0.013 * s if ch != ' ' else 0.008 * s for ch in label]
        wtot = sum(widths)
        ang0 = -wtot / 2 / (r + 0.001)
        acc = 0.0
        for i, ch in enumerate(label):
            a = ang0 + (acc + widths[i] / 2) / (r + 0.001)
            acc += widths[i]
            if ch == ' ':
                continue
            o = text(f'{name}_t{i}', ch, red, (0, 0, 0), 0.026 * s, None, extrude=0.0015, font=FONT_BOLD)
            o.matrix_basis = Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((0, -(r + 0.0015), -0.005 * s)) @ \
                Euler((D(90), 0, 0)).to_matrix().to_4x4()
            objs.append(o)
    for o in objs:
        o.matrix_basis = M @ o.matrix_basis
    return objs


def hand_item(name, kind, side=1):
    """objeto en la mano (marco local de la muñeca: -Z = dedos). kind: taza | taza_jefe | cuchara | telefono"""
    if kind in ('taza', 'taza_jefe'):
        return mug(name, Matrix.Rotation(D(90), 4, 'Z'), label='#1 BOSS' if kind == 'taza_jefe' else '', r=0.034)
    if kind == 'cuchara':
        wood = clay('madera_cuchara', '#C08A52', rough=0.6, prints=0.6)
        return [tube(f'{name}_mango', wood, [(0, 0, 0.09), (0, 0, -0.02), (0, -0.01, -0.16)], [0.009, 0.009, 0.008], None,
                     ring=10, per=3),
                blob(f'{name}_pala', wood, mat4((0, -0.012, -0.2), (D(-8), 0, 0), (0.026, 0.01, 0.042)), None, disp=0.001)]
    if kind == 'telefono':
        return [superbox(f'{name}_tel', clay('telefono', '#1E1E22', rough=0.3), (0, -0.01, -0.02), (0.035, 0.006, 0.07), None,
                         e=0.2, disp=0)]
    raise KeyError(f'objeto de mano desconocido: {kind}')


def contour_mesh(name, contours, size, depth, mat, bevel=0.006):
    """contornos 2D (logo) -> malla extruida mirando a -Y"""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    cu.extrude = depth
    cu.bevel_depth = bevel
    cu.bevel_resolution = 3
    cu.offset = -bevel + 1e-4
    for c in contours:
        sp = cu.splines.new('POLY')
        sp.points.add(len(c) - 1)
        for i, (x, y) in enumerate(c):
            sp.points[i].co = (x * size, y * size, 0, 1)
        sp.use_cyclic_u = True
    cu.materials.append(mat)
    o = bpy.data.objects.new(name + '_c', cu)
    link(o)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bpy.data.objects.remove(o)
    bpy.data.curves.remove(cu)
    me.transform(Matrix.Rotation(D(90), 4, 'X'))
    ob = bpy.data.objects.new(name, me)
    link(ob)
    for p in me.polygons:
        p.use_smooth = abs(p.normal.y) < 0.9
    return ob


# ------------------------------------------------------------------ recibo térmico (se revela de arriba abajo)
def receipt_material(tex_path):
    m = bpy.data.materials.new('recibo_termico')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bs.inputs['Roughness'].default_value = 0.55
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(tex_path)
    nt.links.new(tex.outputs['Color'], bs.inputs['Base Color'])
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    val = nt.nodes.new('ShaderNodeValue')
    val.name = 'largo'
    val.outputs[0].default_value = 0.0
    neg = nt.nodes.new('ShaderNodeMath'); neg.operation = 'MULTIPLY'; neg.inputs[1].default_value = -1.0
    nt.links.new(val.outputs[0], neg.inputs[0])
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'
    nt.links.new(sep.outputs['Z'], gt.inputs[0])
    nt.links.new(neg.outputs[0], gt.inputs[1])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(gt.outputs[0], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(bs.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    try:
        m.surface_render_method = 'DITHERED'
    except Exception:
        pass
    return m


def receipt_strip(name, mat, length=1.05, width=0.062):
    bm = bmesh.new()
    n = 160
    uv = bm.loops.layers.uv.new()
    rows = []
    for i in range(n + 1):
        z = -length * i / n
        yy = -0.012 * math.sin(i / n * math.pi * 3.0) - 0.04 * (i / n) ** 2
        rows.append([bm.verts.new((-width / 2, yy, z)), bm.verts.new((width / 2, yy, z))])
    for i in range(n):
        f = bm.faces.new((rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]))
        for lp, (u, v) in zip(f.loops, ((0, 1 - i / n), (1, 1 - i / n), (1, 1 - (i + 1) / n), (0, 1 - (i + 1) / n))):
            lp[uv].uv = (u, v)
    o = bm_obj(name, bm, mat, None, sub=0, disp=0)
    m = o.modifiers.new('grosor', 'SOLIDIFY')
    m.thickness = 0.0008
    return o
