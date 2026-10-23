# sfx_fetch.py — baja un SFX del banco EditorBrain con verificación SHA-256 (no guarda URLs firmadas).
#   buscar:  editorbrain sfx search --project dji-20261019-p2 --bank editorbrain-essentials-v1 --query "pop" --limit 6
#   bajar:   python3 sfx_fetch.py <sound_id> <nombre> <proyecto>   -> <proyecto>/audio/sfx/<nombre>.wav (+ sfx-ids.jsonl)
import hashlib, json, os, subprocess, sys, urllib.request

sid, name, P = sys.argv[1], sys.argv[2], os.path.abspath(sys.argv[3])
r = subprocess.run(['editorbrain', 'sfx', 'get', sid, '--project', 'dji-20261019-p2', '--bank', 'editorbrain-essentials-v1',
                    '--catalog-sha256', '06d734fa78e777b476c42056f9fe4960144c7dcb2b3da49e7ee43c5f1f130166'],
                   capture_output=True, text=True)
if r.returncode != 0:
    sys.exit(f'editorbrain sfx get falló: {r.stderr.strip()[:400]}')
d = json.loads(r.stdout)
req = urllib.request.Request(d['asset']['url'], headers={'User-Agent': 'Mozilla/5.0'})
data = urllib.request.urlopen(req, timeout=60).read()
h = hashlib.sha256(data).hexdigest()
assert h == d['asset']['sha256'] == d['entry']['sha256'], 'hash no coincide'
os.makedirs(os.path.join(P, 'audio', 'sfx'), exist_ok=True)
out = os.path.join(P, 'audio', 'sfx', f'{name}.wav')
tmp = out + '.src'
open(tmp, 'wb').write(data)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-ac', '1', '-ar', '48000', out], check=True)
os.remove(tmp)
rec = dict(id=sid, nombre=name, banco_nombre=d['entry']['name'], sha256=h, segundos=d['entry'].get('durationSeconds'),
           archivo=f'audio/sfx/{name}.wav')
with open(os.path.join(P, 'audio', 'sfx', 'sfx-ids.jsonl'), 'a') as fh:
    fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
print(json.dumps(rec, ensure_ascii=False))
