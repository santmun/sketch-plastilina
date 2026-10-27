<div align="center">

# Sketch de plastilina

**Sketches cómicos en 3D de plastilina, con personajes que hablan y mascotas de IA, a partir de un tema.**

Un skill de Claude Code con motor propio en Blender. Le das un tema y te entrega un video vertical
de 60-70 s: guion, voces, lip-sync, puesta en escena, cámaras, subtítulos, SFX y mezcla.

<img src="docs/img/hero.jpg" alt="Planos de «A escondidas»: Santi, la presentación, el jefe, ChatGPT en el hombro y Gemini con Mariana" width="100%">

</div>

---

## El formato

Nace de **«A escondidas»**, un sketch de 70 s. Santi usa IA a escondidas en la oficina de noche y Clawd
lo cubre desde distintos escondites. El ChatGPT del jefe, sentado en su hombro, lo delata con un recibo
de «cuarenta y siete» mensajes. Al final, Gemini le susurra algo a Mariana.

<table>
<tr>
<td width="34%" valign="top"><img src="docs/img/demo.gif" alt="Fragmentos de «A escondidas» en movimiento" width="100%"></td>
<td valign="top">

**Por qué funciona**

- **Hook en los primeros 2 s**: una situación que la gente ya vive con la IA.
- **Revelaciones que escalan**: cada línea sube la apuesta.
- **Remate y giro final**: la última escena reabre el chiste con otro personaje.
- **Todos hablan**, incluidas las IAs, con boca sincronizada a su propia voz.
- **Muchos cortes**: closes, planos sobre el hombro, un duelo de miradas solo entre IAs
  y un micro push-in/out en cada plano.
- **Look de oficina de noche**: luz de lámpara cálida contra ciudad fría.

El skill separa lo que hizo funcionar ese video de lo que era propio de él. Así, el tema,
los personajes, las voces y el escenario cambian por proyecto.

</td>
</tr>
</table>

## Qué puedes cambiar

| | Cómo |
|---|---|
| **Tema e historia** | Guion de 26-32 líneas con etiquetas de emoción de ElevenLabs v4 (`guion.json`) |
| **Personajes humanos** | Cara, piel, pelo, ropa, complexión y accesorios desde `cast.json` |
| **Mascotas de IA** | Clawd, ChatGPT (con su recibo), Gemini o una mascota nueva por forma y color |
| **Voces** | Una voz de ElevenLabs por personaje, elegida para que se distingan entre sí |
| **Actuación** | Miradas, expresiones, gestos y escondites anclados a líneas y palabras (`blocking.json`) |
| **Cámara** | Planos desde `shots.json`, con encuadre automático y micro push en todos |
| **Escenario y luz** | Sets intercambiables (`office_night`, `cafe`) y luz de noche o de día |

<img src="docs/img/caras.jpg" alt="Tres opciones de cara para el protagonista" width="100%">

<sub>Opciones de cara del protagonista antes de animar. La «cara A» facetada quedó como cara por defecto.</sub>

## Lip-sync para todos

La boca de cada personaje sigue el volumen de su voz, cuadro por cuadro. Abre en las vocales y
cierra en las m, b y p, con los tiempos de cada palabra que da AssemblyAI. Funciona igual para un
humano que para una mascota.

<img src="docs/img/bocas.jpg" alt="Formas de boca de los personajes durante el diálogo" width="100%">

## Gramática de planos

<img src="docs/img/planos-clave.jpg" alt="Planos clave de la oficina de noche" width="100%">

El duelo de IAs es solo de closes de las mascotas, sin humanos en cuadro:

<img src="docs/img/duelo.jpg" alt="Duelo de miradas entre Clawd y ChatGPT" width="100%">

## Cuando el objeto es el chiste, es un prop real

El recibo de «47 mensajes» que ChatGPT saca no es texto flotante. Es un objeto 3D con su textura,
generado con `scripts/recibo.py`.

<p align="center"><img src="docs/img/recibo.jpg" alt="Recibo digital de ChatGPT como prop 3D" width="420"></p>

## Probado con otro tema

Para comprobar que el motor no depende de «A escondidas», se hizo una prueba con un tema, un elenco
y un set distintos. Un chef le pregunta a «Bollo», su mascota-pan, quién sabe que la receta no era de
la abuela. Son 4 líneas en una cafetería nueva, con voces, tiempos, SFX y mezcla reales. El borrador es
de 360 px.

<img src="docs/img/prueba-cafe.jpg" alt="Prueba del motor: un chef y la mascota Bollo en una cafetería" width="100%">

## Cómo se produce

```mermaid
flowchart LR
  A[Tema] --> B[3 conceptos]
  B -->|tú eliges| C[Guion]
  C -->|aprobado| D[Retratos de look]
  D -->|aprobado| E[Voces ElevenLabs v4]
  E --> F[Tiempos AssemblyAI + RMS]
  F --> G[Blocking + planos]
  G --> H[Stills + --check de choques]
  H --> I[SFX + mezcla −14 LUFS]
  I --> J[Review 720 px]
  J -->|aprobado| K[Final 1080×1920]
```

Cada flecha marcada exige aprobación. Nada se renderiza en alta sin un «sí».

```bash
SK=~/.claude/skills/sketch-plastilina
python3 $SK/scripts/doctor.py                      # ¿tengo todo? (la primera vez)
B="$(python3 $SK/scripts/doctor.py --blender)"

python3 $SK/scripts/new_project.py mi-sketch --set cafe
"$B" -b -P $SK/engine/scene.py -- --project mi-sketch --retratos --res 720
python3 $SK/scripts/tts.py mi-sketch
python3 $SK/scripts/timeline.py mi-sketch
python3 $SK/scripts/transcribe.py mi-sketch
"$B" -b -P $SK/engine/scene.py -- --project mi-sketch --shotstills --check --res 360 --samples 8
python3 $SK/scripts/render.py mi-sketch review
python3 $SK/scripts/render.py mi-sketch final --ver v1
```
En Windows usa `py` en lugar de `python3`.

En la práctica no corres esto a mano. Le dices a Claude Code *«haz un sketch de plastilina sobre X»*
y el skill sigue el flujo, deteniéndose en cada aprobación.

## Estructura

```
SKILL.md              instrucciones del flujo para Claude
engine/
  scene.py            construye y renderiza un proyecto en Blender (retratos, stills, check, anim)
  render.sh           atajo de macOS para scripts/render.py
  characters/         humanos genéricos, mascotas (Clawd, ChatGPT, Gemini, genérica) y props
  perform.py          lee blocking.json: miradas, expresiones, gestos, escondites
  cameras.py          planos desde shots.json, dúo sobre el hombro, duelo, micro push
  sets/               office_night, cafe (interfaz para agregar más)
  looks.py            luz de noche y de día
  clay.py · rig.py    materiales de plastilina y rig
scripts/              doctor (revisa la computadora), entorno, render, new_project, tts, voces, timeline,
                      transcribe, auto_shots, sfx_gen, sfx_fetch, mix, subs, assemble, contact, recibo, pose_search
templates/            plantillas de proyecto
references/           formato, guion, casting, personajes, blocking, tomas, producción
assets/               guion y código original de «A escondidas» como referencia
```

## Requisitos e instalación

Funciona en **macOS**, **Linux** y **Windows 10/11**. Necesitas:

| Qué | Para qué | Cómo instalarlo |
|---|---|---|
| **Blender 5.x** (probado en 5.2) | el motor 3D, sin interfaz | macOS `brew install --cask blender` · Windows `winget install BlenderFoundation.Blender` · Linux `sudo snap install blender --classic` · o [blender.org](https://www.blender.org/download/) |
| **Python 3.9+** con numpy, scipy y pillow | guion, audio, subtítulos | `python3 -m pip install --user numpy scipy pillow` |
| **ffmpeg** (con libx264) | video y mezcla | macOS `brew install ffmpeg` · Windows `winget install Gyan.FFmpeg` · Linux `sudo apt install ffmpeg` |
| Llave de **ElevenLabs** | las voces (gasta créditos) | [elevenlabs.io → API keys](https://elevenlabs.io/app/settings/api-keys) |
| Llave de **AssemblyAI** | los tiempos de cada palabra (lip-sync) | [assemblyai.com → API keys](https://www.assemblyai.com/app/api-keys), tiene capa gratis |
| ~10 GB libres y una GPU | render (1-3 h el final de 70 s) | Mac M-series o PC con tarjeta de video |

Las llaves van en `~/.config/sketch-plastilina/.env`:
```
ELEVENLABS_API_KEY=...
ASSEMBLYAI_API_KEY=...
```
(o como variables de entorno). Ningún script las imprime ni las guarda en el proyecto.

Para revisar todo de una vez, y saber exactamente qué te falta y cómo instalarlo en tu sistema:
```bash
python3 ~/.claude/skills/sketch-plastilina/scripts/doctor.py
python3 ~/.claude/skills/sketch-plastilina/scripts/doctor.py --en-linea --prueba   # prueba las llaves y un render real
```
Claude Code corre este chequeo solo la primera vez y te ayuda a instalar lo que falte.

**Voces**: los IDs de las plantillas son de la cuenta de Santi (incluida su voz clonada). Con tu cuenta, elige las
tuyas con `python3 scripts/voces.py --es` y ponlas en `cast.json`.

**Efectos de sonido**: `scripts/sfx_gen.py` los genera con tu llave de ElevenLabs, o usa tus propios `.wav`.
El banco de EditorBrain (`sfx_fetch.py`) es opcional.

## Límites conocidos

- Cada set nuevo (una clínica, un aula) se programa en Python. Lo mismo una IA de marca con su logo real.
- La postura de cada personaje, sentado o parado, es fija durante el sketch, y caminar es un ciclo simple.
- Las líneas pueden encimarse con una pausa negativa (risas); los subtítulos de risas se omiten.
- El ajuste automático de cámara solo esquiva lo que tapa el centro del encuadre.

---

<div align="center"><sub>Horizontes IA</sub></div>
