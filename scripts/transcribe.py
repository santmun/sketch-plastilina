# transcribe.py — tiempos de cada palabra de audio/dialogo.wav -> audio/palabras.json (ms), para lip-sync y subtítulos.
#   python3 transcribe.py <proyecto>                       AssemblyAI (ASSEMBLYAI_API_KEY en el entorno o en .env)
#   python3 transcribe.py <proyecto> --importar w.json     tiempos de otra herramienta (MCP de ElevenLabs/Scribe, Whisper…)
#   python3 transcribe.py <proyecto> --whisper             Whisper local (pip install faster-whisper; sin llaves)
# El idioma sale de guion.json → "idioma" (default es).
# Compara las palabras con el guion por línea y avisa si AssemblyAI escuchó algo distinto (revisa la toma).
import json, os, re, sys, time, unicodedata, urllib.request

P = os.path.abspath(sys.argv[1])
argv = sys.argv[2:]
OUT = os.path.join(P, 'audio', 'palabras.json')
LANG = (json.load(open(os.path.join(P, 'guion.json'))).get('idioma') or 'es')[:2]


def to_ms(words):
    """[{text, start, end}] en segundos o milisegundos -> milisegundos (detecta la unidad)"""
    words = [w for w in words if str(w.get('text', '')).strip() and w.get('type', 'word') == 'word']
    if not words:
        return []
    secs = max(float(w['end']) for w in words) < 3600 and any(isinstance(w['end'], float) and w['end'] % 1 for w in words)
    k = 1000 if secs else 1
    return [dict(text=str(w['text']).strip(), start=int(round(float(w['start']) * k)), end=int(round(float(w['end']) * k)),
                 confidence=w.get('confidence') or w.get('logprob'), speaker=w.get('speaker') or w.get('speaker_id'))
            for w in words]


def from_file(path):
    """palabras con tiempos de otra herramienta: lista [{text,start,end}], {"words": [...]} (ElevenLabs Scribe/AssemblyAI)
    o {"segments": [{"words": [...]}]} (Whisper)"""
    d = json.load(open(path))
    if isinstance(d, dict):
        if 'words' in d:
            d = d['words']
        elif 'segments' in d:
            d = [dict(text=w.get('word', w.get('text')), start=w['start'], end=w['end']) for sg in d['segments']
                 for w in sg.get('words', [])]
    return to_ms([dict(w, text=w.get('text', w.get('word'))) for w in d])


def from_whisper():
    """Whisper local (faster-whisper), sin llaves ni internet después de bajar el modelo"""
    from faster_whisper import WhisperModel
    model = WhisperModel(os.environ.get('WHISPER_MODEL', 'small'), compute_type='int8')
    segs, _ = model.transcribe(os.path.join(P, 'audio', 'dialogo.wav'), language=LANG, word_timestamps=True)
    return to_ms([dict(text=w.word, start=w.start, end=w.end, confidence=w.probability) for sg in segs for w in sg.words])


def from_assemblyai():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import entorno
    H = {'authorization': entorno.require_key('ASSEMBLYAI_API_KEY', P), 'User-Agent': 'Mozilla/5.0'}

    def call(url, data=None, ctype='application/json'):
        req = urllib.request.Request(url, data=data, headers={**H, 'content-type': ctype}, method='POST' if data else 'GET')
        return json.load(urllib.request.urlopen(req, timeout=300))
    audio = open(os.path.join(P, 'audio', 'dialogo.wav'), 'rb').read()
    up = call('https://api.assemblyai.com/v2/upload', audio, 'application/octet-stream')
    tr = call('https://api.assemblyai.com/v2/transcript',
              json.dumps(dict(audio_url=up['upload_url'], language_code=LANG, punctuate=True, format_text=True)).encode())
    while True:
        r = call(f"https://api.assemblyai.com/v2/transcript/{tr['id']}")
        if r['status'] in ('completed', 'error'):
            break
        time.sleep(2)
    if r['status'] == 'error':
        sys.exit(f"AssemblyAI: {r.get('error')}")
    return [dict(text=w['text'], start=w['start'], end=w['end'], confidence=w.get('confidence'), speaker=w.get('speaker'))
            for w in r['words']]


if '--importar' in argv:
    words = from_file(os.path.abspath(argv[argv.index('--importar') + 1]))
elif '--whisper' in argv:
    words = from_whisper()
else:
    words = from_assemblyai()
json.dump(words, open(OUT, 'w'), ensure_ascii=False)
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
