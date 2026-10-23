# Puesta en escena: `blocking.json`

Toda la actuación es data anclada al guion, no Python. Si el TTS cambia, los tiempos se mueven solos.

## Referencias de tiempo

`"inicio"`, `"fin"`, `"L3"` (inicio de la línea 3), `"L3.end"`, `"L3.mid"`, `"L3:palabra"` (inicio de la primera
palabra que empieza con «palabra», sin acentos ni mayúsculas), `"L3:palabra#2"` (segunda vez), `"L3:palabra.end"`,
con desplazamiento: `"L3-0.2"`, `"L12:presentación+0.1"`, o segundos (`4.5`). Las palabras salen de AssemblyAI;
si no oyó una («Uf»), se interpola por letras dentro de la línea.

## Estructura

```json
{
 "personajes": {
  "SANTI": {
   "lugar":      [["inicio", "principal"]],
   "mira_a":     [["inicio", "auto"], ["L18", "JEFE"], ["L20.end", "abajo"]],
   "expresion":  [["inicio", "nervioso"], ["L3", "alivio"], ["L7", "susto", 0.15]],
   "gestos":     [["inicio", "regazo"], ["L1.end", "abraza_mascota"], ["L7", "arriba", 0.18]],
   "acciones":   [["L3", "suspiro"], ["L7", "sobresalto"]],
   "inclinacion": [["inicio", 14], ["L7", 4, "out"]],
   "giro":       [["L18", -165]],
   "oculto":     [["inicio", false]]
  },
  "CLAWD": {
   "lugar":     [["inicio", "bajo_escritorio"], ["L1-0.2", "asomado"], ["L1.end", "SANTI.regazo"], ["L8", "escritorio", 0.5]],
   "mira_a":    [["inicio", "auto"]],
   "expresion": [["inicio", "normal"], ["L2", "calm"], ["L6", "happy"]],
   "brazos":    [["inicio", "abajo"], ["L12", "senala"]],
   "acciones":  [["L18", "asoma_ojo", 1.5]],
   "orientacion": [["L20", 30]]
  },
  "CHATGPT": {"lugar": [["inicio", "JEFE.hombro_izq"]], "recibo": [["L22", 0.0], ["L22.end", 0.38, "lin"], ["L25", 1.05, "in"]],
              "acciones": [["L20", "susurra", 1.5]]},
  "GEMINI": {"lugar": [["inicio", "MARIANA.hombro_izq"]], "aparece": "L28-0.5"}
 },
 "props": {"puerta": [["inicio", -72], ["L18-0.3", -118, "out"]], "cajon": [["L18", 0.18, "out"], ["L18+0.5", 0.02]],
           "pata": [["L18+0.6", 1, "step"]], "diapositiva": [["L12:presentación", 1, "step"]]},
 "gestos_custom": {}
}
```
Cada pista: `[tiempo, valor, (transición en s | "ease" | "lin" | "in" | "out" | "back" | "step")]`.

## Pistas

- **lugar**: asiento o anclaje del set, o `PERSONAJE.anclaje`. Humanos de pie caminan (0.9 m/s) y voltean hacia
  donde van. Mascotas saltan en arco (más alto si suben) o trotan si es plano; aplastan y estiran al despegar y
  aterrizar. El tercer valor fija la duración del viaje. Si una mascota salta al cuerpo de alguien, ese humano se
  echa para atrás para hacerle espacio. Anclajes con `sigue` (el cajón) se mueven con su prop.
- **mira_a**: `auto` (default: mira al que habla; si habla él, a su interlocutor), un personaje, `PERSONAJE.anclaje`,
  un anclaje o probe del set, `frente`, `abajo`, `arriba`, `izquierda`, `derecha`. Cabeza hasta ±65° y 28° de
  inclinación; el resto lo hacen los ojos (los ojos se adelantan a la cabeza). Sentados giran el torso si hace falta.
- **expresion**: `neutral`, `calma`, `nervioso`, `alivio`, `feliz`, `sonrisa_nerviosa`, `sorpresa`, `susto`,
  `triste`, `culpable`, `enojado`, `sospecha`, `presumido`, `determinado`, `tierno`, `serio`. Las mismas palabras
  sirven para mascotas (se traducen a sus ojos); a las mascotas también les sirven `normal`, `calm`, `happy`,
  `wide`, `sad`, `determined`, `suspicious`. Sudor automático en `susto`, `culpable`, `sonrisa_nerviosa`.
- **gestos** (humanos): `regazo`, `abraza_mascota`, `susurro`, `arriba`, `mejillas`, `pecho`, `palmas`, `nuca`,
  `rasca_nuca`, `descansa`, `colgando`, `senala`, `senala_izq`, `taza`, `sorbo`, `jarras`, `mostrador`, o uno de
  `gestos_custom`. Lado `None` = esa mano se queda como estaba. Los gestos que tocan la cabeza pasan por un punto
  de paso afuera para no atravesarla. Sentado y parado cambian los gestos base (`regazo` ↔ `colgando`).
- **brazos** (mascotas): `abajo`, `arriba`, `senala`, `senala_izq`, `jarras`, `abrazo`, `manos_juntas`, `encoge`,
  `tapa_boca`. Al hablar los brazos se mueven solos.
- **acciones** (aditivas, con duración opcional): humanos `asiente`, `niega`, `sobresalto`, `suspiro`, `risa`,
  `encoge`; mascotas `salta`, `asoma_ojo`, `saluda`, `tiembla`, `susurra`.
- **inclinacion**, **giro**: inclinación del torso (grados adelante) y giro del cuerpo/silla (grados).
- **oculto** / **aparece**: esconder o hacer aparecer con «pop».
- **orientacion** (mascotas): fija su yaw en grados o `host` (mira como su anfitrión); si no, mira a su objetivo.
- **recibo** (ChatGPT): metros desenrollados.
- **props** del set: valor por cuadro (office_night: `puerta` grados, `cajon` metros, `pata` 0/1, `diapositiva` 0/1).

## Gestos propios sin choques

Si `--check` reporta `mano-cabeza`, busca una pose que no atraviese la cabeza con varias posiciones de cabeza:
```bash
$B -b -P $SK/scripts/pose_search.py -- --project <dir> --quien CHEF --lado L --zona boca --guardar susurro_chef
```
Zonas: `nuca`, `mejilla`, `boca`, `pecho`. Queda en `gestos_custom` y se usa como cualquier gesto. Si no hay
solución, prueba la otra mano (un objeto en la mano —la cuchara del chef— choca con la cara).

## Lo que hizo «A escondidas» (referencia)

Clawd cambió de escondite con la historia: bajo el escritorio → asomado → regazo → escritorio tras el teclado →
junto a la pantalla («De mí») → junto a la taza (Mariana) → cajón con una pata afuera (entra el jefe) → asoma un
ojo en el duelo → asoma ojos y boca para pelear con ChatGPT. Santi giró la silla −165° hacia el jefe. ChatGPT en el
hombro izquierdo del jefe, inclinándose para susurrarle. El código original de esa actuación (hecha a mano) está en
`assets/ejemplo-a-escondidas/perf.py` como referencia de timing fino.
