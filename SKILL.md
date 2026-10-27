---
name: sketch-plastilina
description: Sketch cómico vertical (9:16, 60-70 s) en 3D de plastilina con personajes que hablan y mascotas de IA (Clawd, ChatGPT, Gemini o una mascota nueva), con el formato aprobado de «A escondidas» — situación real con IA, revelaciones que escalan, remate y giro final; bocas con lip-sync a voces de ElevenLabs v4, muchos cortes con micro push-in, look de oficina de noche, subtítulos quemados y SFX a −14 LUFS. Úsalo cuando el usuario diga «haz un sketch de plastilina sobre X», «video estilo A escondidas», «otro como A escondidas pero de…», «sketch animado 3D con personajes que hablan», «sketch de plastilina con Clawd», o pida una escena 3D clay con diálogo entre humanos e IAs. Motor propio en Blender 5.x (EEVEE, sin interfaz) que corre en macOS, Linux y Windows; la primera vez revisa e instala lo necesario con scripts/doctor.py. NO es para clips generados con IA (Higgsfield → corto-mascota) ni motion graphics (editorbrain-motion).
---

# Sketch de plastilina (formato «A escondidas»)

Un sketch de diálogo de ~60-70 s en plastilina 3D: una situación que la gente vive con la IA, contada en
revelaciones que escalan, con remate y un giro final. Cada personaje (incluidas las IAs) tiene boca sincronizada
con su voz. Muchos cortes, closes, un duelo de miradas solo entre IAs y un micro push-in/out en cada plano.

Ejemplo de referencia: `docs/img/demo.gif` y `docs/img/hero.jpg`; el código hecho a mano de «A escondidas» quedó en
`assets/ejemplo-a-escondidas/`. (En la Mac de Santi el video aprobado está en
`~/editorharness/.local/style-explorations/20261021/a-escondidas/a-escondidas-v3.mp4`; no lo modifiques.)

## Qué hay aquí

| Ruta | Qué es |
|---|---|
| `engine/scene.py` | Construye y renderiza un proyecto en Blender: `--retratos`, `--shotstills`, `--stills`, `--check`, `--anim`, `--vista` |
| `scripts/render.py` | Render por tramos con guardia de disco + mezcla + subtítulos + ensamble (`draft`/`review`/`final`); `engine/render.sh` es el atajo de macOS |
| `scripts/doctor.py` · `scripts/entorno.py` | Revisión de la computadora (qué falta y cómo instalarlo) y lo que depende del sistema (Blender, llaves, fuentes, disco) |
| `engine/characters/` | `humans.py` (humano genérico desde `cast.json`), `mascots.py` (Clawd, ChatGPT, Gemini, mascota genérica), `props.py` |
| `engine/perform.py` | Lee `blocking.json`: miradas automáticas, expresiones, gestos, escondites, acciones, props |
| `engine/cameras.py` | Planos desde `shots.json`: encuadre automático, dúo sobre el hombro, duelo, micro push en todos |
| `engine/sets/` | Sets intercambiables: `office_night` (el de «A escondidas»), `sala_juntas`, `cafe`. Interfaz en `sets/__init__.py` |
| `engine/looks.py` | Luz `noche` (la aprobada) y `dia` |
| `scripts/` | `new_project`, `tts`, `voces`, `timeline`, `transcribe`, `auto_shots`, `sfx_gen`, `sfx_fetch`, `mix`, `subs`, `assemble`, `contact`, `recibo`, `pose_search` |
| `templates/` | Plantillas de proyecto (Santi + Clawd en la oficina) |

`SK=~/.claude/skills/sketch-plastilina` (o donde esté instalado este skill) ·
`B="$(python3 $SK/scripts/doctor.py --blender)"` (ruta de Blender en cualquier sistema; en Windows usa `py` en vez de
`python3`) · llaves: `ELEVENLABS_API_KEY` y `ASSEMBLYAI_API_KEY` en el entorno o en `~/.config/sketch-plastilina/.env`
(Santi las tiene en Doppler: antepone `doppler run --project editorbrain --config dev --`). Nunca imprimas llaves.

## 0. Preparar la computadora (obligatorio la primera vez en cada máquina)

Antes de proponer conceptos o gastar créditos, corre:
```bash
python3 $SK/scripts/doctor.py
```
Revisa sistema, Python 3.9+, numpy/scipy/pillow, ffmpeg (con libx264 y loudnorm), Blender 5.x, las dos llaves,
espacio en disco (10 GB) y fuentes, y para cada cosa que falte imprime el comando exacto para su sistema
(Homebrew en macOS, winget en Windows, apt/snap en Linux). Si algo dice FALTA, **ayuda al usuario a instalarlo
antes de seguir**, explicando en una línea para qué sirve:

- **Paquetes de Python**: puedes correr tú el `pip install --user …` que sugiere.
- **ffmpeg, Blender, Python, Homebrew**: propón el comando y córrelo solo con el «sí» del usuario. Si pide
  contraseña (`sudo`, instalador de Homebrew), pídele que lo corra él en su terminal.
- **Blender instalado en otra carpeta**: `export BLENDER=/ruta/al/ejecutable` (o el equivalente en Windows).
- **Llaves**: guíalo a crear cuenta en ElevenLabs (voces; necesita créditos) y AssemblyAI (tiempos de palabra;
  tiene capa gratis). Crea tú `~/.config/sketch-plastilina/.env` con `ELEVENLABS_API_KEY=` y `ASSEMBLYAI_API_KEY=`
  vacíos y pídele que pegue sus llaves **en el archivo**, no en el chat. Nunca las leas en voz alta ni las imprimas.

Cuando todo diga OK, confirma una vez que de verdad funciona (≈1-3 min, gasta 0 créditos de voz):
```bash
python3 $SK/scripts/doctor.py --en-linea --prueba     # prueba las llaves y hace un render real chiquito en EEVEE
```
Si la prueba de render falla, suele ser el driver de video (EEVEE necesita GPU/OpenGL 4.3): actualízalo o usa otra
máquina. Expectativas que conviene decirle: un sketch de 60-70 s tarda ~1-3 h en el render final (Mac M-series o PC con
GPU dedicada) y ocupa 3-8 GB temporales; las voces gastan créditos de ElevenLabs (cada regeneración también).

**Voces de otra cuenta**: los IDs de `references/casting.md` y de `templates/cast.json` son de la cuenta de Santi (incluye
su voz clonada «Santiago»). Con otra cuenta, elige voces propias con `python3 $SK/scripts/voces.py --es` (o agrégalas
desde la Voice Library) y cámbialas en `cast.json` antes del paso 4. `tts.py` avisa si una voz no está en la cuenta.

## Flujo con puertas de aprobación del usuario

**1. Concepto → 3 opciones.** Situaciones reales que la gente vive con la IA (usarla a escondidas, confesarle
cosas, celos entre IAs, que te delate, depender de ella). Para cada opción: premisa en una línea, elenco, set,
3 revelaciones que escalan, remate y giro. Lee `references/format.md`. **Espera a que el usuario elija.**

**2. Guion → aprobación.** 26-32 líneas con etiquetas v4 y pausas (`references/guion.md`). Revisa coherencia
interna (en «A escondidas» hubo que corregir «mañana» vs «en cuatro minutos»). Elenco y voces:
`references/casting.md`. **No sigas sin aprobación.**

**3. Proyecto + look de personajes → aprobación ANTES de animar.**
```bash
python3 $SK/scripts/new_project.py <dir> --set office_night|cafe
# edita guion.json, cast.json (references/personajes.md), look.json
$B -b -P $SK/engine/scene.py -- --project <dir> --retratos --res 720     # -> <dir>/look/<PERSONAJE>.png
```
Enséñale los retratos (y un still del set si es nuevo). Ajusta hasta que diga que sí. Si el usuario quiere aparecer él
mismo, ajusta `cast.json` (pelo, piel, ropa, accesorios) a partir de una foto suya hasta que se reconozca.

**4. Voces (ElevenLabs v4) y tiempos.**
```bash
python3 $SK/scripts/tts.py <dir>          # una toma por línea (ElevenLabs; caché: solo regenera lo que cambió)
python3 $SK/scripts/timeline.py <dir>     # diálogo + RMS por cuadro (pausa negativa = encima la línea, p. ej. risas)
python3 $SK/scripts/transcribe.py <dir>   # palabras de AssemblyAI
```
Escucha `audio/dialogo.wav`. Si una toma suena mal, regenera solo esa (`--solo N --forzar`).

**5. Puesta en escena.** Escribe `blocking.json` (`references/blocking.md`) anclado a líneas y palabras
(`"L12:presentación"`), y `shots.json` (`references/tomas.md`; borrador: `scripts/auto_shots.py <dir> --sobrescribir`).
Itera barato:
```bash
$B -b -P $SK/engine/scene.py -- --project <dir> --shotstills --check --res 360 --samples 8
python3 $SK/scripts/contact.py <dir>/test/shots <dir>/test/planos.jpg --cols 8
```
**Mira la hoja de contactos** (no te fíes del log) y corrige hasta que `--check` dé 0 problemas:
mascota que atraviesa un cuerpo, mano que atraviesa la cabeza (`scripts/pose_search.py` encuentra una pose
sin choques y la guarda como gesto propio), plano tapado.

**6. SFX + mezcla.** Cada SFX es un `audio/sfx/<nombre>.wav` que `sfx.json` coloca en el tiempo. Tres fuentes:
```bash
python3 $SK/scripts/sfx_gen.py <dir> pop1 "cartoon pop, short" --seg 0.6     # ElevenLabs Sound Effects (cualquiera)
# o un .wav propio con licencia en audio/sfx/<nombre>.wav, o los sintetizados de mix.py ("synth:puerta", "synth:ding"…)
# con el CLI de EditorBrain (Santi): editorbrain sfx search --project dji-20261019-p2 --bank editorbrain-essentials-v1 \
#   --query "pop" --limit 6   y   python3 $SK/scripts/sfx_fetch.py <sound_id> pop1 <dir>
```
Nada de SFX de western en el duelo (no funcionaron en «A escondidas»).

**7. Revisión en baja → aprobación.** `python3 $SK/scripts/render.py <dir> draft` (360 px, rápido) o `review`
(720 px, 12 muestras). Haz hoja de contactos del mp4 (`contact.py <dir>/review-v1.mp4 … --cada 0.5`), revísala
tú (bocas se mueven, nadie se atraviesa, los cortes cortan, subtítulos legibles y sin cruzar cortes), y
manda el review al usuario. **No renderices el final sin su aprobación.**

**8. Final.** `python3 $SK/scripts/render.py <dir> final --ver v1` → `<dir>/<nombre>-v1.mp4` (1080×1920, 40 muestras)
+ `-preview.mp4` (<23 MB). Mide el primer tramo y dile al usuario cuánto va a tardar. Un solo Blender a la vez; el
script revisa el disco antes de cada tramo. Después de verificar cada versión borra tramos y pruebas superados
(`references/produccion.md`). En macOS sigue funcionando el atajo `$SK/engine/render.sh <dir> final`.

Si el usuario es Santi y es contenido de Horizontes IA, actualiza la ficha del video en Obsidian (`status`,
`skill_siguiente`).

## Reglas que no se negocian (lecciones de «A escondidas»)

- Paso 0 primero: sin `doctor.py` en OK no se gastan créditos ni se promete un video.
- Puertas de aprobación: concepto → guion → look → review → final. Nunca render final sin «sí».
- Todos los que hablan tienen boca y lip-sync; un bigote nunca tapa la boca.
- Ninguna mascota atraviesa un cuerpo (ChatGPT se sentó en el hombro del jefe sin hundirse). Ninguna mano
  atraviesa la cabeza: corre `--check` y usa `pose_search.py` para gestos junto a la cara.
- Clawd es 22.5 % más alto que el ref (`alto: 1.225`) y cambia de escondite con la historia
  (regazo → escritorio → pantalla → junto al café → cajón con una pata afuera).
- Piel y ropa no se queman a blanco con la lámpara: la camiseta crema bajó de `#EFE4CF` a `#D6C7A8`
  (el motor avisa si una ropa pasa de luminancia 0.80).
- Guion internamente coherente (fechas, números, quién sabe qué).
- Un subtítulo nunca cruza un corte (`subs.py` lo parte solo).
- Render: un Blender a la vez, por tramos, guardia de disco (`MINFREE=8`), borrar renders superados.
- Si un objeto ES el chiste (el recibo de 47 mensajes), constrúyelo como prop real (`scripts/recibo.py`);
  prefiere assets reales a texto flotante.
- Español y sin emojis (ni en subtítulos ni en props), salvo que el usuario pida otra cosa.

## Referencias

`references/format.md` (anatomía del formato) · `guion.md` · `casting.md` (voces e IDs) · `personajes.md`
(`cast.json`) · `blocking.md` (`blocking.json`) · `tomas.md` (`shots.json`, gramática de planos) ·
`produccion.md` (render, mezcla, disco, límites conocidos).
