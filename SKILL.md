---
name: sketch-plastilina
description: Sketch cómico vertical (9:16, 30-90 s) en 3D de plastilina, sobre cualquier tema que pida el usuario (no tiene que ser de IA), con personajes que hablan — humanos (incluido el propio usuario como avatar), animales, mascotas, productos u objetos, o IAs (Clawd, ChatGPT, Gemini, Meta AI, Grok, DeepSeek). Pregunta primero qué quiere el usuario (tema, protagonista, avatar, set, tono de humor — sarcástico, absurdo, tierno, telenovela, mockumentary… — y estilo) y propone conceptos con el formato de sketch que funciona — gancho, revelaciones que escalan, remate y giro final —; bocas con lip-sync, muchos cortes con micro push-in, subtítulos quemados y SFX a −14 LUFS. Las voces y tiempos salen de la vía que tenga el usuario (API o MCP de ElevenLabs, grabaciones propias, AssemblyAI, Whisper). Úsalo cuando el usuario diga «haz un sketch de plastilina sobre X», «un video animado 3D de plastilina», «sketch animado con personajes que hablan», «una escena 3D clay con diálogo», o pida un sketch con mascotas o productos que hablan. Motor propio en Blender 5.x (EEVEE, sin interfaz) en macOS, Linux y Windows; la primera vez revisa e instala lo necesario con scripts/doctor.py. NO es para clips generados con IA de video ni motion graphics.
---

# Sketch de plastilina

Un sketch de diálogo vertical en plastilina 3D sobre **el tema del usuario**, sea cual sea (trabajo, ventas, familia,
escuela, salud, mascotas, un producto; la IA es solo un tema más): una situación que su audiencia reconoce, contada en
revelaciones que escalan, con remate y giro final, en el tono de humor que elija. Cada personaje que habla tiene boca
sincronizada con su voz. Muchos cortes, closes y un micro push-in/out en cada plano.

El estilo de plastilina, la animación y la gramática de planos son el punto de partida, no una plantilla
cerrada: si el usuario quiere otra paleta, otra luz, otro set u otro tipo de personaje, se adapta. Nada del
elenco, las voces ni la historia de ejemplos anteriores se copia por defecto.

## Qué hay aquí

| Ruta | Qué es |
|---|---|
| `engine/scene.py` | Construye y renderiza un proyecto en Blender: `--retratos`, `--shotstills`, `--stills`, `--check`, `--anim`, `--vista`, `--motor-cycles --save --granja` (exportar para granja) |
| `scripts/render.py` | Render por tramos con guardia de disco + mezcla + subtítulos + ensamble (`draft`/`review`/`final`); `engine/render.sh` es el atajo de macOS |
| `scripts/doctor.py` · `scripts/entorno.py` | Revisión de la computadora (qué falta y cómo instalarlo) y lo que depende del sistema (Blender, llaves, fuentes, disco) |
| `engine/characters/` | `humans.py` (humano desde `cast.json`), `mascots.py` (mascotas de IA, mascota genérica por forma y color), `props.py` |
| `engine/perform.py` | Lee `blocking.json`: miradas automáticas, expresiones, gestos, escondites, acciones, poses inertes, props |
| `engine/cameras.py` | Planos desde `shots.json`: encuadre automático, dúo sobre el hombro, duelo, micro push en todos |
| `engine/sets/` | Sets intercambiables: `office_night`, `sala_juntas`, `cafe`. Uno nuevo se programa con la interfaz de `sets/__init__.py` |
| `engine/looks.py` | Luz `noche`, `dia`, `atardecer` |
| `scripts/` | `new_project`, `tts`, `voces`, `timeline`, `transcribe`, `auto_shots`, `sfx_gen`, `sfx_fetch`, `mix`, `subs`, `assemble`, `contact`, `recibo`, `pose_search`, `unir`, `flashback` |
| `templates/` | Proyecto neutro: un protagonista genérico y una mascota genérica, sin voces asignadas |

`SK=~/.claude/skills/sketch-plastilina` (o donde esté instalado este skill) ·
`B="$(python3 $SK/scripts/doctor.py --blender)"` (ruta de Blender en cualquier sistema; en Windows usa `py` en vez de
`python3`). Nunca imprimas llaves.

## 0. Preparar la computadora (obligatorio la primera vez en cada máquina)

Primero averigua **cómo va a hacer las voces y los tiempos de palabra**, según lo que tenga:

| Vía | Cuándo | Bandera de `doctor.py` |
|---|---|---|
| MCP de ElevenLabs conectado al agente | busca herramientas de texto a voz de ElevenLabs (p. ej. con ToolSearch «elevenlabs text to speech») | `--voces mcp` |
| API de ElevenLabs | el usuario tiene (o quiere crear) su llave | `--voces api` (default) |
| Voces grabadas por el usuario | quiere actuar él mismo los personajes | `--voces grabadas` |
| AssemblyAI (API) | tiene llave (hay capa gratis) | `--tiempos api` (default) |
| Transcripción del MCP de ElevenLabs (Scribe) u otra con tiempos por palabra | ya tiene esa herramienta | `--tiempos mcp` |
| Whisper local | sin llaves ni costo | `--tiempos whisper` |

Usa lo que ya tenga conectado antes de pedirle cuentas nuevas. Luego corre:
```bash
python3 $SK/scripts/doctor.py --voces <vía> --tiempos <vía>
```
Revisa sistema, Python 3.9+, numpy/scipy/pillow, ffmpeg (con libx264 y loudnorm), Blender 5.x, las llaves de la vía
elegida, espacio en disco (10 GB) y fuentes, y para cada cosa que falte imprime el comando exacto para su sistema
(Homebrew en macOS, winget en Windows, apt/snap en Linux). Si algo dice FALTA, **ayuda al usuario a instalarlo antes
de seguir**, explicando en una línea para qué sirve:

- **Paquetes de Python** (y `faster-whisper` si eligió Whisper): puedes correr tú el `pip install --user …`.
- **ffmpeg, Blender, Python, Homebrew**: propón el comando y córrelo solo con el «sí» del usuario. Si pide
  contraseña (`sudo`, instalador de Homebrew), pídele que lo corra él en su terminal.
- **Blender en otra carpeta**: `export BLENDER=/ruta/al/ejecutable` (o el equivalente en Windows).
- **Llaves** (solo si su vía las usa): crea tú `~/.config/sketch-plastilina/.env` con `ELEVENLABS_API_KEY=` y/o
  `ASSEMBLYAI_API_KEY=` vacíos y pídele que pegue sus llaves **en el archivo**, no en el chat. Si ya usa otro gestor
  de secretos (Doppler, 1Password…), basta con que las llaves estén en el entorno al correr los scripts.

Cuando todo diga OK, confirma una vez que de verdad funciona (≈1-3 min, no gasta créditos de voz):
```bash
python3 $SK/scripts/doctor.py --voces <vía> --tiempos <vía> --en-linea --prueba
```
Si la prueba de render falla, suele ser el driver de video (EEVEE necesita GPU/OpenGL 4.3). Dile qué esperar: un
sketch de 60 s tarda ~1-3 h en el render final (Mac M-series o PC con GPU dedicada) y ocupa 3-8 GB temporales; las
voces de ElevenLabs gastan créditos (cada regeneración también).

## Flujo con puertas de aprobación del usuario

**1. Preguntas → brief.** Antes de proponer nada, entiende qué quiere. Pregunta solo lo que no sepas (máx. 3-4
preguntas por ronda, con opciones recomendadas):

- **Tema y mensaje**: de qué trata, qué situación vive su audiencia, qué quiere que sienta o haga quien lo vea.
- **Protagonista / avatar**: el propio usuario (pídele 1-2 fotos y lo modelas desde ellas), un personaje neutro
  inventado, una mascota (por forma y colores) o un **producto** que habla (su producto, marca o empaque). No uses el
  avatar ni la voz de otra persona.
- **Elenco**: quién más aparece (compañeros, clientes, IAs, mascotas, productos de la competencia…).
- **Set**: oficina de noche, sala de juntas, cafetería, o uno nuevo (su tienda, su consultorio, su aula…).
- **Tono de humor**: ofrece 3-4 opciones que encajen con su tema (sarcástico/deadpan, absurdo, tierno, telenovela,
  mockumentary, suspenso cómico, cringe, parodia de comercial, fábula, terror cómico; tabla en
  `references/format.md`).
- **Estilo visual**: plastilina (default) de noche, de día o atardecer; colores de su marca. Si quiere otro estilo,
  se ajustan materiales, luz y paleta.
- **Idioma, duración y plataforma**: español por default; 30-90 s; Reels/TikTok/Shorts (9:16).

Resúmelo en un brief de 5-8 líneas y confírmalo.

**2. Concepto → 3 opciones.** Para cada una: premisa en una línea, tono, elenco, set, 3 revelaciones que escalan,
remate y giro. Si el usuario no eligió tono, varía el tono entre las opciones. Usa la estructura de `references/format.md` aplicada **a su tema** (no a otro video). **Espera a que elija.**

**3. Guion → aprobación.** Líneas con etiquetas de emoción y pausas (`references/guion.md`), frases que una persona
diría de verdad. Revisa coherencia interna (fechas, números, quién sabe qué). **No sigas sin aprobación.**

**4. Proyecto + look de personajes → aprobación ANTES de animar.**
```bash
python3 $SK/scripts/new_project.py <dir> --set office_night|sala_juntas|cafe
# reemplaza el elenco neutro de la plantilla: cast.json (references/personajes.md), guion.json, look.json
$B -b -P $SK/engine/scene.py -- --project <dir> --retratos --res 720     # -> <dir>/look/<PERSONAJE>.png
```
Enséñale los retratos (y un still del set si es nuevo). Ajusta hasta que diga que sí: si es su avatar, hasta que se
reconozca; si es un producto o una IA de marca, con su forma y colores reales (una clase nueva en `mascots.py` si la
forma genérica no basta, como se hizo con DeepSeek).

**5. Voces y tiempos** (con la vía del paso 0). Elige voces de **su** cuenta (`references/casting.md`):
```bash
# API de ElevenLabs
python3 $SK/scripts/tts.py <dir>                 # una toma por línea; caché: solo regenera lo que cambió
# MCP de ElevenLabs, otra herramienta o grabaciones propias
python3 $SK/scripts/tts.py <dir> --plan          # JSON con archivo, texto, voz y modelo de cada toma que falta
#   genera cada toma con la herramienta y guárdala en el «archivo» indicado (mp3/wav/m4a), luego:
python3 $SK/scripts/tts.py <dir> --registrar
python3 $SK/scripts/timeline.py <dir>            # diálogo + RMS por cuadro (pausa negativa = líneas encimadas)
# tiempos de palabra: AssemblyAI, o lo que dé su herramienta, o Whisper local
python3 $SK/scripts/transcribe.py <dir>                        # AssemblyAI
python3 $SK/scripts/transcribe.py <dir> --importar palabras.json  # Scribe del MCP de ElevenLabs u otra (lista de {text,start,end})
python3 $SK/scripts/transcribe.py <dir> --whisper              # local
```
Con el MCP, transcribe `audio/dialogo.wav`, guarda su respuesta en un JSON dentro del proyecto y pásala a
`--importar`. Escucha `audio/dialogo.wav`. Si una toma suena mal, regenera solo esa. Si una voz suena más baja que el
resto, súbela con `"voz_db": 6` en su personaje de `cast.json`.

**6. Puesta en escena.** Escribe `blocking.json` (`references/blocking.md`) anclado a líneas y palabras
(`"L12:presentación"`), y `shots.json` (`references/tomas.md`; borrador: `scripts/auto_shots.py <dir> --sobrescribir`).
Itera barato:
```bash
$B -b -P $SK/engine/scene.py -- --project <dir> --shotstills --check --res 360 --samples 8
python3 $SK/scripts/contact.py <dir>/test/shots <dir>/test/planos.jpg --cols 8
```
**Mira la hoja de contactos** (no te fíes del log) y corrige hasta que `--check` dé 0 problemas: mascota que atraviesa
un cuerpo, mano que atraviesa la cabeza (`scripts/pose_search.py`), plano tapado. Nadie debe mirar a algo pegado a su
propio cuerpo (gira loco): para mirar al regazo usa un punto un poco adelante.

**7. SFX + mezcla.** Cada SFX es un `audio/sfx/<nombre>.wav` que `sfx.json` coloca en el tiempo:
```bash
python3 $SK/scripts/sfx_gen.py <dir> pop1 "cartoon pop, short" --seg 0.6     # ElevenLabs Sound Effects (API)
# o el MCP de ElevenLabs (efecto de sonido) guardado como audio/sfx/<nombre>.wav, un .wav propio con licencia,
# o los sintetizados de mix.py ("synth:puerta", "synth:ding"…). Con el CLI de EditorBrain: sfx_fetch.py
```

**8. Revisión en baja → aprobación.** `python3 $SK/scripts/render.py <dir> draft` (360 px, rápido; para revisar
historia y tiempos basta) o `review` (720 px). Haz hoja de contactos del mp4 (`contact.py <dir>/draft.mp4 … --cada
0.5`), revísala tú (bocas, choques, cortes, subtítulos sincronizados y sin cruzar cortes) y mándala al usuario.
**No renderices el final sin su aprobación.**

**9. Final.** `python3 $SK/scripts/render.py <dir> final --ver v1` → `<dir>/<nombre>-v1.mp4` (1080×1920) +
`-preview.mp4` (<23 MB). Mide el primer tramo y dile cuánto va a tardar. Un solo Blender a la vez. Varias escenas o
un flashback: `unir.py` y `flashback.py` (`references/produccion.md`). Para una granja de render que solo acepta
Cycles y una sola cámara: `scene.py … --motor-cycles --save --granja` (ver producción). Después de verificar cada
versión borra tramos y pruebas superados.

## Reglas que no se negocian

- Paso 0 primero: sin `doctor.py` en OK no se gastan créditos ni se promete un video.
- Puertas de aprobación: brief → concepto → guion → look → revisión → final. Nunca render final sin «sí».
- El elenco, las voces y la historia salen de lo que pide el usuario. Nunca uses el avatar, la voz o la historia
  de otra persona por default; la plantilla es neutra a propósito.
- Todos los que hablan tienen boca y lip-sync; un bigote nunca tapa la boca.
- Ninguna mascota atraviesa un cuerpo; ninguna mano atraviesa la cabeza (`--check`, `pose_search.py`).
- Piel y ropa no se queman a blanco con la luz (el motor avisa si una ropa pasa de luminancia 0.80).
- Guion internamente coherente y con frases naturales.
- Un subtítulo nunca cruza un corte y va sincronizado palabra por palabra (`subs.py` lo hace solo).
- Render: un Blender a la vez, por tramos, guardia de disco, borrar renders superados.
- Si un objeto ES el chiste, constrúyelo como prop real (`scripts/recibo.py` como ejemplo); prefiere assets reales a
  texto flotante. Cada marca usa su propio logo y forma.
- Idioma del usuario (español por default) y sin emojis en subtítulos ni props, salvo que pida otra cosa.

## Referencias

`references/format.md` (anatomía del formato) · `guion.md` · `casting.md` (voces) · `personajes.md` (`cast.json`,
avatares, productos) · `blocking.md` (`blocking.json`) · `tomas.md` (`shots.json`, gramática de planos) ·
`produccion.md` (sets, render, mezcla, varias escenas, granja).
