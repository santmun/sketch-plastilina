# tts.py — una toma por línea del guion con la voz de cada personaje (cast.json). Tres vías, según lo que tenga el usuario:
#   python3 tts.py <proyecto> [--solo 3,5] [--modelo eleven_v4] [--forzar]   API de ElevenLabs (ELEVENLABS_API_KEY)
#   python3 tts.py <proyecto> --plan        lista JSON de las tomas que faltan: archivo, texto, voz y modelo. Sirve para
#                                           generarlas con el MCP de ElevenLabs u otra herramienta, o grabarlas a mano
#   python3 tts.py <proyecto> --registrar   da por buenas las tomas que ya están en audio/lineas (mp3/wav/m4a) y las firma
# -> <proyecto>/audio/lineas/NN_QUIEN.<ext> + manifest.json (no regenera líneas sin cambios). Nunca imprime la llave.
import glob, hashlib, json, os, sys, time, urllib.request, urllib.error

P = os.path.abspath(sys.argv[1])
argv = sys.argv[2:]


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entorno
MODE = 'plan' if '--plan' in argv else 'registrar' if '--registrar' in argv else 'api'
KEY = entorno.require_key('ELEVENLABS_API_KEY', P) if MODE == 'api' else None
guion = json.load(open(os.path.join(P, 'guion.json')))
cast = json.load(open(os.path.join(P, 'cast.json')))['personajes']
model = opt('--modelo', guion.get('modelo', 'eleven_v4'))
solo = {int(x) for x in opt('--solo', '').split(',') if x}
out = os.path.join(P, 'audio', 'lineas')
os.makedirs(out, exist_ok=True)
man_p = os.path.join(out, 'manifest.json')
man = json.load(open(man_p)) if os.path.exists(man_p) else {}
PLAN = []
for i, ln in enumerate(guion['lineas'], 1):
    who, text = ln[0], ln[1]
    if solo and i not in solo:
        continue
    spec = cast.get(who) or {}
    voice = spec.get('voz') or guion.get('voces', {}).get(who)
    if not voice and MODE == 'api':
        sys.exit(f'línea {i}: {who} no tiene voz (cast.json personajes.{who}.voz): elige una con voces.py --es o el MCP')
    voice = voice or ('grabada' if MODE == 'registrar' else None)
    settings = spec.get('voz_ajustes')
    sig = hashlib.sha256(json.dumps([voice, model, text, settings], ensure_ascii=False).encode()).hexdigest()[:16]
    found = [f for f in glob.glob(os.path.join(out, f'{i:02d}_{who}.*')) if f.endswith(('.mp3', '.wav', '.m4a'))]
    fn = found[0] if found else os.path.join(out, f'{i:02d}_{who}.mp3')
    fresh = bool(found) and man.get(f'{i:02d}') == sig
    if MODE == 'plan':
        PLAN.append(dict(n=i, quien=who, voz=voice, modelo=model, texto=text, ajustes=settings, archivo=os.path.relpath(fn, P),
                         estado='listo' if fresh else ('cambio' if found else 'falta')))
        continue
    if MODE == 'registrar':
        if found:
            man[f'{i:02d}'] = sig
            print(f'{i:02d} {who:8s} registrada  {os.path.basename(fn)}')
        else:
            print(f'{i:02d} {who:8s} FALTA {os.path.relpath(fn, P)}')
        continue
    if fresh and '--forzar' not in argv:
        print(f'{i:02d} {who:8s} sin cambios')
        continue
    for f in found:                        # la API escribe mp3: quita una toma anterior con otra extensión
        if not f.endswith('.mp3'):
            os.remove(f)
    fn = os.path.join(out, f'{i:02d}_{who}.mp3')
    body = dict(text=text, model_id=model)
    if settings:
        body['voice_settings'] = settings
    if guion.get('idioma'):
        body['language_code'] = guion['idioma']
    req = urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128',
                                 data=json.dumps(body).encode(), method='POST',
                                 headers={'xi-api-key': KEY, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg',
                                          'User-Agent': 'Mozilla/5.0'})
    for attempt in range(3):
        try:
            data = urllib.request.urlopen(req, timeout=120).read()
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            if 'voice_not_found' in msg or (e.code == 404 and 'voice' in msg.lower()):
                sys.exit(f'línea {i}: la voz {voice} de {who} no está en tu cuenta de ElevenLabs. Elige una con  '
                         f'python3 {os.path.dirname(os.path.abspath(__file__))}/voces.py --es  (o agrégala desde la Voice '
                         f'Library) y cámbiala en cast.json.')
            if e.code in (401, 403) or 'quota' in msg.lower() or 'credits' in msg.lower():
                sys.exit(f'línea {i}: ElevenLabs {e.code}: revisa tu llave y que tu plan tenga créditos ({msg[:160]})')
            sys.exit(f'línea {i}: ElevenLabs {e.code}: {msg}')
    open(fn, 'wb').write(data)
    man[f'{i:02d}'] = sig
    json.dump(man, open(man_p, 'w'), indent=1)
    print(f'{i:02d} {who:8s} {len(data) // 1024} KB  {text}')
if MODE == 'plan':
    print(json.dumps([x for x in PLAN if x['estado'] != 'listo'] if '--todas' not in argv else PLAN, ensure_ascii=False, indent=1))
    sys.exit(0)
if MODE == 'registrar':
    json.dump(man, open(man_p, 'w'), indent=1)
print('listo: corre scripts/timeline.py y luego scripts/transcribe.py')
