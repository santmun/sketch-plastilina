# looks.py — iluminación y color. 'noche' = el look aprobado de «A escondidas» (añil/petróleo, bruma, prácticas cálidas,
# contraluces fríos, AgX Punchy); 'dia' = neutro cálido. Cada personaje lleva su luz clave y su contraluz pegadas a su
# raíz (lo siguen si camina o gira). El set aporta sus luces prácticas vía setinfo['looks'][look].
import bpy, math
from mathutils import Vector
from clay import D, hexc, node
from sets.common import add_light, aim

WARM = (1.0, 0.66, 0.38)
COLD = (0.45, 0.66, 1.0)


def render_settings(SC, res_x, samples, exposure=0.0):
    SC.render.engine = 'BLENDER_EEVEE'
    SC.render.resolution_x = res_x
    SC.render.resolution_y = int(round(res_x * 16 / 9))
    SC.render.resolution_percentage = 100
    SC.view_settings.view_transform = 'AgX'
    SC.view_settings.exposure = exposure
    ee = SC.eevee
    ee.taa_render_samples = samples
    for k, v in (('use_raytracing', True), ('use_shadows', True), ('shadow_ray_count', 2), ('shadow_step_count', 6),
                 ('use_fast_gi', True), ('fast_gi_method', 'GLOBAL_ILLUMINATION')):
        try:
            setattr(ee, k, v)
        except Exception as e:
            print('[skip]', k, e)
    SC.render.film_transparent = False


def _world(SC, color, strength):
    w = SC.world or bpy.data.worlds.new('mundo')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = hexc(color)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = strength
    SC.world = w
    return w


def character_lights(chars, look, eyes_local, energy_k=1.0):
    """clave + contraluz por personaje, en el marco de su raíz (frente = -Y local)"""
    out = {}
    for name, ch in chars.items():
        e = eyes_local[name]
        small = ch.kind != 'humano'
        s = 0.45 if small else 1.0
        parent = ch.root.obj
        if look == 'noche':
            kc, ke, rc, re = WARM, 26.0, COLD, 120.0
        else:
            kc, ke, rc, re = (1.0, 0.9, 0.8), 30.0, (1.0, 0.86, 0.7), 70.0
        if small:
            ke, re = ke * 0.28, re * 0.3
        k = add_light(f'key_{name}', 'AREA', tuple(e + Vector((0.42, -0.72, 0.28)) * s), (0, 0, 0), ke * energy_k, kc,
                      0.22 * s, parent=parent)
        aim(k, e)
        r = add_light(f'rim_{name}', 'SPOT', tuple(e + Vector((-0.45, 0.62, 0.42)) * s), (0, 0, 0), re * energy_k, rc,
                      0.2 * s, spot=(D(45), 0.5), parent=parent)
        aim(r, e)
        # aim() usa la ubicación local; como el padre está en reposo en el origen, local == mundo aquí
        out[k.name], out[r.name] = 0.0, 0.5
    return out


def apply(SC, look, setinfo, ctx, chars, eyes_local):
    params = ctx.get('look', {})
    if look == 'noche':
        w = _world(SC, params.get('mundo', '#0A1724'), params.get('mundo_fuerza', 0.35))
        nt = w.node_tree
        vol = node(nt, 'ShaderNodeVolumePrincipled', {'Density': params.get('bruma', 0.012), 'Anisotropy': 0.45})
        vol.inputs['Color'].default_value = hexc('#C9D6E6')
        out = [n for n in nt.nodes if n.type == 'OUTPUT_WORLD'][0]
        nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])
        ee = SC.eevee
        for k, v in (('volumetric_tile_size', '4'), ('volumetric_samples', 64), ('volumetric_end', 9.0),
                     ('volumetric_sample_distribution', 0.6), ('use_volumetric_shadows', False),
                     ('bokeh_max_size', 120.0), ('bokeh_threshold', 0.6), ('bokeh_neighbor_max', 12.0)):
            try:
                setattr(ee, k, v)
            except Exception as e:
                print('[skip]', k, e)
        try:
            SC.view_settings.look = 'AgX - Punchy'
        except Exception as e:
            print('[skip] look', e)
        amb = add_light('n_amb', 'AREA', (0.0, 0.8, 2.6), (0, 0, 0), params.get('luz_ambiente', 32.0), (0.5, 0.62, 0.85), 4.0)
        aim(amb, (0, 0.8, 0))
    else:
        _world(SC, params.get('mundo', '#6E655C'), params.get('mundo_fuerza', 0.8))
        try:
            SC.view_settings.look = 'AgX - Medium High Contrast'
        except Exception:
            pass
        amb = add_light('d_amb', 'AREA', (0.0, -0.5, 2.6), (0, 0, 0), params.get('luz_ambiente', 90.0), (1.0, 0.95, 0.9), 4.0)
        aim(amb, (0, 0.3, 0))
    vf = {}
    hook = setinfo.get('looks', {}).get(look)
    if hook:
        vf.update(hook(SC, ctx) or {})
    vf.update(character_lights(chars, look, eyes_local, params.get('luz_personajes', 1.0)))
    for o in bpy.data.objects:
        if o.type != 'LIGHT':
            continue
        o.data.volume_factor = vf.get(o.name, 0.0)
        # sombras solo en las luces que esculpen (evita llenar el búfer de sombras de EEVEE)
        if o.name.endswith('_glow') or o.name in ('n_amb', 'd_amb') or o.name.startswith('ceil_L'):
            o.data.use_shadow = False
