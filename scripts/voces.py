# voces.py — lista las voces de ElevenLabs de la cuenta (id, nombre, género, edad, acento) para elegir el casting.
#   python3 voces.py [--es]   (--es: solo voces en español; llave: ELEVENLABS_API_KEY en el entorno o en .env)
# Prueba una voz antes de fijarla: genera UNA línea del guion con tts.py --solo N.
import json, os, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entorno
KEY = entorno.require_key('ELEVENLABS_API_KEY')
req = urllib.request.Request('https://api.elevenlabs.io/v2/voices?page_size=100', headers={'xi-api-key': KEY, 'User-Agent': 'Mozilla/5.0'})
for v in json.load(urllib.request.urlopen(req, timeout=30))['voices']:
    lb = v.get('labels') or {}
    if '--es' in sys.argv and lb.get('language') != 'es':
        continue
    print(f"{v['voice_id']}  {v['name'][:42]:42s} {lb.get('gender') or '-':7s} {lb.get('age') or '-':12s} "
          f"{lb.get('accent') or '-':16s} {lb.get('descriptive') or lb.get('description') or ''}")
