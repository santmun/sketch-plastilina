# doctor.py — revisa que la computadora tenga todo para hacer sketches de plastilina y dice cómo instalar lo que falte.
#   python3 doctor.py                 revisión rápida (sale con 1 si falta algo obligatorio)
#   python3 doctor.py --en-linea      además prueba que las llaves de ElevenLabs y AssemblyAI funcionen
#   python3 doctor.py --prueba        además hace un render real chiquito en Blender (EEVEE) para confirmar que todo corre
#   python3 doctor.py --json          resultado en JSON (para el agente)
#   python3 doctor.py --blender       solo imprime la ruta de Blender (para  B=$(python3 doctor.py --blender))
# Nunca imprime llaves. No instala nada por su cuenta: dice el comando exacto para cada sistema.
import importlib, json, os, platform, shutil, subprocess, sys, tempfile, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entorno

SYS = entorno.SYSTEM
OS_NAME = {'Darwin': 'macOS', 'Windows': 'Windows', 'Linux': 'Linux'}.get(SYS, SYS)
PY = 'python3' if SYS != 'Windows' else 'py'
HOW = {
    'brew': {'Darwin': 'Instala Homebrew (https://brew.sh):  /bin/bash -c "$(curl -fsSL '
                        'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'},
    'python': {'Darwin': 'brew install python', 'Windows': 'winget install Python.Python.3.12',
               'Linux': 'sudo apt install python3 python3-pip   (o el gestor de tu distribución)'},
    'pip': {'any': f'{PY} -m pip install --user numpy scipy pillow'},
    'ffmpeg': {'Darwin': 'brew install ffmpeg', 'Windows': 'winget install Gyan.FFmpeg   (luego abre una terminal nueva)',
               'Linux': 'sudo apt install ffmpeg'},
    'blender': {'Darwin': 'brew install --cask blender   (o descárgalo de https://www.blender.org/download/)',
                'Windows': 'winget install BlenderFoundation.Blender   (o https://www.blender.org/download/)',
                'Linux': 'sudo snap install blender --classic   (o el .tar.xz de https://www.blender.org/download/; '
                         'el de apt suele ser viejo)'},
    'eleven': {'any': 'Crea tu llave en https://elevenlabs.io/app/settings/api-keys (permiso de Text to Speech y Sound '
                      'Effects) y agrégala a ' + os.path.join(entorno.CONFIG_DIR, '.env') + ' como  ELEVENLABS_API_KEY=...'},
    'assembly': {'any': 'Crea tu llave gratis en https://www.assemblyai.com/app/api-keys y agrégala a ' +
                        os.path.join(entorno.CONFIG_DIR, '.env') + ' como  ASSEMBLYAI_API_KEY=...'},
}


def how(k):
    h = HOW[k]
    return h.get(SYS) or h.get('any') or next(iter(h.values()))


checks = []


def add(name, ok, detail, fix=None, required=True):
    checks.append(dict(nombre=name, ok=bool(ok), obligatorio=required, detalle=detail, como_arreglar=None if ok else fix))


def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout + r.stderr
    except Exception as e:
        return 1, str(e)


def main():
    argv = sys.argv[1:]
    if '--blender' in argv:
        b = entorno.find_blender()
        if not b:
            sys.exit('no encontré Blender 5.x: ' + how('blender'))
        print(b)
        return

    # 1. sistema y Python
    add('Sistema', SYS in ('Darwin', 'Linux', 'Windows'), f'{OS_NAME} {platform.release()} ({platform.machine()})',
        'Sistema no probado: usa macOS, Linux o Windows 10/11.')
    pv = sys.version_info
    add('Python 3.9+', pv >= (3, 9), f'Python {pv.major}.{pv.minor}.{pv.micro}', how('python'))

    # 2. paquetes de Python
    missing = []
    for mod, pkg in (('numpy', 'numpy'), ('scipy', 'scipy'), ('PIL', 'pillow')):
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(pkg)
    add('Paquetes de Python (numpy, scipy, pillow)', not missing,
        'completos' if not missing else 'faltan: ' + ', '.join(missing), how('pip'))

    # 3. ffmpeg
    ff, fp = shutil.which('ffmpeg'), shutil.which('ffprobe')
    if ff and fp:
        _, enc = run([ff, '-hide_banner', '-encoders'])
        _, fil = run([ff, '-hide_banner', '-filters'])
        ok = 'libx264' in enc and 'loudnorm' in fil
        add('ffmpeg + ffprobe (con libx264 y loudnorm)', ok, ff if ok else 'falta libx264 o loudnorm en tu ffmpeg',
            how('ffmpeg'))
    else:
        add('ffmpeg + ffprobe', False, 'no están en el PATH', how('ffmpeg'))

    # 4. Blender
    b_any = entorno.find_blender(require_version=False)
    b = entorno.find_blender()
    if b:
        v = entorno.blender_version(b)
        add('Blender 5.x', True, f'{".".join(map(str, v))} en {b}' + ('' if v[:2] >= (5, 2) else '  (probado en 5.2; si algo '
                                                                                               'falla, actualiza)'))
    elif b_any:
        v = entorno.blender_version(b_any)
        add('Blender 5.x', False, f'encontré Blender {".".join(map(str, v))} en {b_any}, pero el motor necesita 5.0 o más nuevo',
            how('blender'))
    else:
        add('Blender 5.x', False, 'no lo encontré (ni en $BLENDER ni en las rutas típicas)',
            how('blender') + '. Si está en otra carpeta, exporta  BLENDER=/ruta/al/ejecutable')

    # 5. llaves (nunca se imprimen)
    origin = entorno.load_keys()
    online = '--en-linea' in argv
    for key, label, fixk in (('ELEVENLABS_API_KEY', 'Llave de ElevenLabs (voces)', 'eleven'),
                             ('ASSEMBLYAI_API_KEY', 'Llave de AssemblyAI (tiempos de cada palabra)', 'assembly')):
        val = os.environ.get(key)
        if not val:
            add(label, False, 'no está en el entorno ni en ningún .env', how(fixk))
            continue
        detail = f'encontrada ({"en " + origin[key] if origin.get(key) != "entorno" else "en el entorno"})'
        ok = True
        if online:
            ok, msg = check_key(key, val)
            detail += f'; {msg}'
        add(label, ok, detail, how(fixk))

    # 6. disco
    gb = entorno.free_gb(os.getcwd())
    add('Espacio en disco (10 GB libres)', gb >= 10, f'{gb:.0f} GB libres en esta carpeta',
        'Libera espacio: cada video ocupa ~3-8 GB mientras se renderiza (se puede borrar al terminar).')

    # 7. fuentes
    try:
        f = entorno.find_font(20)
        name = ' '.join(f.getname()) if hasattr(f, 'getname') else 'la de PIL'
        add('Fuente para subtítulos', True, name, required=False)
    except Exception as e:
        add('Fuente para subtítulos', False, str(e), how('pip'), required=False)

    # 8. opcionales
    add('CLI de EditorBrain (banco de SFX, opcional)', bool(shutil.which('editorbrain')),
        'instalado' if shutil.which('editorbrain') else 'no instalado: los SFX se generan con scripts/sfx_gen.py (ElevenLabs) '
        'o se usan tus propios .wav', None, required=False)

    # 9. prueba real de render
    if '--prueba' in argv and b:
        ok, msg = smoke_render(b)
        add('Prueba de render (Blender + EEVEE)', ok, msg,
            'Revisa que tu tarjeta de video tenga drivers al día (EEVEE necesita GPU/OpenGL 4.3). En Linux sin pantalla '
            'usa una máquina con GPU o instala los drivers de Mesa.')

    req_ok = all(c['ok'] for c in checks if c['obligatorio'])
    if '--json' in argv:
        print(json.dumps(dict(listo=req_ok, sistema=OS_NAME, revisiones=checks), ensure_ascii=False, indent=1))
    else:
        print(f'\nSketch de plastilina · revisión de la computadora ({OS_NAME})\n')
        for c in checks:
            tag = 'OK    ' if c['ok'] else ('FALTA ' if c['obligatorio'] else 'opc.  ')
            print(f'  {tag}{c["nombre"]}: {c["detalle"]}')
            if c['como_arreglar']:
                print(f'          -> {c["como_arreglar"]}')
        print('\n' + ('Todo listo para hacer sketches.' if req_ok else
                      'Falta algo obligatorio: arréglalo con los comandos de arriba y vuelve a correr este chequeo.'))
        if req_ok and '--prueba' not in argv:
            print(f'Siguiente (opcional): {PY} {os.path.abspath(__file__)} --en-linea --prueba')
    sys.exit(0 if req_ok else 1)


def check_key(key, val):
    try:
        if key == 'ELEVENLABS_API_KEY':
            req = urllib.request.Request('https://api.elevenlabs.io/v1/voices?page_size=1',
                                         headers={'xi-api-key': val, 'User-Agent': 'Mozilla/5.0'})
        else:
            req = urllib.request.Request('https://api.assemblyai.com/v2/transcript?limit=1',
                                         headers={'authorization': val, 'User-Agent': 'Mozilla/5.0'})
        urllib.request.urlopen(req, timeout=20).read()
        return True, 'funciona'
    except urllib.error.HTTPError as e:
        return False, f'el servicio la rechazó (HTTP {e.code})'
    except Exception as e:
        return False, f'no pude conectarme ({type(e).__name__})'


def smoke_render(blender):
    """retrato de Clawd a 240 px con el set de la oficina: prueba Blender, EEVEE, el motor y las fuentes"""
    d = tempfile.mkdtemp(prefix='sketch-prueba-')
    code, out = run([sys.executable, os.path.join(entorno.SK, 'scripts', 'new_project.py'), d], timeout=60)
    if code:
        return False, 'no pude crear el proyecto de prueba: ' + out[-300:]
    code, out = run([blender, '-b', '-P', os.path.join(entorno.SK, 'engine', 'scene.py'), '--', '--project', d, '--retratos',
                     '--res', '240'], timeout=900)
    pngs = [f for f in os.listdir(os.path.join(d, 'look')) if f.endswith('.png')] if os.path.isdir(os.path.join(d, 'look')) else []
    if pngs:
        shutil.rmtree(d, ignore_errors=True)
        return True, f'Blender renderizó {len(pngs)} retratos de prueba'
    tail = '\n'.join(l for l in out.splitlines() if 'Error' in l or 'Traceback' in l or 'error' in l)[-400:]
    return False, f'el render falló (proyecto en {d}): {tail or out[-400:]}'


if __name__ == '__main__':
    main()
