# render.py — render por tramos + mezcla + subtítulos + ensamble (macOS, Linux y Windows). UN solo Blender a la vez;
# si el disco baja de --minfree GB espera hasta 40 min y luego se detiene (los tramos hechos se conservan).
#   python3 render.py <proyecto> draft     -> 360x640,   4 muestras -> <proyecto>/draft.mp4
#   python3 render.py <proyecto> review    -> 720x1280, 12 muestras -> <proyecto>/review-<ver>.mp4 (<23 MB)
#   python3 render.py <proyecto> final     -> 1080x1920, 40 muestras -> <proyecto>/<nombre>-<ver>.mp4 + -preview (<23 MB)
# Opciones: --ver v1 · --step 240 (cuadros por tramo) · --minfree 8 · --forzar (re-renderiza tramos que ya existen)
# Blender: $BLENDER o el que encuentre scripts/entorno.py.
import os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entorno

MODES = {'draft': (360, 4), 'preview': (540, 6), 'review': (720, 12), 'final': (1080, 40)}


def opt(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def main():
    argv = sys.argv[1:]
    if not argv or argv[0].startswith('-'):
        sys.exit('uso: render.py <proyecto> draft|review|final|preview [--ver v1] [--step 240] [--minfree 8] [--forzar]')
    P = os.path.abspath(argv[0])
    mode = argv[1] if len(argv) > 1 and not argv[1].startswith('-') else 'review'
    if mode not in MODES:
        sys.exit(f'modo desconocido: {mode} (draft, preview, review, final)')
    ver = opt(argv, '--ver', os.environ.get('VER', 'v1'))
    step = int(opt(argv, '--step', os.environ.get('STEP', 240)))
    minfree = float(opt(argv, '--minfree', os.environ.get('MINFREE', 8)))
    force = '--forzar' in argv or bool(os.environ.get('FORCE'))
    res, samples = MODES[mode]
    name = os.path.basename(P)
    out = os.path.join(P, {'draft': 'draft.mp4', 'preview': f'preview-{ver}.mp4', 'review': f'review-{ver}.mp4',
                           'final': f'{name}-{ver}.mp4'}[mode])
    blender = entorno.find_blender()
    if not blender:
        sys.exit('no encontré Blender 5.x. Corre  python3 ' + os.path.join(entorno.SK, 'scripts', 'doctor.py'))
    sys.path.insert(0, os.path.join(entorno.SK, 'engine'))
    from project import Project
    total = Project(P).n_frames - 1
    os.makedirs(os.path.join(P, 'renders'), exist_ok=True)
    py, S = sys.executable, os.path.join(entorno.SK, 'scripts')
    subprocess.run([py, os.path.join(S, 'mix.py'), P], check=True)
    t0 = time.time()
    for a in range(0, total + 1, step):
        b = min(a + step - 1, total)
        f = os.path.join('renders', f'c{res}_{a:04d}.mp4')
        fp = os.path.join(P, f)
        if not force and os.path.exists(fp) and os.path.getsize(fp) > 0:
            print(f'ya existe {f}')
            continue
        waited = 0
        while entorno.free_gb(P) < minfree:
            if waited >= 2400:
                print(f'DISCO BAJO ({entorno.free_gb(P):.0f} GB) por 40 min: me detengo antes del tramo {a}')
                sys.exit(2)
            print(f'disco bajo ({entorno.free_gb(P):.0f} GB), espero...', flush=True)
            time.sleep(30)
            waited += 30
        print(f'tramo {a}-{b} ({time.strftime("%H:%M:%S")}, libre {entorno.free_gb(P):.0f} GB)', flush=True)
        log = os.path.join(P, 'renders', f'log_{res}_{a}.txt')
        with open(log, 'w') as fh:
            subprocess.run([blender, '-b', '-P', os.path.join(entorno.SK, 'engine', 'scene.py'), '--', '--project', P,
                            '--anim', str(a), str(b), '--res', str(res), '--samples', str(samples), '--out', f],
                           stdout=fh, stderr=subprocess.STDOUT, cwd=P)
        txt = open(log, encoding='utf-8', errors='replace').read()
        done = [l for l in txt.splitlines() if '[render]' in l]
        if not done:
            print(f'falló el tramo {a}')
            print('\n'.join(txt.splitlines()[-20:]))
            sys.exit(1)
        print(done[-1], flush=True)
    print(f'render: {int(time.time() - t0)} s')
    asm = os.path.join(S, 'assemble.py')
    if mode == 'final':
        subprocess.run([py, asm, P, str(res), out], check=True)
        subprocess.run([py, asm, P, str(res), os.path.splitext(out)[0] + '-preview.mp4', '--maxmb', '23'], check=True)
    else:
        subprocess.run([py, asm, P, str(res), out, '--maxmb', '23'], check=True)


if __name__ == '__main__':
    main()
