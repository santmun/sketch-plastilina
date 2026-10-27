# entorno.py — lo que depende de la computadora, en un solo lugar (macOS, Linux y Windows):
#   find_blender()  ruta del ejecutable de Blender ($BLENDER, PATH o las rutas de instalación típicas)
#   load_keys()     llaves de ElevenLabs/AssemblyAI desde el entorno o un archivo .env (nunca las imprime)
#   find_font()     una fuente negrita del sistema para subtítulos y hojas de contacto
#   free_gb()       GB libres en el disco de una carpeta
import glob, os, platform, shutil, subprocess, sys

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM = platform.system()          # 'Darwin' | 'Linux' | 'Windows'
KEYS = ('ELEVENLABS_API_KEY', 'ASSEMBLYAI_API_KEY')
CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'sketch-plastilina')
MIN_BLENDER = (5, 0)


def _blender_candidates():
    if os.environ.get('BLENDER'):
        yield os.environ['BLENDER']
    w = shutil.which('blender')
    if w:
        yield w
    if SYSTEM == 'Darwin':
        yield '/Applications/Blender.app/Contents/MacOS/Blender'
        yield os.path.expanduser('~/Applications/Blender.app/Contents/MacOS/Blender')
        yield from sorted(glob.glob('/Applications/Blender*.app/Contents/MacOS/Blender'), reverse=True)
    elif SYSTEM == 'Windows':
        for root in (os.environ.get('ProgramFiles', r'C:\Program Files'), os.environ.get('ProgramFiles(x86)', '')):
            if root:
                yield from sorted(glob.glob(os.path.join(root, 'Blender Foundation', 'Blender*', 'blender.exe')), reverse=True)
        yield from sorted(glob.glob(os.path.expanduser(r'~\AppData\Local\Programs\Blender Foundation\Blender*\blender.exe')),
                          reverse=True)
    else:
        yield '/snap/bin/blender'
        yield '/usr/bin/blender'
        yield '/usr/local/bin/blender'
        yield from sorted(glob.glob(os.path.expanduser('~/blender*/blender')), reverse=True)
        yield from sorted(glob.glob('/opt/blender*/blender'), reverse=True)


def blender_version(path):
    """(5, 2, 1) o None si no corre"""
    try:
        out = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return None
    for line in out.splitlines():
        if line.startswith('Blender '):
            nums = line.split()[1].split('.')
            try:
                return tuple(int(n) for n in nums[:3])
            except ValueError:
                return None
    return None


def find_blender(require_version=True):
    """ruta del primer Blender que corre (y que es >= 5.0 si require_version); None si no hay"""
    seen = set()
    for c in _blender_candidates():
        if not c or c in seen or not os.path.isfile(c):
            continue
        seen.add(c)
        v = blender_version(c)
        if v and (not require_version or v[:2] >= MIN_BLENDER):
            return c
    return None


def _parse_env(path):
    out = {}
    try:
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            out[k.strip().removeprefix('export ').strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def env_files(project=None):
    """archivos .env que se leen, del más específico al más general"""
    fs = []
    if project:
        fs.append(os.path.join(os.path.abspath(project), '.env'))
    fs += [os.path.join(os.getcwd(), '.env'), os.path.join(CONFIG_DIR, '.env'), os.path.join(SK, '.env')]
    return fs


def load_keys(project=None):
    """pone en os.environ las llaves que falten, leyéndolas del primer .env que las tenga. Devuelve {llave: origen}"""
    origin = {}
    for k in KEYS:
        if os.environ.get(k):
            origin[k] = 'entorno'
    for f in env_files(project):
        vals = _parse_env(f)
        for k in KEYS:
            if k not in origin and vals.get(k):
                os.environ[k] = vals[k]
                origin[k] = f
    return origin


def require_key(name, project=None):
    load_keys(project)
    v = os.environ.get(name)
    if not v:
        sys.exit(f'falta {name}. Ponla en {os.path.join(CONFIG_DIR, ".env")} como  {name}=tu_llave  '
                 f'(o expórtala en la terminal). Corre  python3 {SK}/scripts/doctor.py  para revisar todo.')
    return v


FONT_CANDIDATES = {
    'Darwin': [('/System/Library/Fonts/Avenir Next.ttc', 'Bold'), ('/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf', None),
               ('/System/Library/Fonts/Supplemental/Arial Bold.ttf', None)],
    'Windows': [(r'C:\Windows\Fonts\arialbd.ttf', None), (r'C:\Windows\Fonts\segoeuib.ttf', None),
                (r'C:\Windows\Fonts\calibrib.ttf', None)],
    'Linux': [('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', None),
              ('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', None),
              ('/usr/share/fonts/TTF/DejaVuSans-Bold.ttf', None), ('/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf', None)],
}


def find_font(size, mono=False):
    """ImageFont de PIL en negritas (o monoespaciada) que exista en esta computadora; la de PIL si no hay ninguna"""
    from PIL import ImageFont
    if mono:
        cands = {'Darwin': [('/System/Library/Fonts/Menlo.ttc', None)], 'Windows': [(r'C:\Windows\Fonts\consolab.ttf', None)],
                 'Linux': [('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', None)]}.get(SYSTEM, [])
    else:
        cands = FONT_CANDIDATES.get(SYSTEM, [])
    bundled = sorted(glob.glob(os.path.join(SK, 'assets', 'fonts', '*.[ot]t[fc]')))
    for path, style in list(cands) + [(b, None) for b in bundled]:
        if not os.path.exists(path):
            continue
        for i in range(12 if path.endswith('.ttc') else 1):
            try:
                f = ImageFont.truetype(path, size, index=i)
            except Exception:
                break
            if style is None or f.getname()[1] == style:
                return f
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def font_files_for_blender():
    """rutas de .ttf/.ttc para los letreros 3D, en orden de preferencia"""
    return [p for p, _ in FONT_CANDIDATES.get(SYSTEM, []) if p.endswith(('.ttf', '.otf'))] + \
        sorted(glob.glob(os.path.join(SK, 'assets', 'fonts', '*.[ot]tf')))


def free_gb(path='.'):
    return shutil.disk_usage(os.path.abspath(path)).free / 1e9
