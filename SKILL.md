---
name: sketch-plastilina
description: Sketch cómico vertical (9:16, 60-70 s) en 3D de plastilina con personajes que hablan y mascotas de IA (Clawd, ChatGPT, Gemini o una mascota nueva), con el formato aprobado de «A escondidas» — situación real con IA, revelaciones que escalan, remate y giro final; bocas con lip-sync a voces de ElevenLabs v4, muchos cortes con micro push-in, look de oficina de noche, subtítulos quemados y SFX a −14 LUFS. Úsalo cuando Santi diga «haz un sketch de plastilina sobre X», «video estilo A escondidas», «otro como A escondidas pero de…», «sketch animado 3D con personajes que hablan», «sketch de plastilina con Clawd», o pida una escena 3D clay con diálogo entre humanos e IAs. Motor propio en Blender 5.2 (EEVEE, sin interfaz). NO es para clips generados con IA (Higgsfield → corto-mascota) ni motion graphics (editorbrain-motion).
---

# Sketch de plastilina (formato «A escondidas»)

Un sketch de diálogo de ~60-70 s en plastilina 3D: una situación que la gente vive con la IA, contada en
revelaciones que escalan, con remate y un giro final. Cada personaje (incluidas las IAs) tiene boca sincronizada
con su voz. Muchos cortes, closes, un duelo de miradas solo entre IAs y un micro push-in/out en cada plano.

Ejemplo aprobado (léelo para calibrar): `/Users/santiagomunoz/editorharness/.local/style-explorations/20261021/a-escondidas/a-escondidas-v3.mp4`
(no lo modifiques; su código hecho a mano quedó en `assets/ejemplo-a-escondidas/`).

## Qué hay aquí

| Ruta | Qué es |
|---|---|
| `engine/scene.py` | Construye y renderiza un proyecto en Blender: `--retratos`, `--shotstills`, `--stills`, `--check`, `--anim`, `--vista` |
| `engine/render.sh` | Render por tramos con guardia de disco + mezcla + subtítulos + ensamble (`draft`/`review`/`final`) |
| `engine/characters/` | `humans.py` (humano genérico desde `cast.json`), `mascots.py` (Clawd, ChatGPT, Gemini, mascota genérica), `props.py` |
| `engine/perform.py` | Lee `blocking.json`: miradas automáticas, expresiones, gestos, escondites, acciones, props |
| `engine/cameras.py` | Planos desde `shots.json`: encuadre automático, dúo sobre el hombro, duelo, micro push en todos |
| `engine/sets/` | Sets intercambiables: `office_night` (el de «A escondidas»), `cafe`. Interfaz en `sets/__init__.py` |
| `engine/looks.py` | Luz `noche` (la aprobada) y `dia` |
| `scripts/` | `new_project`, `tts`, `voces`, `timeline`, `transcribe`, `auto_shots`, `sfx_fetch`, `mix`, `subs`, `assemble`, `contact`, `recibo`, `pose_search` |
| `templates/` | Plantillas de proyecto (Santi + Clawd en la oficina) |

`B=/Applications/Blender.app/Contents/MacOS/Blender` · `SK=~/.claude/skills/sketch-plastilina` ·
llaves: `doppler run --project editorbrain --config dev -- <comando>` (nunca imprimas llaves).

## Flujo con puertas de aprobación de Santi

**1. Concepto → 3 opciones.** Situaciones reales que la gente vive con la IA (usarla a escondidas, confesarle
cosas, celos entre IAs, que te delate, depender de ella). Para cada opción: premisa en una línea, elenco, set,
3 revelaciones que escalan, remate y giro. Lee `references/format.md`. **Espera a que Santi elija.**

**2. Guion → aprobación.** 26-32 líneas con etiquetas v4 y pausas (`references/guion.md`). Revisa coherencia
interna (en «A escondidas» hubo que corregir «mañana» vs «en cuatro minutos»). Elenco y voces:
`references/casting.md`. **No sigas sin aprobación.**

**3. Proyecto + look de personajes → aprobación ANTES de animar.**
```bash
python3 $SK/scripts/new_project.py <dir> --set office_night|cafe
# edita guion.json, cast.json (references/personajes.md), look.json
$B -b -P $SK/engine/scene.py -- --project <dir> --retratos --res 720     # -> <dir>/look/<PERSONAJE>.png
```
Enséñale los retratos (y un still del set si es nuevo). Ajusta hasta que diga que sí.

**4. Voces (ElevenLabs v4) y tiempos.**
```bash
doppler run --project editorbrain --config dev -- python3 $SK/scripts/tts.py <dir>        # una toma por línea
python3 $SK/scripts/timeline.py <dir>                                                     # diálogo + RMS por cuadro
doppler run --project editorbrain --config dev -- python3 $SK/scripts/transcribe.py <dir> # palabras de AssemblyAI
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

**6. SFX + mezcla.** Busca en el banco EditorBrain y baja con verificación SHA-256:
```bash
editorbrain sfx search --project dji-20261019-p2 --bank editorbrain-essentials-v1 --query "pop" --limit 6
python3 $SK/scripts/sfx_fetch.py <sound_id> pop1 <dir>       # -> audio/sfx/pop1.wav; plan en sfx.json
```
Nada de SFX de western en el duelo (Santi los vetó).

**7. Revisión en baja → aprobación.** `$SK/engine/render.sh <dir> draft` (360 px, rápido) o `review`
(720 px, 12 muestras). Haz hoja de contactos del mp4 (`contact.py <dir>/review-v1.mp4 … --cada 0.5`), revísala
tú (bocas se mueven, nadie se atraviesa, los cortes cortan, subtítulos legibles y sin cruzar cortes), y
manda el review a Santi. **No renderices el final sin su aprobación.**

**8. Final.** `VER=v1 $SK/engine/render.sh <dir> final` → `<dir>/<nombre>-v1.mp4` (1080×1920, 40 muestras)
+ `-preview.mp4` (<23 MB). Un solo Blender a la vez; revisa disco antes (`df -h /System/Volumes/Data`). Después
de verificar cada versión borra tramos y pruebas superados (`references/produccion.md`).

Si es contenido de Horizontes IA, actualiza la ficha del video en Obsidian (`status`, `skill_siguiente`).

## Reglas que no se negocian (lecciones de «A escondidas»)

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
- Identidad de Santi: español, sin emojis (ni en subtítulos ni en props).

## Referencias

`references/format.md` (anatomía del formato) · `guion.md` · `casting.md` (voces e IDs) · `personajes.md`
(`cast.json`) · `blocking.md` (`blocking.json`) · `tomas.md` (`shots.json`, gramática de planos) ·
`produccion.md` (render, mezcla, disco, límites conocidos).
