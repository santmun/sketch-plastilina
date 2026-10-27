# transcribe.py — tiempos por palabra de AssemblyAI sobre audio/dialogo.wav (español) -> audio/palabras.json (ms).
#   python3 transcribe.py <proyecto>   (llave: ASSEMBLYAI_API_KEY en el entorno o en .env)
# Compara las palabras con el guion por línea y avisa si AssemblyAI escuchó algo distinto (revisa la toma).
import json, os, re, sys, time, unicodedata, urllib.request

P = os.path.abspath(sys.argv[1])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entorno
KEY = entorno.require_key('ASSEMBLYAI_API_KEY', P)
H = {'authorization': KEY, 'User-Agent': 'Mozilla/5.0'}


def call(url, data=None, ctype='application/json'):
    req = urllib.request.Request(url, data=data, headers={**H, 'content-type': ctype}, method='POST' if data else 'GET')
    return json.load(urllib.request.urlopen(req, timeout=300))


audio = open(os.path.join(P, 'audio', 'dialogo.wav'), 'rb').read()
up = call('https://api.assemblyai.com/v2/upload', audio, 'application/octet-stream')
tr = call('https://api.assemblyai.com/v2/transcript',
          json.dumps(dict(audio_url=up['upload_url'], language_code='es', punctuate=True, format_text=True)).encode())
while True:
    r = call(f"https://api.assemblyai.com/v2/transcript/{tr['id']}")
    if r['status'] in ('completed', 'error'):
        break
    time.sleep(2)
if r['status'] == 'error':
    sys.exit(f"AssemblyAI: {r.get('error')}")
words = [dict(text=w['text'], start=w['start'], end=w['end'], confidence=w.get('confidence'), speaker=w.get('speaker'))
         for w in r['words']]
json.dump(words, open(os.path.join(P, 'audio', 'palabras.json'), 'w'), ensure_ascii=False)
print(f'{len(words)} palabras -> audio/palabras.json')


def norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    return re.sub(r'[^a-z0-9ñ ]+', '', ''.join(c for c in s if unicodedata.category(c) != 'Mn')).split()


tl_p = os.path.join(P, 'build', 'timeline.json')
if os.path.exists(tl_p):
    for ln in json.load(open(tl_p))['lineas']:
        heard = ' '.join(w['text'] for w in words if ln['start'] - 0.25 <= w['start'] / 1000 <= ln['end'] + 0.1)
        want = norm(re.sub(r'\[[^\]]*\]', '', ln['text']))
        got = norm(heard)
        miss = [w for w in want if w not in got]
        flag = '  <-- revisar' if len(miss) > max(1, len(want) // 4) else ''
        print(f"{ln['i']:02d} {ln['who']:8s} {heard}{flag}")
