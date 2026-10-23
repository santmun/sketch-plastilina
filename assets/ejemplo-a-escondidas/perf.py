# perf.py — actuación, lip-sync, parpadeos y plan de planos de «A escondidas»
import json, math, os, random
from mathutils import Vector
from rig import Track, ease, lerp

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 24
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
WORDS = json.load(open(os.path.join(HERE, 'audio', 'palabras.json')))   # AssemblyAI sobre el dialogo.wav final (ms)
RMS = TL['rms']
LINES = TL['lineas']
from timing import T_END, N_FRAMES, W, keep_old, OLD_CUT, OLD_GAP, V, U   # re-tiempo (sin bpy)



def L(i):
    return LINES[i - 1]


# ============================================================ lip-sync
def _smooth(a, k=1):
    out = []
    for i in range(len(a)):
        s = a[max(0, i - k):i + k + 1]
        out.append(sum(s) / len(s))
    return out


RMS_S = _smooth(RMS, 1)
GAIN = {'SANTI': 1.0, 'CLAWD': 1.0, 'JEFE': 1.0, 'CHATGPT': 1.0, 'GEMINI': 1.0, 'MARIANA': 0.9}


def _line_norm():
    out = []
    for ln in LINES:
        f0, f1 = int(ln['start'] * FPS), int(ln['end'] * FPS) + 1
        seg = sorted(RMS_S[f0:min(f1, len(RMS_S))]) or [0.1]
        p90 = seg[int(len(seg) * 0.9) - 1] if len(seg) > 2 else seg[-1]
        out.append(max(0.04, p90))
    return out


NORM = _line_norm()


def _word_at(t):
    for w in WORDS:
        if w['start'] / 1000 - 0.02 <= t <= w['end'] / 1000 + 0.02:
            return w
    return None


def speech(who, t):
    """(abertura, redondez, ancho) de la boca de `who` en el tiempo t"""
    f = int(t * FPS)
    for i, ln in enumerate(LINES):
        if ln['who'] != who:
            continue
        if ln['start'] - 0.03 <= t <= ln['end'] + 0.05:
            r = RMS_S[min(f, len(RMS_S) - 1)]
            o = max(0.0, min(1.0, (r - 0.012) / (NORM[i] - 0.012)))
            o = o ** 0.75 * GAIN[who]
            if 'whisper' in ln['text']:
                o *= 0.75
            rnd, wide = 0.0, 0.0
            w = _word_at(t)
            if w:
                letters = [c for c in w['text'].lower() if c.isalpha()]
                if letters:
                    x = (t - w['start'] / 1000) / max(0.05, (w['end'] - w['start']) / 1000)
                    c = letters[min(len(letters) - 1, max(0, int(x * len(letters))))]
                    if c in 'oóuú':
                        rnd = 0.75
                    elif c in 'ií':
                        wide = 0.35
                    elif c in 'mbp':
                        o *= 0.25
            return min(1.0, o), rnd * min(1.0, o + 0.3), wide * o
    return 0.0, 0.0, 0.0


def talking(who, t, pad=0.0):
    for ln in LINES:
        if ln['who'] == who and ln['start'] - pad <= t <= ln['end'] + pad:
            return True
    return False


# ============================================================ parpadeos
def blink_schedule(seed, extra=()):
    rnd = random.Random(seed)
    ts = []
    t = rnd.uniform(0.5, 2.0)
    while t < T_END:
        ts.append(t)
        t += rnd.uniform(2.2, 4.6)
    return sorted(ts + list(extra))


def blink_val(sched, t, dur=0.13):
    for b in sched:
        if b <= t <= b + dur:
            x = (t - b) / dur
            return 1.0 if x < 0.6 else 1.0 - (x - 0.6) / 0.4
    return 0.0


# ============================================================ capas de presets (brazos)
class Blend:
    """[(t, valor, duración_transición)] — valor = cualquier cosa interpolable por fn"""

    def __init__(self, keys, fn):
        self.keys = sorted(keys, key=lambda k: k[0])
        self.fn = fn

    def __call__(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        cur = ks[0][1]
        for i in range(1, len(ks)):
            ti, vi, di = ks[i]
            if t < ti:
                break
            if t < ti + di:
                return self.fn(cur, vi, ease((t - ti) / di))
            cur = vi
        return cur


def lerp_arm(a, b, x):
    return (tuple(Vector(a[0]).lerp(Vector(b[0]), x)), tuple(Vector(a[1]).lerp(Vector(b[1]), x)),
            tuple(Vector(a[2]).lerp(Vector(b[2]), x)), b[3] if x > 0.5 else a[3])


# ------------------------------------------------------------ SANTI: presets de brazo (marco de la columna salvo 'root')
# (objetivo muñeca, polo, muñeca euler grados, espacio)
SA = {
    'lapL': ((0.15, -0.30, 0.61), (0.6, 1.0, -0.3), (0, 0, 80), 'root'),
    'lapR': ((-0.15, -0.30, 0.61), (-0.6, 1.0, -0.3), (0, 0, -80), 'root'),
    'clawdL': ((0.19, -0.27, 0.66), (0.8, 0.6, -0.4), (0, 20, 70), 'root'),     # manos alrededor de Clawd
    'clawdR': ((-0.19, -0.27, 0.66), (-0.8, 0.6, -0.4), (0, -20, -70), 'root'),
    'whisperR': ((-0.12, -0.21, 0.47), (-1.0, 0.2, -0.6), (0, 0, -100), 'spine'),
    'upL': ((0.27, -0.2, 0.46), (1.0, 0.6, -0.8), (-20, 0, 10), 'spine'),
    'upR': ((-0.27, -0.2, 0.46), (-1.0, 0.6, -0.8), (-20, 0, -10), 'spine'),
    'cheekoutL': ((0.3, -0.26, 0.34), (0.6, -0.3, -1.0), (0, 30, 90), 'spine'),
    'cheekoutR': ((-0.3, -0.26, 0.34), (-0.6, -0.3, -1.0), (0, -30, -90), 'spine'),
    'cheekL': ((0.16, -0.12, 0.38), (0.6, -0.3, -1.0), (0, 30, 90), 'spine'),
    'cheekR': ((-0.16, -0.12, 0.38), (-0.6, -0.3, -1.0), (0, -30, -90), 'spine'),
    'chestR': ((-0.05, -0.14, 0.25), (-1.0, 0.5, -0.5), (0, 0, -60), 'spine'),
    'palmsL': ((0.2, -0.33, 0.24), (1.0, 0.5, -0.4), (0, 0, -60), 'spine'),
    'palmsR': ((-0.2, -0.33, 0.24), (-1.0, 0.5, -0.4), (0, 0, 60), 'spine'),
    'neckR': ((-0.17, 0.04, 0.52), (-1.0, -0.3, 0.6), (-30, 50, 20), 'spine'),   # mano en la nuca, válida en los 3 momentos
    'napeoutR': ((-0.33, 0.08, 0.56), (-1.0, -0.3, 0.6), (0, 40, 10), 'spine'),   # paso por fuera antes de la nuca
    'scratchR': ((-0.18, 0.04, 0.5), (-1.0, -0.3, 0.6), (0, 40, 10), 'spine'),   # mano en la nuca (búsqueda sin choques)
    'clasp': None,
    'hangL': ((0.2, 0.0, 0.0), (0.6, 1.0, 0.0), (0, 0, 0), 'spine'),
    'hangR': ((-0.2, 0.0, 0.0), (-0.6, 1.0, 0.0), (0, 0, 0), 'spine'),
    'armrestL': ((0.24, -0.16, 0.66), (1.0, 0.5, -0.2), (0, 0, 70), 'root'),
    'armrestR': ((-0.24, -0.16, 0.66), (-1.0, 0.5, -0.2), (0, 0, -70), 'root'),
}


def sa(name):
    return SA[name]


def K(*keys, default=0.0):
    return Track(list(keys), default)


# ============================================================ ACTUACIÓN
# tiempos útiles
T = {ln['i']: (ln['start'], ln['end']) for ln in LINES}

# ------------------------------------------------------------ SANTI
S_lean = K((0, 18), (4.9, 16), (5.4, 10), (6.3, 12), (8.6, 12), (9.3, 12), (10.9, 4, 'out'), (11.4, 6), (13.9, 18, 'out'),
           (14.9, 15), (17.6, 14), (20.4, 13), (23.3, 10), (24.6, 10), (25.7, 14), (27.8, 13), (30.5, 8, 'out'),
           (31.4, 6), (32.3, 12), (36.1, 18), (38.7, 19), (43.5, 15), (45.6, 15), (45.75, 4, 'out'), (46.4, 6),
           (48.4, 4), (52.0, 6), (53.8, 4), (56.0, 6))
S_twist = K((0, 0), (30.5, 0), (31.3, -24), (32.4, -24), (33.0, 0), (45.6, 0), (45.9, -10), (47.0, 0))
S_side = K((0, 0), (8.6, 0), (9.0, 5), (9.6, 0), (25.7, 0), (26.6, -4), (27.6, 3), (28, 0))
S_yaw = K((0, 0), (46.1, 0), (46.7, -165, 'back'), (59, -165))
# cabeza: (pitch, yaw, roll) — pitch + mira abajo
S_head = K((0, (24, -4, 0)), (1.8, (26, -20, -4)), (2.4, (26, -14, -2)), (3.0, (24, 4, 2)), (4.3, (26, 0, 0)),
           (5.0, (8, 0, 0)), (5.5, (-6, 0, 4)), (6.4, (14, 0, 0)), (8.6, (16, 6, 8)), (9.5, (18, 4, 6)),
           (10.9, (2, 0, 0), 'out'), (11.4, (6, -3, -4)), (13.9, (28, 0, 0), 'out'), (14.9, (24, 6, -6)),
           (15.3, (22, 0, 0)), (17.7, (22, -6, 2)), (17.95, (30, -6, 2), 'out'), (18.3, (20, 4, -2)), (19.4, (22, -8, 0)),
           (20.4, (22, 0, 0)), (21.0, (16, 0, 0)), (21.7, (8, 22, 2)), (23.1, (10, 18, 2)), (23.4, (14, 0, -8)),
           (24.6, (16, 0, -10)), (25.7, (24, 0, 0)), (26.3, (22, 8, 4)), (27.0, (22, -8, -4)), (27.8, (24, 0, 0)),
           (30.5, (8, -10, 0), 'out'), (31.4, (6, -55, 0)), (32.3, (8, -60, 0)), (32.9, (16, -20, 0)),
           (36.1, (32, 0, -4)), (38.7, (30, 4, -6)), (41.0, (26, 0, -4)), (43.5, (30, 12, -6)), (44.6, (26, 18, -8)),
           (45.6, (24, 0, 0)), (45.8, (0, 0, 0), 'out'), (46.4, (0, -20, 0)), (47.0, (-8, 0, 0)), (48.4, (-6, 0, 6)),
           (49.2, (-4, 0, -6)), (50.3, (-6, 0, 6)), (51.2, (-8, 0, -4)), (52.4, (-6, -14, 0)), (53.6, (-6, 0, 0)),
           (55.8, (-8, 0, 2)), (57.5, (-6, -10, 0)))
S_gaze = K((0, (0, -6)), (1.7, (-25, -4)), (2.3, (-10, -6)), (3.0, (12, -4)), (3.6, (0, -8)), (21.7, (0, -8)),
           (21.9, (16, 0)), (23.1, (10, -4)), (23.4, (0, -8)), (30.5, (0, -8)), (31.2, (-30, 4)), (32.6, (-30, 4)),
           (33.0, (0, -8)), (43.6, (0, -8)), (43.9, (18, -14)), (45.4, (10, -12)), (45.6, (0, -6)), (46.2, (-14, 0)),
           (47.0, (0, 6)), (52.4, (-14, 6)), (53.0, (6, 6)), (53.8, (0, 6)), (56.2, (14, -2)), (57.2, (-10, -10)))
S_lidU = K((0, 32), (5.05, 32), (5.15, 8), (5.9, 8), (6.2, 32), (10.9, 58, 'out'), (12.4, 46), (13.9, 54), (15.2, 44),
           (17.2, 36), (20.4, 36), (20.9, 50), (21.6, 36), (23.3, 14), (24.7, 16), (25.0, 30), (30.5, 58, 'out'),
           (32.4, 50), (33.2, 34), (36.1, 22), (38.7, 24), (41.0, 28), (43.5, 22), (45.5, 26), (45.7, 60, 'out'),
           (46.8, 46), (48.4, 30), (52.4, 36), (53.8, 40), (55.8, 34))
S_lidL = K((0, 28), (8.6, 22), (9.5, 22), (10.0, 28), (10.9, 40), (12.4, 32), (23.3, 16), (24.7, 18), (25.0, 28),
           (30.5, 40), (32.6, 30), (43.5, 22), (45.5, 22), (45.7, 40), (47.0, 30), (48.4, 16), (52.0, 18), (52.4, 28))
S_brow = K((0, 0.0), (8.6, 0.0), (8.8, 0.9), (9.6, 0.5), (10.9, 1.3, 'out'), (12.0, 0.8), (13.9, 1.0), (15.2, 0.3),
           (17.7, 0.2), (20.9, 0.8), (21.6, 0.2), (23.3, -0.4), (24.7, -0.3), (25.0, 0.0), (30.5, 1.3, 'out'),
           (32.4, 1.0), (33.2, 0.2), (36.1, 0.0), (45.6, 0.0), (45.75, 1.2), (47.0, 0.6), (48.4, 0.7), (52.0, 0.5),
           (53.8, 0.3), (55.8, 0.4))
S_browL = K((0, 0.0), (23.3, 0.0), (23.5, 0.9), (24.7, 0.8), (25.0, 0.0))
S_worry = K((0, 0.7), (4.9, 0.7), (5.4, 0.0), (8.6, 0.0), (10.9, 0.3), (13.9, 1.0), (15.2, 0.5), (17.7, 0.9),
            (20.4, 0.6), (23.3, 0.0), (25.7, 0.9), (27.8, 0.6), (30.5, 0.4), (32.6, 0.5), (36.1, 1.0), (38.7, 0.9),
            (41.0, 0.4), (43.5, 0.5), (45.6, 0.4), (46.0, 0.8), (48.4, 0.9), (52.0, 0.9), (53.8, 0.5), (55.8, 0.2))
S_angry = K((0, 0.0), (23.3, 0.0), (23.5, 0.5), (24.7, 0.4), (25.0, 0.0))
S_smile = K((0, 0.0), (6.6, 0.0), (7.6, 0.3), (8.6, 0.8), (9.6, 0.6), (10.0, 0.0), (36.0, 0.0), (36.1, -0.3),
            (38.7, -0.3), (41.0, 0.1), (42.6, 0.35), (43.5, 0.5), (45.5, 0.4), (45.7, 0.0), (48.3, 0.0), (48.5, 0.9),
            (52.0, 0.8), (53.8, 0.6), (55.9, 0.8))
S_wide = K((0, 0.0), (10.9, 0.0), (11.0, 0.5), (11.5, 0.0), (48.4, 0.0), (48.6, 0.55), (51.9, 0.5), (52.4, 0.3),
           (53.8, 0.1))
S_sweat = K((0, 0), (11.9, 0, 'step'), (12.0, 1, 'step'), (25.0, 1, 'step'), (25.1, 0, 'step'), (25.8, 0, 'step'),
            (25.9, 1, 'step'), (30.0, 1, 'step'), (30.1, 0, 'step'), (46.0, 0, 'step'), (46.1, 1, 'step'),
            (54.5, 1, 'step'), (54.6, 0, 'step'))
S_arms = Blend([(0, (sa('lapL'), sa('lapR')), 0.01), (3.3, (sa('clawdL'), sa('clawdR')), 0.5),
                (5.0, (sa('lapL'), sa('lapR')), 0.5), (8.55, (sa('lapL'), sa('chestR')), 0.4),
                (9.7, (sa('clawdL'), sa('clawdR')), 0.4), (10.88, (sa('upL'), sa('upR')), 0.18),
                (12.2, (sa('lapL'), sa('lapR')), 0.6), (13.75, (sa('cheekoutL'), sa('cheekoutR')), 0.15), (13.92, (sa('cheekL'), sa('cheekR')), 0.15),
                (15.3, (sa('cheekoutL'), sa('cheekoutR')), 0.18), (15.5, (sa('lapL'), sa('lapR')), 0.5),
                (17.5, (sa('lapL'), sa('napeoutR')), 0.3), (17.82, (sa('lapL'), sa('neckR')), 0.3),
                (20.2, (sa('lapL'), sa('napeoutR')), 0.25), (20.47, (sa('lapL'), sa('lapR')), 0.4), (25.65, (sa('palmsL'), sa('palmsR')), 0.35),
                (27.9, (sa('lapL'), sa('lapR')), 0.5), (30.5, (sa('upL'), sa('upR')), 0.2),
                (32.6, (sa('lapL'), sa('lapR')), 0.5), (36.0, (sa('lapL'), sa('lapR')), 0.7),
                (43.3, (sa('lapL'), sa('napeoutR')), 0.35), (43.7, (sa('lapL'), sa('neckR')), 0.35), (45.4, (sa('lapL'), sa('napeoutR')), 0.18),
                (45.6, (sa('upL'), sa('upR')), 0.15),
                (46.8, (sa('armrestL'), sa('armrestR')), 0.4), (48.3, (sa('armrestL'), sa('napeoutR')), 0.2), (48.52, (sa('armrestL'), sa('scratchR')), 0.25),
                (52.2, (sa('armrestL'), sa('armrestR')), 0.5), (55.9, (sa('lapL'), sa('lapR')), 0.6)],
               lambda a, b, x: (lerp_arm(a[0], b[0], x), lerp_arm(a[1], b[1], x)))
S_blinks = blink_schedule(11, extra=(4.15, 17.8, 36.0, 43.45, 53.75))


def santi(t_real, cheat=None):
    t = U(t_real)   # pistas en tiempo de autor; el habla en tiempo real
    open_, rnd, wide = speech('SANTI', t_real)
    talk = open_ > 0.02
    hp, hy, hr = S_head(t)
    # micro-movimiento al hablar + respiración
    hp += 4.0 * open_ * (1 if talk else 0)
    hr += 1.5 * math.sin(t * 2.1)
    lean = S_lean(t) + 1.2 * math.sin(t * 2 * math.pi / 3.6)
    if 38.8 < t < 41.5:   # sonrisa nerviosa «Yo solito, jefe»
        lean += 1.5 * abs(math.sin(t * 11))
    armL, armR = S_arms(t)
    p = dict(pos=(0, 0, 0), yaw=S_yaw(t), lean=lean, twist=S_twist(t), side=S_side(t), head=(hp, hy, hr),
             gaze=S_gaze(t), lidU=S_lidU(t) + 6, lidL=S_lidL(t), blink=blink_val(S_blinks, t),
             brow=S_brow(t), browL=S_brow(t) + S_browL(t), browR=S_brow(t), worry=S_worry(t), angry=S_angry(t),
             sweat=S_sweat(t),
             mouth=dict(open=open_, round=rnd, wide=max(wide, S_wide(t)), smile=max(0.0, S_smile(t)),
                        frown=max(0.0, -S_smile(t))),
             arms={'L': armL[:3], 'R': armR[:3]}, arm_space={'L': armL[3], 'R': armR[3]})
    if cheat:
        p.update(cheat)
    return p


# ------------------------------------------------------------ CLAWD
LAP = (0.0, -0.265, 0.585)
UNDER = (0.0, -1.02, 0.0)
PEEK = (0.0, -0.6, 0.0)
SIDE_PEEK = (-0.8, -0.86, 0.0)
# blocking v3 (Santi, 21-10-2026): Clawd cambia de escondite con la historia, siempre a escondidas
DESK_Z = 0.752
D_KEY = (0.02, -1.02, DESK_Z)      # «Mañana capacitas…»: sobre el escritorio, asomado tras el teclado
D_MON = (-0.15, -1.08, DESK_Z)     # «Ya te hice la presentación… De mí»: junto a la pantalla, señalándola
D_EDGE = (0.6, -0.92, DESK_Z)      # orilla del escritorio junto al cubículo
CUB = (0.875, -0.36, 1.246)        # «¿Mi jefe tiene IA?»: en lo alto del cubículo, asomado hacia la puerta del jefe
D_MUG = (-0.15, -0.99, DESK_Z)     # Mariana: quieto junto a la taza de Santi
C_pos = K((0, UNDER), (0.85, UNDER), (1.25, PEEK, 'out'), (2.32, PEEK), (2.75, LAP, 'lin'), (10.95, LAP),
          (11.45, D_KEY, 'lin'), (21.55, D_KEY), (22.05, D_MON), (30.6, D_MON), (31.0, D_EDGE, 'lin'),
          (31.5, CUB, 'lin'), (35.8, CUB), (36.25, D_EDGE, 'lin'), (37.6, D_MUG), (45.62, D_MUG),
          (45.95, (-0.16, -0.62, 0.0), 'lin'), (46.45, UNDER, 'lin'), (48.0, UNDER), (48.6, (0.06, -0.66, 0.0)),
          (55.2, (0.06, -0.66, 0.0)), (55.7, (-0.2, -1.0, 0.0)), (56.05, SIDE_PEEK, 'lin'), (59, SIDE_PEEK))
C_hop = K((0, 0), (2.32, 0), (2.54, 0.26, 'out'), (2.75, 0, 'in'), (10.95, 0), (11.2, 0.3, 'out'), (11.45, 0, 'in'),
          (30.6, 0), (30.8, 0.1, 'out'), (31.0, 0, 'in'), (31.25, 0.28, 'out'), (31.5, 0, 'in'),
          (35.8, 0), (36.0, 0.12, 'out'), (36.25, 0, 'in'), (45.62, 0), (45.78, 0.16, 'out'), (45.95, 0, 'in'))
C_yaw = K((0, 180), (2.32, 180), (2.75, 172), (10.95, 172), (11.45, 180), (21.55, 180), (22.05, 160),
          (30.6, 160), (30.7, 120), (31.5, 204), (35.8, 204), (35.9, 250), (36.3, 270), (37.4, 270), (37.7, 158),
          (45.6, 158), (45.75, 180), (46.0, 20), (46.45, 0), (48.0, 0), (48.5, 165), (55.2, 165), (55.6, 90), (56.05, 30),
          (59, 30))
C_tilt = K((0, 0), (1.25, 0), (1.45, -22), (2.2, -22), (2.32, 8), (2.6, -10), (2.75, 6), (2.95, -20), (9.6, -20),
           (9.75, -8), (10.8, -8), (11.0, -20), (24.7, -20), (24.85, -6), (25.4, -6), (25.6, -20), (38.8, -22),
           (43.0, -20), (45.6, -20), (45.7, 10), (46.45, 0), (48.6, -18), (55.2, -18), (55.6, 0), (56.1, -10))
C_squashK = K((0, 0), (2.18, 0), (2.32, -0.32, 'out'), (2.42, 0.22), (2.72, 0.1), (2.78, -0.28), (2.95, 0.05),
              (3.1, 0), (9.62, 0), (9.78, 0.18, 'back'), (10.8, 0.14), (11.0, 0), (24.78, 0), (24.92, 0.22, 'back'),
              (25.5, 0.16), (25.7, 0), (37.6, 0), (37.9, -0.12), (45.45, -0.12), (45.6, -0.25), (45.7, 0.2), (45.95, -0.2), (46.1, 0), (56.0, 0),
              (56.2, 0.12), (56.5, 0))
C_arms = Blend([(0, ((0, 0), (0, 0)), 0.01), (1.3, ((25, 10), (25, 10)), 0.25), (2.2, ((-20, 0), (-20, 0)), 0.15),
                (2.75, ((35, 0), (35, 0)), 0.12), (3.0, ((5, 0), (5, 0)), 0.3),
                (4.3, ((5, 0), (5, 0)), 0.2), (7.0, ((5, 0), (30, 25)), 0.3), (8.3, ((5, 0), (5, 0)), 0.3),
                (9.7, ((55, 10), (55, 10)), 0.2), (10.9, ((10, 0), (10, 0)), 0.3),
                (11.8, ((10, 0), (45, 35)), 0.25), (12.6, ((40, 35), (10, 0)), 0.3), (13.4, ((10, 0), (10, 0)), 0.3),
                (15.2, ((10, 0), (10, 0)), 0.2), (16.3, ((50, 0), (50, 0)), 0.2), (16.8, ((10, 0), (10, 0)), 0.3),
                (20.4, ((10, 0), (60, 30)), 0.25), (21.3, ((10, 0), (10, 0)), 0.25),
                (22.1, ((10, 0), (80, 25)), 0.25), (23.0, ((10, 0), (10, 0)), 0.3),
                (24.85, ((20, 0), (95, 30)), 0.15), (25.6, ((10, 0), (10, 0)), 0.3),
                (28.0, ((10, 0), (10, 0)), 0.2), (29.0, ((10, 0), (70, 20)), 0.25), (30.4, ((10, 0), (10, 0)), 0.3),
                (39.0, ((0, 0), (0, 0)), 0.5), (41.0, ((20, 30), (20, 30)), 0.6), (43.0, ((0, 0), (0, 0)), 0.5),
                (45.6, ((80, 0), (80, 0)), 0.1), (46.0, ((-10, 0), (-10, 0)), 0.15), (48.6, ((20, 10), (20, 10)), 0.3),
                (56.1, ((10, 0), (10, 0)), 0.3), (57.0, ((70, 10), (10, 0)), 0.2), (57.3, ((95, 10), (10, 0)), 0.15),
                (57.6, ((70, 10), (10, 0)), 0.15), (57.9, ((95, 10), (10, 0)), 0.15), (58.2, ((70, 10), (10, 0)), 0.15)],
               lambda a, b, x: (tuple(Vector(a[0]).lerp(Vector(b[0]), x)), tuple(Vector(a[1]).lerp(Vector(b[1]), x))))
C_eyes = [(0, 'normal'), (4.25, 'calm'), (4.9, 'normal'), (7.6, 'happy'), (8.4, 'normal'), (9.65, 'calm'),
          (10.85, 'normal'), (11.7, 'determined'), (13.85, 'normal'), (15.15, 'calm'), (17.3, 'normal'),
          (20.4, 'determined'), (21.5, 'happy'), (23.2, 'normal'), (24.8, 'happy'), (25.65, 'normal'), (27.9, 'calm'),
          (30.4, 'normal'), (32.45, 'calm'), (35.5, 'normal'), (38.9, 'calm'), (40.4, 'happy'), (42.2, 'sad'),
          (43.4, 'happy'), (45.6, 'wide'), (46.6, 'normal'), (48.6, 'normal'), (52.3, 'suspicious'), (53.8, 'wide'),
          (55.9, 'happy')]
C_blinks = blink_schedule(23, extra=(4.0, 27.85))


def clawd_eyes(t):
    cur = C_eyes[0][1]
    for tt, e in C_eyes:
        if t >= tt:
            cur = e
    return cur


def clawd(t_real, cheat=None):
    t = U(t_real)   # pistas en tiempo de autor; el habla en tiempo real
    open_, _, _ = speech('CLAWD', t_real)
    pos = Vector(C_pos(t))
    pos.y += DRAWER(t) * C_inD(t)      # dentro del cajón se mueve con él
    pos.z += C_hop(t)
    # trote: fase según la distancia recorrida
    v = (Vector(C_pos(t + 0.05)) - Vector(C_pos(t - 0.05))).length / 0.1
    trot = min(1.0, v / 0.4)
    ph = t * 2 * math.pi * 4.2
    bob = 0.006 * abs(math.sin(ph)) * trot
    sq = C_squashK(t) + 0.20 * open_ + 0.015 * math.sin(t * 2 * math.pi / 2.8)
    tilt = C_tilt(t) - 6 * open_
    yaw = C_yaw(t)
    if talking('CLAWD', t_real):
        yaw += 5 * math.sin(t * 5.3)
    (aL, aR) = C_arms(t)
    aL = (aL[0] + 12 * open_, aL[1])
    aR = (aR[0] + 12 * open_, aR[1])
    tuck = max(0.0, min(1.0, C_hop(t) / 0.12))
    p = dict(pos=tuple(pos), yaw=yaw, tilt=tilt, squash=sq, bob=bob, armL=aL, armR=aR, legphase=ph,
             lean_side=16 if 41.9 < t < 43.4 else 0,   # asoma UN ojo en el duelo
             legamp=32 * trot, tuck=tuck, eyes=clawd_eyes(t), blink=blink_val(C_blinks, t), mouth=min(1.0, open_ * 1.6),
             gaze=C_gaze(t))
    if cheat:
        cheat = dict(cheat)
        for k in ('yaw', 'tilt'):   # dyaw/dtilt: desplazamiento sobre la animación (trucos de plano)
            if 'd' + k in cheat:
                p[k] += cheat.pop('d' + k)
        if 'dpos' in cheat:
            p['pos'] = tuple(Vector(p['pos']) + Vector(cheat.pop('dpos')))
        p.update(cheat)
    return p


# ------------------------------------------------------------ JEFE
B_OFFICE = (-1.08, 5.1, 0.0)
B_DOOR = (-0.85, 3.95, 0.0)
B_END = (-0.38, 1.0, 0.0)
B_pos = K((0, B_OFFICE), (45.3, B_OFFICE, 'step'), (45.35, B_DOOR, 'step'), (46.25, B_DOOR), (47.9, B_END, 'lin'),
          (59, B_END))
B_yaw = K((0, 8), (45.3, 8, 'step'), (45.35, 0, 'step'), (46.25, 0), (46.5, 12), (47.9, 22), (59, 22))
B_head = K((0, (14, 18, 0)), (32.4, (14, 18, 0)), (33.2, (10, 30, -2)), (35.0, (12, 22, 0)), (36.0, (14, 18, 0)),
           (45.3, (0, 0, 0), 'step'), (46.1, (-6, 0, 0)), (46.6, (4, 0, 0)), (47.4, (2, 6, 4)), (48.1, (6, 10, 0)),
           (50.0, (8, 6, -1)), (52.3, (6, 10, 0)), (52.6, (4, 24, -2)), (53.5, (4, 22, -2)), (53.85, (16, 6, 0)),
           (54.3, (14, 4, 0)), (54.6, (-14, 4, 0), 'out'), (55.8, (-12, 4, -4)), (59, (-10, 4, -4)))
B_lean = K((0, 8), (45.3, 8, 'step'), (45.35, 0, 'step'), (46.1, -2), (46.5, 6), (48.0, 2), (52.4, 4), (53.85, 8),
           (54.5, -9, 'out'), (59, -8))
B_lidU = K((0, 22), (32.5, 22), (33.2, 12), (35.0, 14), (36.0, 22), (45.3, 40, 'step'), (46.0, 52), (48.0, 34),
           (52.5, 20), (53.5, 16), (53.85, 26), (54.6, 6), (59, 8))
B_brow = K((0, 0.0), (45.3, 0.6, 'step'), (46.1, 1.2), (48.0, 0.8), (52.5, 0.2), (53.85, 0.0), (54.6, 0.9), (59, 0.8))
B_smile = K((0, 0.2), (45.3, 0.0, 'step'), (48.5, 0.0), (49.5, 0.1), (52.4, 0.2), (53.6, 0.3), (54.6, 0.8), (59, 0.8))
B_arms = Blend([(0, (((0.24, -0.08, 0.15), (1, 0.5, 0), (0, 0, 0)), ((-0.15, -0.3, 0.4), (-1, 0.3, -0.5), (0, 0, 0))), 0.01),
                (6.0, (((0.24, -0.08, 0.15), (1, 0.5, 0), (0, 0, 0)), ((-0.06, -0.24, 0.55), (-1, 0.3, -0.8), (0, 0, 0))), 0.5),
                (7.4, (((0.24, -0.08, 0.15), (1, 0.5, 0), (0, 0, 0)), ((-0.15, -0.3, 0.4), (-1, 0.3, -0.5), (0, 0, 0))), 0.5),
                (45.3, (((0.3, -0.05, 0.12), (1, 0.5, 0), (0, 0, 0)), ((-0.18, -0.3, 0.38), (-1, 0.3, -0.5), (0, 0, 0))), 0.01),
                (46.05, (((0.2, -0.42, 0.42), (1, 0.4, -0.2), (0, 0, 0)), ((-0.18, -0.3, 0.38), (-1, 0.3, -0.5), (0, 0, 0))), 0.2),
                (47.1, (((0.28, -0.32, 0.2), (1, 0.4, -0.2), (0, 0, 60)), ((-0.18, -0.3, 0.38), (-1, 0.3, -0.5), (0, 0, 0))), 0.3),
                (48.2, (((0.24, -0.08, 0.15), (1, 0.5, 0), (0, 0, 0)), ((-0.18, -0.3, 0.38), (-1, 0.3, -0.5), (0, 0, 0))), 0.4),
                (50.2, (((0.24, -0.08, 0.15), (1, 0.5, 0), (0, 0, 0)), ((-0.06, -0.24, 0.55), (-1, 0.3, -0.8), (0, 0, 0))), 0.4),
                (51.2, (((0.24, -0.08, 0.15), (1, 0.5, 0), (0, 0, 0)), ((-0.18, -0.3, 0.38), (-1, 0.3, -0.5), (0, 0, 0))), 0.4),
                (53.8, (((0.06, -0.24, 0.5), (1, 0.3, -0.6), (0, 0, -40)), ((-0.18, -0.3, 0.38), (-1, 0.3, -0.5), (0, 0, 0))), 0.25),
                (54.5, (((0.26, -0.05, 0.14), (1, 0.5, 0), (0, 0, 0)), ((-0.2, -0.3, 0.48), (-1, 0.3, -0.5), (0, 0, 0))), 0.35)],
               lambda a, b, x: tuple(tuple(tuple(Vector(a[k][j]).lerp(Vector(b[k][j]), x)) for j in range(3))
                                     for k in range(2)))
B_blinks = blink_schedule(37)


def boss(t_real, cheat=None):
    t = U(t_real)   # pistas en tiempo de autor; el habla en tiempo real
    open_, rnd, wide = speech('JEFE', t_real)
    pos = Vector(B_pos(t))
    v = (Vector(B_pos(t + 0.05)) - Vector(B_pos(t - 0.05))).length / 0.1
    walking = min(1.0, v / 0.5)
    ph = t * 2 * math.pi * 1.6
    hp, hy, hr = B_head(t)
    hp += 5 * open_
    armL, armR = B_arms(t)
    p = dict(pos=tuple(pos), yaw=B_yaw(t), walkphase=ph, walkamp=24 * walking, lean=B_lean(t),
             head=(hp, hy, hr), lidU=B_lidU(t), lidL=40, blink=blink_val(B_blinks, t), brow=B_brow(t), raised=-1,
             mouth=dict(open=open_, round=rnd, wide=wide, smile=B_smile(t)),
             gaze=B_gaze(t), angry=B_angry(t), sweat=1 if 41.6 < t < 43.6 else 0,
             arms={'L': armL, 'R': armR})
    if cheat:
        p.update(cheat)
    return p


# ------------------------------------------------------------ ChatGPT (en el hombro izquierdo del jefe)
G_LEAN = [(43.2, 45.4)]                       # le susurra al jefe «A mano… con Claude»
G_TO_CLAWD = [(45.5, 52.6), (56.9, 58.2)]     # pelea con Clawd (mira hacia el cajón)


def _in(ws, t):
    return any(a < t < b for a, b in ws)


def gpt(t_real, cheat=None):
    t = U(t_real)   # pistas en tiempo de autor; el habla en tiempo real
    open_, _, _ = speech('CHATGPT', t_real)
    lean_in = 1.0 if _in(G_LEAN, t) else 0.0
    duel = 41.68 < t < 43.28
    to_clawd = _in(G_TO_CLAWD, t)
    # sentado sobre el hombro izquierdo del jefe v3, sin tocar la cabeza (BVH)
    p = dict(pos=(0.33, -0.04, 0.595 - 0.006 * lean_in), yaw=-18 - 22 * lean_in + (14 if to_clawd else 0),
             roll=-6 + 12 * lean_in, pitch=6 if (to_clawd or duel) else 0, pulse=open_,
             spin=8 * math.sin(t * 6.0) * open_ + (6 * math.sin(t * 1.3)) * (0 if duel else 1),
             lidU=3 if duel else (8 if (lean_in or to_clawd) else 14),
             gaze=(-30, 0) if lean_in else ((8, -24) if (duel or to_clawd) else (0, -6)),
             blink=0.0 if duel else blink_val(G_blinks, t), mouth=open_, receipt=RECEIPT(t))
    if 57.1 < t < 58.4:
        p.update(lidU=6)
    if cheat:
        p.update(cheat)
    return p


G_blinks = blink_schedule(51)


# ------------------------------------------------------------ compañeros
def coworker(i, t_real):
    t = U(t_real)
    look = 0.0
    if t > 34.4:                                   # entra el jefe: todos voltean a ver
        look = min(1.0, (t - 34.4) / 0.4)
    yaw0 = (70, -70, 50, -55)[i]
    p = dict(yaw=yaw0 * look + 6 * math.sin(t * 0.7 + i), pitch=8 * (1 - look) + 3 * math.sin(t * 0.5 + i * 2),
             roll=2 * math.sin(t * 0.9 + i), blink=blink_val(CW_BL[i], t), gy=0, gp=-4 * (1 - look), mouth=0.0)
    if i == 0:   # Mariana: escucha a Gemini en su hombro y contesta
        m_, _, _ = speech('MARIANA', t_real)
        p['mouth'] = m_
        if t > 62.6:
            x = min(1.0, (t - 62.6) / 0.5)
            p['yaw'] = p['yaw'] * (1 - x) + 42 * x
            p['pitch'] = p['pitch'] * (1 - x) + 12 * x
            p['gy'] = 14 * x
    return p


CW_BL = [blink_schedule(60 + i) for i in range(4)]
AI_POP = [0.0, 69.15, 69.4, 69.65]   # Gemini (Mariana) siempre ahí; Beto, Lupe, Iván aparecen en el remate


def critter(i, t_real):
    t = U(t_real)
    t0 = AI_POP[i]
    if t < t0:
        return dict(hide=True)
    x = min(1.0, (t - t0) / 0.25)
    s = 1 + 0.25 * math.sin(x * math.pi) if x < 1 else 1.0
    p = dict(hide=False, bob=0.01 * math.sin((t - t0) * 6 + i) + (1 - x) * -0.05,
             roll=8 * math.sin((t - t0) * 4 + i), yaw=0, scale=s * (1.35 if i == 0 else 1.8))
    if i == 0:
        o, _, _ = speech('GEMINI', t_real)
        p.update(mouth=o, roll=4 * math.sin(t * 1.7), yaw=-8 if t > 62.6 else 0)
    return p


# ============================================================ PLAN DE PLANOS
# cada plano: inicio (s), nombre, cámara (objetivo, desplazamiento, lente, f/), movimiento, subtítulos, trucos
# objetivo: punto con nombre (ver scene.probe) o tupla; off: vector cámara-objetivo en mundo.
SHOTS = [
    dict(t=0.00, n='S01 general oficina', tgt=(0.0, -0.5, 0.58), pos=(-1.75, -0.2, 0.98), lens=26, f=4.0, push=0.88,
         focus='santi_head', sub='top'),
    dict(t=1.62, n='S02 bajo el escritorio', tgt=(0.0, -0.3, 0.82), pos=(0.3, -1.08, 0.36), lens=24, f=2.8,
         focus='clawd_eyes', drift=(0, 0.05, 0.02), sub='top'),
    dict(t=3.95, n='S03 Clawd POV', pos=(0.06, -0.80, 0.50), tgt=(0.0, -0.33, 0.74), lens=24, f=3.2, focus='clawd_eyes', push=0.92,
         cheat_clawd=dict(dyaw=180, dtilt=14, dpos=(0, -0.07, 0.03)), sub='top'),
    dict(t=4.88, n='S04 Santi uf', tgt='santi_face', pos=(0.06, -0.95, 0.82), lens=36, f=2.2, push=0.94, sub='low'),
    dict(t=6.62, n='S05 perfil dos', tgt=(0.0, -0.2, 0.86), pos=(-1.05, -0.32, 0.95), lens=36, f=3.5,
         focus='clawd_eyes', sub='top'),
    dict(t=8.48, n='S06 Santi ah si', tgt='santi_face', pos=(-0.14, -0.95, 0.83), lens=38, f=2.2, push=0.93,
         sub='low'),
    dict(t=9.62, n='S07 Clawd contrapicado', pos=(0.1, -0.80, 0.46), tgt=(0.0, -0.33, 0.76), lens=22, f=2.0,
         push=0.85, focus='clawd_eyes', cheat_clawd=dict(dyaw=180, dtilt=14, dpos=(0, -0.07, 0.03)), sub='low'),
    dict(t=10.85, n='S08 Santi que', tgt='santi_face', pos=(0.04, -0.9, 0.84), lens=40, f=2.0, shake=(10.92, 0.9),
         sub='low'),
    dict(t=11.65, n='S09 Clawd capacitas', tgt='clawd_eyes', pos=(0.3, 0.02, 1.12), lens=45, f=2.8, push=0.95,
         focus='clawd_eyes', sub='top'),
    dict(t=13.86, n='S10 Santi en que', tgt='santi_face', pos=(-0.1, -0.95, 0.82), lens=34, f=2.2, shake=(14.0, 0.5),
         push=0.9, sub='low'),
    dict(t=15.08, n='S11 frontal sobre el escritorio', tgt=(0.0, -0.28, 0.9), pos=(-0.42, -1.52, 1.3), lens=32,
         f=3.5, focus='santi_face', push=0.93, sub='top'),
    dict(t=17.45, n='S12 Santi cuanto tiempo', tgt='santi_face', pos=(0.12, -0.97, 0.82), lens=38, f=2.2, push=0.82,
         sub='low'),
    dict(t=20.3, n='S13 Clawd cuatro minutos', tgt='clawd_eyes', pos=(0.2, -0.42, 0.98), lens=40, f=2.5,
         push=0.94, sub='top'),
    dict(t=21.48, n='S14 inserto presentación', tgt='monitor', pos=(0.02, -0.62, 1.12), lens=38, f=4.0, push=0.82,
         sub='low'),
    dict(t=23.2, n='S15 Santi de que trata', tgt='santi_face', pos=(0.2, -0.95, 0.83), lens=38, f=2.2, push=0.95,
         sub='low'),
    dict(t=24.78, n='S16 Clawd de mi', tgt=(0.07, -1.12, 0.95), pos=(0.3, -0.48, 1.06), lens=26, f=3.2,
         focus='clawd_eyes', push=0.88, shake=(24.9, 0.35), sub='low'),
    dict(t=25.62, n='S17 Santi y si me preguntan', tgt='santi_chest', pos=(-0.4, -1.12, 0.99), lens=34, f=2.8,
         focus='santi_face', push=0.92, sub='top'),
    dict(t=27.88, n='S18 Clawd IA de tu jefe', tgt='clawd_eyes', pos=(-0.32, -0.5, 0.98), lens=40, f=2.5, push=0.93,
         sub='top'),
    dict(t=30.42, n='S19 Santi mi jefe tiene IA', tgt='santi_face', pos=(-0.6, -0.62, 1.04), lens=40, f=2.0,
         shake=(30.6, 0.8), sub='low'),
    dict(t=32.4, n='S20a Clawd en el cubiculo', tgt='clawd_eyes', pos=(0.5, 0.5, 1.32), lens=45, f=2.8, push=0.93,
         sub='low'),
    dict(t=33.35, n='S20 despacho del jefe', tgt='boss_gpt', pos=(-0.98, 2.3, 1.32), lens=45, f=4.5, push=0.72,
         sub='low'),
    dict(t=35.75, n='S21 Santi algo yo solo', tgt='santi_face', pos=(-0.08, -0.97, 0.81), lens=38, f=2.0, push=0.88,
         sub='low'),
    dict(t=38.8, n='S22 Clawd una cosa', tgt='clawd_eyes', pos=(0.02, -0.5, 0.97), lens=45, f=2.4, push=0.96,
         sub='top'),
    dict(t=41.25, n='S23 perfil quieto', tgt=(0.0, -0.2, 0.9), pos=(-0.9, -0.42, 0.98), lens=45, f=2.8,
         focus='santi_face', push=0.97, sub='top'),
    dict(t=43.38, n='S24 Santi tierno', tgt='santi_face', pos=(0.2, -0.96, 0.83), lens=40, f=2.0, push=0.94,
         sub='low'),
    dict(t=45.5, n='S25 susto', tgt=(0.0, -0.3, 0.8), pos=(-1.45, -0.85, 1.12), lens=28, f=4.0, shake=(45.65, 0.7),
         focus='santi_head', sub='top'),
    dict(t=46.2, n='S26 jefe contrapicado', tgt='boss_head', pos=(-0.15, 0.25, 0.62), lens=24, f=3.5, track=True,
         sub='low'),
    dict(t=48.25, n='S27 risa nerviosa', tgt='santi_face', pos=(-0.05, 1.62, 1.32), lens=42, f=2.8, push=0.92,
         sub='top'),
    dict(t=52.2, n='S28 GPT susurra', tgt='gpt', off=(0.55, -0.95, 0.06), lens=50, f=3.2, push=0.93,
         sub='low'),
    dict(t=53.72, n='S29 jefe yo tambien', tgt='boss_gpt', off=(1.05, -0.75, -0.12), lens=30, f=4.0, push=0.95,
         sub='low'),
    dict(t=55.85, n='S30 IAs izquierda', tgt=(-1.7, 0.9, 0.62), pos=(-0.35, -0.95, 1.25), lens=24, f=5.6,
         push=0.93, sub='top', probe_frac=[0.75]),
    dict(t=57.15, n='S31 IAs derecha y general', tgt=(1.9, 0.5, 0.85), off=(-0.55, -1.75, 0.45), lens=24, f=5.6,
         end_off=(-2.3, -5.0, 1.3), end_lens=18, sub='top', ease_dur=1.85, probe_frac=[0.3, 0.97]),
]
for i, s in enumerate(SHOTS):
    s['end'] = SHOTS[i + 1]['t'] if i + 1 < len(SHOTS) else T_END


# ============================================================ GUION v3 (70 s): re-tiempo + final nuevo
def _rt(tr, new=(), old=True):
    ks = [(W(k[0]),) + tuple(k[1:]) for k in tr.keys if keep_old(k[0])] if old else []
    tr.keys = sorted(ks + list(new), key=lambda k: k[0])
    return tr


def _rtb(bl, new=(), old=True):
    ks = [(W(k[0]),) + tuple(k[1:]) for k in bl.keys if keep_old(k[0])] if old else []
    bl.keys = sorted(ks + list(new), key=lambda k: k[0])
    return bl


# ---- cajón del escritorio de Santi (Clawd se esconde ahí cuando entra el jefe)
DRAWER = K((0, 0.0), (33.82, 0.0), (33.9, 0.18, 'out'), (34.32, 0.18), (34.5, 0.02, 'out'),   # abre, cae Clawd, cierra
           (41.85, 0.02), (41.95, 0.1, 'out'),                                                  # rendija: asoma un ojo
           (58.3, 0.1), (58.5, 0.02, 'in'), (68.9, 0.02), (69.2, 0.1, 'out'), (71, 0.1))       # se esconde; remate
PAW = K((0, 0.0), (34.45, 0.0, 'step'), (34.5, 1.0, 'step'), (45.5, 1.0, 'step'), (45.55, 0.0, 'step'), (71, 0.0))
# recibo de ChatGPT (metros desenrollados)
RECEIPT = K((0, 0.0), (49.9, 0.0, 'step'), (50.0, 0.02), (52.46, 0.38, 'lin'), (57.12, 0.38), (57.55, 1.05, 'in'),
            (57.6, 1.02), (57.7, 1.05), (71, 1.05))
DR_IN = (-0.38, -0.71, 0.545)      # dentro del cajón (coordenadas con el cajón cerrado)
DR_PEEK = (-0.38, -0.67, 0.64)     # asoma un ojo por la rendija
DR_TALK = (-0.38, -0.67, 0.66)     # asoma ojos y boca
C_inD = K((0, 0.0), (33.95, 0.0, 'step'), (33.96, 1.0, 'step'), (71, 1.0))

_rt(C_pos, [(24.6, D_MON), (26.0, D_MUG), (33.85, D_MUG), (33.95, (-0.3, -0.7, 0.8), 'lin'),
            (33.96, (-0.3, -0.88, 0.8), 'step'), (34.2, DR_IN, 'in'), (34.5, DR_IN), (41.85, DR_IN), (42.0, DR_PEEK, 'out'),
            (45.4, DR_PEEK), (45.55, DR_TALK, 'out'), (58.2, DR_TALK), (58.45, DR_IN, 'in'), (68.95, DR_IN),
            (69.3, DR_TALK, 'out'), (71, DR_TALK)])
C_pos.keys = [k for k in C_pos.keys if not (W(22.05) + 0.01 < k[0] < 24.6)]
_rt(C_hop, [(33.85, 0), (34.0, 0.14, 'out'), (34.15, 0, 'in')])
C_hop.keys = [k for k in C_hop.keys if k[0] < 12 or k[0] >= 33.85]
_rt(C_yaw, [(24.6, 160), (25.0, 175), (26.0, 158), (33.85, 158), (33.95, 180), (34.5, 172), (52.88, 172),
            (54.2, 132), (58.2, 132), (58.45, 172), (71, 172)])
C_yaw.keys = [k for k in C_yaw.keys if not (W(22.05) + 0.01 < k[0] < 24.6)]
_rt(C_tilt, [(33.85, -20), (33.95, 10), (34.5, 0), (42.0, -6), (45.55, -12), (52.88, -12), (54.2, -16), (71, -10)])
_rt(C_squashK, [(33.8, -0.25), (33.9, 0.2), (34.1, -0.2), (34.3, 0), (52.88, 0), (53.4, -0.08), (57.12, -0.1),
                (57.3, -0.22, 'out'), (57.8, -0.08), (69.2, 0.12), (69.5, 0)])
_rtb(C_arms, [(33.85, ((80, 0), (80, 0)), 0.1), (34.2, ((-10, 0), (-10, 0)), 0.15), (45.6, ((10, 0), (10, 0)), 0.3),
              (46.6, ((10, 0), (60, 30)), 0.25), (47.6, ((10, 0), (10, 0)), 0.3), (69.4, ((70, 10), (10, 0)), 0.2),
              (69.8, ((95, 10), (10, 0)), 0.15), (70.2, ((70, 10), (10, 0)), 0.15)])
C_eyes[:] = [(W(t), e) for t, e in C_eyes if keep_old(t)] + [
    (33.85, 'wide'), (34.6, 'normal'), (41.9, 'normal'), (43.3, 'suspicious'), (45.5, 'determined'), (48.66, 'suspicious'),
    (52.88, 'sad'), (55.42, 'sad'), (57.12, 'wide'), (57.9, 'sad'), (69.2, 'happy')]
C_eyes.sort(key=lambda e: e[0])
C_blinks[:] = sorted([W(b) for b in C_blinks if keep_old(b)] + [b for b in C_blinks if b > 33.9 and not 41.6 < b < 43.4])
C_gaze = K((0, (0.0, 0.6)), (33.85, (0.0, 0.6)), (33.9, (0.0, 0.0)), (41.9, (-0.6, 0.3)), (45.5, (-0.3, 0.5)),
           (52.88, (-0.3, 0.5)), (54.2, (0.4, 0.4)), (71, (0.4, 0.4)))

# ---- Santi
_rt(S_lean, [(33.95, 4, 'out'), (34.6, 6), (38.7, 4), (41.6, 6), (45.5, 10), (48.5, 6), (52.9, 12), (55.4, 16),
             (57.2, 8), (58.6, 10), (60.4, 12), (62.0, 8)])
_rt(S_twist, [(33.82, 0), (33.95, -10), (35.0, 0)])
S_yaw.keys = [(0, 0), (34.4, 0), (35.0, -165, 'back'), (71, -165)]
_rt(S_head, [(33.95, (0, 0, 0), 'out'), (34.6, (0, -20, 0)), (35.3, (-8, 0, 0)), (38.7, (-6, 0, 6)), (39.6, (-4, 0, 3)),
             (40.6, (-6, 0, 6)), (41.95, (-8, 0, 0)), (43.4, (-6, -10, 0)), (45.6, (6, 40, 0)), (48.5, (4, 30, 0)),
             (48.8, (-6, 0, 0)), (52.9, (6, 35, 0)), (55.4, (22, 10, 0)), (57.1, (14, 0, -6)), (58.6, (0, -8, 6)),
             (60.4, (8, -6, 4)), (61.0, (-2, -6, 4)), (61.5, (8, -6, 4)), (62.2, (0, 0, 0))])
_rt(S_gaze, [(33.95, (-14, 0)), (35.3, (0, 6)), (41.7, (14, -2)), (42.5, (-10, -10)), (43.3, (0, 6)),
             (45.6, (30, -10)), (48.8, (0, 6)), (52.9, (30, -10)), (55.4, (-20, -12)), (57.1, (0, 6)), (58.7, (-14, 4)),
             (60.4, (0, 4))])
_rt(S_lidU, [(33.9, 60, 'out'), (35.0, 46), (38.7, 30), (41.7, 40), (42.5, 22), (43.3, 56), (45.6, 44), (52.9, 34),
             (55.4, 22), (57.1, 10), (57.9, 40), (58.6, 34), (60.4, 26), (62.0, 32)])
_rt(S_lidL, [(33.9, 40), (35.0, 30), (38.7, 16), (41.7, 22), (55.4, 30)])
_rt(S_brow, [(33.9, 1.2), (35.0, 0.6), (38.7, 0.7), (41.7, 0.3), (43.3, 1.2), (45.6, 0.8), (52.9, 0.9), (55.4, 0.6),
             (57.1, 1.1), (58.6, 0.4), (60.4, 0.2)])
_rt(S_browL)
_rt(S_worry, [(33.9, 0.8), (38.7, 0.9), (41.7, 1.0), (43.3, 1.0), (52.9, 0.9), (55.4, 1.0), (57.2, 1.0), (58.6, 0.6),
              (60.4, 0.4)])
_rt(S_angry)
_rt(S_smile, [(33.9, 0.0), (38.6, 0.0), (38.8, 0.9), (41.6, 0.7), (43.3, 0.0), (55.4, -0.3), (58.6, 0.0), (60.4, 0.3),
              (62.0, 0.5)])
_rt(S_wide, [(38.6, 0.0), (38.7, 0.55), (41.5, 0.4), (43.3, 0.6), (44.0, 0.2), (57.1, 0.4), (57.6, 0.0)])
_rt(S_sweat, [(33.9, 0, 'step'), (34.0, 1, 'step'), (62.0, 1, 'step'), (62.1, 0, 'step')])
_rt(S_side)
_rtb(S_arms, [(33.95, (sa('upL'), sa('upR')), 0.15), (35.0, (sa('armrestL'), sa('armrestR')), 0.4),
              (38.6, (sa('armrestL'), sa('napeoutR')), 0.2), (38.82, (sa('armrestL'), sa('scratchR')), 0.25),
              (41.45, (sa('armrestL'), sa('napeoutR')), 0.15), (41.72, (sa('armrestL'), sa('armrestR')), 0.35), (55.2, (sa('lapL'), sa('napeoutR')), 0.3), (55.55, (sa('lapL'), sa('neckR')), 0.35),
              (56.75, (sa('lapL'), sa('napeoutR')), 0.25), (57.05, (sa('lapL'), sa('lapR')), 0.4), (58.6, (sa('armrestL'), sa('armrestR')), 0.5)])
S_blinks[:] = sorted([W(b) for b in S_blinks if keep_old(b)] + [b for b in S_blinks if b > 34.0 and not 41.6 < b < 43.4])

# ---- jefe v3
B_pos = K((0, B_OFFICE), (33.8, B_OFFICE, 'step'), (33.85, B_DOOR, 'step'), (34.4, B_DOOR), (36.0, B_END, 'lin'),
          (71, B_END))
B_yaw = K((0, 8), (33.8, 8, 'step'), (33.85, 0, 'step'), (34.4, 0), (34.6, 12), (36.0, 22), (58.4, 22), (58.8, 30),
          (60.3, 30), (60.6, 22))
B_head = K((0, (14, 18, 0)), (33.8, (14, 18, 0)), (33.85, (0, 0, 0), 'step'), (34.4, (-6, 0, 0)), (35.3, (4, 0, 0)),
           (36.5, (6, 6, 0)), (38.5, (8, 4, -1)), (41.7, (10, 0, 0)), (43.3, (4, 22, -2)), (45.4, (6, 0, 0)),
           (48.7, (4, 8, 0)), (52.5, (10, 0, 0)), (57.1, (6, 10, 0)), (58.6, (16, -8, 0)), (60.3, (10, -4, 0)),
           (62.0, (6, 0, 0)))
B_lean = K((0, 8), (33.8, 8, 'step'), (33.85, 0, 'step'), (34.4, -2), (34.8, 6), (36.2, 4), (58.4, 4), (58.7, 16),
           (60.3, 14), (61.0, 4))
B_lidU = K((0, 22), (33.85, 30, 'step'), (36.0, 22), (41.7, 10), (43.3, 18), (45.4, 22), (48.7, 30), (52.5, 20),
           (57.1, 32), (58.6, 14), (61, 20))
B_brow = K((0, 0.0), (33.85, 0.2, 'step'), (41.7, -0.4), (43.3, 0.2), (48.7, 0.9), (52.5, 0.2), (57.1, 1.0),
           (58.6, -0.2))
B_angry = K((0, 0.6), (48.7, 0.2), (52.5, 0.6), (57.1, 0.0), (58.6, 0.5))
B_smile = K((0, 0.0), (52.5, 0.0), (53.5, 0.25), (57.3, 0.45), (58.6, 0.1), (60.4, 0.4))
B_gaze = K((0, (0, -4)), (33.85, (0, 0), 'step'), (36.0, (-6, 0)), (43.2, (-25, 0)), (45.4, (-6, -6)), (48.6, (-6, 0)),
           (71, (-6, 0)))
_BREST = (((0.3, -0.05, 0.15), (1, 0.5, 0), (0, 0, 0)), ((-0.17, -0.34, 0.42), (-1, 0.3, -0.5), (0, 0, 0)))
_BWHI = (((0.3, -0.05, 0.15), (1, 0.5, 0), (0, 0, 0)), ((-0.07, -0.32, 0.64), (-1, 0.3, -0.6), (0, 0, 40)))   # tapa el susurro con la mano de la taza
_BPOINT = (((0.3, -0.05, 0.15), (1, 0.5, 0), (0, 0, 0)), ((-0.2, -0.45, 0.48), (-1, 0.3, -0.5), (0, 0, 0)))
B_arms.keys = [(0, _BREST, 0.01), (34.5, _BPOINT, 0.3), (36.5, _BREST, 0.4), (58.45, _BWHI, 0.25),
               (60.4, _BREST, 0.35)]
B_blinks[:] = [b for b in B_blinks if not 41.6 < b < 43.4]
G_blinks[:] = [b for b in G_blinks if not 41.6 < b < 43.4]

# ---- planos: la primera parte se re-amarra; el final es nuevo
_OLD_SHOTS = [s for s in SHOTS if s['n'].split(' ')[0] in ('S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08',
                                                         'S09', 'S10', 'S11', 'S12', 'S13', 'S14', 'S15', 'S16',
                                                         'S21', 'S22', 'S23', 'S24', 'S25')]
for s in _OLD_SHOTS:
    s['t'] = round(W(s['t']), 3)
    if 'shake' in s:
        s['shake'] = (round(W(s['shake'][0]), 3), s['shake'][1])
    s.pop('end', None)
_REN = {'S21': 'S17', 'S22': 'S18', 'S23': 'S19', 'S24': 'S20', 'S25': 'S21'}
for s in _OLD_SHOTS:
    k = s['n'].split(' ')[0]
    if k in _REN:
        s['n'] = _REN[k] + s['n'][3:]
WEST = dict(western=True, sub='low')
SHOTS = _OLD_SHOTS + [
    dict(t=34.4, n='S22 jefe entra', tgt='boss_head', pos=(-0.15, 0.25, 0.62), lens=24, f=3.5, track=True, sub='low'),
    dict(t=36.3, n='S23 jefe cuatro meses', tgt='boss_head', off=(0.62, -0.95, -0.2), lens=40, f=2.8, push=0.92,
         sub='low'),
    dict(t=38.6, n='S24 Santi yo solito', tgt='santi_face', pos=(0.45, 1.3, 1.25), lens=42, f=2.8, push=0.92,
         sub='top'),
    # ---- duelo de miradas (viejo oeste): cortes de 0.2-0.4 s, closes extremos, crash zoom, dutch, letterbox y tinte
    # duelo SOLO de las IAs (Santi, v3b): ChatGPT <-> Clawd alternados, cada vez más cerca, y al final frente a frente
    dict(t=41.68, n='S25a duelo ojos GPT', tgt='gpt', off=(0.02, -0.44, 0.0), lens=55, push=0.8, f=9.0, dutch=8,
         **WEST),
    dict(t=41.96, n='S25b duelo ojo Clawd', tgt='clawd_eyeL', off=(0.07, 0.3, 0.05), lens=45, push=0.9, f=9.0,
         dutch=-9, **WEST),
    dict(t=42.22, n='S25c duelo patita', tgt=(-0.31, -0.5, 0.66), pos=(-0.66, -0.26, 0.76), lens=42, f=8.0, dutch=6,
         **WEST),
    dict(t=42.46, n='S25d duelo ojos GPT cerca', tgt='gpt', off=(0.0, -0.34, 0.01), lens=70, push=0.8, f=14.0,
         dutch=-10, **WEST),
    dict(t=42.72, n='S25e duelo ojo Clawd cerca', tgt='clawd_eyeL', off=(0.04, 0.2, 0.03), lens=60, push=0.85,
         f=12.0, dutch=10, **WEST),
    dict(t=42.98, n='S25f duelo IAs frente a frente', tgt='gpt', pos=(-0.62, -0.88, 0.76), lens=45, f=11.0,
         focus='gpt', **WEST),
    dict(t=43.28, n='S26 GPT susurra', tgt='gpt', off=(0.55, -0.95, 0.06), lens=50, f=3.2, push=0.93, sub='low'),
    dict(t=45.45, n='S27 Clawd del cajón', tgt='clawd_eyes', pos=(-0.2, -0.2, 0.93), lens=38, f=2.8, push=0.94,
         sub='top'),
    dict(t=48.55, n='S28 GPT copia', tgt='gpt', off=(-0.3, -0.78, -0.02), lens=50, f=3.0, push=0.93, sub='low'),
    dict(t=50.7, n='S29 recibo sale', tgt='boss_gpt', off=(0.85, -1.15, -0.3), lens=32, f=4.0, push=0.95, sub='low'),
    dict(t=52.75, n='S30 Clawd le escribiste', tgt='clawd_eyes', pos=(0.3, -0.36, 0.86), lens=42, f=2.8,
         push=0.95, sub='top'),
    dict(t=55.3, n='S31 Santi fue una vez', tgt='santi_face', pos=(0.32, 0.78, 0.9), lens=30, f=2.2, push=0.95,
         sub='low'),
    dict(t=56.95, n='S32 GPT cuarenta y siete', tgt='gpt', off=(0.4, -0.6, 0.05), lens=45, f=3.2, sub='low'),
    dict(t=57.55, n='S33 recibo total', tgt='receipt_end', off=(0.1, -0.3, 0.12), lens=50, f=5.6, sub='top'),
    dict(t=58.4, n='S34 jefe nadie vio nada', tgt=(-0.18, 0.5, 1.2), pos=(1.15, 0.45, 1.25), lens=32, f=3.2,
         focus='boss_head', push=0.95, sub='low'),
    dict(t=60.3, n='S35 Santi nadie vio nada', tgt='santi_face', pos=(0.3, 0.85, 1.18), lens=45, f=2.2, push=0.94,
         sub='low'),
    dict(t=62.1, n='S36 Mariana al fondo', tgt=(-1.6, 0.3, 1.0), pos=(0.75, -1.45, 1.42), lens=34, f=4.0,
         focus='gemini', push=0.9, sub='top'),
    dict(t=64.4, n='S37 Mariana y Gemini', tgt='gemini_mariana', pos=(-1.12, -0.52, 1.16), lens=34, f=2.4, push=0.95,
         sub='top'),
    dict(t=67.9, n='S38 Mariana ya te perdone', tgt='mariana_face', pos=(-1.45, -0.42, 1.12), lens=55, f=2.2,
         sub='top'),
    dict(t=69.05, n='S39 remate', tgt=(-0.1, 0.9, 0.7), off=(-0.5, -1.6, 0.55), lens=32, f=6.0,
         end_off=(-0.3, -4.2, 1.5), end_lens=18, sub='top', ease_dur=1.7, probe_frac=[0.3, 0.97]),
]
for i, s in enumerate(SHOTS):
    s['end'] = SHOTS[i + 1]['t'] if i + 1 < len(SHOTS) else T_END

# ---- planos a tiempo real del guion vigente (v3b)
for s in SHOTS:
    s['t'] = round(V(s['t']), 3)
    if 'shake' in s:
        s['shake'] = (round(V(s['shake'][0]), 3), s['shake'][1])
for i, s in enumerate(SHOTS):
    s['end'] = SHOTS[i + 1]['t'] if i + 1 < len(SHOTS) else T_END

