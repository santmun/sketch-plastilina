# new_project.py — crea un proyecto de sketch con plantillas listas para editar.
#   python3 new_project.py <carpeta> [--set office_night|cafe]
import json, os, shutil, sys

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.abspath(sys.argv[1])
st = sys.argv[sys.argv.index('--set') + 1] if '--set' in sys.argv else 'office_night'
if os.path.exists(os.path.join(P, 'guion.json')):
    sys.exit(f'{P} ya tiene un proyecto')
for d in ('audio/lineas', 'audio/sfx', 'build', 'look', 'renders', 'test'):
    os.makedirs(os.path.join(P, d), exist_ok=True)
for f in ('guion.json', 'cast.json', 'blocking.json', 'shots.json', 'look.json', 'sfx.json'):
    shutil.copy(os.path.join(SK, 'templates', f), os.path.join(P, f))
look = json.load(open(os.path.join(P, 'look.json')))
look['set'] = st
json.dump(look, open(os.path.join(P, 'look.json'), 'w'), ensure_ascii=False, indent=1)
print(f'''proyecto creado en {P} (set {st})
siguiente:
  1. edita guion.json + cast.json (voces y look de personajes)  -> aprobación del guion
  2. retratos:  Blender -b -P {SK}/engine/scene.py -- --project {P} --retratos      -> aprobación del look
  3. voces:     doppler run --project editorbrain --config dev -- python3 {SK}/scripts/tts.py {P}
  4. tiempos:   python3 {SK}/scripts/timeline.py {P}  &&  doppler run ... python3 {SK}/scripts/transcribe.py {P}
  5. blocking.json + shots.json (borrador: python3 {SK}/scripts/auto_shots.py {P} --sobrescribir)
  6. revisión:  {SK}/engine/render.sh {P} draft   (o review)  -> aprobación
  7. final:     {SK}/engine/render.sh {P} final   (solo con aprobación)''')
