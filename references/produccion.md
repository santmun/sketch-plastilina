# Producción: render, audio, disco y lecciones

## Estructura del proyecto

```
<dir>/ guion.json cast.json blocking.json shots.json look.json sfx.json [recibo.json]
       audio/lineas/NN_QUIEN.mp3 (+ NN.wav recortadas, manifest.json)  audio/dialogo.wav  audio/palabras.json
       audio/sfx/<nombre>.wav (+ sfx-ids.jsonl)  audio/mezcla.wav
       build/timeline.json  shots_resolved.json  eventos.json  check.json  sfx-plan.json  [recibo.png]
       look/<PERSONAJE>.png   test/   renders/ (tramos, subs, logs)   draft.mp4 / review-vN.mp4 / <nombre>-vN.mp4
```
`look.json`: `set` (`office_night`, `cafe`), `luz` (`noche`, `dia`), `dof`, `exposicion`, `entrada`, `cola`,
`ambiente` (tono de sala de la mezcla), `set_params` (textos del set: diapositiva, menú, letrero, taza),
`mundo`, `mundo_fuerza`, `bruma`, `luz_ambiente` (W de la luz general), `luz_personajes` (multiplica claves y contraluces).

## Render

```bash
df -h /System/Volumes/Data                      # si hay < ~8 GB, libera antes
$SK/engine/render.sh <dir> draft                # 360x640, 4 muestras: revisión de puesta en escena
$SK/engine/render.sh <dir> review               # 720x1280, 12 muestras -> review-v1.mp4 (<23 MB) para Santi
VER=v1 $SK/engine/render.sh <dir> final         # 1080x1920, 40 muestras -> <nombre>-v1.mp4 + -preview.mp4
```
- Renderiza por tramos de 240 cuadros (`STEP`), **un solo Blender a la vez**. Antes de cada tramo revisa el disco;
  si baja de `MINFREE` (8 GB) espera hasta 40 min y luego se detiene. Los tramos que ya existen se saltan
  (`FORCE=1` para rehacer). Cada tramo es un proceso nuevo: todo lo aleatorio está sembrado (no hay saltos entre tramos).
- Referencia de tiempos (M-series, café de prueba): 360 px / 4 muestras ≈ 0.2 s por cuadro. El final a 1080/40 es
  mucho más lento: mide el primer tramo y estima antes de lanzar 70 s completos.
- `render.sh` corre `mix.py` antes y `assemble.py` después (subtítulos PNG + mezcla).
- **Disco**: se llena rápido. Después de verificar cada versión, borra lo superado: `renders/c*_*.mp4` de
  resoluciones viejas, `renders/subs_*`, `renders/log_*`, `test/`, versiones `review` anteriores. Nunca borres el
  final aprobado ni el audio. Un solo render por máquina a la vez.

## Audio

- Voces: `tts.py` (ElevenLabs `eleven_v4`, caché por línea; `--solo`, `--forzar`, `--modelo`).
- `timeline.py`: recorta silencios de cada toma, arma `dialogo.wav` con las pausas del guion, mide RMS por cuadro
  (24 fps) → `build/timeline.json` (`lineas` con `start`/`end`, `rms`, `t_end`).
- `transcribe.py`: AssemblyAI en español → `audio/palabras.json` (ms) y compara con el guion (marca líneas raras).
- Lip-sync (automático): abertura por la envolvente RMS normalizada por línea, redondez en o/u, ancho en i,
  cierre en m/b/p (f/v a medias), menos abertura al susurrar.
- `mix.py`: diálogo + tono de sala sintetizado según el set + SFX de `sfx.json` → **−14 LUFS**, pico ≤ −1.5 dBTP.
  SFX del banco: `editorbrain sfx search … --query`, `sfx_fetch.py <id> <nombre> <dir>` (verifica SHA-256, no guarda
  URLs firmadas). Sintetizados: `synth:puerta`, `impresora`, `caja_registradora`, `papel`, `golpe`, `ding`, `cajon`.
  `corta_en` deja silencio limpio antes de un susurro o remate. `build/eventos.json` lista saltos y apariciones
  para colocar pops y whooshes. **Sin silbido ni twang de western en el duelo** (Santi no lo quiso).

## Revisión (antes de mandar cualquier cosa a Santi)

1. `scene.py --check` en 0 problemas (o justificados: el gafete rozando a la mascota al aterrizar, vidrio a propósito).
2. Hoja de contactos del mp4 cada 0.25-0.5 s **y mírala**: bocas abiertas/cerradas con la voz, nadie atravesado,
   un plano distinto en cada corte, subtítulos dentro de cuadro y sin cruzar cortes, nada quemado a blanco.
3. Escucha la mezcla completa una vez (picos de SFX, silencios intencionales).

## Lecciones de «A escondidas» (convertidas en reglas del motor)

| Lección | Dónde quedó |
|---|---|
| Mano a la cabeza atravesaba la cabeza | gestos con punto de paso + `--check` + `pose_search.py` |
| ChatGPT en el hombro sin hundirse | anclajes `PERSONAJE.hombro_izq` + 2 cm de holgura + `--check` |
| Clawd 22.5 % más alto y cambiando de escondite | `alto: 1.225`; anclajes del set y `lugar` en blocking |
| Piel y camiseta crema se quemaban a blanco | aviso de luminancia en el build; camiseta `#D6C7A8` |
| «Mañana» vs «en cuatro minutos» | revisión de coherencia en guion.md |
| SFX de western en el duelo, vetado | fuera del banco sintetizado; regla en tomas.md |
| Disco lleno a media producción | tramos + `MINFREE` + borrar lo superado |
| Subtítulo encima de un corte | `subs.py` parte en cada corte |
| Objeto chiste = prop real (recibo) | `recibo.py` + `recibo` de ChatGPT |

## Agregar un set nuevo

Copia `engine/sets/cafe.py`: construye la maqueta con `sets/common.py` (cartón pluma + plastilina) y devuelve
`seats`, `anchors` (escondites y marcas), `props` (objetos animables), `probes`, `looks` (`noche`/`dia`: luces
prácticas del set) y `publico`. Prueba con `--shotstills` y una hoja de contactos antes de usarlo.

## Límites conocidos

- La postura (sentado/parado) es fija por personaje; no se levanta de la silla en cámara.
- Caminar es un ciclo simple; no hay escaleras ni obstáculos.
- El encuadre automático evita muebles en el rayo central, no en los bordes: revisa los generales.
- Interacción física (agarrar a la mascota, pasarse objetos) se resuelve con anclajes y poses, no con física.
- Una sola envolvente RMS: las líneas no pueden encimarse.
