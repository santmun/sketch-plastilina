# timeline.py — recorta el silencio de cada toma, arma el diálogo (entrada 0.3 s + pausa por línea del guion) y mide la
# envolvente RMS por cuadro (24 fps) para el lip-sync.
#   python3 timeline.py <proyecto>  -> audio/lineas/NN.wav, audio/dialogo.wav, build/timeline.json
import glob, json, os, subprocess, sys
import numpy as np

P = os.path.abspath(sys.argv[1])
SR, FPS = 48000, 24
guion = json.load(open(os.path.join(P, 'guion.json')))
look = json.load(open(os.path.join(P, 'look.json'))) if os.path.exists(os.path.join(P, 'look.json')) else {}
cast = json.load(open(os.path.join(P, 'cast.json'))).get('personajes', {}) if os.path.exists(os.path.join(P, 'cast.json')) else {}
L = os.path.join(P, 'audio', 'lineas')


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def save(path, x):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f64le', '-ar', str(SR), '-ac', '1', '-i', '-', '-c:a', 'pcm_s16le', path],
                   input=x.astype(np.float64).tobytes(), check=True)


def trim(x, thr_db=-45.0, pad=0.04):
    """quita silencio al inicio y al final (umbral relativo al pico, envolvente de 10 ms)"""
    if not len(x):
        return x
    w = int(0.01 * SR)
    env = np.sqrt(np.convolve(x ** 2, np.ones(w) / w, mode='same'))
    thr = np.max(env) * 10 ** (thr_db / 20)
    idx = np.where(env > thr)[0]
    if not len(idx):
        return x
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(x), idx[-1] + int(pad * SR))
    y = x[a:b].copy()
    f = int(0.008 * SR)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y


lead = float(look.get('entrada', 0.3))
parts, lines, t = [], [], lead          # parts = (inicio en s, audio); una pausa negativa encima la siguiente línea
for i, ln in enumerate(guion['lineas'], 1):
    who, text = ln[0], ln[1]
    pause = float(ln[2]) if len(ln) > 2 else 0.2
    cands = [f for f in glob.glob(os.path.join(L, f'{i:02d}_{who}.*')) if f.endswith(('.mp3', '.wav', '.m4a'))]
    if not cands:
        sys.exit(f'falta audio/lineas/{i:02d}_{who}.mp3 (o .wav/.m4a): genérala con scripts/tts.py, el MCP de ElevenLabs '
                 f'o grábala (python3 tts.py <proyecto> --plan lista lo que falta)')
    src = cands[0]
    x = trim(load(src))
    db = float((cast.get(who) or {}).get('voz_db', 0.0))      # cast.json: "voz_db": 6 sube esa voz 6 dB
    if db:
        x = x * 10 ** (db / 20)
    save(os.path.join(L, f'{i:02d}.wav'), x)
    d = len(x) / SR
    lines.append(dict(i=i, who=who, text=text, start=round(t, 3), end=round(t + d, 3)))
    parts.append((t, x))
    t += d + pause
end = max(a + len(x) / SR for a, x in parts) + max(0.0, pause)
dia = np.zeros(int(round(end * SR)) + 1)
for a, x in parts:
    k = int(round(a * SR))
    dia[k:k + len(x)] += x
dia = np.clip(dia, -1.0, 1.0)
dur = len(dia) / SR
save(os.path.join(P, 'audio', 'dialogo.wav'), dia)
hop = SR // FPS
rms = [round(float(np.sqrt(np.mean(dia[k * hop:(k + 1) * hop] ** 2))), 5) for k in range(int(np.ceil(len(dia) / hop)))]
t_end = round(lines[-1]['end'] + float(look.get('cola', 0.8)), 3)
os.makedirs(os.path.join(P, 'build'), exist_ok=True)
json.dump(dict(fps=FPS, duracion=round(dur, 3), t_end=t_end, lineas=lines, rms=rms),
          open(os.path.join(P, 'build', 'timeline.json'), 'w'), ensure_ascii=False)
for ln in lines:
    print(f"{ln['i']:02d} {ln['who']:8s} {ln['start']:6.2f}-{ln['end']:6.2f}  {ln['text']}")
print(f'diálogo {dur:.2f} s, video {t_end:.2f} s ({int(round(t_end * FPS))} cuadros)')
if not 55 <= t_end <= 75:
    print(f'[aviso] el formato pide 60-70 s; este dura {t_end:.1f} s (ok para pruebas cortas)')
