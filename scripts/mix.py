# mix.py — diálogo + tono de sala sintetizado (según el set) + SFX (banco EditorBrain o sintetizados) -> −14 LUFS.
#   python3 mix.py <proyecto>  -> audio/mezcla.wav (TP ≤ −1.5 dBTP) + build/sfx-plan.json
# sfx.json: [{"t": "L3:palabra-0.05", "sfx": "pop1" | "synth:puerta", "gain_db": -9, "rate": 1.0, "uso": "...",
#             "corta_en": "L5-0.1"}]   (archivos del banco en audio/sfx/<nombre>.wav, bajados con sfx_fetch.py)
import json, os, subprocess, sys
import numpy as np
from scipy.signal import butter, sosfilt

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SK, 'engine'))
from project import Project

P = os.path.abspath(sys.argv[1])
prj = Project(P)
SR = 48000
N = int(prj.t_end * SR)
A = os.path.join(P, 'audio')
rng = np.random.default_rng(7)


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def db(x):
    return 10 ** (x / 20)


def place(buf, sig, t, gain_db=0.0, rate=1.0):
    if rate != 1.0:
        idx = np.arange(0, len(sig) - 1, rate)
        sig = np.interp(idx, np.arange(len(sig)), sig)
    i = max(0, int(t * SR))
    j = min(N, i + len(sig))
    if j > i:
        buf[i:j] += sig[:j - i] * db(gain_db)


def bp(lo, hi, n):
    return sosfilt(butter(2, [lo, hi], btype='band', fs=SR, output='sos'), rng.standard_normal(n))


mix = np.zeros(N)
dia = load(os.path.join(A, 'dialogo.wav'))
mix[:min(N, len(dia))] += dia[:N]
# ---- tono de sala (muy bajo) según el set
tt = np.arange(N) / SR
amb = prj.look.get('ambiente') or {'office_night': 'oficina', 'cafe': 'cafe'}.get(prj.look.get('set', ''), 'oficina')
if amb == 'cafe':
    room = bp(120, 2500, N)
    room = room / np.sqrt(np.mean(room ** 2)) * db(-52)
    # murmullo lejano: ruido modulado lento + tintineo ocasional de tazas
    room *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.21 * tt) * np.sin(2 * np.pi * 0.07 * tt + 1)
    for k in range(int(prj.t_end / 3.5)):
        t0 = rng.uniform(0.5, max(0.6, prj.t_end - 0.5))
        n = int(0.4 * SR)
        x = np.arange(n) / SR
        clink = sum(a * np.sin(2 * np.pi * f * x) * np.exp(-x * d) for f, a, d in ((2900, 1, 18), (4300, 0.5, 25)))
        place(room, clink, t0, -54 + rng.uniform(-4, 2))
else:
    room = bp(70, 900, N)
    room = room / np.sqrt(np.mean(room ** 2)) * db(-50)
    room += db(-62) * np.sin(2 * np.pi * 120 * tt) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.13 * tt))
env = np.clip(tt / 0.6, 0, 1) * np.clip((prj.t_end - tt) / 1.0, 0, 1)
mix += room * env


# ---- SFX sintetizados (los que no existen en editorbrain-essentials-v1). Sin silbidos ni twang de western: Santi los vetó.
def synth(kind, dur=None):
    if kind == 'puerta':
        n = int(0.7 * SR); t = np.arange(n) / SR
        thump = np.sin(2 * np.pi * (62 + 30 * np.exp(-t * 18)) * t) * np.exp(-t * 9)
        body = bp(90, 700, n) * np.exp(-t * 22)
        latch = sosfilt(butter(2, 2500, btype='high', fs=SR, output='sos'), rng.standard_normal(n)) * np.exp(-t * 160)
        s = 0.9 * thump + 0.8 * body / np.max(np.abs(body)) + 0.35 * latch / np.max(np.abs(latch))
    elif kind == 'impresora':
        n = int((dur or 1.5) * SR); t = np.arange(n) / SR
        lines = (np.sin(2 * np.pi * 26 * t) > 0.6).astype(float)
        fade = np.clip(t / 0.03, 0, 1) * np.clip(((dur or 1.5) - t) / 0.05, 0, 1)
        s = bp(600, 3200, n) * (0.35 + 0.65 * lines) * fade + 0.2 * np.sin(2 * np.pi * 180 * t) * fade
    elif kind == 'caja_registradora':
        n = int(1.4 * SR); t = np.arange(n) / SR
        clunk = bp(200, 1200, n) * np.exp(-t * 40)
        bell = sum(a * np.sin(2 * np.pi * f * (t - 0.12)) * np.exp(-np.maximum(t - 0.12, 0) * d) * (t > 0.12)
                   for f, a, d in ((2093, 1, 3), (2637, 0.8, 3.5), (3136, 0.5, 4), (4186, 0.3, 6)))
        s = 0.8 * clunk / np.max(np.abs(clunk)) + bell
    elif kind == 'papel':
        n = int(0.25 * SR); t = np.arange(n) / SR
        s = bp(400, 5000, n) * np.exp(-t * 35)
    elif kind == 'golpe':
        n = int(0.35 * SR); t = np.arange(n) / SR
        s = np.sin(2 * np.pi * (55 + 70 * np.exp(-t * 30)) * t) * np.exp(-t * 14) + \
            0.3 * sosfilt(butter(2, 1800, btype='high', fs=SR, output='sos'), rng.standard_normal(n)) * np.exp(-t * 90)
    elif kind == 'ding':
        n = int(1.8 * SR); t = np.arange(n) / SR
        s = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((1318, 1, 2.2), (2637, 0.5, 3.5), (3950, 0.25, 5)))
    elif kind == 'cajon':
        n = int(0.5 * SR); t = np.arange(n) / SR
        s = bp(150, 1400, n) * np.exp(-t * 9) * (0.6 + 0.4 * np.sin(2 * np.pi * 40 * t)) + \
            0.5 * np.sin(2 * np.pi * 90 * t) * np.exp(-np.maximum(t - 0.35, 0) * 30) * (t > 0.35)
    else:
        raise KeyError(f'sfx sintetizado desconocido: {kind}')
    return s / np.max(np.abs(s))


cache = {}
plan = []
for e in prj.sfx:
    if not isinstance(e, dict) or e.get('_nota'):
        continue
    t = prj.T(e['t'])
    k = e['sfx']
    if k.startswith('synth:'):
        sig = synth(k[6:], e.get('dur'))
    else:
        if k not in cache:
            fp = os.path.join(A, 'sfx', f'{k}.wav')
            if not os.path.exists(fp):
                sys.exit(f'falta {fp}: bájalo con scripts/sfx_fetch.py <sound_id> {k} {P}')
            cache[k] = load(fp)
        sig = cache[k]
    if e.get('corta_en') is not None:     # silencio limpio antes de un remate o susurro
        n = int((prj.T(e['corta_en']) - t) * SR)
        n = min(max(n, 0), len(sig))
        sig = sig[:n] * np.clip((n - np.arange(n)) / (0.08 * SR), 0, 1)
    place(mix, sig, t, e.get('gain_db', -12), e.get('rate', 1.0))
    plan.append(dict(t=round(t, 3), sfx=k, gain_db=e.get('gain_db', -12), rate=e.get('rate', 1.0), uso=e.get('uso', '')))
os.makedirs(os.path.join(P, 'build'), exist_ok=True)
json.dump(plan, open(os.path.join(P, 'build', 'sfx-plan.json'), 'w'), ensure_ascii=False, indent=1)

pre = os.path.join(A, '_premix.f32')
mix.astype(np.float32).tofile(pre)
src = ['-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', pre]


def measure(args):
    r = subprocess.run(['ffmpeg', '-hide_banner', *args, '-af', 'loudnorm=I=-14:TP=-1.5:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    return json.loads(r[r.rindex('{'):r.rindex('}') + 1])


gain = -14.0 - float(measure(src)['input_i'])
out = os.path.join(A, 'mezcla.wav')
for it in range(4):
    af = f"volume={gain:.2f}dB,alimiter=limit=0.83:attack=2:release=60:level=disabled,aresample=48000"
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *src, '-af', af, '-ac', '2', '-c:a', 'pcm_s24le', out], check=True)
    err = -14.0 - float(measure(['-i', out])['input_i'])
    if abs(err) < 0.15:
        break
    gain += err
os.remove(pre)
c = measure(['-i', out])
print(f"mezcla.wav  I={c['input_i']} LUFS  TP={c['input_tp']} dBTP  ({len(plan)} SFX)")
