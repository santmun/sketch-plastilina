# perform.py — convierte blocking.json (anclado a líneas/palabras del guion) en poses por cuadro.
# Genérico: miradas automáticas (al que habla), expresiones, gestos con puntos de paso, escondites con saltos,
# mascotas sobre hombros, props del set, parpadeo e idle. Ver references/blocking.md.
import math
from mathutils import Vector
from rig import Track, ease
from project import blink_schedule, blink_val, seed_of

# ------------------------------------------------------------------ expresiones
# humano: lidU lidL brow browL(+) worry angry smile wide sweat      | mascota: ojos
EXPR = {
    'neutral':          (dict(lidU=32, lidL=28), 'normal'),
    'calma':            (dict(lidU=26, lidL=30, smile=0.15), 'calm'),
    'nervioso':         (dict(lidU=38, lidL=26, brow=0.3, worry=0.8), 'normal'),
    'alivio':           (dict(lidU=10, lidL=30, brow=0.2, smile=0.25), 'calm'),
    'feliz':            (dict(lidU=30, lidL=34, brow=0.3, smile=0.75), 'happy'),
    'sonrisa_nerviosa': (dict(lidU=34, lidL=24, worry=0.9, smile=0.85, wide=0.5, sweat=1), 'happy'),
    'sorpresa':         (dict(lidU=56, lidL=40, brow=1.2, wide=0.4), 'wide'),
    'susto':            (dict(lidU=60, lidL=40, brow=1.3, worry=0.5, wide=0.5, sweat=1), 'wide'),
    'triste':           (dict(lidU=22, lidL=30, brow=0.4, worry=1.0, smile=-0.3), 'sad'),
    'culpable':         (dict(lidU=20, lidL=30, brow=0.3, worry=1.0, smile=-0.2, sweat=1), 'sad'),
    'enojado':          (dict(lidU=20, lidL=34, brow=-0.4, angry=0.7, smile=-0.2), 'determined'),
    'sospecha':         (dict(lidU=14, lidL=30, browL=0.9, angry=0.3), 'suspicious'),
    'presumido':        (dict(lidU=16, lidL=34, smile=0.45, browL=0.4), 'calm'),
    'determinado':      (dict(lidU=24, lidL=30, brow=-0.2, angry=0.35), 'determined'),
    'tierno':           (dict(lidU=26, lidL=32, worry=0.6, smile=0.3), 'happy'),
    'serio':            (dict(lidU=24, lidL=34, smile=0.0, brow=-0.1), 'normal'),
}
MASCOT_EYES = ('normal', 'calm', 'happy', 'wide', 'sad', 'determined', 'suspicious')
FACE_KEYS = ('lidU', 'lidL', 'brow', 'browL', 'worry', 'angry', 'smile', 'wide', 'sweat')
FACE_DEF = dict(lidU=32, lidL=28, brow=0.0, browL=0.0, worry=0.0, angry=0.0, smile=0.0, wide=0.0, sweat=0.0)

# ------------------------------------------------------------------ gestos de brazos (humanos)
# (objetivo muñeca, polo del codo, muñeca euler grados, espacio, tipo) — calibrados en Santi (hombro x 0.15, z 0.36)
# tipo: 'cabeza' = toca la cabeza (se pasa por un punto «fuera» para no atravesarla); 'hombro' / 'centro' = escalado por complexión
A = {
    'lapL': ((0.15, -0.30, 0.61), (0.6, 1.0, -0.3), (0, 0, 80), 'root', 'centro'),
    'lapR': ((-0.15, -0.30, 0.61), (-0.6, 1.0, -0.3), (0, 0, -80), 'root', 'centro'),
    'clawdL': ((0.29, -0.25, 0.63), (0.8, 0.6, -0.4), (0, 20, 70), 'root', 'centro'),     # junto a Clawd, por fuera
    'clawdR': ((-0.29, -0.25, 0.63), (-0.8, 0.6, -0.4), (0, -20, -70), 'root', 'centro'),
    'whisperR': ((-0.12, -0.21, 0.47), (-1.0, 0.2, -0.6), (0, 0, -100), 'spine', 'cabeza'),
    'upL': ((0.27, -0.2, 0.46), (1.0, 0.6, -0.8), (-20, 0, 10), 'spine', 'hombro'),
    'upR': ((-0.27, -0.2, 0.46), (-1.0, 0.6, -0.8), (-20, 0, -10), 'spine', 'hombro'),
    'cheekoutL': ((0.3, -0.26, 0.34), (0.6, -0.3, -1.0), (0, 30, 90), 'spine', 'cabeza'),
    'cheekoutR': ((-0.3, -0.26, 0.34), (-0.6, -0.3, -1.0), (0, -30, -90), 'spine', 'cabeza'),
    'cheekL': ((0.16, -0.12, 0.38), (0.6, -0.3, -1.0), (0, 30, 90), 'spine', 'cabeza'),
    'cheekR': ((-0.16, -0.12, 0.38), (-0.6, -0.3, -1.0), (0, -30, -90), 'spine', 'cabeza'),
    'chestR': ((-0.05, -0.14, 0.25), (-1.0, 0.5, -0.5), (0, 0, -60), 'spine', 'centro'),
    'palmsL': ((0.2, -0.33, 0.24), (1.0, 0.5, -0.4), (0, 0, -60), 'spine', 'hombro'),
    'palmsR': ((-0.2, -0.33, 0.24), (-1.0, 0.5, -0.4), (0, 0, 60), 'spine', 'hombro'),
    'neckR': ((-0.17, 0.04, 0.52), (-1.0, -0.3, 0.6), (-30, 50, 20), 'spine', 'cabeza'),
    'napeoutR': ((-0.33, 0.08, 0.56), (-1.0, -0.3, 0.6), (0, 40, 10), 'spine', 'cabeza'),
    'scratchR': ((-0.18, 0.04, 0.5), (-1.0, -0.3, 0.6), (0, 40, 10), 'spine', 'cabeza'),
    'hangL': ((0.2, 0.0, 0.0), (0.6, 1.0, 0.0), (0, 0, 0), 'spine', 'hombro'),
    'hangR': ((-0.2, 0.0, 0.0), (-0.6, 1.0, 0.0), (0, 0, 0), 'spine', 'hombro'),
    'armrestL': ((0.24, -0.16, 0.66), (1.0, 0.5, -0.2), (0, 0, 70), 'root', 'hombro'),
    'armrestR': ((-0.24, -0.16, 0.66), (-1.0, 0.5, -0.2), (0, 0, -70), 'root', 'hombro'),
    'pointR': ((-0.14, -0.42, 0.36), (-1.0, 0.3, -0.5), (0, 0, 0), 'spine', 'hombro'),
    'pointL': ((0.14, -0.42, 0.36), (1.0, 0.3, -0.5), (0, 0, 0), 'spine', 'hombro'),
    'mugR': ((-0.1, -0.3, 0.22), (-1.0, 0.3, -0.5), (0, 0, 0), 'spine', 'centro'),
    'mugsipR': ((-0.04, -0.25, 0.44), (-1.0, 0.3, -0.6), (0, 0, 40), 'spine', 'cabeza'),
    'hipL': ((0.24, -0.02, 0.1), (1.0, 0.8, 0.0), (0, 0, 70), 'spine', 'hombro'),
    'hipR': ((-0.24, -0.02, 0.1), (-1.0, 0.8, 0.0), (0, 0, -70), 'spine', 'hombro'),
    'counterL': ((0.18, -0.36, 0.0), (1.0, 0.5, -0.3), (0, 0, 80), 'spine', 'hombro'),
    'counterR': ((-0.18, -0.36, 0.0), (-1.0, 0.5, -0.3), (0, 0, -80), 'spine', 'hombro'),
}
# gesto -> (izq, der); None = el gesto base de la postura
GESTOS = {
    'regazo': ('lapL', 'lapR'), 'abraza_mascota': ('clawdL', 'clawdR'), 'susurro': (None, 'whisperR'),
    'arriba': ('upL', 'upR'), 'mejillas': ('cheekL', 'cheekR'), 'pecho': (None, 'chestR'), 'palmas': ('palmsL', 'palmsR'),
    'nuca': (None, 'neckR'), 'rasca_nuca': (None, 'scratchR'), 'descansa': ('armrestL', 'armrestR'),
    'colgando': ('hangL', 'hangR'), 'senala': (None, 'pointR'), 'senala_izq': ('pointL', None),
    'taza': (None, 'mugR'), 'sorbo': (None, 'mugsipR'), 'jarras': ('hipL', 'hipR'), 'mostrador': ('counterL', 'counterR'),
}
VIA = {'cheekL': 'cheekoutL', 'cheekR': 'cheekoutR', 'neckR': 'napeoutR', 'scratchR': 'napeoutR', 'whisperR': None,
       'mugsipR': None}

# brazos de mascota: (subir, adelante) en grados por lado
MASCOT_ARMS = {
    'abajo': ((5, 0), (5, 0)), 'arriba': ((80, 0), (80, 0)), 'senala': ((10, 0), (80, 25)), 'senala_izq': ((80, 25), (10, 0)),
    'jarras': ((-20, 0), (-20, 0)), 'abrazo': ((35, 0), (35, 0)), 'manos_juntas': ((55, 10), (55, 10)),
    'encoge': ((25, 10), (25, 10)), 'tapa_boca': ((70, 35), (70, 35)),
}


def _rel(v):
    return v if isinstance(v, (int, float)) else 0.0


class Ctx:
    """lo que el actor necesita del mundo: proyecto, personajes, set"""

    def __init__(self, prj, chars, setinfo):
        self.prj = prj
        self.chars = chars
        self.set = setinfo


class Performer:
    def __init__(self, prj, chars, setinfo):
        self.prj = prj
        self.chars = chars
        self.set = setinfo
        self.B = {k: v for k, v in prj.blocking.get('personajes', {}).items() if not k.startswith('_')}
        for gname, g in prj.blocking.get('gestos_custom', {}).items():
            if gname.startswith('_'):
                continue
            pair = []
            for side in 'LR':
                spec = g.get(side)
                if not spec:
                    pair.append(None)
                    continue
                key = f'{gname}_{side}'
                A[key] = (tuple(spec[0]), tuple(spec[1]), tuple(spec[2]), spec[3] if len(spec) > 3 else 'spine',
                          spec[4] if len(spec) > 4 else 'centro')
                if A[key][4] == 'cabeza':
                    via = g.get('via_' + side)
                    if via:
                        A[key + '_fuera'] = (tuple(via[0]), tuple(via[1]), tuple(via[2]), 'spine', 'cabeza')
                    else:   # punto de paso: la misma mano más afuera y más atrás de la cabeza
                        tg = A[key][0]
                        A[key + '_fuera'] = ((tg[0] * 1.9, tg[1] + 0.05, tg[2] + 0.04), A[key][1], A[key][2], 'spine', 'cabeza')
                    VIA[key] = key + '_fuera'
                pair.append(key)
            GESTOS[gname] = tuple(pair)
        self.T = prj.T
        self.dt = 2.0 / prj.fps
        self.state = {n: {} for n in chars}
        self.events = []
        self.hidden = {}
        self.blinks = {n: blink_schedule(seed_of(n), prj.t_end) for n in chars}
        self._prep()

    # -------------------------------------------------------------- utilidades de pistas
    def track(self, keys, default=None):
        """[[tiempo, valor, (dur|modo)], ...] -> lista ordenada (t, v, extra)"""
        out = []
        for k in keys or []:
            t = self.T(k[0])
            out.append((t, k[1], k[2] if len(k) > 2 else None))
        out.sort(key=lambda x: x[0])
        if not out and default is not None:
            out = [(0.0, default, None)]
        return out

    @staticmethod
    def step(keys, t):
        cur = keys[0][1] if keys else None
        t0 = keys[0][0] if keys else 0.0
        for tk, v, _ in keys:
            if t >= tk:
                cur, t0 = v, tk
        return cur, t0

    def _prep(self):
        prj = self.prj
        self.look = {}
        self.expr = {}
        self.arms = {}
        self.places = {}
        self.actions = {}
        self.extra = {}
        for name, ch in self.chars.items():
            b = self.B.get(name, {})
            self.look[name] = self.track(b.get('mira_a'), 'auto')
            self.expr[name] = self.track(b.get('expresion'), 'neutral')
            self.actions[name] = self.track(b.get('acciones'))
            hid = self.track(b.get('oculto'), False)
            if b.get('aparece') is not None:
                ta = self.T(b['aparece'])
                hid = [(0.0, True, None), (ta, False, None)]
                self.events.append(dict(t=round(ta, 3), quien=name, evento='aparece'))
            self.hidden[name] = hid
            if ch.kind == 'humano':
                base = 'regazo' if ch.sit else 'colgando'
                self.arms[name] = self._human_arm_plan(ch, self.track(b.get('gestos'), base), base)
                self.extra[name] = dict(lean=Track([(t, v, e if isinstance(e, str) else 'ease') for t, v, e in
                                                    self.track(b.get('inclinacion'))], None) if b.get('inclinacion') else None,
                                        giro=self.track(b.get('giro'), 0.0))
            else:
                self.arms[name] = self.track(b.get('brazos'), 'abajo')
            lug = b.get('lugar') or ([[0, prj.cast[name]['lugar']]] if prj.cast.get(name, {}).get('lugar') else None)
            self.places[name] = self._place_plan(name, ch, self.track(lug))
        self.props = {k: Track([(t, v, e if isinstance(e, str) else 'ease') for t, v, e in self.track(keys)], 0.0)
                      for k, keys in prj.blocking.get('props', {}).items() if not k.startswith('_')}
        # saltos de mascota hacia/desde el cuerpo de un humano: ese humano se echa para atrás y deja espacio
        self.make_room = {}
        for name, plan in self.places.items():
            for i in range(1, len(plan)):
                for spec in (plan[i]['spec'], plan[i - 1]['spec']):
                    if isinstance(spec, str) and '.' in spec and spec.split('.')[0] in self.chars:
                        self.make_room.setdefault(spec.split('.')[0], []).append(plan[i]['t'])

    # -------------------------------------------------------------- lugares (anclajes del set o de otros personajes)
    def anchor_point(self, spec, t=None):
        """'set:nombre' | 'nombre' (anclaje del set) | 'PERSONAJE.anclaje' -> (Vector mundo, yaw grados, host)"""
        if isinstance(spec, (list, tuple)):
            return Vector(spec), 0.0, None
        s = str(spec)
        if '.' in s and s.split('.')[0] in self.chars:
            who, sock = s.split('.', 1)
            host = self.chars[who]
            return host.world_point(sock), None, who
        key = s[4:] if s.startswith('set:') else s
        A = self.set['anchors']
        if key in A:
            a = A[key]
            p = Vector(a['pos'])
            if a.get('sigue') and a['sigue'] in self.props:
                d = a.get('eje', (0, 1, 0))
                p = p + Vector(d) * self.props[a['sigue']](t if t is not None else 0.0)
            return p, a.get('yaw', None), None
        S = self.set['seats']
        if key in S:
            return Vector(S[key]['pos']), S[key].get('yaw', 0.0), None
        raise KeyError(f'lugar desconocido «{spec}». Anclajes del set: {sorted(A)}; asientos: {sorted(S)}')

    def _place_plan(self, name, ch, keys):
        if not keys:
            return []
        plan = []
        for i, (t, spec, extra) in enumerate(keys):
            plan.append(dict(t=t, spec=spec, dur=extra if isinstance(extra, (int, float)) else None))
        return plan

    def place(self, name, t):
        """(pos, yaw_ancla, host, fase_salto 0..1|None, velocidad)"""
        ch = self.chars[name]
        plan = self.places[name]
        if not plan:
            return Vector((0, 0, 0)), 0.0, None, None, 0.0
        cur = plan[0]
        k = 0
        for i, s in enumerate(plan):
            if t >= s['t']:
                cur, k = s, i
        p1, y1, host = self.anchor_point(cur['spec'], t)
        if k == 0:
            return p1, y1, host, None, 0.0
        prev = plan[k - 1]
        p0, y0, _ = self.anchor_point(prev['spec'], cur['t'])
        dist = (p1 - p0).length
        if ch.kind == 'humano':
            dur = cur['dur'] or max(0.4, dist / 0.9)
        else:
            dur = cur['dur'] or max(0.3, min(0.75, 0.25 + dist * 0.8))
        x = (t - cur['t']) / dur
        if x >= 1.0:
            return p1, y1, host, None, 0.0
        if ch.kind == 'humano':
            p = p0.lerp(p1, ease(x) if dist < 0.3 else x)
            return p, y1, None, x, dist / dur
        xe = ease(x)
        p = p0.lerp(p1, xe)
        hop = abs(p1.z - p0.z) > 0.04 or dist > 0.3
        if hop:
            # arco alto si sube (salta POR ENCIMA de rodillas/bordes, no a través)
            p.z += (0.08 + 0.25 * dist + 0.6 * max(0.0, p1.z - p0.z)) * math.sin(math.pi * xe) * 0.75
        return p, y1, host, x, (dist / dur) * (0 if hop else 1)

    # -------------------------------------------------------------- miradas
    def look_target(self, name, t):
        spec, t0 = self.step(self.look[name], t)
        if spec != 'auto':
            return spec
        prj = self.prj
        sp = prj.who_speaks(t + 0.15, pad=0.0) or prj.who_speaks(t, pad=0.25)
        if sp and sp != name and sp in self.chars and not self.is_hidden(sp, t):
            return sp
        # si habla él (o nadie): mira al último interlocutor distinto, o al siguiente
        k = prj.line_at(t)
        for j in list(range(k, -1, -1)) + list(range(k + 1, len(prj.lines))):
            w = prj.lines[j]['who'] if j >= 0 else None
            if w and w != name and w in self.chars and not self.is_hidden(w, t):
                return w
        return 'frente'

    def look_point(self, name, spec, t):
        ch = self.chars[name]
        eye = ch.world_point('ojos')
        fwd = ch.facing()
        if spec in ('frente', None):
            return eye + fwd * 2.0
        if spec == 'abajo':
            return eye + fwd * 0.5 + Vector((0, 0, -0.6))
        if spec == 'arriba':
            return eye + fwd * 1.0 + Vector((0, 0, 0.6))
        if spec in ('izquierda', 'derecha'):
            side = fwd.cross(Vector((0, 0, 1))) * (-1 if spec == 'izquierda' else 1)
            return eye + side * 1.5 + fwd * 0.4
        if isinstance(spec, (list, tuple)):
            return Vector(spec)
        s = str(spec)
        if s in self.chars:
            return self.chars[s].world_point('ojos')
        p, _, _ = self.anchor_point(s, t)
        return p

    def is_hidden(self, name, t):
        v, _ = self.step(self.hidden[name], t)
        return bool(v)

    # -------------------------------------------------------------- expresiones
    def face(self, name, t):
        """(valores de cara del humano, ojos de mascota) con transición suave entre expresiones"""
        prev = cur = dict(FACE_DEF)
        eyes, t0, dur = 'normal', 0.0, 0.25
        for tk, v, d in self.expr[name]:
            if t < tk:
                break
            if v not in EXPR and v not in MASCOT_EYES:
                raise KeyError(f'{name}: expresión desconocida «{v}». Opciones: {sorted(EXPR)}')
            hv, ev = EXPR.get(v, (None, v))
            nxt = dict(FACE_DEF)
            if hv:
                nxt.update(hv)
            prev, cur, eyes, t0 = cur, nxt, ev, tk
            dur = d if isinstance(d, (int, float)) else 0.25
        x = ease(min(1.0, max(0.0, (t - t0) / max(1e-3, dur))))
        return {k: prev[k] + (cur[k] - prev[k]) * x for k in FACE_KEYS}, eyes

    # -------------------------------------------------------------- brazos de humanos
    def _preset(self, ch, name):
        if name is None:
            return None
        tgt, pole, wr, space, kind = A[name]
        tgt = list(tgt)
        if kind == 'hombro' or space == 'root':
            tgt[0] += math.copysign((ch.sh_x - 0.15) * 0.8, tgt[0])
            if space == 'spine':
                tgt[2] += (ch.sh_z - 0.36) * 0.6
        elif kind == 'cabeza':     # relativo a la cabeza real (Santi: cuello a 0.43, cabeza rx 0.156)
            tgt[2] += ch.neck_z - 0.43
            tgt[0] *= ch.H.rx / 0.156
        if not ch.sit and space == 'root':
            return self._preset(ch, 'hangL' if tgt[0] > 0 else 'hangR')
        if not ch.sit and space == 'spine' and name in ('lapL', 'lapR'):
            return self._preset(ch, 'hangL' if tgt[0] > 0 else 'hangR')
        return (tuple(tgt), pole, wr, space)

    def _human_arm_plan(self, ch, keys, base):
        """lista por lado de (t, preset, dur) con puntos de paso para los gestos que tocan la cabeza"""
        basev = GESTOS[base]
        plan = {'L': [], 'R': []}
        last = {'L': basev[0], 'R': basev[1]}
        for t, g, d in keys:
            if g not in GESTOS:
                raise KeyError(f'{ch.name}: gesto desconocido «{g}». Opciones: {sorted(GESTOS)}')
            pair = GESTOS[g]
            dur = d if isinstance(d, (int, float)) else 0.35
            for i, side in enumerate('LR'):
                want = pair[i] if pair[i] is not None else last[side]   # None = esa mano se queda como estaba
                if not ch.sit and want in ('lapL', 'lapR', 'armrestL', 'armrestR', 'clawdL', 'clawdR'):
                    want = 'hangL' if side == 'L' else 'hangR'
                old = last[side]
                if want == old and plan[side]:
                    continue
                if old in VIA and VIA[old]:            # sale de la cabeza por fuera
                    plan[side].append((t - 0.02, VIA[old], 0.2))
                    t_ = t + 0.2
                else:
                    t_ = t
                if want in VIA and VIA[want]:          # entra a la cabeza por fuera
                    plan[side].append((t_ - 0.25, VIA[want], 0.25))
                    plan[side].append((t_, want, 0.3))
                else:
                    plan[side].append((t_, want, dur))
                last[side] = want
        for side in 'LR':
            plan[side].sort(key=lambda x: x[0])
            if not plan[side] or plan[side][0][0] > 0:
                plan[side].insert(0, (0.0, basev[0 if side == 'L' else 1], 0.01))
        return plan

    def human_arm(self, ch, plan, t):
        cur = self._preset(ch, plan[0][1])
        for i in range(1, len(plan)):
            ti, pi, di = plan[i]
            if t < ti:
                break
            nxt = self._preset(ch, pi)
            if t < ti + di:
                x = ease((t - ti) / di)
                return (tuple(Vector(cur[0]).lerp(Vector(nxt[0]), x)), tuple(Vector(cur[1]).lerp(Vector(nxt[1]), x)),
                        tuple(Vector(cur[2]).lerp(Vector(nxt[2]), x)), nxt[3] if x > 0.5 else cur[3])
            cur = nxt
        return cur

    # -------------------------------------------------------------- acciones (aditivas)
    def action(self, name, t):
        out = {}
        for tk, a, d in self.actions[name]:
            dur = d if isinstance(d, (int, float)) else {'asiente': 0.6, 'niega': 0.8, 'sobresalto': 0.7, 'suspiro': 1.0,
                                                         'risa': 1.0, 'salta': 0.45, 'asoma_ojo': 1.5, 'saluda': 1.2,
                                                         'tiembla': 0.8, 'susurra': 1.5, 'encoge': 0.8}.get(a, 0.6)
            if not tk <= t <= tk + dur:
                continue
            x = (t - tk) / dur
            env = math.sin(math.pi * x)
            if a == 'asiente':
                out['hp'] = out.get('hp', 0) + 9 * math.sin(2 * math.pi * 2 * x) * env
            elif a == 'niega':
                out['hy'] = out.get('hy', 0) + 14 * math.sin(2 * math.pi * 2 * x) * env
            elif a == 'sobresalto':
                out['lean'] = out.get('lean', 0) - 10 * (1 - x) ** 2 * (x > 0.02)
                out['hp'] = out.get('hp', 0) - 10 * env
            elif a == 'suspiro':
                out['lean'] = out.get('lean', 0) + 6 * env
                out['hp'] = out.get('hp', 0) + 6 * env
            elif a == 'risa':
                out['lean'] = out.get('lean', 0) + 3 * abs(math.sin(x * math.pi * 8)) * env
                out['hp'] = out.get('hp', 0) - 4 * env
            elif a == 'encoge':
                out['side'] = out.get('side', 0)
                out['hp'] = out.get('hp', 0) - 3 * env
            elif a == 'salta':
                out['dz'] = out.get('dz', 0) + 0.06 * math.sin(math.pi * x)
                out['squash'] = out.get('squash', 0) + (0.2 if 0.15 < x < 0.85 else -0.25) * env
            elif a == 'asoma_ojo':
                out['lean_side'] = 16 * min(1.0, x * 5, (1 - x) * 5)
            elif a == 'saluda':
                out['armR'] = (70 + 25 * math.sin(2 * math.pi * 3 * x), 10)
            elif a == 'tiembla':
                out['roll'] = out.get('roll', 0) + 4 * math.sin(2 * math.pi * 9 * x) * env
            elif a == 'susurra':
                out['whisper'] = env
        return out

    # -------------------------------------------------------------- poses
    def _smooth(self, name, key, target, tau):
        st = self.state[name]
        if key not in st:
            st[key] = target
            return target
        a = 1 - math.exp(-self.dt / tau)
        if isinstance(target, tuple):
            v = tuple(c + (tt - c) * a for c, tt in zip(st[key], target))
        else:
            v = st[key] + (target - st[key]) * a
        st[key] = v
        return v

    def pose(self, name, t):
        ch = self.chars[name]
        if ch.kind == 'humano':
            return self.pose_human(name, ch, t)
        return self.pose_mascot(name, ch, t)

    def pose_human(self, name, ch, t):
        sp = self.prj.speech
        o, rnd, wide = sp.mouth(name, t)
        pos, yaw_a, host, walk_x, speed = self.place(name, t)
        ex = self.extra[name]
        giro, _ = self.step(ex['giro'], t)
        yaw = (yaw_a if yaw_a is not None else 0.0)
        walking = walk_x is not None and speed > 0.05
        if walking:
            d = self.place(name, t + 0.05)[0] - self.place(name, t - 0.05)[0]
            if d.length > 1e-4:
                yaw = math.degrees(math.atan2(d.x, -d.y))
        yaw = self._smooth(name, 'yaw', yaw + _rel(giro), 0.12)
        fx, _ = self.face(name, t)
        act = self.action(name, t)
        lean0 = 12.0 if ch.sit else 2.0
        if ex['lean'] is not None:
            lean0 = ex['lean'](t)
        room = 0.0
        for th in self.make_room.get(name, ()):
            x = (t - (th - 0.2)) / 1.0
            if 0 <= x <= 1:
                room = max(room, math.sin(math.pi * x))
        lean = lean0 + 1.2 * math.sin(t * 2 * math.pi / 3.6) + act.get('lean', 0) - 14 * room
        # mirada: cabeza + ojos hacia el objetivo, en el marco del cuerpo
        tgt = self.look_target(name, t)
        P = self.look_point(name, tgt, t)
        eye = ch.world_point('ojos')
        v = P - eye
        c, s = math.cos(math.radians(-yaw)), math.sin(math.radians(-yaw))
        lx, ly = v.x * c - v.y * s, v.x * s + v.y * c
        yaw_t = math.degrees(math.atan2(lx, -ly))
        pitch_t = math.degrees(math.atan2(-v.z, max(1e-4, math.hypot(lx, ly))))
        twist = 0.0
        if ch.sit and abs(yaw_t) > 60:
            twist = math.copysign(min(25.0, abs(yaw_t) - 60), yaw_t)
        hy = max(-65.0, min(65.0, yaw_t - twist))
        hp = max(-25.0, min(28.0, pitch_t - lean))     # el resto de la mirada lo hacen los ojos
        gy = max(-28.0, min(28.0, (yaw_t - twist) - hy))
        gp = -max(-20.0, min(20.0, (pitch_t - lean) - hp))
        hy = self._smooth(name, 'hy', hy, 0.16)
        hp = self._smooth(name, 'hp', hp, 0.16)
        twist = self._smooth(name, 'tw', twist, 0.25)
        gy = self._smooth(name, 'gy', gy, 0.06)
        gp = self._smooth(name, 'gp', gp, 0.06)
        hp += 4.0 * o + act.get('hp', 0) - 14 * room
        hy += act.get('hy', 0)
        hr = 1.5 * math.sin(t * 2.1) + act.get('hr', 0)
        walkamp = 24 * min(1.0, speed / 0.5) if walking else 0.0
        arms = {k: self.human_arm(ch, self.arms[name][k], t) for k in 'LR'}
        return dict(pos=tuple(pos), yaw=yaw, hide=self.is_hidden(name, t), lean=lean, side=act.get('side', 0), twist=twist,
                    head=(hp, hy, hr), gaze=(gy, gp), lidU=fx['lidU'], lidL=fx['lidL'],
                    blink=blink_val(self.blinks[name], t), brow=fx['brow'], browL=fx['brow'] + fx['browL'], browR=fx['brow'],
                    worry=fx['worry'], angry=fx['angry'], sweat=fx['sweat'],
                    mouth=dict(open=o, round=rnd, wide=max(wide, fx['wide']), smile=max(0.0, fx['smile']),
                               frown=max(0.0, -fx['smile'])),
                    arms={k: a[:3] for k, a in arms.items()}, arm_space={k: a[3] for k, a in arms.items()},
                    walkphase=t * 2 * math.pi * 1.6, walkamp=walkamp)

    def pose_mascot(self, name, ch, t):
        sp = self.prj.speech
        o, _, _ = sp.mouth(name, t)
        pos, yaw_a, host, hop_x, speed = self.place(name, t)
        act = self.action(name, t)
        tgt = self.look_target(name, t)
        P = self.look_point(name, tgt, t)
        here = pos + Vector((0, 0, ch.half_h))
        v = P - here
        yaw_t = math.degrees(math.atan2(v.x, -v.y)) if v.xy.length > 1e-3 else 0.0
        ori = self._cache_list(f'{name}.orientacion', self.B.get(name, {}).get('orientacion'))
        if ori:
            ov, _ = self.step(ori, t)
            if isinstance(ov, (int, float)):
                yaw_t = ov
            elif ov in ('host', 'anfitrion') and host is not None:
                yaw_t = math.degrees(math.atan2(*(lambda f: (f.x, -f.y))(self.chars[host].facing())))
        if host is not None:
            # sobre otro personaje: se sienta un poco más arriba para no hundirse en él (la plastilina tiene relieve)
            pos = pos + Vector((0, 0, 0.022))
        if hop_x is not None and speed == 0:     # durante el salto mira hacia donde va
            pass
        yaw_t = self._unwrap(name, yaw_t)
        yaw = self._smooth(name, 'yaw', yaw_t, 0.14)
        pitch_t = math.degrees(math.atan2(v.z, max(1e-3, v.xy.length)))
        gz = max(-1.0, min(1.0, pitch_t / 35.0))
        # squash & stretch: anticipación, estiramiento en el aire, aterrizaje; respira y se infla al hablar
        sq = 0.015 * math.sin(t * 2 * math.pi / 2.8) + 0.20 * o + act.get('squash', 0)
        tuck = 0.0
        if hop_x is not None and speed == 0:
            sq += 0.22 * math.sin(math.pi * hop_x) - (0.28 * (1 - hop_x / 0.12) if hop_x < 0.12 else 0)
            tuck = math.sin(math.pi * hop_x)
        land = self._landing(name, t)
        sq -= (0.1 if host is not None else 0.25) * land     # sobre alguien aterriza suave (no se desparrama encima)
        trot = min(1.0, speed / 0.4) if speed > 0 else 0.0
        ph = t * 2 * math.pi * 4.2
        _, eyes = self.face(name, t)
        arm_name, _ = self.step(self.arms[name], t)
        arm = MASCOT_ARMS.get(arm_name, MASCOT_ARMS['abajo'])
        aL = (arm[0][0] + 12 * o, arm[0][1])
        aR = act.get('armR', (arm[1][0] + 12 * o, arm[1][1]))
        whisper = act.get('whisper', 0.0)
        hid = self.is_hidden(name, t)
        scale = float(self.prj.cast[name].get('escala', 1.0))
        b_ap = self.B.get(name, {}).get('aparece')
        if b_ap is not None and not hid:
            x = (t - self.T(b_ap)) / 0.25
            if 0 <= x < 1:
                scale *= 0.2 + 0.8 * x + 0.25 * math.sin(x * math.pi)
        return dict(pos=tuple(pos + Vector((0, 0, act.get('dz', 0) + 0.006 * abs(math.sin(ph)) * trot))),
                    yaw=yaw + (5 * math.sin(t * 5.3) if o > 0.05 else 0), pitch=0, roll=act.get('roll', 0) + 8 * whisper,
                    tilt=-6 * o - 10 * whisper, squash=sq, bob=0.0, lean_side=act.get('lean_side', 0),
                    armL=aL, armR=aR, legphase=ph, legamp=32 * trot, tuck=tuck, eyes=eyes,
                    blink=blink_val(self.blinks[name], t), mouth=min(1.0, o * 1.6), gaze=(0.0, gz * 0.5),
                    receipt=self.props_val(f'{name}.recibo', t), hide=hid, scale=scale)

    def _unwrap(self, name, a):
        st = self.state[name]
        if 'yaw' in st:
            prev = st['yaw']
            while a - prev > 180:
                a -= 360
            while a - prev < -180:
                a += 360
        return a

    def _landing(self, name, t):
        plan = self.places[name]
        for i in range(1, len(plan)):
            s = plan[i]
            p0, _, _ = self.anchor_point(plan[i - 1]['spec'], s['t'])
            p1, _, _ = self.anchor_point(s['spec'], s['t'])
            dist = (p1 - p0).length
            dur = s['dur'] or max(0.3, min(0.75, 0.25 + dist * 0.8))
            te = s['t'] + dur
            if te <= t <= te + 0.2:
                return math.sin(math.pi * (t - te) / 0.2)
        return 0.0

    def props_val(self, key, t):
        b = self.B.get(key.split('.')[0], {})
        k = key.split('.')[1]
        if k in b:
            tr = self._cache_track(key, b[k])
            return tr(t)
        return 0.0

    def _cache_list(self, key, keys):
        c = self.__dict__.setdefault('_tl', {})
        if key not in c:
            c[key] = self.track(keys) if keys else []
        return c[key]

    def _cache_track(self, key, keys):
        c = self.__dict__.setdefault('_tc', {})
        if key not in c:
            c[key] = Track([(t, v, e if isinstance(e, str) else 'ease') for t, v, e in self.track(keys)], 0.0)
        return c[key]

    def hop_events(self):
        """saltos/llegadas de mascotas (para sugerir SFX): build/eventos.json"""
        ev = list(self.events)
        for name, plan in self.places.items():
            for i in range(1, len(plan)):
                ev.append(dict(t=round(plan[i]['t'], 3), quien=name, evento=f'va a {plan[i]["spec"]}'))
        return sorted(ev, key=lambda e: e['t'])
