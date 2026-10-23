# timeline.py — recorta el silencio de cada toma, arma el diálogo (entrada 0.3 s + pausa por línea del guion) y mide la
# envolvente RMS por cuadro (24 fps) para el lip-sync.
#   python3 timeline.py <proyecto>  -> audio/lineas/NN.wav, audio/dialogo.wav, build/timeline.json
import glob, json, os, subprocess, sys
import numpy as np

P = os.path.abspath(sys.argv[1])
SR, FPS = 48000, 24
guion = json.load(open(os.path.join(P, 'guion.json')))
look = json.load(open(os.path.join(P, 'look.json'))) if os.path.exists(os.path.join(P, 'look.json')) else {}
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
parts, lines, t = [np.zeros(int(lead * SR))], [], lead
for i, ln in enumerate(guion['lineas'], 1):
    who, text = ln[0], ln[1]
    pause = float(ln[2]) if len(ln) > 2 else 0.2
    src = os.path.join(L, f'{i:02d}_{who}.mp3')
    if not os.path.exists(src):
        sys.exit(f'falta {src}: corre scripts/tts.py')
    x = trim(load(src))
    save(os.path.join(L, f'{i:02d}.wav'), x)
    d = len(x) / SR
    lines.append(dict(i=i, who=who, text=text, start=round(t, 3), end=round(t + d, 3)))
    parts += [x, np.zeros(int(pause * SR))]
    t += d + pause
dia = np.concatenate(parts)
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
