# project.py — carga un proyecto de sketch, resuelve referencias de tiempo y calcula el lip-sync.
# Sin dependencias de Blender: lo usan scene.py (dentro de Blender) y los scripts (mix, subs, auto_shots).
import json, math, os, random, re, unicodedata

FPS = 24


def jload(path, default=None):
    if not os.path.exists(path):
        if default is not None:
            return default
        raise FileNotFoundError(path)
    with open(path) as fh:
        return json.load(fh)


def norm(s):
    """minúsculas, sin acentos ni signos: para buscar palabras en referencias de tiempo"""
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9ñ]+', '', s)


def clean_tags(s):
    s = re.sub(r'\[[^\]]*\]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


_REF = re.compile(r'^\s*(?:(?P<fin>fin|inicio)|L(?P<i>\d+)(?::(?P<w>[^.#+\-\s]+)(?:#(?P<n>\d+))?)?'
                  r'(?P<edge>\.end|\.mid|\.start)?)\s*(?P<off>[+-]\s*\d+(?:\.\d+)?)?\s*$', re.I)


class Project:
    """dir/ guion.json cast.json blocking.json shots.json look.json  +  build/timeline.json  +  audio/palabras.json"""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        p = lambda *a: os.path.join(self.root, *a)
        self.path = p
        self.guion = jload(p('guion.json'))
        self.cast = {k: v for k, v in jload(p('cast.json'))['personajes'].items() if not k.startswith('_')}
        self.blocking = jload(p('blocking.json'), {})
        self.shots_spec = [s for s in jload(p('shots.json'), []) if isinstance(s, dict) and not s.get('_nota')]
        self.look = jload(p('look.json'), {})
        self.sfx = jload(p('sfx.json'), [])
        tl = jload(p('build', 'timeline.json'), {})
        self.timeline = tl
        self.fps = tl.get('fps', FPS)
        self.lines = tl.get('lineas', [])
        self.rms = tl.get('rms', [])
        self.t_end = float(tl.get('t_end', tl.get('duracion', 1.0) + 1.0))
        self.n_frames = int(round(self.t_end * self.fps))
        self.words = jload(p('audio', 'palabras.json'), [])
        # palabras por línea (AssemblyAI sobre el diálogo completo, en ms)
        self.line_words = []
        for ln in self.lines:
            ws = [w for w in self.words if ln['start'] - 0.25 <= w['start'] / 1000 <= ln['end'] + 0.1]
            self.line_words.append(ws)
        self.speech = Speech(self)

    # ------------------------------------------------------------ tiempo
    def T(self, ref):
        """número | 'inicio' | 'fin' | 'L3' | 'L3.end' | 'L3.mid' | 'L3:palabra' | 'L3:palabra#2.end' | ... ±seg"""
        if isinstance(ref, (int, float)):
            return float(ref)
        m = _REF.match(str(ref))
        if not m:
            try:
                return float(ref)
            except ValueError:
                raise ValueError(f'referencia de tiempo inválida: {ref!r}')
        off = float(m.group('off').replace(' ', '')) if m.group('off') else 0.0
        if m.group('fin'):
            return (self.t_end if m.group('fin').lower() == 'fin' else 0.0) + off
        i = int(m.group('i'))
        if not 1 <= i <= len(self.lines):
            raise ValueError(f'{ref!r}: la línea {i} no existe (hay {len(self.lines)})')
        ln = self.lines[i - 1]
        a, b = ln['start'], ln['end']
        if m.group('w'):
            key = norm(m.group('w'))
            nth = int(m.group('n') or 1)
            hits = [w for w in self.line_words[i - 1] if norm(w['text']).startswith(key)]
            if len(hits) >= nth:
                a, b = hits[nth - 1]['start'] / 1000, hits[nth - 1]['end'] / 1000
            else:
                # sin palabras de AssemblyAI: interpola por caracteres en el texto limpio
                txt = clean_tags(ln['text'])
                toks = txt.split(' ')
                idx = [k for k, tk in enumerate(toks) if norm(tk).startswith(key)]
                if len(idx) < nth:
                    raise ValueError(f'{ref!r}: no encuentro «{m.group("w")}» en la línea {i}: {txt}')
                k = idx[nth - 1]
                tot = sum(len(t) + 1 for t in toks)
                pre = sum(len(t) + 1 for t in toks[:k])
                a = ln['start'] + (ln['end'] - ln['start']) * pre / tot
                b = ln['start'] + (ln['end'] - ln['start']) * (pre + len(toks[k])) / tot
        edge = (m.group('edge') or '.start').lower()
        t = b if edge == '.end' else (a + b) / 2 if edge == '.mid' else a
        return t + off

    def who_speaks(self, t, pad=0.12):
        for ln in self.lines:
            if ln['start'] - pad <= t <= ln['end'] + pad:
                return ln['who']
        return None

    def line_at(self, t):
        """índice (0-based) de la última línea que empezó antes de t"""
        k = -1
        for i, ln in enumerate(self.lines):
            if ln['start'] <= t:
                k = i
        return k


# ================================================================ lip-sync genérico
class Speech:
    """abertura/redondez/ancho de la boca a partir de la envolvente RMS del diálogo + vocales de las palabras.
    o/u redondean, i ensancha, m/b/p cierran, f/v casi cierran. Los susurros abren menos."""

    def __init__(self, prj):
        self.prj = prj
        self.fps = prj.fps
        rms = prj.rms or [0.0]
        self.rms = [sum(rms[max(0, i - 1):i + 2]) / len(rms[max(0, i - 1):i + 2]) for i in range(len(rms))]
        self.norm = []
        for ln in prj.lines:
            f0, f1 = int(ln['start'] * self.fps), int(ln['end'] * self.fps) + 1
            seg = sorted(self.rms[f0:min(f1, len(self.rms))]) or [0.1]
            p90 = seg[int(len(seg) * 0.9) - 1] if len(seg) > 2 else seg[-1]
            self.norm.append(max(0.04, p90))
        self.gain = {k: float(v.get('boca_ganancia', 1.0)) for k, v in prj.cast.items()}

    def _word_at(self, i, t):
        for w in self.prj.line_words[i]:
            if w['start'] / 1000 - 0.02 <= t <= w['end'] / 1000 + 0.02:
                return w
        return None

    def mouth(self, who, t):
        f = int(t * self.fps)
        for i, ln in enumerate(self.prj.lines):
            if ln['who'] != who or not (ln['start'] - 0.03 <= t <= ln['end'] + 0.05):
                continue
            r = self.rms[min(f, len(self.rms) - 1)] if self.rms else 0.0
            o = max(0.0, min(1.0, (r - 0.012) / (self.norm[i] - 0.012)))
            o = o ** 0.75 * self.gain.get(who, 1.0)
            if 'whisper' in ln['text'].lower() or 'susurr' in ln['text'].lower():
                o *= 0.75
            rnd = wide = 0.0
            w = self._word_at(i, t)
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
                    elif c in 'fv':
                        o *= 0.5
            return min(1.0, o), rnd * min(1.0, o + 0.3), wide * o
        return 0.0, 0.0, 0.0

    def talking(self, who, t, pad=0.0):
        return any(ln['who'] == who and ln['start'] - pad <= t <= ln['end'] + pad for ln in self.prj.lines)


# ================================================================ parpadeo
def blink_schedule(seed, t_end, extra=()):
    rnd = random.Random(seed)
    ts, t = [], rnd.uniform(0.5, 2.0)
    while t < t_end:
        ts.append(t)
        t += rnd.uniform(2.2, 4.6)
    return sorted(ts + list(extra))


def blink_val(sched, t, dur=0.13):
    for b in sched:
        if b <= t <= b + dur:
            x = (t - b) / dur
            return 1.0 if x < 0.6 else 1.0 - (x - 0.6) / 0.4
    return 0.0


def seed_of(name):
    return sum((i + 1) * ord(c) for i, c in enumerate(name)) % 9973


def resolved_shots(prj):
    """metadatos de planos a tiempo real (n, t, end, sub) para subtítulos y mezcla; los escribe scene.py"""
    return jload(prj.path('build', 'shots_resolved.json'), [])
