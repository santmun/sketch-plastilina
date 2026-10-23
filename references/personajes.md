# Personajes: `cast.json`

```json
{"personajes": {"SANTI": {...}, "CLAWD": {...}}}
```
El nombre (MAYÚSCULAS) es el mismo en `guion.json`, `blocking.json` y `shots.json`. Claves que empiezan con `_`
se ignoran (notas). Antes de animar, renderiza retratos y pide aprobación:
`$B -b -P $SK/engine/scene.py -- --project <dir> --retratos [--res 720] [--cuerpo] [--yaw 20]`.

## Humano (`"tipo": "humano"`)

| Campo | Valores | Notas |
|---|---|---|
| `voz` | voice ID | ver casting.md |
| `postura` | `sentado` \| `parado` | sentado: piernas fijas y silla del asiento (gira con él). Parado: camina entre anclajes |
| `lugar` | asiento o anclaje del set | lugar inicial si `blocking.json` no trae `lugar` |
| `escala` | 1.0 | tamaño uniforme (Santi = 1.0) |
| `complexion` | `delgado` \| `medio` \| `robusto` \| 0-1 | delgado = Santi; robusto = el Jefe (hombros anchos, pecho de barril, manos grandes) |
| `cara.preset` | `A` \| `B` \| `C` \| `cuadrada` \| `redonda` | **A = la aprobada** (facetas grandes); cuadrada = Jefe; redonda = óvalo amable; C = lisa |
| `cara.nariz` | factor | A usa 0.88 por default (la nariz −12 % aprobada) |
| `cara.ojos_tam`, `ojos_color`, `cejas` (`delgadas`/`gruesas`), `cejas_color`, `boca_ancho`, `orejas`, `tam` | | ajustes finos |
| `piel` | hex | Santi `#D4956C`; Jefe `#D29C80`. Piel con luminancia > 0.72 se quema |
| `labios` | hex | por default, la piel oscurecida |
| `pelo` | `{"estilo": ..., "color": ...}` | `copete` (Santi), `atras` (Jefe), `corto`, `chongo`, `coleta`, `bob`, `rizado`, `calvo`, `ninguno` |
| `ropa.estilo` | `camiseta` \| `manga_larga` \| `sueter` \| `saco` \| `chef` | saco = solapas, cuello, botones; chef = filipina con doble botonadura |
| `ropa.torso`, `piernas`, `zapatos`, `camisa`, `botones` | hex | **ropa con luminancia > 0.80 se quema a blanco** (el motor avisa) |
| `accesorios` | lista | `gafete`, `corbata`, `delantal`, `gorro_chef`, `lentes`, `bigote`, `barba`, `lunares` |
| `corbata_color`, `gafete_color`, `delantal_color`, `gorro_color`, `lentes_color`, `bigote_tam` | | |
| `mano_der` / `mano_izq` | `taza` \| `taza_jefe` \| `cuchara` \| `telefono` | objeto pegado a la mano |
| `boca_ganancia` | 1.0 | cuánto abre la boca con su voz (Mariana usó 0.9) |

Santi (aprobado):
```json
"SANTI": {"tipo": "humano", "voz": "qGrxMQgsw74f3cWR4I0K", "postura": "sentado", "lugar": "principal",
  "cara": {"preset": "A", "nariz": 0.88, "ojos_color": "#4A2A18"}, "piel": "#D4956C",
  "pelo": {"estilo": "copete", "color": "#1A1511"},
  "ropa": {"estilo": "camiseta", "torso": "#D6C7A8", "piernas": "#3C4250", "zapatos": "#ECE5D8"},
  "accesorios": ["gafete", "lunares"]}
```
Jefe (aprox. al de v3): `"postura": "parado", "complexion": "robusto", "cara": {"preset": "cuadrada"}, "piel": "#D29C80",
"pelo": {"estilo": "atras", "color": "#B9B4AB"}, "ropa": {"estilo": "saco", "torso": "#262830", "piernas": "#262830",
"zapatos": "#1E1714"}, "accesorios": ["corbata", "bigote", "barba"], "mano_der": "taza_jefe"`.

## Mascotas de IA

| `tipo` | Campos | Notas |
|---|---|---|
| `clawd` | `alto` (1.225), `u` (0.026), `color` (`#D6572D`) | silueta exacta del ref, ojos con 7 expresiones, boca voxel. **22.5 % más alto que el ref** |
| `chatgpt` | `tamano` (0.11), `recibo` (bool), `recibo_textura` (`build/recibo.png`), `recibo_largo` (1.05) | nudo negro, ojos de canica, sonrisa presumida; el recibo se desenrolla con `blocking.personajes.CHATGPT.recibo` |
| `gemini` | `tamano` (0.11) | destello de 4 puntas con degradado azul-violeta |
| `mascota` | `forma`, `tamano`, `color`, `color2`, `brillo`, `ojos` (`canica`/`pixel`), `ojos_tam`, `ojos_sep`, `boca_z`, `boca_color`, `brazos`, `patas` | genérica: `pan`, `blob`, `fantasma`, `gota`, `bot`, `caja`, `ballena`, `estrella`, `gemini` |

Todas: `voz`, `escala`. Todas tienen boca que abre con su voz, parpadeo y expresiones
(`normal`, `calm`, `happy`, `wide`, `sad`, `determined`, `suspicious`), y su luz clave + contraluz propias.
Una IA de marca nueva (Copilot, Grok…) se hace como `mascota` con su forma y colores, o como clase nueva en
`engine/characters/mascots.py` si necesita su logo real (contorno como `assets/chatgpt-knot.json`). Cada marca usa
su propio logo, no el de otra.

## Anclajes de personaje (para `lugar`, `mira_a` y cámaras)

Humanos: `hombro_izq`, `hombro_der`, `regazo`, `cara`, `boca`, `ojos`, `cabeza`, `coronilla`, `pecho`,
`mano_izq`, `mano_der`, `pies`. Mascotas: `ojos`, `ojo_izq`, `ojo_der`, `centro`, `pies`.
Se escriben `PERSONAJE.anclaje` (`"JEFE.hombro_izq"`, `"SANTI.regazo"`, `"CLAWD.ojo_izq"`).

## Reglas de diseño

- Caricatura de plastilina, no realismo: cabeza grande, rasgos simples, huellas y grumos en el material.
- Cada personaje se distingue en silueta (pelo, complexión, accesorio) antes que en color.
- Ropa y piel en tonos medios: la luz de noche es cálida y fuerte; los blancos puros se queman.
- Bigote siempre arriba de la boca; lentes que no tapen los ojos; el gorro abraza la cabeza.
- Mascota sobre una persona: va en un anclaje (`hombro_izq`, `regazo`) y el motor la levanta 2 cm; nunca debe
  hundirse en el cuerpo (`--check` lo vigila). Quien la carga se echa hacia atrás cuando salta a su regazo.
- Variedad de elenco (edad, género, tono de piel); no repetir el mismo tipo latino para todos.
- Personajes reales de marca o personas públicas: solo con su imagen auténtica o caricatura respetuosa, nunca
  fingiendo ser ellos.
