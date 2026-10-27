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
python3 $SK/scripts/doctor.py                     # disco libre, Blender, ffmpeg (si hay < ~8 GB, libera antes)
python3 $SK/scripts/render.py <dir> draft         # 360x640, 4 muestras: revisión de puesta en escena
python3 $SK/scripts/render.py <dir> review        # 720x1280, 12 muestras -> review-v1.mp4 (<23 MB) para aprobar
python3 $SK/scripts/render.py <dir> final --ver v1   # 1080x1920, 40 muestras -> <nombre>-v1.mp4 + -preview.mp4
```
- Renderiza por tramos de 240 cuadros (`STEP`), **un solo Blender a la vez**. Antes de cada tramo revisa el disco;
  si baja de `MINFREE` (8 GB) espera hasta 40 min y luego se detiene. Los tramos que ya existen se saltan
  (`--forzar` para rehacer; hazlo siempre que cambie el blocking, los planos o el set: un tramo viejo se mezclaría con el nuevo). Cada tramo es un proceso nuevo: todo lo aleatorio está sembrado (no hay saltos entre tramos).
- Referencia de tiempos (M-series, café de prueba): 360 px / 4 muestras ≈ 0.2 s por cuadro. El final a 1080/40 es
  mucho más lento: mide el primer tramo y estima antes de lanzar 70 s completos.
- `render.py` corre `mix.py` antes y `assemble.py` después (subtítulos PNG + mezcla). En macOS `engine/render.sh`
  hace lo mismo (`VER`, `STEP`, `MINFREE`, `FORCE=1`).
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
  SFX: `sfx_gen.py <dir> <nombre> "descripción en inglés" --seg 1` (ElevenLabs Sound Effects), tus propios `.wav` en
  `audio/sfx/`, o el banco de EditorBrain (`editorbrain sfx search … --query`, `sfx_fetch.py <id> <nombre> <dir>`,
  verifica SHA-256 y no guarda URLs firmadas). Sintetizados: `synth:puerta`, `impresora`, `caja_registradora`, `papel`, `golpe`, `ding`, `cajon`.
  `corta_en` deja silencio limpio antes de un susurro o remate. `build/eventos.json` lista saltos y apariciones
  para colocar pops y whooshes. **Sin silbido ni twang de western en el duelo** (no funcionó en «A escondidas»).

## Sets y sus parámetros (`look.json → set_params`)

- **office_night** (la oficina de «A escondidas»): `diapositiva` (2 renglones), `diapositiva_por`, `taza`,
  `placas` (`{"cubiculo_2": "DIRECTORA"}`: placa en el escritorio), `chat` (`{"prompt": "hazla bien", "saludo": "…"}`:
  un chat en el monitor que se escribe letra por letra con el prop `tecleo`). Anclajes extra: `cubiculo_N_escritorio`
  (mascota sobre el escritorio de cada cubículo).
- **sala_juntas** (capacitación con proyector, atril y dos filas): `titulo1`/`titulo2`/`por` (portada), `s1_titulo`/
  `s1_sub` (diapositiva 1), `empresa` (placa del atril), `hora: "noche"` (ciudad de noche, techo con prop `luces`,
  pasillo cálido detrás de la puerta; usa `"luz": "noche"`), `luz_techo` (W), `mesita_vacia`, `caja_juguete`
  (`{"pos", "cerrada", "color", "banda", "letras", "arriba", "abajo", "letrita"}`: caja de juguete con ventana o
  cerrada con tapa que vuela). Anclajes: `atril`, `atril_dentro`/`atril_asoma`/`atril_arriba`, `mesita`, `pasillo`,
  `entrando`, `puerta`, `caja_dentro`/`caja_borde`/`caja_frente`, `silla_junto_lucia`.
- **cafe**. Looks: `noche`, `dia`, `atardecer` (sala_juntas con sol bajo por el ventanal).

## Varias escenas, flashbacks y risas

- **Un proyecto por set.** Si la historia cambia de lugar («Esa noche…»), haz otro proyecto y únelos:
  `python3 $SK/scripts/unir.py final.mp4 escena1.mp4 escena2.mp4 --letrero "Esa noche…"` (el letrero va sobre los
  primeros 2 s de la escena que sigue: dale `"entrada": 1.8` en su look.json para que no tape el primer subtítulo).
- **Flashback** (un recuerdo en otro set): en la escena deja la pausa y la línea en off; renderiza el recuerdo como
  proyecto aparte y mételo con `python3 $SK/scripts/flashback.py escena.mp4 recuerdo.mp4 <t_entra> <t_sale> salida.mp4`
  (look cálido desaturado, viñeta, grano y destello; instrucciones de tiempos en el encabezado del script).
- **Risas encimadas**: líneas `"[laughs hard] ¡Jajajaja!"` con pausa negativa (`-0.9`) se mezclan una encima de otra;
  `subs.py` no les pone subtítulo. Combínalas con la acción `risa` de cada mascota.
- **Suspenso**: silencio de 3 s después de la línea, prop que tiembla/brilla (`caja`, `caja_luz`), todos con
  `mira_a` al objeto y ojos `wide`, cámara con `push` 0.8 y `dutch`, SFX de anticipación y un impacto al revelar.

## Revisión (antes de mandar cualquier cosa al usuario)

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
