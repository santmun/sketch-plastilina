# assemble.py — tramos de video + subtítulos (PNG) + audio/mezcla.wav -> mp4
#   python3 assemble.py <proyecto> <ancho> <salida.mp4> [--maxmb 23] [--chunks 'renders/c360_*.mp4'] [--sin-subs]
import glob, json, os, subprocess, sys

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P, W, OUT = os.path.abspath(sys.argv[1]), int(sys.argv[2]), os.path.abspath(sys.argv[3])
argv = sys.argv[4:]
maxmb = float(argv[argv.index('--maxmb') + 1]) if '--maxmb' in argv else None
pat = argv[argv.index('--chunks') + 1] if '--chunks' in argv else f'renders/c{W}_*.mp4'
chunks = sorted(glob.glob(os.path.join(P, pat)))
assert chunks, f'no hay tramos {pat}'
lst = os.path.join(P, 'renders', '_concat.txt')
with open(lst, 'w') as fh:
    for c in chunks:
        fh.write(f"file '{c}'\n")
subs = []
if '--sin-subs' not in argv:
    subdir = os.path.join(P, 'renders', f'subs_{W}')
    subprocess.run([sys.executable, os.path.join(SK, 'scripts', 'subs.py'), P, str(W), subdir], check=True, capture_output=True)
    subs = json.load(open(os.path.join(subdir, 'subs.json')))
args = ['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst]
for s in subs:
    args += ['-i', s['png']]
args += ['-i', os.path.join(P, 'audio', 'mezcla.wav')]
fc, prev = [], '0:v'
for k, s in enumerate(subs):
    fc.append(f"[{prev}][{k + 1}:v]overlay=0:{s['y']}:enable='between(t,{s['a']:.3f},{s['b']:.3f})'[v{k}]")
    prev = f'v{k}'
fc.append(f'[{prev}]format=yuv420p[vout]')
args += ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', f'{len(subs) + 1}:a', '-c:v', 'libx264', '-preset', 'slow',
         '-profile:v', 'high', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '192k', '-shortest']
if maxmb:
    tl = json.load(open(os.path.join(P, 'build', 'timeline.json')))
    vbr = int((maxmb * 8 * 1024 * 1024 / tl['t_end'] - 200_000) * 0.92)
    args += ['-b:v', str(vbr), '-maxrate', str(int(vbr * 1.4)), '-bufsize', str(vbr * 2)]
else:
    args += ['-crf', '16']
subprocess.run(args + [OUT], check=True)
print(f'{OUT}  {os.path.getsize(OUT) / 1e6:.1f} MB  ({len(chunks)} tramos, {len(subs)} subtítulos)')
