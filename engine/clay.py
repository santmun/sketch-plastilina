# clay.py — utilidades de plastilina (geometría + materiales). Extraído de «A escondidas» sin cambios de look.
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Matrix, Euler, Quaternion

D = math.radians

def hexc(h, a=1.0):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, a)


def link(o, parent=None):
    bpy.context.scene.collection.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def empty(name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    o.empty_display_size = 0.05
    link(o, parent)
    o.location = loc
    o.rotation_euler = rot
    return o


def mat4(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return (Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4()
            @ Matrix.Diagonal((*scale, 1.0)))


def frame_from(z_dir, y_hint):
    """matriz 3x3 cuyo eje Z = z_dir y eje Y lo más cerca posible de y_hint"""
    z = Vector(z_dir).normalized()
    y = Vector(y_hint)
    y = (y - y.dot(z) * z)
    if y.length < 1e-6:
        y = z.orthogonal()
    y.normalize()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed()


def finish(o, sub=1, disp=0.0, dscale=0.18, smooth=True):
    """suaviza + subdivide + desplazamiento procedural (bordes irregulares de plastilina)"""
    if smooth and o.type == 'MESH':
        for p in o.data.polygons:
            p.use_smooth = True
    if sub:
        m = o.modifiers.new('sub', 'SUBSURF')
        m.levels = sub
        m.render_levels = sub
    if disp:
        key = f'clay_noise_{dscale:.3f}'
        tex = bpy.data.textures.get(key)
        if tex is None:
            tex = bpy.data.textures.new(key, 'CLOUDS')
            tex.noise_scale = dscale
            tex.noise_depth = 2
        m = o.modifiers.new('disp', 'DISPLACE')
        m.texture = tex
        m.strength = disp
        m.mid_level = 0.5
    return o


def bm_obj(name, bm, mat, parent=None, sub=1, disp=0.004, dscale=0.18, smooth=True):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    link(o, parent)
    return finish(o, sub, disp, dscale, smooth)


def blob(name, mat, M, parent=None, deform=None, seg=(40, 20), sub=1, disp=0.004, dscale=0.18, cut=None, ico=0,
         smooth=True, bevel=0.0):
    """esfera unitaria -> deform(v) -> matriz M. cut=(punto, normal) conserva el lado positivo y cierra el hueco.
    ico>0: icoesfera de ese nivel (facetas triangulares); smooth=False + bevel: planos de plastilina."""
    bm = bmesh.new()
    if ico:
        bmesh.ops.create_icosphere(bm, subdivisions=ico, radius=1.0)
    else:
        bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0)
    if deform:
        for v in bm.verts:
            v.co = deform(v.co.copy())
    if cut:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                               plane_co=Vector(cut[0]), plane_no=Vector(cut[1]), clear_inner=True)
        bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=0)
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
    o = bm_obj(name, bm, mat, parent, sub, disp, dscale, smooth)
    if bevel:
        m = o.modifiers.new('bev', 'BEVEL')
        m.width = bevel
        m.segments = 2
        m.limit_method = 'ANGLE'
        m.angle_limit = D(8)
        o.modifiers.move(len(o.modifiers) - 1, 0)
    return o


def sphere(name, mat, loc, r, parent=None, rot=(0, 0, 0), **kw):
    rr = r if isinstance(r, (tuple, list)) else (r, r, r)
    return blob(name, mat, mat4(loc, rot, rr), parent, **kw)


def superbox(name, mat, loc, size, parent=None, rot=(0, 0, 0), e=0.28, **kw):
    """caja redondeada de plastilina (superelipsoide) — size = semiejes"""
    def d(v):
        return Vector([math.copysign(abs(c) ** e, c) for c in v])
    return blob(name, mat, mat4(loc, rot, size), parent, deform=d, seg=(48, 24), **kw)


def box(name, mat, loc, size, parent=None, rot=(0, 0, 0), bevel=0.004):
    """caja nítida (cartón pluma, madera) — size = semiejes"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.transform(bm, matrix=mat4(loc, rot, size), verts=bm.verts[:])
    o = bm_obj(name, bm, mat, parent, sub=0, disp=0, smooth=False)
    if bevel:
        m = o.modifiers.new('bev', 'BEVEL')
        m.width = bevel
        m.segments = 2
    return o


def cylinder(name, mat, loc, r, h, parent=None, rot=(0, 0, 0), seg=40, r2=None, sub=0, disp=0, bevel=0.003):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                          radius2=r if r2 is None else r2, depth=h)
    bmesh.ops.transform(bm, matrix=mat4(loc, rot), verts=bm.verts[:])
    o = bm_obj(name, bm, mat, parent, sub=sub, disp=disp, smooth=True)
    for p in o.data.polygons:
        p.use_smooth = abs(p.normal.z) < 0.5
    if bevel:
        m = o.modifiers.new('bev', 'BEVEL')
        m.width = bevel
        m.segments = 2
        o.modifiers.move(len(o.modifiers) - 1, 0)
    return o


def catmull(pts, per=8, closed=False):
    P = [Vector(p) for p in pts]
    if closed:
        ext = [P[-1]] + P + [P[0], P[1]]
        nseg = len(P)
    else:
        ext = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
        nseg = len(P) - 1
    out = []
    for i in range(nseg):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1].copy())
    return out


def tube(name, mat, pts, radius, parent=None, ring=18, per=8, caps=True, flat=1.0, ref=None,
         closed=False, sub=1, disp=0.003, dscale=0.12):
    """«salchicha» de plastilina a lo largo de una spline, con puntas redondas"""
    C = catmull(pts, per, closed)
    n = len(C)
    if isinstance(radius, (int, float)):
        R = [radius] * n
    else:
        rl = list(radius)
        R = []
        for i in range(n):
            u = i / (n - 1 if not closed else n) * (len(rl) - 1)
            j = min(int(u), len(rl) - 2)
            f = u - j
            f = f * f * (3 - 2 * f)
            R.append(rl[j] * (1 - f) + rl[j + 1] * f)
    T = []
    for i in range(n):
        if closed:
            t = C[(i + 1) % n] - C[i - 1]
        else:
            t = C[min(i + 1, n - 1)] - C[max(i - 1, 0)]
        T.append(t.normalized())
    # marcos: referencia fija o transporte paralelo
    N = []
    if ref is not None:
        rv = Vector(ref)
        for t in T:
            a2 = (rv - rv.dot(t) * t)
            a2 = a2.normalized() if a2.length > 1e-6 else t.orthogonal().normalized()
            N.append(a2)
    else:
        a2 = T[0].orthogonal().normalized()
        for i, t in enumerate(T):
            if i:
                rot = T[i - 1].rotation_difference(t)
                a2 = (rot @ a2)
                a2 = (a2 - a2.dot(t) * t).normalized()
            N.append(a2.copy())
    rings = []  # (center, a1, a2, r)
    if caps and not closed:
        for k in range(4, 0, -1):
            ph = k / 4 * math.pi / 2
            rings.append((C[0] - T[0] * R[0] * math.sin(ph), N[0].cross(T[0]), N[0], R[0] * math.cos(ph)))
    for i in range(n):
        rings.append((C[i], N[i].cross(T[i]), N[i], R[i]))
    if caps and not closed:
        for k in range(1, 5):
            ph = k / 4 * math.pi / 2
            rings.append((C[-1] + T[-1] * R[-1] * math.sin(ph), N[-1].cross(T[-1]), N[-1], R[-1] * math.cos(ph)))
    bm = bmesh.new()
    vr = []
    for c, a1, a2, r in rings:
        if r < 1e-5:
            vr.append([bm.verts.new(c)])
            continue
        vr.append([bm.verts.new(c + r * (math.cos(2 * math.pi * j / ring) * a1
                                         + flat * math.sin(2 * math.pi * j / ring) * a2)) for j in range(ring)])
    pairs = list(zip(vr[:-1], vr[1:]))
    if closed:
        pairs.append((vr[-1], vr[0]))
    for A, B in pairs:
        if len(A) == 1 and len(B) == 1:
            continue
        if len(A) == 1:
            for j in range(ring):
                bm.faces.new((A[0], B[j], B[(j + 1) % ring]))
        elif len(B) == 1:
            for j in range(ring):
                bm.faces.new((A[j], A[(j + 1) % ring], B[0]))
        else:
            for j in range(ring):
                bm.faces.new((A[j], A[(j + 1) % ring], B[(j + 1) % ring], B[j]))
    return bm_obj(name, bm, mat, parent, sub, disp, dscale)


def text(name, s, mat, loc, size, parent=None, rot=(D(90), 0, 0), extrude=0.002, align='CENTER', font=None):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = s
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = extrude * 0.4
    cu.align_x = align
    cu.align_y = 'CENTER'
    if font:
        cu.font = font
    o = bpy.data.objects.new(name, cu)
    o.data.materials.append(mat)
    link(o, parent)
    o.location = loc
    o.rotation_euler = rot
    return o


def load_font(*paths):
    for p in paths:
        if os.path.exists(p):
            try:
                return bpy.data.fonts.load(p)
            except Exception:
                pass
    return None


def _system_fonts():
    """negritas de Windows/Linux (y las de assets/fonts) por si no están las de macOS"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
        import entorno
        return entorno.font_files_for_blender()
    except Exception:
        return []


FONT_BOLD = load_font('/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf',
                      '/System/Library/Fonts/Supplemental/Arial Bold.ttf', *_system_fonts())


# ============================================================================ materiales
def node(nt, t, inputs=None, **props):
    n = nt.nodes.new(t)
    for k, v in props.items():
        setattr(n, k, v)
    for k, v in (inputs or {}).items():
        n.inputs[k].default_value = v
    return n


_MATS = {}


def clay(name, color, rough=0.62, prints=1.0, sss=0.06, sheen=0.25, bump=1.0, spec=0.35, coat=0.0):
    """plastilina mate: grumos + huellas dactilares por celdas + marcas de herramienta + oclusión en recovecos"""
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    L = nt.links.new
    out = node(nt, 'ShaderNodeOutputMaterial')
    bs = node(nt, 'ShaderNodeBsdfPrincipled', {
        'Roughness': rough, 'Subsurface Weight': sss, 'Subsurface Scale': 0.02,
        'Specular IOR Level': spec, 'Sheen Weight': sheen, 'Sheen Roughness': 0.6, 'Coat Weight': coat,
        'Coat Roughness': 0.25})
    tc = node(nt, 'ShaderNodeTexCoord')
    # grumos de baja frecuencia
    n1 = node(nt, 'ShaderNodeTexNoise', {'Scale': 7.0, 'Detail': 3.0, 'Roughness': 0.55})
    L(tc.outputs['Object'], n1.inputs['Vector'])
    # marcas de herramienta / abolladuras
    vo = node(nt, 'ShaderNodeTexVoronoi', {'Scale': 16.0, 'Randomness': 1.0}, feature='SMOOTH_F1')
    L(tc.outputs['Object'], vo.inputs['Vector'])
    # huellas: anillos alrededor del centro de cada celda, distorsionados
    vc = node(nt, 'ShaderNodeTexVoronoi', {'Scale': 6.5, 'Randomness': 0.9})
    L(tc.outputs['Object'], vc.inputs['Vector'])
    sub = node(nt, 'ShaderNodeVectorMath', operation='SUBTRACT')
    L(tc.outputs['Object'], sub.inputs[0])
    L(vc.outputs['Position'], sub.inputs[1])
    sc = node(nt, 'ShaderNodeVectorMath', operation='MULTIPLY')
    sc.inputs[1].default_value = (1.0, 1.45, 0.8)
    L(sub.outputs[0], sc.inputs[0])
    ln = node(nt, 'ShaderNodeVectorMath', operation='LENGTH')
    L(sc.outputs[0], ln.inputs[0])
    nd = node(nt, 'ShaderNodeTexNoise', {'Scale': 40.0, 'Detail': 2.0})
    L(tc.outputs['Object'], nd.inputs['Vector'])
    ndm = node(nt, 'ShaderNodeMath', {1: 0.004}, operation='MULTIPLY')
    L(nd.outputs['Fac'], ndm.inputs[0])
    add = node(nt, 'ShaderNodeMath', operation='ADD')
    L(ln.outputs['Value'], add.inputs[0])
    L(ndm.outputs[0], add.inputs[1])
    ring = node(nt, 'ShaderNodeMath', {1: 1150.0}, operation='MULTIPLY')
    L(add.outputs[0], ring.inputs[0])
    sn = node(nt, 'ShaderNodeMath', operation='SINE')
    L(ring.outputs[0], sn.inputs[0])
    # máscara: solo algunas celdas y desvanecido con la distancia al centro
    fall = node(nt, 'ShaderNodeMapRange', {'From Min': 0.012, 'From Max': 0.055, 'To Min': 1.0, 'To Max': 0.0})
    L(ln.outputs['Value'], fall.inputs['Value'])
    sep = node(nt, 'ShaderNodeSeparateColor')
    L(vc.outputs['Color'], sep.inputs[0])
    gate = node(nt, 'ShaderNodeMath', {1: 0.45}, operation='GREATER_THAN')
    L(sep.outputs[0], gate.inputs[0])
    msk = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    L(fall.outputs[0], msk.inputs[0])
    L(gate.outputs[0], msk.inputs[1])
    fp = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    L(sn.outputs[0], fp.inputs[0])
    L(msk.outputs[0], fp.inputs[1])
    fpw = node(nt, 'ShaderNodeMath', {1: 0.28 * prints}, operation='MULTIPLY')
    L(fp.outputs[0], fpw.inputs[0])
    # altura combinada
    h1 = node(nt, 'ShaderNodeMath', {1: 0.9}, operation='MULTIPLY')
    L(n1.outputs['Fac'], h1.inputs[0])
    h2 = node(nt, 'ShaderNodeMath', {1: 0.6}, operation='MULTIPLY')
    L(vo.outputs['Distance'], h2.inputs[0])
    s1 = node(nt, 'ShaderNodeMath', operation='ADD')
    L(h1.outputs[0], s1.inputs[0])
    L(h2.outputs[0], s1.inputs[1])
    s2 = node(nt, 'ShaderNodeMath', operation='ADD')
    L(s1.outputs[0], s2.inputs[0])
    L(fpw.outputs[0], s2.inputs[1])
    bp = node(nt, 'ShaderNodeBump', {'Strength': 0.35 * bump, 'Distance': 0.004})
    L(s2.outputs[0], bp.inputs['Height'])
    L(bp.outputs['Normal'], bs.inputs['Normal'])
    L(bp.outputs['Normal'], bs.inputs['Coat Normal'])
    # color con leve variación + suciedad en recovecos
    base = Vector(hexc(color)[:3])
    cr = node(nt, 'ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (*(base * 0.86), 1)
    cr.color_ramp.elements[1].color = (*(base * 1.08), 1)
    cr.color_ramp.elements[0].position = 0.3
    cr.color_ramp.elements[1].position = 0.7
    L(n1.outputs['Fac'], cr.inputs['Fac'])
    ao = node(nt, 'ShaderNodeAmbientOcclusion', {'Distance': 0.03}, samples=8)
    aor = node(nt, 'ShaderNodeMapRange', {'From Min': 0.0, 'From Max': 1.0, 'To Min': 0.55, 'To Max': 1.0})
    L(ao.outputs['AO'], aor.inputs['Value'])
    mul = node(nt, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mul.inputs['Factor'].default_value = 1.0
    L(cr.outputs['Color'], mul.inputs['A'])
    L(aor.outputs[0], mul.inputs['B'])
    L(mul.outputs['Result'], bs.inputs['Base Color'])
    L(bs.outputs[0], out.inputs[0])
    _MATS[name] = m
    return m


def simple(name, color, rough=0.5, metal=0.0, emit=None, estr=0.0, coat=0.0, alpha=1.0, trans=0.0):
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = hexc(color)
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    bs.inputs['Coat Weight'].default_value = coat
    bs.inputs['Transmission Weight'].default_value = trans
    if alpha < 1.0:
        bs.inputs['Alpha'].default_value = alpha
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    if emit:
        bs.inputs['Emission Color'].default_value = hexc(emit)
        bs.inputs['Emission Strength'].default_value = estr
    _MATS[name] = m
    return m


def marble(name, color):
    """canica brillante para los ojos"""
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = hexc(color)
    bs.inputs['Roughness'].default_value = 0.12
    bs.inputs['Coat Weight'].default_value = 1.0
    bs.inputs['Coat Roughness'].default_value = 0.02
    bs.inputs['Subsurface Weight'].default_value = 0.15
    bs.inputs['Subsurface Scale'].default_value = 0.01
    _MATS[name] = m
    return m


def card(name, color, rough=0.85, grain=1.0):
    """cartón pluma pintado: papel con fibras y brochazos suaves"""
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links.new
    bs = nt.nodes['Principled BSDF']
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Specular IOR Level'].default_value = 0.25
    tc = node(nt, 'ShaderNodeTexCoord')
    n1 = node(nt, 'ShaderNodeTexNoise', {'Scale': 3.0, 'Detail': 4.0})
    L(tc.outputs['Object'], n1.inputs['Vector'])
    n2 = node(nt, 'ShaderNodeTexNoise', {'Scale': 160.0, 'Detail': 2.0})
    L(tc.outputs['Object'], n2.inputs['Vector'])
    wv = node(nt, 'ShaderNodeTexWave', {'Scale': 9.0, 'Distortion': 6.0, 'Detail': 3.0})
    L(tc.outputs['Object'], wv.inputs['Vector'])
    base = Vector(hexc(color)[:3])
    cr = node(nt, 'ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (*(base * 0.88), 1)
    cr.color_ramp.elements[1].color = (*(base * 1.06), 1)
    L(n1.outputs['Fac'], cr.inputs['Fac'])
    L(cr.outputs['Color'], bs.inputs['Base Color'])
    s = node(nt, 'ShaderNodeMath', operation='ADD')
    L(n2.outputs['Fac'], s.inputs[0])
    w2 = node(nt, 'ShaderNodeMath', {1: 0.3}, operation='MULTIPLY')
    L(wv.outputs['Fac'], w2.inputs[0])
    L(w2.outputs[0], s.inputs[1])
    bp = node(nt, 'ShaderNodeBump', {'Strength': 0.12 * grain, 'Distance': 0.002})
    L(s.outputs[0], bp.inputs['Height'])
    L(bp.outputs['Normal'], bs.inputs['Normal'])
    _MATS[name] = m
    return m


def screen_mat():
    if 'screen' in _MATS:
        return _MATS['screen']
    m = bpy.data.materials.new('screen')
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links.new
    nt.nodes.clear()
    out = node(nt, 'ShaderNodeOutputMaterial')
    em = node(nt, 'ShaderNodeEmission', {'Strength': 2.2})
    tc = node(nt, 'ShaderNodeTexCoord')
    br = node(nt, 'ShaderNodeTexBrick', {'Scale': 5.0, 'Mortar Size': 0.18, 'Bias': 0.4,
                                         'Brick Width': 1.6, 'Row Height': 0.18,
                                         'Color1': hexc('#F2C9A0'), 'Color2': hexc('#E8A87A'),
                                         'Mortar': hexc('#2A2320')}, offset=0.7, squash=1.0)
    L(tc.outputs['UV'], br.inputs['Vector'])
    L(br.outputs['Color'], em.inputs['Color'])
    L(em.outputs[0], out.inputs[0])
    _MATS['screen'] = m
    return m


class Head:
    """cabeza elipsoidal con barbilla afinada; superficie analítica para colocar rasgos"""

    def __init__(self, rx, ry, rz, taper, jowl=0.0):
        self.rx, self.ry, self.rz, self.taper, self.jowl = rx, ry, rz, taper, jowl

    def f(self, z):
        k = 1.0 - self.taper * max(0.0, -z) ** 1.6
        k += self.jowl * math.exp(-((z + 0.45) / 0.3) ** 2)
        return k

    def deform(self, v):
        k = self.f(v.z)
        return Vector((v.x * k, v.y * k, v.z))

    def M(self):
        return Matrix.Diagonal((self.rx, self.ry, self.rz, 1.0))

    def surf(self, sx, sz, out=0.0, back=False):
        y = math.sqrt(max(0.0, 1 - sx * sx - sz * sz)) * (1 if back else -1)
        k = self.f(sz)
        p = Vector((self.rx * k * sx, self.ry * k * y, self.rz * sz))
        n = Vector((sx / self.rx, y / self.ry, sz / self.rz)).normalized()
        return p + n * out


def _lerp_pts(pts, z):
    if z <= pts[0][0]:
        return pts[0][1]
    for (z0, a), (z1, b) in zip(pts, pts[1:]):
        if z <= z1:
            u = (z - z0) / (z1 - z0)
            return a + (b - a) * u
    return pts[-1][1]


class PlaneHead:
    """cabeza por planos: frente ancha, pómulos, mandíbula delgada y barbilla con forma.
    Misma interfaz que Head (rx, ry, rz, f, deform, surf, M) para colocar rasgos y la boca."""

    def __init__(self, rx, ry, rz, kx, ky, e=0.7, chin_z=-0.8, chin_flat=0.4, chin_fwd=0.0, cheek=0.0,
                 mesh=None, feat=None):
        self.rx, self.ry, self.rz = rx, ry, rz
        self.kx, self.ky = kx, ky
        self.e, self.chin_z, self.chin_flat, self.chin_fwd, self.cheek = e, chin_z, chin_flat, chin_fwd, cheek
        self.taper = 0.0
        self.mesh = mesh or dict(seg=(64, 36))
        self.feat = feat or {}

    def scaled(self, a, b, c):
        h = PlaneHead(self.rx * a, self.ry * b, self.rz * c, self.kx, self.ky, self.e, self.chin_z, self.chin_flat,
                      self.chin_fwd, self.cheek, self.mesh, self.feat)
        return h

    def f(self, z):
        return _lerp_pts(self.kx, z)

    def deform(self, v):
        x, y, z = v.x, v.y, v.z
        kx = _lerp_pts(self.kx, z)
        ky = _lerp_pts(self.ky, z)
        # sección más cuadrada: aplana el frente y los lados
        ys = math.copysign(abs(y) ** self.e, y) if abs(y) > 1e-9 else 0.0
        # pómulo: ensancha y adelanta un poco a media altura, hacia los lados del frente
        ck = self.cheek * math.exp(-((z + 0.12) / 0.16) ** 2)
        side = min(1.0, abs(x) / 0.75)
        X = x * kx * (1 + ck * 0.6)
        Y = ys * ky * (1 + ck * side * (1.0 if y < 0 else 0.0))
        # barbilla: un poco adelante en el centro
        if y < 0:
            Y -= self.chin_fwd * math.exp(-((z + 0.82) / 0.13) ** 2) * max(0.0, 1 - abs(x) * 2.2)
        Z = z
        if z < self.chin_z:
            Z = self.chin_z + (z - self.chin_z) * self.chin_flat
        return Vector((X, Y, Z))

    def M(self):
        return Matrix.Diagonal((self.rx, self.ry, self.rz, 1.0))

    def _p(self, sx, sz, back=False):
        y = math.sqrt(max(0.0, 1 - sx * sx - sz * sz)) * (1 if back else -1)
        d = self.deform(Vector((sx, y, sz)))
        return Vector((d.x * self.rx, d.y * self.ry, d.z * self.rz))

    def surf(self, sx, sz, out=0.0, back=False):
        p = self._p(sx, sz, back)
        if out == 0.0:
            return p
        h = 0.004
        a = self._p(sx + h, sz, back) - self._p(sx - h, sz, back)
        b = self._p(sx, sz + h, back) - self._p(sx, sz - h, back)
        n = a.cross(b)
        if n.length < 1e-9:
            n = p.copy()
        n.normalize()
        if n.dot(p) < 0:
            n = -n
        return p + n * out


def hand(parent, name, mat, pos, fwd, palm, side=1, curl=0.3, spread=1.0, s=1.0, thumb_curl=0.3):
    """mano de plastilina: palma + 4 dedos salchicha + pulgar. side=+1 mano izquierda del personaje (+X)"""
    Rm = frame_from(fwd, palm).to_4x4()  # Z=dedos, Y=palma
    M = Matrix.Translation(Vector(pos)) @ Rm @ Matrix.Diagonal((s, s, s, 1))
    sphere(f'{name}_palm', mat, (0, 0, 0), (0.042, 0.022, 0.05), None, disp=0.002, dscale=0.06)
    objs = [bpy.data.objects[f'{name}_palm']]
    for i, x in enumerate((-0.027, -0.009, 0.009, 0.027)):
        ln = (0.042, 0.05, 0.048, 0.038)[i if side > 0 else 3 - i]
        xx = x * spread
        c = curl + 0.05 * i
        pts = [(xx, 0.0, 0.03), (xx * 1.05, c * 0.03, 0.03 + ln * 0.6), (xx * 1.1, c * 0.07, 0.03 + ln * (1 - 0.5 * c))]
        objs.append(tube(f'{name}_f{i}', mat, pts, [0.0115, 0.0105, 0.0095], None, ring=12, per=4,
                         disp=0.0015, dscale=0.05))
    tx = 0.04 * side * -1
    objs.append(tube(f'{name}_th', mat, [(tx * 0.6, 0.004, -0.012), (tx * 1.25, 0.02 + thumb_curl * 0.01, 0.012),
                                          (tx * 1.2, 0.03 + thumb_curl * 0.03, 0.04)],
                     [0.013, 0.012, 0.011], None, ring=12, per=4, disp=0.0015, dscale=0.05))
    for o in objs:
        o.matrix_world = M @ o.matrix_world
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Identity(4)
    return objs


def place(objs, M, parent):
    for o in objs:
        o.matrix_basis = M @ o.matrix_basis
        o.parent = parent

