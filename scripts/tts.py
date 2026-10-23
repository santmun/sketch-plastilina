# tts.py — una toma de ElevenLabs (v4 por default) por línea del guion, con la voz de cada personaje (cast.json).
#   doppler run --project editorbrain --config dev -- python3 tts.py <proyecto> [--solo 3,5] [--modelo eleven_v4] [--forzar]
# -> <proyecto>/audio/lineas/NN_QUIEN.mp3 + manifest.json (no regenera líneas sin cambios). Nunca imprime la llave.
import hashlib, json, os, sys, time, urllib.request, urllib.error

P = os.path.abspath(sys.argv[1])
argv = sys.argv[2:]


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


KEY = os.environ.get('ELEVENLABS_API_KEY')
if not KEY:
    sys.exit('falta ELEVENLABS_API_KEY: corre con  doppler run --project editorbrain --config dev -- python3 tts.py ...')
guion = json.load(open(os.path.join(P, 'guion.json')))
cast = json.load(open(os.path.join(P, 'cast.json')))['personajes']
model = opt('--modelo', guion.get('modelo', 'eleven_v4'))
solo = {int(x) for x in opt('--solo', '').split(',') if x}
out = os.path.join(P, 'audio', 'lineas')
os.makedirs(out, exist_ok=True)
man_p = os.path.join(out, 'manifest.json')
man = json.load(open(man_p)) if os.path.exists(man_p) else {}
for i, ln in enumerate(guion['lineas'], 1):
    who, text = ln[0], ln[1]
    if solo and i not in solo:
        continue
    spec = cast.get(who) or {}
    voice = spec.get('voz') or guion.get('voces', {}).get(who)
    if not voice:
        sys.exit(f'línea {i}: {who} no tiene voz (cast.json personajes.{who}.voz)')
    settings = spec.get('voz_ajustes')
    sig = hashlib.sha256(json.dumps([voice, model, text, settings], ensure_ascii=False).encode()).hexdigest()[:16]
    fn = os.path.join(out, f'{i:02d}_{who}.mp3')
    if os.path.exists(fn) and man.get(f'{i:02d}') == sig and '--forzar' not in argv:
        print(f'{i:02d} {who:8s} sin cambios')
        continue
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
            sys.exit(f'línea {i}: ElevenLabs {e.code}: {msg}')
    open(fn, 'wb').write(data)
    man[f'{i:02d}'] = sig
    json.dump(man, open(man_p, 'w'), indent=1)
    print(f'{i:02d} {who:8s} {len(data) // 1024} KB  {text}')
print('listo: corre scripts/timeline.py y luego scripts/transcribe.py')
