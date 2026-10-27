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
| `escala` | 1.0 | tamaño uniforme |
| `complexion` | `delgado` \| `medio` \| `robusto` \| 0-1 | robusto = hombros anchos, pecho de barril, manos grandes |
| `cara.preset` | `A` \| `B` \| `C` \| `cuadrada` \| `redonda` | A = facetas grandes (la de default); cuadrada = mandíbula ancha; redonda = óvalo amable; C = lisa |
| `cara.nariz` | factor | A usa 0.88 por default (la nariz −12 % aprobada) |
| `cara.ojos_tam`, `ojos_color`, `cejas` (`delgadas`/`gruesas`), `cejas_color`, `boca_ancho`, `orejas`, `tam` | | ajustes finos |
| `piel` | hex | p. ej. `#D4956C`, `#C98E6A`, `#8D5A3B`. Piel con luminancia > 0.72 se quema |
| `labios` | hex | por default, la piel oscurecida |
| `pelo` | `{"estilo": ..., "color": ...}` | `copete`, `atras` (peinado hacia atrás), `corto`, `chongo`, `coleta`, `bob` (melena a la quijada con fleco de lado; deja la cara libre), `rizado`, `calvo`, `ninguno` |
| `ropa.estilo` | `camiseta` \| `manga_larga` \| `sueter` \| `saco` \| `chef` | saco = solapas, cuello, botones; chef = filipina con doble botonadura |
| `ropa.torso`, `piernas`, `zapatos`, `camisa`, `botones` | hex | **ropa con luminancia > 0.80 se quema a blanco** (el motor avisa) |
| `accesorios` | lista | `gafete`, `corbata`, `delantal`, `gorro_chef`, `lentes`, `bigote`, `barba`, `lunares` |
| `corbata_color`, `gafete_color`, `delantal_color`, `gorro_color`, `lentes_color`, `bigote_tam` | | |
| `mano_der` / `mano_izq` | `taza` \| `taza_jefe` \| `cuchara` \| `telefono` | objeto en la mano; `blocking` → `objeto_der`/`objeto_izq` (0/1) lo saca o lo guarda |
| `voz_db` | 0 | sube o baja esa voz en la mezcla (dB) |
| `boca_ganancia` | 1.0 | cuánto abre la boca con su voz (0.9 = un poco menos) |

Ejemplo neutro:
```json
"PROTA": {"tipo": "humano", "voz": "", "postura": "sentado", "lugar": "principal",
  "cara": {"preset": "A", "nariz": 0.9, "ojos_color": "#3A2414"}, "piel": "#C98E6A",
  "pelo": {"estilo": "corto", "color": "#2B211B"},
  "ropa": {"estilo": "sueter", "torso": "#6F8A9B", "piernas": "#3C4250", "zapatos": "#E4DCCC"},
  "accesorios": ["gafete"]}
```
Un jefe de pie: `"postura": "parado", "complexion": "robusto", "cara": {"preset": "cuadrada"}, "pelo": {"estilo": "atras"},
"ropa": {"estilo": "saco", ...}, "accesorios": ["corbata", "bigote"]`.

## Avatares: el usuario, alguien neutro, una mascota o un producto

- **El propio usuario**: pídele 1-2 fotos de frente y modela su versión de plastilina: tono de piel, forma de cara
  (`cara.preset`, `nariz`, `ojos_color`, `cejas`), pelo (estilo y color), ropa y accesorios que lo identifiquen
  (lentes, barba, lunares). Itera con `--retratos` hasta que diga «sí soy yo». No copies rasgos de otra persona.
- **Personaje neutro**: rasgos y ropa inventados; varía edad, género y tono de piel en el elenco.
- **Mascota**: `"tipo": "mascota"` con `forma` (`blob`, `pan`, `gota`, `fantasma`, `bot`, `caja`, `ballena`,
  `estrella`) y sus colores. Para la mascota de una marca, sus colores exactos.
- **Producto que habla**: empieza con una mascota genérica de forma parecida (`caja` para un empaque, `gota` para una
  botella o un frasco, `bot` para un aparato) y sus colores. Si el chiste depende de su forma o logo exactos, crea una
  clase nueva en `engine/characters/mascots.py` (copia el patrón de `DeepSeekBallena` o `NuevoModelo`: cuerpo, ojos,
  boca que abre con la voz, brazos opcionales) y regístrala en `build()`. Usa siempre su logo y forma reales.
- **IA de marca**: hay clases listas (abajo). Una nueva sigue el mismo patrón, con su propio logo.

## Mascotas de IA

| `tipo` | Campos | Notas |
|---|---|---|
| `clawd` | `alto` (1.225), `u` (0.026), `color` (`#D6572D`) | silueta exacta del ref, ojos con 7 expresiones, boca voxel. **22.5 % más alto que el ref** |
| `chatgpt` | `tamano` (0.11), `recibo` (bool), `recibo_textura` (`build/recibo.png`), `recibo_largo` (1.05) | nudo negro, ojos de canica, sonrisa presumida; el recibo se desenrolla con `blocking.personajes.CHATGPT.recibo` |
| `gemini` | `tamano` (0.11) | destello de 4 puntas con degradado azul-violeta |
| `metaai` | `tamano` (0.1), `brillo` | anillo de Meta AI con degradado azul → violeta → rosa que flota; ojos de canica dentro del hueco |
| `muse` | `tamano` | agente de Meta (sept. 2026) |
| `grok` | `tamano` (0.1-0.17), `color` | esfera negra con las dos píldoras blancas del logo de Grok Bot; boca solo al hablar |
| `deepseek` | `tamano` (0.15), `color` (`#4D6BFE`) | ballenita azul del logo de DeepSeek: panza clara, cola enroscada sobre la cabeza, aletas como brazos |
| `nuevo` / `agi` | `tamano` (0.14), `letras` (`AGI`), `color`, `placa` | robotito de juguete genérico (sin marca): visor negro, placa en el pecho, antena |
| `mascota` | `forma`, `tamano`, `color`, `color2`, `brillo`, `ojos` (`canica`/`pixel`), `ojos_tam`, `ojos_sep`, `boca_z`, `boca_color`, `brazos`, `patas` | genérica: `pan`, `blob`, `fantasma`, `gota`, `bot`, `caja`, `ballena`, `estrella`, `gemini` |

Todas: `voz`, `escala`. Todas tienen boca que abre con su voz, parpadeo y expresiones
(`normal`, `calm`, `happy`, `wide`, `sad`, `determined`, `suspicious`), y su luz clave + contraluz propias.
Una IA de marca nueva (Copilot, Grok…) se hace como `mascota` con su forma y colores, o como clase nueva en
`engine/characters/mascots.py` si necesita su logo real (contorno como `assets/chatgpt-knot.json`). Cada marca usa
su propio logo, no el de otra.

## Anclajes de personaje (para `lugar`, `mira_a` y cámaras)

Humanos: `hombro_izq`, `hombro_der`, `hombro_izq_ext`, `hombro_der_ext` (más afuera, para que la mascota no choque
con la cabeza al voltear), `regazo`, `cara`, `boca`, `ojos`, `cabeza`, `coronilla`, `pecho`, `mano_izq`, `mano_der`, `pies`. Mascotas: `ojos`, `ojo_izq`, `ojo_der`, `centro`, `pies`.
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
