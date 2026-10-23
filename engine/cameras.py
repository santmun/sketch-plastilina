# cameras.py — una cámara por plano desde shots.json (con marcadores de corte), encuadres automáticos por
# tamaño de plano y el micro push-in/out constante de «A escondidas» en TODOS los planos. Ver references/tomas.md.
import bpy, math
from mathutils import Vector, Quaternion
import clay
from clay import D
from rig import REC, ease

# tamaño de plano -> (alto vertical encuadrado en m, lente por defecto, altura de cámara relativa al objetivo).
# En 9:16 el ancho visible es 0.56 x el alto: un close de cara (~0.62 m de alto) deja ~0.35 m de ancho, como en el referente.
# Las mascotas (más chicas) usan 0.7 x estos tamaños.
PLANOS = {
    'extremo': (0.26, 60, 0.0), 'detalle': (0.32, 50, 0.03), 'close': (0.62, 40, 0.03), 'medio': (0.95, 35, 0.08),
    'duo': (1.25, 32, 0.12), 'americano': (1.6, 30, 0.15), 'general': (2.8, 24, 0.4),
}


def resolve_shots(prj, spec):
    """tiempos (refs de guion) -> segundos, ordena y calcula 'end'"""
    shots = []
    for s in spec:
        s = dict(s)
        s['t'] = round(prj.T(s.get('t', s.get('en', 0))), 3)
        if 'shake' in s:
            s['shake'] = (round(prj.T(s['shake'][0]), 3), s['shake'][1])
        shots.append(s)
    shots.sort(key=lambda s: s['t'])
    for i, s in enumerate(shots):
        s['end'] = shots[i + 1]['t'] if i + 1 < len(shots) else prj.t_end
        s.setdefault('n', f'S{i + 1:02d}')
    return shots


def noise(seed, t):
    return sum(math.sin(t * fr + seed * ph) * a for fr, ph, a in ((23.0, 1.3, 0.5), (37.0, 2.1, 0.3), (51.0, 0.7, 0.2)))


def duel_overlays(co, cd, letterbox=True, tint=True):
    """letterbox + viraje cálido pegados a la cámara (duelo de miradas entre IAs)"""
    d = 0.02
    hh = d * 18.0 / cd.lens
    hw = hh * 9 / 16
    if letterbox:
        bars = clay.simple('letterbox', '#000000', rough=1.0)
        bh = hh * 0.12
        for k, sgn in (('top', 1), ('bot', -1)):
            clay.box(f'{co.name}_lb_{k}', bars, (0, sgn * (hh - bh), -d), (hw * 1.3, bh, 0.0002), co, bevel=0)
    if tint:
        m = bpy.data.materials.get('viraje_duelo')
        if m is None:
            m = bpy.data.materials.new('viraje_duelo')
            m.use_nodes = True
            nt = m.node_tree
            nt.nodes.clear()
            out = nt.nodes.new('ShaderNodeOutputMaterial')
            tr = nt.nodes.new('ShaderNodeBsdfTransparent')
            tr.inputs['Color'].default_value = (1.0, 0.78, 0.5, 1)
            nt.links.new(tr.outputs[0], out.inputs[0])
            try:
                m.surface_render_method = 'BLENDED'
            except Exception:
                pass
        clay.box(f'{co.name}_tinte', m, (0, 0, -d * 1.02), (hw * 1.5, hh * 1.2, 0.0002), co, bevel=0)
    cd.clip_start = 0.005


def auto_position(s, tgt, facing, k=1.0):
    """posición de cámara desde plano/ángulo/altura respecto a hacia dónde mira el sujeto. k escala el tamaño
    del encuadre (mascotas: según su altura)"""
    H, lens0, h0 = PLANOS[s.get('plano', 'close')]
    H, h0 = H * k, h0 * k
    lens = s.get('lens', lens0)
    d = H * lens / 36.0 * float(s.get('distancia', 1.0))
    f3 = Vector(facing)
    f = Vector((f3.x, f3.y, 0))
    if f.length < 1e-6:
        f = Vector((0, -1, 0))
    f.normalize()
    vz = max(-0.6, min(0.4, f3.z)) * 0.7      # si el sujeto mira abajo, la cámara baja con su cara (y viceversa)
    ang = math.radians(float(s.get('angulo', 0)))
    # +ángulo = la cámara se va hacia la izquierda del sujeto (+X local)
    c, sn = math.cos(-ang), math.sin(-ang)
    dirv = Vector((f.x * c - f.y * sn, f.x * sn + f.y * c, 0))
    alt = s.get('altura', h0)
    if alt == 'contrapicado':
        alt = -0.38 * d
    elif alt == 'picado':
        alt = 0.42 * d
    elif alt == 'ojos':
        alt = 0.0
    return tgt + dirv * d * math.sqrt(max(0.2, 1 - vz * vz)) + Vector((0, 0, float(alt) + vz * d)), lens


def build(SC, shots, probe, facing, fps, dofk=1.0, subject_k=lambda spec: 1.0, free=None, publico=Vector((0, -1, 0))):
    """probe(spec, frame) -> Vector ; facing(spec, frame) -> Vector. Devuelve la lista de cámaras."""
    cams = []
    for i, s in enumerate(shots):
        f0 = int(round(s['t'] * fps))
        f1 = int(round(s['end'] * fps))
        mid = (f0 + f1) // 2
        cd = bpy.data.cameras.new(f'CAM_{i + 1:02d}')
        cd.sensor_width = 36
        cd.sensor_fit = 'AUTO'
        cd.clip_start = 0.01
        cd.dof.use_dof = True
        cd.dof.aperture_blades = 6
        co = bpy.data.objects.new(f'CAM_{i + 1:02d}', cd)
        SC.collection.objects.link(co)
        co.rotation_mode = 'XYZ'
        tgt_spec = s.get('tgt', s.get('objetivo'))
        fixed_tgt = probe(tgt_spec, int(s['tgt_at'] * fps) if s.get('tgt_at') else mid)
        two = isinstance(tgt_spec, str) and '|' in tgt_spec
        if 'pos' in s:
            base_pos = Vector(s['pos'])
            lens = s.get('lens', 35)
        elif two and s.get('plano', 'duo') == 'duo' and 'off' not in s:
            # dúo en 9:16 = sobre el hombro: la cámara detrás de B mirando a A (A al centro, B en primer término)
            a_spec, b_spec = tgt_spec.split('|')[:2]
            pa, pb = probe(a_spec, mid), probe(b_spec, mid)
            low_b = pa.z - pb.z > 0.12           # B es una mascota más baja: la cámara se queda a su altura
            fixed_tgt = pa.lerp(pb, 0.4 if low_b else 0.12)
            dh = Vector((pb.x - pa.x, pb.y - pa.y, 0))
            if dh.length < 1e-4:
                dh = Vector((0, -1, 0))
            u = dh.normalized()
            sgn = 1 if float(s.get('angulo', 15)) >= 0 else -1
            side = Vector((-u.y, u.x, 0)) * sgn          # la cámara se abre a un lado de la cabeza de B
            lens = s.get('lens', 32)
            k = float(s.get('distancia', 1.0))
            up = 0.07 if low_b else max(0.0, pa.z - pb.z) + float(s.get('altura', 0.06))
            base_pos = pb + u * (0.38 * k) + side * (0.24 * k) + Vector((0, 0, up))
        else:
            desde = s.get('desde', 'set' if s.get('plano') == 'general' else 'sujeto')
            fac = Vector(publico) if desde == 'set' else facing(tgt_spec, mid)   # 'set' = desde el lado del público
            base_pos, lens = auto_position(s, fixed_tgt, fac, subject_k(tgt_spec))
            if free is not None and not s.get('libre') is False:
                base_pos, note = free(s, fixed_tgt, base_pos, mid, tgt_spec)
                if note:
                    s['_ajuste'] = note
        s['lens'] = lens
        s['_cam'] = tuple(round(c, 3) for c in base_pos)
        s['_tgt'] = tuple(round(c, 3) for c in fixed_tgt)
        cd.lens = lens
        cd.dof.aperture_fstop = max(1.4, s.get('f', 2.8) * dofk)
        prev = None
        duel = s.get('duelo') or s.get('western')
        for f in range(f0 - 1, f1 + 2):
            t = f / fps
            x = (f - f0) / max(1, (f1 - f0))
            xe = ease(min(1.0, (t - s['t']) / s['ease_dur'])) if 'ease_dur' in s else x
            tgt = probe(tgt_spec, f) if s.get('track') else fixed_tgt.copy()
            if s.get('track') and prev is not None:
                tgt = prev.lerp(tgt, 0.25)
            prev = tgt.copy()
            pos = base_pos.copy()
            if 'end_off' in s:
                pos = fixed_tgt + Vector(s['off']).lerp(Vector(s['end_off']), xe)
                REC.key(cd, 'lens', 0, f, lens + (s.get('end_lens', lens) - lens) * xe, 'LINEAR')
            push = s.get('push', 1.0)
            if push != 1.0:
                pos = tgt + (pos - tgt) * (1 + (push - 1) * ease(x))
            if 'drift' in s:
                pos = pos + Vector(s['drift']) * ease(x)
            if not duel and not s.get('fijo'):
                # micro movimiento constante (como el referente): 4 % de dolly alternando entrada/salida + 1.5 % lateral
                d0 = (pos - tgt).length
                sgn = -1 if i % 2 == 0 else 1
                pos = tgt + (pos - tgt) * (1 + sgn * 0.04 * x)
                side = (tgt - pos).cross(Vector((0, 0, 1)))
                if side.length > 1e-6:
                    pos = pos + side.normalized() * (0.015 * d0 * (x - 0.5) * (1 if i % 3 else -1))
            rot = (tgt - pos).to_track_quat('-Z', 'Y')
            if 'dutch' in s:
                rot = rot @ Quaternion((0, 0, 1), D(s['dutch']))
            rot = rot.to_euler()
            if 'shake' in s:
                ts, amp = s['shake']
                if t >= ts:
                    k = amp * math.exp(-(t - ts) * 5.0)
                    rot.x += D(1.4) * k * noise(1, t)
                    rot.y += D(1.0) * k * noise(2, t)
                    rot.z += D(1.4) * k * noise(3, t)
            rot.x += D(0.12) * math.sin(t * 1.7 + i)     # respiración de cámara en mano, muy leve
            rot.z += D(0.12) * math.sin(t * 1.3 + 2 * i)
            for k in range(3):
                REC.key(co, 'location', k, f, pos[k], 'LINEAR')
                REC.key(co, 'rotation_euler', k, f, rot[k], 'LINEAR')
            fp = probe(s['focus'], f) if 'focus' in s else tgt
            REC.key(cd, 'dof.focus_distance', 0, f, max(0.05, (fp - pos).length), 'LINEAR')
        m = SC.timeline_markers.new(s['n'], frame=f0)
        m.camera = co
        cams.append(co)
        if duel:
            duel_overlays(co, cd, s.get('letterbox', True), s.get('tinte', True))
    SC.camera = cams[0]
    return cams
