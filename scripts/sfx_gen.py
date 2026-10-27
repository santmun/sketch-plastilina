# sfx_gen.py — genera un efecto de sonido con ElevenLabs (Sound Effects) para quien no tiene el banco de EditorBrain.
#   python3 sfx_gen.py <proyecto> <nombre> "descripción en inglés" [--seg 1.5] [--forzar]
#   -> <proyecto>/audio/sfx/<nombre>.wav (mono 48 kHz) + registro en audio/sfx/sfx-ids.jsonl; úsalo en sfx.json como "sfx": "<nombre>"
# Describe el sonido en inglés y concreto («wooden door creaks open slowly», «light switch click», «cartoon pop»).
# Gasta créditos de ElevenLabs: genera solo los que vayas a usar y escúchalos antes de mezclar.
import json, os, subprocess, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entorno

if len(sys.argv) < 4:
    sys.exit('uso: sfx_gen.py <proyecto> <nombre> "descripción en inglés" [--seg 1.5] [--forzar]')
P, name, prompt = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3]
argv = sys.argv[4:]
seg = float(argv[argv.index('--seg') + 1]) if '--seg' in argv else None
key = entorno.require_key('ELEVENLABS_API_KEY', P)
d = os.path.join(P, 'audio', 'sfx')
os.makedirs(d, exist_ok=True)
out = os.path.join(d, f'{name}.wav')
if os.path.exists(out) and '--forzar' not in argv:
    sys.exit(f'{out} ya existe (usa --forzar para regenerarlo)')
body = dict(text=prompt, prompt_influence=0.5)
if seg:
    body['duration_seconds'] = max(0.5, min(22.0, seg))
req = urllib.request.Request('https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128',
                             data=json.dumps(body).encode(), method='POST',
                             headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg',
                                      'User-Agent': 'Mozilla/5.0'})
try:
    data = urllib.request.urlopen(req, timeout=120).read()
except urllib.error.HTTPError as e:
    sys.exit(f'ElevenLabs {e.code}: {e.read().decode("utf-8", "replace")[:300]}')
tmp = out + '.mp3'
open(tmp, 'wb').write(data)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-ac', '1', '-ar', '48000', out], check=True)
os.remove(tmp)
rec = dict(id=f'elevenlabs:{prompt}', nombre=name, origen='ElevenLabs Sound Effects', duracion=seg, archivo=f'audio/sfx/{name}.wav')
with open(os.path.join(d, 'sfx-ids.jsonl'), 'a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
print(json.dumps(rec, ensure_ascii=False))
